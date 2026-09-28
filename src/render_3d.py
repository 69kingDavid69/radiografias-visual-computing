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


def explorar_3d(volumen, espaciado, umbral_inicial=None, reduccion=2):
    """Abre una ventana 3D con una barra de sensibilidad (umbral).

    Todo lo que tenga densidad menor al umbral se vuelve invisible; se dibuja
    la superficie (isosuperficie) donde el volumen cruza ese valor.
    """
    malla = a_pyvista(volumen, espaciado, reduccion)
    minimo, maximo = float(np.min(volumen)), float(np.max(volumen))
    if umbral_inicial is None:
        umbral_inicial = minimo + 0.6 * (maximo - minimo)

    pl = pv.Plotter()
    pl.add_text("Arrastra la barra para cambiar la densidad visible", font_size=10)

    def actualizar(umbral):
        superficie = malla.contour([umbral], scalars="densidad")
        if superficie.n_points == 0:
            pl.remove_actor("estructura")
            return
        pl.add_mesh(superficie, name="estructura", color="ivory",
                    smooth_shading=True, specular=0.4)

    pl.add_slider_widget(actualizar, rng=(minimo, maximo), value=umbral_inicial,
                         title="Umbral de densidad", fmt="%.0f")
    pl.show()
