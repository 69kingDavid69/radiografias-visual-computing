"""Herramienta 1: navegación multicorte en 2D con un deslizador."""
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider


def explorar_cortes(volumen, espaciado):
    """Muestra un corte axial y un slider para recorrer el volumen en z."""
    dz, dy, dx = espaciado
    n = volumen.shape[0]
    fig, ax = plt.subplots(figsize=(7, 7))
    fig.subplots_adjust(bottom=0.15)

    imagen = ax.imshow(volumen[n // 2], cmap="gray",
                       vmin=volumen.min(), vmax=volumen.max(),
                       aspect=dy / dx)
    ax.set_title("Corte axial")
    ax.axis("off")

    barra = Slider(fig.add_axes([0.15, 0.05, 0.7, 0.03]), "Corte", 0, n - 1,
                   valinit=n // 2, valstep=1)

    def actualizar(valor):
        imagen.set_data(volumen[int(valor)])
        ax.set_title(f"Corte axial {int(valor)} / {n - 1}  (z = {int(valor) * dz:.1f} mm)")
        fig.canvas.draw_idle()

    barra.on_changed(actualizar)
    actualizar(n // 2)
    plt.show()
