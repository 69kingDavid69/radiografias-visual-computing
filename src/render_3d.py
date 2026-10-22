"""Herramienta 2: reconstrucción 3D por umbral de densidad."""
import numpy as np
import pyvista as pv

from src.densidades import EN_ARCADA, EXPERIMENTALES, color_para, presets_para, suavizado_para
from src.region import arcada_dental
from src.filtros import suavizar


def a_pyvista(volumen, espaciado, reduccion=1, origen_z_mm=0.0):
    """Convierte el volumen (z, y, x) en una malla regular de PyVista.

    `reduccion` toma uno de cada N vóxeles por eje: un CBCT de 512³ es pesado
    y con reduccion=2 el render es ~8 veces más liviano. `origen_z_mm` desplaza la
    malla en z cuando el volumen es solo una franja (la arcada), para que quede en su
    lugar respecto de las demás superficies.
    """
    v = volumen[::reduccion, ::reduccion, ::reduccion]
    malla = pv.ImageData(dimensions=v.shape[::-1],
                         spacing=tuple(s * reduccion for s in espaciado[::-1]),
                         origin=(0.0, 0.0, origen_z_mm))
    # VTK recorre x más rápido, igual que un ravel en orden C sobre (z, y, x).
    malla.point_data["densidad"] = v.ravel(order="C")
    return malla


def superficie_por_banda(volumen, espaciado, minimo, maximo=None, reduccion=2, suavizado_mm=0.0,
                         rango_z=None):
    """Superficie de la estructura cuya densidad está entre `minimo` y `maximo`.

    Sin `maximo` (None o infinito) es la isosuperficie de siempre: todo lo que supera `minimo`.
    Con `maximo` se aísla la banda (por ejemplo, el esmalte sin el metal de los
    brackets). Una isosuperficie en `maximo` no sirve para eso, porque queda
    encerrada dentro de la de `minimo`; en cambio se marca con 1 cada vóxel de la
    banda y con 0 el resto, y marching cubes dibuja la frontera en 0.5.

    `suavizado_mm` aplica un gaussiano (sigma en mm) antes de marching cubes: sobre la
    densidad si no hay máximo, sobre la máscara si lo hay.

    `rango_z` = (z0, z1) limita la superficie a esa franja de capas (p. ej. la arcada
    dental de src/region.py), para separar lo que la densidad sola no separa.
    """
    z0 = 0
    if rango_z is not None:
        z0, z1 = rango_z
        volumen = volumen[z0:z1]
    # Primero se reduce y después se suaviza: es 8 veces menos trabajo con reduccion=2.
    v = volumen[::reduccion, ::reduccion, ::reduccion]
    esp = tuple(s * reduccion for s in espaciado)
    if maximo is None or np.isinf(maximo):
        campo, nivel = suavizar(v, esp, suavizado_mm), minimo
    else:
        mascara = ((v >= minimo) & (v <= maximo)).astype(np.float32)
        campo, nivel = suavizar(mascara, esp, suavizado_mm), 0.5
    # a_pyvista nombra el campo "densidad"; con máximo contiene la máscara (0 a 1).
    return a_pyvista(campo, esp, 1, origen_z_mm=z0 * espaciado[0]).contour([nivel], scalars="densidad")


# El metal brilla como metal: reflejo especular más fuerte y concentrado.
ACABADO_METAL = {"specular": 1.0, "specular_power": 60}

# Vista de implante: hueso casi transparente para ver el metal dentro de él (idea de David).
CAPAS_IMPLANTE = [("hueso", 0.2), ("metal", 1.0)]

# Vista experimental de tejidos blandos: siempre con corte sagital, para ver el interior
# y nunca la cara (la grasa está justo bajo la piel). Ver densidades.EXPERIMENTALES.
CAPAS_BLANDAS = [("grasa", 0.35), ("musculo", 1.0), ("hueso", 1.0)]


