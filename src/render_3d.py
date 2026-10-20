"""Herramienta 2: reconstrucción 3D por umbral de densidad."""
import numpy as np
import pyvista as pv

from src.filtros import suavizar


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


def superficie_por_banda(volumen, espaciado, minimo, maximo=None, reduccion=2, suavizado_mm=0.0):
    """Superficie de la estructura cuya densidad está entre `minimo` y `maximo`.

    Sin `maximo` (None o infinito) es la isosuperficie de siempre: todo lo que supera `minimo`.
    Con `maximo` se aísla la banda (por ejemplo, el esmalte sin el metal de los
    brackets). Una isosuperficie en `maximo` no sirve para eso, porque queda
    encerrada dentro de la de `minimo`; en cambio se marca con 1 cada vóxel de la
    banda y con 0 el resto, y marching cubes dibuja la frontera en 0.5.

    `suavizado_mm` aplica un gaussiano (sigma en mm) antes de marching cubes: sobre la
    densidad si no hay máximo, sobre la máscara si lo hay.
    """
    # Primero se reduce y después se suaviza: es 8 veces menos trabajo con reduccion=2.
    v = volumen[::reduccion, ::reduccion, ::reduccion]
    esp = tuple(s * reduccion for s in espaciado)
    if maximo is None or np.isinf(maximo):
        campo, nivel = suavizar(v, esp, suavizado_mm), minimo
    else:
        mascara = ((v >= minimo) & (v <= maximo)).astype(np.float32)
        campo, nivel = suavizar(mascara, esp, suavizado_mm), 0.5
    # a_pyvista nombra el campo "densidad"; con máximo contiene la máscara (0 a 1).
    return a_pyvista(campo, esp, 1).contour([nivel], scalars="densidad")


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
    #con el event_type="end", la actualización solo se da al momento de soltar el click del mouse.
    pl.add_slider_widget(actualizar, rng=(minimo, maximo), value=umbral_inicial,
                         title="Umbral de densidad", fmt="%.0f", interaction_event="end")
    pl.show()
