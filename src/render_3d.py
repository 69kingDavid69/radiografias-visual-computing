"""Herramienta 2: reconstrucción 3D por umbral de densidad."""
import time

import numpy as np
import pyvista as pv
from scipy import ndimage

from src.densidades import (EN_ARCADA, EXPERIMENTALES, UMBRAL_FRACTURA, UMBRAL_TEJIDO, color_para,
                            escala_de, presets_para, suavizado_para)
from src.orientacion import OPUESTA, texto
from src.region import arcada_dental, hueso_del_paciente, piezas_con_esmalte
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
                         rango_z=None, pulido=0, conservar=None):
    """Superficie de la estructura cuya densidad está entre `minimo` y `maximo`.

    Sin `maximo` (None o infinito) es la isosuperficie de siempre: todo lo que supera `minimo`.
    Con `maximo` se aísla la banda (por ejemplo, el esmalte sin el metal de los
    brackets). Una isosuperficie en `maximo` no sirve para eso, porque queda
    encerrada dentro de la de `minimo`. Se usa el campo continuo
    min(densidad − mínimo, máximo − densidad), positivo dentro de la banda, y marching
    cubes dibuja su cero. A diferencia de una máscara 0/1, el campo conserva los valores
    intermedios y la superficie se interpola entre vóxeles: no sale escalonada.

    `conservar` = máscara booleana (del tamaño de la franja `rango_z`) de lo que se
    dibuja; el resto se lleva al mínimo. Se dilata 2 vóxeles para no recortar el borde
    que marching cubes necesita para interpolar.

    `suavizado_mm` aplica un gaussiano (sigma en mm) a la densidad antes de marching
    cubes. `pulido` = iteraciones de suavizado Taubin sobre la malla (encoge ~1 %, a
    diferencia del Laplaciano); sirve para el tejido blando, que es ruidoso.

    `rango_z` = (z0, z1) limita la superficie a esa franja de capas (p. ej. la arcada
    dental de src/region.py), para separar lo que la densidad sola no separa.
    """
    z0 = 0
    if rango_z is not None:
        z0, z1 = rango_z
        volumen = volumen[z0:z1]
    if conservar is not None:
        volumen = np.where(ndimage.binary_dilation(conservar, iterations=2), volumen, volumen.min())
    # Primero se reduce y después se suaviza: es 8 veces menos trabajo con reduccion=2.
    v = volumen[::reduccion, ::reduccion, ::reduccion]
    esp = tuple(s * reduccion for s in espaciado)
    v = suavizar(v, esp, suavizado_mm)
    if maximo is None or np.isinf(maximo):
        campo, nivel = v, minimo
    else:
        campo, nivel = np.minimum(v - minimo, maximo - v).astype(np.float32), 0.0
    # a_pyvista nombra el campo "densidad"; con máximo contiene la distancia a la banda.
    # flying_edges: la misma superficie que marching cubes, multihilo y 4–5 veces más rápida.
    superficie = a_pyvista(campo, esp, 1, origen_z_mm=z0 * espaciado[0]).contour([nivel], scalars="densidad",
                                                                             method="flying_edges")
    if pulido and superficie.n_points:
        superficie = superficie.smooth_taubin(n_iter=pulido, pass_band=0.05)
    return superficie


# Interior de los dientes (pulpa y conductos) al cortar con el plano: el mismo rojo de la página.
COLOR_INTERIOR = "#d94a3d"

# El metal brilla como metal: reflejo especular más fuerte y concentrado.
ACABADO_METAL = {"specular": 1.0, "specular_power": 60}

# Vista de implante: hueso casi transparente para ver el metal dentro de él (idea de David).
CAPAS_IMPLANTE = [("hueso", 0.2), ("metal", 1.0)]

# Vista experimental de tejidos blandos: siempre con corte sagital, para ver el interior
# y nunca la cara (la grasa está justo bajo la piel). Ver densidades.EXPERIMENTALES.
CAPAS_BLANDAS = [("grasa", 0.35), ("musculo", 1.0), ("hueso", 1.0)]
PULIDO_BLANDOS = 20     # iteraciones de Taubin para el tejido blando (ruidoso en CBCT)

# Nivel de detalle automático: la malla se calcula sobre una rejilla de a lo sumo ~8 M de
# vóxeles. El Post (43 M) queda en reducción 2, como siempre; un CBCT de cabeza completa de
# 400×512×512 (105 M) pasa a 3. Sin esto "blandos" llegaba a 5,9 M triángulos y 4,3 s.
VOXELES_MAX_3D = 8_000_000