class Render3D:
    """Motor de renderizado 3D para tomografías dentales CBCT.

    Implementa el contrato para que la interfaz gráfica (QtInteractor o Plotter)
    pueda controlar la visualización, el umbral de densidad y los presets.
    """

    def __init__(self, plotter: pv.Plotter):
        # Lienzo donde se dibuja la escena 3D (Plotter estándar o QtInteractor de la app)
        self.pl = plotter

        # Variables de estado interno para almacenar los datos procesados
        self.malla = None
        self.volumen = None
        self.espaciado = None
        self.umbral_actual = None
        self.reduccion = 2
        self.presets = {}            # presets que corresponden a la escala del estudio
        self.arcada = None           # (z0, z1) de la arcada dental, para los presets de dientes
        self._vista_lateral = False  # la vista de tejidos blandos gira la cámara de costado
        self.preset_actual = None
        self._actores = []           # nombres de los actores dibujados (para borrarlos al cambiar)

    def mostrar(self, estudio, reduccion: int = 2):
        """Prepara el volumen con la reducción óptima (reduccion=2) y dibuja el modelo inicial."""
        # Soporta tanto un objeto Estudio (con atributos) como una tupla (volumen, espaciado).
        # Solo un Estudio trae su escala de densidad; con una tupla no hay presets.
        if hasattr(estudio, "volumen"):
            self.volumen, self.espaciado = estudio.volumen, estudio.espaciado
            self.presets = presets_para(estudio)
        else:
            self.volumen, self.espaciado = estudio
            self.presets = {}
        self.reduccion = reduccion
        # La arcada se ubica por el esmalte; sin preset de esmalte no se limita nada.
        self.arcada = (arcada_dental(self.volumen, self.espaciado, self.presets["esmalte"][0])
                       if "esmalte" in self.presets else None)

        # Convierte el volumen NumPy a ImageData de PyVista aplicando la reducción por defecto
        self.malla = a_pyvista(self.volumen, self.espaciado, reduccion=reduccion)

        # Si se conoce la escala se arranca en el preset "hueso"; si no, umbral al 60 % del rango.
        # (Con datos normalizados el 60 % cae en ~2100, que ya es zona de metal.)
        if "hueso" in self.presets:
            self.aplicar_preset("hueso")
        else:
            minimo, maximo = float(np.min(self.volumen)), float(np.max(self.volumen))
            self.set_umbral(minimo + 0.6 * (maximo - minimo))

        # Vista frontal de la cara (en la muestra de Slicer es el plano XZ) y encuadre
        self.pl.view_xz()
        self.pl.reset_camera()

    def set_umbral(self, valor: float):
        """Recalcula la isosuperficie (Marching Cubes) cuando se modifica el umbral."""
        if self.malla is None:
            return

        # Marching Cubes extrae la superficie 3D en el valor de densidad indicado
        superficie = self.malla.contour([valor], scalars="densidad")
        self.preset_actual = None    # la barra libre deja de seguir un preset

        # Si no hay vóxeles en ese rango, eliminamos el actor visual previo
        if superficie.n_points == 0:
            self._limpiar()
            return

        # name="estructura" actualiza la superficie existente sin recargar toda la escena
        self._dibujar("estructura", superficie, color="ivory")
        self.umbral_actual = valor

    def aplicar_preset(self, nombre: str):
        """Aísla una estructura con su rango de densidad (src/densidades.py).

        Usa superficie_por_banda: con máximo finito dibuja solo la banda (p. ej. el
        esmalte sin el metal) y suaviza con el sigma medido para esa estructura.
        """
        if nombre not in self.presets:
            disponibles = ", ".join(self.presets) or "ninguno (escala del estudio desconocida)"
            raise KeyError(f"Preset '{nombre}' no disponible. Disponibles: {disponibles}")

        minimo, maximo = self.presets[nombre]
        superficie = superficie_por_banda(self.volumen, self.espaciado, minimo, maximo,
                                          reduccion=self.reduccion,
                                          suavizado_mm=suavizado_para(nombre),
                                          rango_z=self._rango_z(nombre))
        self._limpiar()
        self._volver_al_frente()
        if superficie.n_points > 0:
            self._dibujar("estructura", superficie, color=color_para(nombre), **self._acabado(nombre))
        self.umbral_actual = minimo
        self.preset_actual = nombre

    def aplicar_capas(self, capas=CAPAS_IMPLANTE, corte_sagital=False):
        """Dibuja varios presets a la vez, cada uno con su opacidad.

        `capas` es una lista de (nombre_preset, opacidad). Por defecto es la vista de
        implante: hueso al 20 % y metal sólido. `corte_sagital` deja media cabeza
        (x < centro, el corte por el plano medio) y la mira desde el lado del corte, es
        decir, el interior: nunca la cara de frente ni de perfil.
        """
        faltan = [nombre for nombre, _ in capas if nombre not in self.presets]
        if faltan:
            raise KeyError(f"Presets no disponibles para este estudio: {', '.join(faltan)}")

        self._limpiar()
        for nombre, opacidad in capas:
            minimo, maximo = self.presets[nombre]
            superficie = superficie_por_banda(self.volumen, self.espaciado, minimo, maximo,
                                              reduccion=self.reduccion,
                                              suavizado_mm=suavizado_para(nombre),
                                              rango_z=self._rango_z(nombre))
            if corte_sagital and superficie.n_points > 0:
                centro_x = self.volumen.shape[2] * self.espaciado[2] / 2
                superficie = superficie.clip(normal=(1, 0, 0), origin=(centro_x, 0, 0))
            if superficie.n_points > 0:
                self._dibujar(f"capa_{nombre}", superficie, color=color_para(nombre),
                              opacity=opacidad, **self._acabado(nombre))
        self.preset_actual = "+".join(nombre for nombre, _ in capas)
        if corte_sagital:
            self.pl.view_yz()            # cámara en +x: mira la cara cortada, hacia el interior
            self.pl.reset_camera()
            self._vista_lateral = True
        else:
            self._volver_al_frente()

    def captura(self, ruta: str):
        """Guarda una captura de pantalla del render 3D actual."""
        self.pl.screenshot(ruta)

    def _volver_al_frente(self):
        if self._vista_lateral:
            self.pl.view_xz()
            self.pl.reset_camera()
            self._vista_lateral = False

    def _rango_z(self, nombre):
        return self.arcada if nombre in EN_ARCADA else None

    @staticmethod
    def _acabado(nombre):
        return ACABADO_METAL if nombre == "metal" else {}

    def _dibujar(self, nombre, superficie, **estilo):
        estilo = {"specular": 0.4, **estilo}
        self.pl.add_mesh(superficie, name=nombre, smooth_shading=True, **estilo)
        if nombre not in self._actores:
            self._actores.append(nombre)

    def _limpiar(self):
        for nombre in self._actores:
            self.pl.remove_actor(nombre)
        self._actores = []


