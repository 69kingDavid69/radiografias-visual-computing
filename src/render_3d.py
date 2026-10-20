"""Herramienta 2: reconstrucción 3D por umbral de densidad."""
import numpy as np
import pyvista as pv


def a_pyvista(volumen, espaciado, reduccion=1):
    """Convierte el volumen (z, y, x) en una malla regular de PyVista.

    `reduccion` toma uno de cada N vóxeles por eje: un CBCT de 512³ es pesado
    y con reduccion=2 el render es ~8 veces más liviano.
    """
    v = volumen[::reduccion, ::reduccion, ::reduccion]
    malla = pv.ImageData(dimensions=v.shape[::-1],
                         spacing=tuple(s * reduccion for s in espaciado[::-1]))
    # VTK recorre x más rápido, igual que un ravel en orden C sobre (z, y, x).
    malla.point_data["densidad"] = v.ravel(order="C")
    return malla


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

    def mostrar(self, estudio, reduccion: int = 2):
        """Prepara el volumen con la reducción óptima (reduccion=2) y dibuja el modelo inicial."""
        # Soporta tanto un objeto Estudio (con atributos) como una tupla (volumen, espaciado)
        if hasattr(estudio, "volumen"):
            self.volumen, self.espaciado = estudio.volumen, estudio.espaciado
        else:
            self.volumen, self.espaciado = estudio

        # Convierte el volumen NumPy a ImageData de PyVista aplicando la reducción por defecto
        self.malla = a_pyvista(self.volumen, self.espaciado, reduccion=reduccion)

        # Umbral inicial al 60% del rango de densidades para aislar tejido denso/hueso
        minimo, maximo = float(np.min(self.volumen)), float(np.max(self.volumen))
        umbral_inicial = minimo + 0.6 * (maximo - minimo)

        # Dibuja la isosuperficie inicial y acomoda la cámara
        self.set_umbral(umbral_inicial)
        self.pl.reset_camera()

    def set_umbral(self, valor: float):
        """Recalcula la isosuperficie (Marching Cubes) cuando se modifica el umbral."""
        if self.malla is None:
            return

        # Marching Cubes extrae la superficie 3D en el valor de densidad indicado
        superficie = self.malla.contour([valor], scalars="densidad")

        # Si no hay vóxeles en ese rango, eliminamos el actor visual previo
        if superficie.n_points == 0:
            self.pl.remove_actor("estructura")
            return

        # name="estructura" actualiza la superficie existente sin recargar toda la escena
        self.pl.add_mesh(superficie, name="estructura", color="ivory",
                         smooth_shading=True, specular=0.4)
        self.umbral_actual = valor

    def aplicar_preset(self, nombre: str):
        """Aplica colores y umbrales por estructura (preparado para Fase 2)."""
        pass

    def captura(self, ruta: str):
        """Guarda una captura de pantalla del render 3D actual."""
        self.pl.screenshot(ruta)


def explorar_3d(volumen, espaciado, umbral_inicial=None, reduccion=2):
    """Abre una ventana 3D interactiva utilizando la clase Render3D."""
    pl = pv.Plotter()
    pl.add_text("Arrastra la barra para cambiar la densidad visible", font_size=10)

    # Creamos la instancia del motor y mostramos el volumen
    render = Render3D(pl)
    render.mostrar((volumen, espaciado), reduccion=reduccion)

    minimo, maximo = float(np.min(volumen)), float(np.max(volumen))
    if umbral_inicial is None:
        umbral_inicial = minimo + 0.6 * (maximo - minimo)

    # El slider conecta directamente con el método set_umbral del motor 3D
    pl.add_slider_widget(render.set_umbral, rng=(minimo, maximo), value=umbral_inicial,
                         title="Umbral de densidad", fmt="%.0f", interaction_event="end")
    pl.show()