# La vista de fractura va a resolución completa: una línea de fractura mide 1–2 vóxeles y
# al reducir desaparece. Solo se reduce si el volumen pasa de ~130 M de vóxeles (en un
# Mac de 8 GB la etiquetación y la malla ya no caben).
VOXELES_MAX_FRACTURA = 130_000_000

# Radio y sesgo (mm) de la oclusión ambiental: una fractura mide ~1 mm de ancho.
RADIO_RELIEVE_MM = 2.0
SESGO_RELIEVE_MM = 0.2

# Cubo de orientación de la vista 3D: la cara anterior (el frente del paciente) en turquesa.
COLOR_CARA_ANTERIOR = (0.27, 0.76, 0.85)
COLOR_CARA = (0.17, 0.22, 0.30)
COLOR_TEXTO_CARA = (0.91, 0.93, 0.96)


def reduccion_para(forma, minima=2, maximo_voxeles=VOXELES_MAX_3D):
    """Menor reducción (≥ `minima`) que deja la rejilla 3D por debajo de `maximo_voxeles`."""
    reduccion = max(1, int(minima))
    while np.prod(forma) / reduccion ** 3 > maximo_voxeles:
        reduccion += 1
    return reduccion


class Render3D:
    """Motor de renderizado 3D para tomografías dentales CBCT.

    Implementa el contrato para que la interfaz gráfica (QtInteractor o Plotter)
    pueda controlar la visualización, el umbral de densidad y los presets.

    Además de la estructura, guarda tres opciones de visualización que se aplican a
    todo lo que se dibuja (preguntas 2, 4 y 5 de la propuesta):
      - `phong`: sombreado Phong (normales interpoladas) o plano (una normal por triángulo);
      - `suavizar_malla`: suavizado Taubin de la malla, que no la encoge;
      - plano de corte interactivo (`activar_corte`), que pinta el interior en rojo.
    Y mide cada cálculo en `ultima_medicion` (triángulos y milisegundos, pregunta 3).
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
        self._ultima_accion = None   # para redibujar igual al cambiar una opción

        # Opciones de visualización
        self.phong = True
        self.suavizar_malla = False
        self.relieve = False         # oclusión ambiental (SSAO): oscurece grietas y huecos
        self.orientacion = None      # "LPS", "RAS"… del estudio; None si no se conoce
        self.escala = None
        self._marcador = None        # widget del cubo de orientación
        self._plano_corte = None     # vtkPlane mientras el plano de corte está activo
        self.ultima_medicion = {"triangulos": 0, "ms": 0.0}

    def mostrar(self, estudio, reduccion: int = 2):
        """Prepara el volumen con la reducción óptima (reduccion=2) y dibuja el modelo inicial."""
        # Soporta tanto un objeto Estudio (con atributos) como una tupla (volumen, espaciado).
        # Solo un Estudio trae su escala de densidad; con una tupla no hay presets.
        if hasattr(estudio, "volumen"):
            self.volumen, self.espaciado = estudio.volumen, estudio.espaciado
            self.presets = presets_para(estudio)
            self.escala = escala_de(estudio)
            self.orientacion = estudio.metadatos.get("orientacion")
        else:
            self.volumen, self.espaciado = estudio
            self.presets = {}
            self.escala = self.orientacion = None
        self._poner_marcador()
        self.reduccion = reduccion_para(self.volumen.shape, reduccion)
        # La arcada se ubica por el esmalte; sin preset de esmalte no se limita nada.
        self.arcada = (arcada_dental(self.volumen, self.espaciado, self.presets["esmalte"][0])
                       if "esmalte" in self.presets else None)
        # Un estudio nuevo no hereda el plano de corte del anterior (sus medidas son otras).
        self.desactivar_corte()

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
        self._vista_frontal()
        self.pl.reset_camera()

    def set_umbral(self, valor: float):
        """Recalcula la isosuperficie (Marching Cubes) cuando se modifica el umbral."""
        if self.malla is None:
            return
        self._ultima_accion = ("umbral", float(valor))

        # Marching Cubes (flying edges: la misma superficie, 4–5 veces más rápido)
        t0 = time.perf_counter()
        superficie = self._acabar(self.malla.contour([valor], scalars="densidad", method="flying_edges"))
        self.preset_actual = None    # la barra libre deja de seguir un preset

        # Si no hay vóxeles en ese rango, eliminamos el actor visual previo
        self._limpiar()
        if superficie.n_points > 0:
            self._dibujar("estructura", superficie, color=self._color_para_umbral(valor))
        self.umbral_actual = valor
        self._medir(t0)

    def aplicar_preset(self, nombre: str):
        """Aísla una estructura con su rango de densidad (src/densidades.py).

        Usa superficie_por_banda: con máximo finito dibuja solo la banda (p. ej. el
        esmalte sin el metal) y suaviza con el sigma medido para esa estructura.
        """
        if nombre not in self.presets:
            disponibles = ", ".join(self.presets) or "ninguno (escala del estudio desconocida)"
            raise KeyError(f"Preset '{nombre}' no disponible. Disponibles: {disponibles}")
        self._ultima_accion = ("preset", nombre)

        t0 = time.perf_counter()
        minimo, maximo = self.presets[nombre]
        superficie = self._acabar(superficie_por_banda(self.volumen, self.espaciado, minimo, maximo,
                                                       reduccion=self.reduccion,
                                                       suavizado_mm=suavizado_para(nombre),
                                                       rango_z=self._rango_z(nombre),
                                                       conservar=self._piezas_dentales(nombre, minimo)))
        self._limpiar()
        if superficie.n_points > 0:
            self._dibujar("estructura", superficie, color=color_para(nombre), **self._acabado(nombre))
        self.umbral_actual = minimo
        self.preset_actual = nombre
        self._medir(t0)
        # Cada estructura tiene otro tamaño (los dientes son una franja): se reencuadra
        # de frente para que no quede pequeña ni fuera de vista.
        self._encuadrar_de_frente()

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
        self._ultima_accion = ("capas", list(capas), corte_sagital)

        t0 = time.perf_counter()
        self._limpiar()
        # El corte sagital se hace sobre el volumen (x < centro) y no sobre la malla: recortar
        # después una malla de ~1,7 M triángulos duplicaba la memoria y, con poca RAM libre,
        # VTK abortaba la aplicación entera.
        volumen = self.volumen[:, :, :(self.volumen.shape[2] + 1) // 2] if corte_sagital else self.volumen
        for nombre, opacidad in capas:
            minimo, maximo = self.presets[nombre]
            superficie = self._acabar(superficie_por_banda(volumen, self.espaciado, minimo, maximo,
                                                           reduccion=self.reduccion,
                                                           suavizado_mm=suavizado_para(nombre),
                                                           rango_z=self._rango_z(nombre),
                                                           pulido=PULIDO_BLANDOS if nombre in EXPERIMENTALES else 0))
            if superficie.n_points > 0:
                self._dibujar(f"capa_{nombre}", superficie, color=color_para(nombre),
                              opacity=opacidad, **self._acabado(nombre))
        self.preset_actual = "+".join(nombre for nombre, _ in capas)
        self._medir(t0)
        if corte_sagital:
            self.pl.view_yz()            # cámara en +x: mira la cara cortada, hacia el interior
            self.pl.reset_camera()
            self._vista_lateral = True
        else:
            self._encuadrar_de_frente()

    def aplicar_fractura(self):
        """Vista para buscar huesos rotos: resolución completa, sin suavizar y solo el hueso.

        Una línea de fractura mide 1–2 vóxeles; el gaussiano y la reducción de los otros
        presets la promedian con el hueso de al lado y la borran. Se quita lo que no es
        hueso del paciente (el soporte de cabeza o la camilla: placas delgadas fuera del
        cuerpo, ver `region.cuerpo`) pero se conservan todos los fragmentos de hueso, y se
        enciende el relieve para que las grietas se vean como rayas oscuras.
        """
        if "hueso" not in self.presets:
            raise KeyError("La vista de fractura necesita el preset 'hueso' (escala del estudio desconocida)")
        self._ultima_accion = ("fractura",)

        t0 = time.perf_counter()
        umbral = max(self.presets["hueso"][0], UMBRAL_FRACTURA.get(self.escala, 0))
        reduccion = reduccion_para(self.volumen.shape, 1, VOXELES_MAX_FRACTURA)
        superficie = self._acabar(superficie_por_banda(
            self.volumen, self.espaciado, umbral, None, reduccion=reduccion, suavizado_mm=0.0,
            conservar=hueso_del_paciente(self.volumen, umbral, self.espaciado, UMBRAL_TEJIDO[self.escala])))
        self._limpiar()
        if superficie.n_points > 0:
            self._dibujar("estructura", superficie, color=color_para("hueso"))
        self.umbral_actual = umbral
        self.preset_actual = "fractura"
        self.set_relieve(True)
        self._medir(t0)
        self._encuadrar_de_frente()

    # --- Opciones de visualización ---------------------------------------------

    def set_phong(self, activo: bool):
        """Sombreado Phong (normales interpoladas, luz por píxel) o plano (una normal por cara)."""
        self.phong = bool(activo)
        for nombre in self._actores:
            actor = self.pl.actors.get(nombre)
            if actor is not None:
                actor.prop.interpolation = "phong" if self.phong else "flat"

    def set_relieve(self, activo: bool):
        """Oclusión ambiental en espacio de pantalla (SSAO): oscurece lo que queda en hueco.

        Una fractura de 1 vóxel apenas cambia el brillo de la superficie; con el relieve el
        borde de la grieta proyecta sombra y se ve como una raya oscura. El radio es de 2 mm,
        del orden del ancho de una fractura.
        """
        self.relieve = bool(activo)
        if self.relieve:
            self.pl.enable_ssao(radius=RADIO_RELIEVE_MM, bias=SESGO_RELIEVE_MM, kernel_size=128, blur=True)
        else:
            self.pl.disable_ssao()
        self.pl.render()     # los pasos de renderizado del SSAO se arman en el primer cuadro

    def set_suavizar_malla(self, activo: bool):
        """Suavizado Taubin de la malla (no encoge, a diferencia del Laplaciano). Redibuja."""
        self.suavizar_malla = bool(activo)
        self._redibujar()

    def activar_corte(self, normal=None):
        """Plano de corte interactivo: oculta un lado y muestra el interior en rojo.

        Se arrastra con el ratón (widget de PyVista); se aplica a todo lo que se dibuje
        mientras esté activo, también al cambiar de estructura. Sin `normal`, el plano
        mira en la dirección de la cámara y pasa por el centro de lo dibujado: quita la
        mitad más cercana y deja ver el interior de frente.
        """
        import vtk
        if self._plano_corte is None:
            self._plano_corte = vtk.vtkPlane()
        limites = self._limites_dibujados()
        centro = tuple((limites[2 * i] + limites[2 * i + 1]) / 2 for i in range(3))
        if normal is None:
            vector = tuple(self.pl.camera.direction)
            # La arcada es una U: por el centro solo cortaría las muelas. El plano arranca
            # a un tercio de la profundidad desde el frente, donde están los incisivos.
            n = np.asarray(vector)
            tamano = np.array(limites[1::2]) - np.array(limites[0::2])
            profundidad = float(np.abs(n) @ tamano)
            centro = tuple(np.asarray(centro) - n * profundidad / 6)
        else:
            vector = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}.get(normal, normal)
        self._plano_corte.SetOrigin(*centro)
        self._plano_corte.SetNormal(*vector)

        def mover(nueva_normal, origen):
            self._plano_corte.SetNormal(*nueva_normal)
            self._plano_corte.SetOrigin(*origen)

        self.pl.clear_plane_widgets()
        self.pl.add_plane_widget(mover, normal=vector, origin=centro, bounds=limites, color="#94a3b8",
                                 interaction_event="always", outline_translation=False)
        for nombre in self._actores:
            self._aplicar_corte(self.pl.actors.get(nombre))

    def desactivar_corte(self):
        if self._plano_corte is None:
            return
        self.pl.clear_plane_widgets()
        for nombre in self._actores:
            actor = self.pl.actors.get(nombre)
            if actor is not None:
                actor.mapper.RemoveAllClippingPlanes()
        self._plano_corte = None

    @property
    def corte_activo(self) -> bool:
        return self._plano_corte is not None

    def captura(self, ruta: str):
        """Guarda una captura de pantalla del render 3D actual."""
        self.pl.screenshot(ruta)

    # --- Internos ----------------------------------------------------------------

    def _poner_marcador(self):
        """Cubo de orientación en la esquina: cada cara dice hacia dónde queda ese lado del paciente.

        Gira con la cámara, así que siempre se sabe cuál es la derecha del paciente, y no
        la de la pantalla. Sin orientación conocida (volumen sintético) no se dibuja.
        """
        self._quitar_marcador()
        if not self.orientacion:
            return
        import vtk
        cubo = vtk.vtkAnnotatedCubeActor()
        for eje, letra in zip(("X", "Y", "Z"), self.orientacion):
            for signo, letra_cara in (("Plus", letra), ("Minus", OPUESTA[letra])):
                getattr(cubo, f"Set{eje}{signo}FaceText")(texto(letra_cara))
                cara = getattr(cubo, f"Get{eje}{signo}FaceProperty")()
                # El texto de cada cara lleva el color de su propiedad; el cuerpo, el del cubo.
                cara.SetColor(*(COLOR_CARA_ANTERIOR if letra_cara == "A" else COLOR_TEXTO_CARA))
        cubo.GetCubeProperty().SetColor(*COLOR_CARA)
        cubo.GetTextEdgesProperty().SetColor(0.6, 0.67, 0.75)
        cubo.SetTextEdgesVisibility(True)
        cubo.SetFaceTextScale(0.26)
        self._marcador = self.pl.add_orientation_widget(cubo, interactive=False, viewport=(0.0, 0.0, 0.2, 0.3))

    def _quitar_marcador(self):
        if self._marcador is not None:
            self._marcador.EnabledOff()
            self._marcador = None

    def _limites_dibujados(self):
        """Caja (xmin, xmax, ymin, ymax, zmin, zmax) de lo que se ve, o del volumen si no hay nada."""
        cajas = [self.pl.actors[n].GetBounds() for n in self._actores if n in self.pl.actors]
        if not cajas:
            return self.malla.bounds if self.malla is not None else (-1, 1, -1, 1, -1, 1)
        cajas = np.array(cajas)
        return tuple(float(v) for par in zip(cajas[:, 0::2].min(axis=0), cajas[:, 1::2].max(axis=0)) for v in par)

    def _redibujar(self):
        accion = self._ultima_accion
        if accion is None:
            return
        if accion[0] == "umbral":
            self.set_umbral(accion[1])
        elif accion[0] == "preset":
            self.aplicar_preset(accion[1])
        elif accion[0] == "fractura":
            self.aplicar_fractura()
        else:
            self.aplicar_capas(accion[1], corte_sagital=accion[2])

    def _acabar(self, superficie):
        """Suavizado Taubin opcional (el gaussiano por estructura ya se aplicó al volumen)."""
        if self.suavizar_malla and superficie.n_points > 0:
            return superficie.smooth_taubin(n_iter=20, pass_band=0.1)
        return superficie

    def _medir(self, t0):
        triangulos = sum(self.pl.actors[n].mapper.dataset.n_cells for n in self._actores
                         if n in self.pl.actors and self.pl.actors[n].mapper.dataset is not None)
        self.ultima_medicion = {"triangulos": int(triangulos), "ms": (time.perf_counter() - t0) * 1000}

    def _encuadrar_de_frente(self):
        if self._vista_lateral:
            self._vista_frontal()
            self._vista_lateral = False
        self.pl.reset_camera()

    def _vista_frontal(self):
        """Cámara frente al paciente: del lado anterior, con z hacia arriba.

        Si el eje y crece hacia atrás (LPS, lo habitual) el frente está en y mínimo; en un
        estudio que lo guarda al revés (LAS, como los NIfTI de STS) hay que mirar desde el otro lado.
        """
        self.pl.view_xz(negative=bool(self.orientacion) and self.orientacion[1] == "A")

    def _piezas_dentales(self, nombre, umbral):
        """Para "dientes": solo las piezas conectadas que tienen esmalte (src/region.py)."""
        if nombre != "dientes" or self.arcada is None or "esmalte" not in self.presets:
            return None
        esmalte_min = self.presets["esmalte"][0]
        esmalte_max = self.presets.get("esmalte_sin_metal", (esmalte_min, np.inf))[1]
        metal = self.presets["metal"][0] if "metal" in self.presets else None
        z0, z1 = self.arcada
        return piezas_con_esmalte(self.volumen[z0:z1], umbral, esmalte_min, esmalte_max, metal=metal)

    def _color_para_umbral(self, valor):
        """Color del preset más denso cuyo mínimo no supera `valor` (marfil si no hay ninguno).

        Así la barra libre usa los mismos colores de tejido que los botones y la página.
        """
        candidatos = [(minimo, nombre) for nombre, (minimo, _) in self.presets.items()
                      if nombre not in EXPERIMENTALES and minimo <= valor]
        return color_para(max(candidatos)[1]) if candidatos else "ivory"

    def _rango_z(self, nombre):
        return self.arcada if nombre in EN_ARCADA else None

    @staticmethod
    def _acabado(nombre):
        return ACABADO_METAL if nombre == "metal" else {}

    def _aplicar_corte(self, actor):
        if actor is None or self._plano_corte is None:
            return
        actor.mapper.RemoveAllClippingPlanes()
        actor.mapper.AddClippingPlane(self._plano_corte)
        actor.backface_prop.color = COLOR_INTERIOR      # pulpa y conductos, vistos por dentro

    def _dibujar(self, nombre, superficie, **estilo):
        estilo = {"specular": 0.4, **estilo}
        actor = self.pl.add_mesh(superficie, name=nombre, smooth_shading=True, **estilo)
        actor.prop.interpolation = "phong" if self.phong else "flat"
        self._aplicar_corte(actor)
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
