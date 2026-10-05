"""Herramienta 1: navegación multicorte en 2D con deslizadores de corte y contraste (ventana/nivel)."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider


def aplicar_ventana(corte, centro, ancho):
    """Aplica ventana/nivel (Window/Level) a un corte ajustando el contraste.

    Recorta los valores del corte al rango [centro - ancho/2, centro + ancho/2].
    """
    vmin = centro - (ancho / 2.0)
    vmax = centro + (ancho / 2.0)
    return np.clip(corte, vmin, vmax)


def explorar_cortes(volumen, espaciado):
    """Muestra un corte axial y sliders para recorrer el volumen en z y ajustar el contraste (centro/ancho)."""
    dz, dy, dx = espaciado
    n = volumen.shape[0]

    minimo = float(volumen.min())
    maximo = float(volumen.max())
    rango = maximo - minimo if maximo > minimo else 1.0

    centro_init = (minimo + maximo) / 2.0
    ancho_init = rango

    fig, ax = plt.subplots(figsize=(7, 7.5))
    fig.subplots_adjust(bottom=0.25)

    corte_inicial = aplicar_ventana(volumen[n // 2], centro_init, ancho_init)
    imagen = ax.imshow(
        corte_inicial,
        cmap="gray",
        vmin=centro_init - (ancho_init / 2.0),
        vmax=centro_init + (ancho_init / 2.0),
        aspect=dy / dx
    )
    ax.set_title("Corte axial")
    ax.axis("off")

    ax_corte = fig.add_axes([0.20, 0.15, 0.65, 0.03])
    ax_centro = fig.add_axes([0.20, 0.09, 0.65, 0.03])
    ax_ancho = fig.add_axes([0.20, 0.03, 0.65, 0.03])

    barra_corte = Slider(ax_corte, "Corte", 0, n - 1, valinit=n // 2, valstep=1)
    barra_centro = Slider(ax_centro, "Centro", minimo, maximo, valinit=centro_init)
    barra_ancho = Slider(ax_ancho, "Ancho", 1.0, max(rango, 1.0), valinit=ancho_init)

    def actualizar(_=None):
        corte_idx = int(barra_corte.val)
        c_val = float(barra_centro.val)
        a_val = float(barra_ancho.val)

        corte_procesado = aplicar_ventana(volumen[corte_idx], c_val, a_val)
        imagen.set_data(corte_procesado)

        vmin = c_val - (a_val / 2.0)
        vmax = c_val + (a_val / 2.0)
        imagen.set_clim(vmin=vmin, vmax=vmax)

        ax.set_title(f"Corte axial {corte_idx} / {n - 1}  (z = {corte_idx * dz:.1f} mm)")
        fig.canvas.draw_idle()

    barra_corte.on_changed(actualizar)
    barra_centro.on_changed(actualizar)
    barra_ancho.on_changed(actualizar)

    actualizar()
    plt.show()