def explorar_3d(volumen, espaciado, umbral_inicial=None, reduccion=2, estudio=None):
    """Abre una ventana 3D interactiva utilizando la clase Render3D.

    Si se pasa `estudio`, las teclas 1–9 aplican sus presets e `i` la vista de implante.
    """
    pl = pv.Plotter()

    # Creamos la instancia del motor y mostramos el volumen
    render = Render3D(pl)
    render.mostrar(estudio if estudio is not None else (volumen, espaciado), reduccion=reduccion)

    # Teclas para los presets, en el orden de RANGOS_DENSIDAD
    ayuda = ["Barra: umbral libre"]
    normales = [n for n in render.presets if n not in EXPERIMENTALES]
    for tecla, nombre in zip("123456789", normales):
        pl.add_key_event(tecla, lambda nombre=nombre: render.aplicar_preset(nombre))
        ayuda.append(f"{tecla}: {nombre}")
    if all(nombre in render.presets for nombre, _ in CAPAS_IMPLANTE):
        pl.add_key_event("i", lambda: render.aplicar_capas())
        ayuda.append("i: vista de implante (hueso + metal)")
    if all(nombre in render.presets for nombre, _ in CAPAS_BLANDAS):
        pl.add_key_event("m", lambda: render.aplicar_capas(CAPAS_BLANDAS, corte_sagital=True))
        ayuda.append("m: tejido blando denso / graso (experimental, corte sagital)")
    pl.add_text("\n".join(ayuda), font_size=9)

    minimo, maximo = float(np.min(volumen)), float(np.max(volumen))
    if umbral_inicial is None:
        umbral_inicial = render.umbral_actual

    # El slider conecta directamente con el método set_umbral del motor 3D
    pl.add_slider_widget(render.set_umbral, rng=(minimo, maximo), value=umbral_inicial,
                         title="Umbral de densidad", fmt="%.0f", interaction_event="end")
    pl.show()
