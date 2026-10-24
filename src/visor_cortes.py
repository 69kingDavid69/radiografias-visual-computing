"""Herramienta 1: navegación multicorte en 2D con visualización ortogonal y control de contraste."""
from typing import Any, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.widgets import Slider

# Colores distintivos para identificar los tres planos anatómicos y sus líneas guía
COLOR_AXIAL = "#e74c3c"    # Rojo para corte Axial (Z)
COLOR_CORONAL = "#2ecc71"  # Verde para corte Coronal (Y)
COLOR_SAGITAL = "#3498db"  # Azul para corte Sagital (X)
COLOR_CENTRO = "#9b59b6"   # Púrpura para Centro (Window Level)
COLOR_ANCHO = "#e67e22"    # Naranja para Ancho (Window Width)


def aplicar_ventana(corte: np.ndarray, centro: float, ancho: float) -> np.ndarray:
    """Aplica ventana/nivel (Window/Level) a un corte ajustando el contraste.

    Recorta los valores del corte al rango [centro - ancho/2, centro + ancho/2].
    """
    vmin = centro - (ancho / 2.0)
    vmax = centro + (ancho / 2.0)
    return np.clip(corte, vmin, vmax)


class VisorCortes:
    """Visor interactivo de tres vistas ortogonales (Axial, Coronal y Sagital) con control de contraste.

    Cumple con el contrato arquitectónico de la Fase 1, permitiendo su integración
    tanto en modo interactivo independiente como dentro de una interfaz de usuario embebida.
    """

    def __init__(
        self,
        figura: Figure,
        aspect: str | float = "anatomico",
        crear_sliders: bool = False,
    ):
        """Inicializa el visor sobre la figura de Matplotlib dada."""
        self.figura = figura
        self.aspect: str | float = aspect
        self.crear_sliders: bool = crear_sliders

        # Callbacks opcionales para sincronización con interfaces externas (PySide6)
        self.on_cambio_corte = None
        self.on_cambio_contraste = None

        # Datos del volumen y geometría
        self.volumen: np.ndarray | None = None
        self.espaciado: Tuple[float, float, float] | None = None
        self.dz: float = 1.0
        self.dy: float = 1.0
        self.dx: float = 1.0

        # Dimensiones y posiciones actuales
        self.nz: int = 0
        self.ny: int = 0
        self.nx: int = 0
        self.idx_z: int = 0
        self.idx_y: int = 0
        self.idx_x: int = 0

        # Parámetros de ventana/nivel (contraste)
        self.centro: float = 0.0
        self.ancho: float = 1.0

        # Ejes de los subplots
        self.ax_axial = None
        self.ax_coronal = None
        self.ax_sagital = None
        self.ax_hist = None          # histograma de densidades (solo en la app, sin sliders)
        self._franja_ventana = None  # zona del histograma que muestra la ventana actual
        self.marcas: dict = {}       # nombre → (densidad, color): umbrales de los presets

        # Objetos imagen (imshow)
        self.im_axial = None
        self.im_coronal = None
        self.im_sagital = None

        # Líneas guía de intersección (crosshairs)
        self.linea_ax_y = None
        self.linea_ax_x = None
        self.linea_cor_z = None
        self.linea_cor_x = None
        self.linea_sag_z = None
        self.linea_sag_y = None

        # Deslizadores interactivos
        self.slider_z = None
        self.slider_y = None
        self.slider_x = None
        self.slider_centro = None
        self.slider_ancho = None

    def mostrar(self, estudio: Any, aspect: str | float | None = None):
        """Carga y despliega los planos ortogonales del estudio en la figura.

        Acepta una instancia de `Estudio` (con atributos `volumen` y `espaciado`),
        o una tupla/lista `(volumen, espaciado)`.
        """
        if aspect is not None:
            self.aspect = aspect

        if hasattr(estudio, "volumen") and hasattr(estudio, "espaciado"):
            self.volumen = np.asarray(estudio.volumen, dtype=np.float32)
            self.espaciado = tuple(estudio.espaciado)
        elif isinstance(estudio, (tuple, list)) and len(estudio) >= 2:
            self.volumen = np.asarray(estudio[0], dtype=np.float32)
            self.espaciado = tuple(estudio[1])
        elif isinstance(estudio, dict) and "volumen" in estudio and "espaciado" in estudio:
            self.volumen = np.asarray(estudio["volumen"], dtype=np.float32)
            self.espaciado = tuple(estudio["espaciado"])
        else:
            raise ValueError(
                "El estudio debe ser un objeto con atributos 'volumen' y 'espaciado', "
                "o una tupla/lista (volumen, espaciado)."
            )

        dz_raw, dy_raw, dx_raw = self.espaciado
        self.dz = float(dz_raw)
        self.dy = float(dy_raw)
        self.dx = float(dx_raw)
        self.nz, self.ny, self.nx = self.volumen.shape

        # Validación y corrección de espaciado real:
        if not np.isfinite(self.dz) or self.dz <= 0:
            self.dz = float(self.dx if self.dx > 0 else 1.0)
        elif self.nz > 1 and self.dz > (self.nz * self.dx * 0.5):
            espaciado_real = self.dz / (self.nz - 1)
            if 0.01 <= espaciado_real <= 20.0:
                self.dz = espaciado_real

        if not np.isfinite(self.dy) or self.dy <= 0:
            self.dy = 1.0
        if not np.isfinite(self.dx) or self.dx <= 0:
            self.dx = 1.0

        # Posiciones iniciales al centro del volumen
        self.idx_z = self.nz // 2
        self.idx_y = self.ny // 2
        self.idx_x = self.nx // 2

        # Rango y valores iniciales de contraste
        minimo = float(self.volumen.min())
        maximo = float(self.volumen.max())
        rango = maximo - minimo if maximo > minimo else 1.0

        self.centro = (minimo + maximo) / 2.0
        self.ancho = float(rango)

        # Preparar la figura
        self.figura.clear()
        if self.crear_sliders:
            self.figura.subplots_adjust(left=0.06, right=0.96, top=0.90, bottom=0.28, wspace=0.25)

        # 1. Configurar subplots para las tres vistas ortogonales
        self.ax_axial = self.figura.add_subplot(1, 3, 1)
        self.ax_coronal = self.figura.add_subplot(1, 3, 2)
        self.ax_sagital = self.figura.add_subplot(1, 3, 3)

        # 2. Generar imágenes iniciales con contraste aplicado
        corte_axial = aplicar_ventana(self.volumen[self.idx_z, :, :], self.centro, self.ancho)
        corte_coronal = aplicar_ventana(self.volumen[:, self.idx_y, :], self.centro, self.ancho)
        corte_sagital = aplicar_ventana(self.volumen[:, :, self.idx_x], self.centro, self.ancho)

        vmin = self.centro - (self.ancho / 2.0)
        vmax = self.centro + (self.ancho / 2.0)

        # Configuración de aspecto ('auto' o relación anatómica calculada)
        if self.aspect == "auto":
            aspect_axial = "auto"
            aspect_coronal = "auto"
            aspect_sagital = "auto"
        elif isinstance(self.aspect, (int, float)):
            aspect_axial = "auto"
            aspect_coronal = float(self.aspect)
            aspect_sagital = float(self.aspect)
        else:  # "anatomico", "equal", o valor por defecto
            aspect_axial = (self.dy / self.dx) if (self.dx > 0 and 0.05 <= self.dy / self.dx <= 20.0) else 1.0
            aspect_coronal = (self.dz / self.dx) if (self.dx > 0 and 0.05 <= self.dz / self.dx <= 20.0) else 1.0
            aspect_sagital = (self.dz / self.dy) if (self.dy > 0 and 0.05 <= self.dz / self.dy <= 20.0) else 1.0

        # Vista Axial: volumen[z, :, :], extensión [0, nx, ny, 0]
        extent_axial = (0, self.nx, self.ny, 0)
        self.im_axial = self.ax_axial.imshow(
            corte_axial,
            cmap="gray",
            vmin=vmin,
            vmax=vmax,
            aspect=aspect_axial,
            extent=extent_axial
        )
        self.im_axial.set_extent(extent_axial)
        self.ax_axial.set_xlim(0, self.nx)
        self.ax_axial.set_ylim(self.ny, 0)
        self.ax_axial.set_aspect(aspect_axial)
        self.ax_axial.axis("off")
        self._actualizar_titulo_axial()

        # Vista Coronal: volumen[:, y, :], extensión [0, nx, 0, nz]
        extent_coronal = (0, self.nx, 0, self.nz)
        self.im_coronal = self.ax_coronal.imshow(
            corte_coronal,
            cmap="gray",
            vmin=vmin,
            vmax=vmax,
            aspect=aspect_coronal,
            origin="lower",
            extent=extent_coronal
        )
        self.im_coronal.set_extent(extent_coronal)
        self.ax_coronal.set_xlim(0, self.nx)
        self.ax_coronal.set_ylim(0, self.nz)
        self.ax_coronal.set_aspect(aspect_coronal)
        self.ax_coronal.axis("off")
        self._actualizar_titulo_coronal()

        # Vista Sagital: volumen[:, :, x], extensión [0, ny, 0, nz]
        extent_sagital = (0, self.ny, 0, self.nz)
        self.im_sagital = self.ax_sagital.imshow(
            corte_sagital,
            cmap="gray",
            vmin=vmin,
            vmax=vmax,
            aspect=aspect_sagital,
            origin="lower",
            extent=extent_sagital
        )
        self.im_sagital.set_extent(extent_sagital)
        self.ax_sagital.set_xlim(0, self.ny)
        self.ax_sagital.set_ylim(0, self.nz)
        self.ax_sagital.set_aspect(aspect_sagital)
        self.ax_sagital.axis("off")
        self._actualizar_titulo_sagital()

        # 3. Líneas guía de intersección (crosshairs)
        # Vista Axial: línea horizontal marca corte Y (Coronal), vertical marca corte X (Sagital)
        self.linea_ax_y = self.ax_axial.axhline(self.idx_y, color=COLOR_CORONAL, linestyle="--", linewidth=1.2, alpha=0.85)
        self.linea_ax_x = self.ax_axial.axvline(self.idx_x, color=COLOR_SAGITAL, linestyle="--", linewidth=1.2, alpha=0.85)

        # Vista Coronal: línea horizontal marca corte Z (Axial), vertical marca corte X (Sagital)
        self.linea_cor_z = self.ax_coronal.axhline(self.idx_z, color=COLOR_AXIAL, linestyle="--", linewidth=1.2, alpha=0.85)
        self.linea_cor_x = self.ax_coronal.axvline(self.idx_x, color=COLOR_SAGITAL, linestyle="--", linewidth=1.2, alpha=0.85)

        # Vista Sagital: línea horizontal marca corte Z (Axial), vertical marca corte Y (Coronal)
        self.linea_sag_z = self.ax_sagital.axhline(self.idx_z, color=COLOR_AXIAL, linestyle="--", linewidth=1.2, alpha=0.85)
        self.linea_sag_y = self.ax_sagital.axvline(self.idx_y, color=COLOR_CORONAL, linestyle="--", linewidth=1.2, alpha=0.85)

        # 4. Deslizadores de navegación y contraste
        if self.crear_sliders:
            # Columna izquierda: Selección de cortes ortogonales
            ax_s_z = self.figura.add_axes([0.10, 0.18, 0.35, 0.025])
            ax_s_y = self.figura.add_axes([0.10, 0.11, 0.35, 0.025])
            ax_s_x = self.figura.add_axes([0.10, 0.04, 0.35, 0.025])

            max_z = max(self.nz - 1, 1) if self.nz <= 1 else self.nz - 1
            max_y = max(self.ny - 1, 1) if self.ny <= 1 else self.ny - 1
            max_x = max(self.nx - 1, 1) if self.nx <= 1 else self.nx - 1

            self.slider_z = Slider(ax_s_z, "Corte Z", 0, max_z, valinit=self.idx_z, valstep=1, color=COLOR_AXIAL)
            self.slider_y = Slider(ax_s_y, "Corte Y", 0, max_y, valinit=self.idx_y, valstep=1, color=COLOR_CORONAL)
            self.slider_x = Slider(ax_s_x, "Corte X", 0, max_x, valinit=self.idx_x, valstep=1, color=COLOR_SAGITAL)

            # Columna derecha: Centro y Ancho de ventana
            ax_s_c = self.figura.add_axes([0.58, 0.14, 0.35, 0.025])
            ax_s_a = self.figura.add_axes([0.58, 0.07, 0.35, 0.025])

            val_min_centro = minimo if minimo < maximo else minimo - 1.0
            val_max_centro = maximo if maximo > minimo else maximo + 1.0
            val_max_ancho = max(rango, 10.0)

            self.slider_centro = Slider(ax_s_c, "Centro", val_min_centro, val_max_centro, valinit=self.centro, color=COLOR_CENTRO)
            self.slider_ancho = Slider(ax_s_a, "Ancho", 1.0, val_max_ancho, valinit=self.ancho, color=COLOR_ANCHO)

            # Conectar eventos de los sliders
            self.slider_z.on_changed(lambda val: self.ir_a_corte("axial", int(val)))
            self.slider_y.on_changed(lambda val: self.ir_a_corte("coronal", int(val)))
            self.slider_x.on_changed(lambda val: self.ir_a_corte("sagital", int(val)))

            self.slider_centro.on_changed(lambda _: self._actualizar_contraste())
            self.slider_ancho.on_changed(lambda _: self._actualizar_contraste())
        else:
            self.slider_z = None
            self.slider_y = None
            self.slider_x = None
            self.slider_centro = None
            self.slider_ancho = None
            self.reajustar_tamano()

        # 5. En la app (sin sliders de matplotlib): histograma de densidades en vivo
        self.ax_hist = None
        if not self.crear_sliders:
            self._crear_histograma()
            self.reajustar_tamano()

        # Navegación interactiva por clic en las vistas
        self.figura.canvas.mpl_connect("button_press_event", self._on_click)

        self.figura.canvas.draw_idle()

    def reajustar_tamano(self):
        """Reajusta la distribución de la figura manteniendo la relación de aspecto exacta de los cortes."""
        try:
            if self.crear_sliders:
                self.figura.tight_layout(rect=[0, 0.22, 1, 0.98])
            elif self.ax_axial is not None:
                self._distribuir_paneles()
        except Exception:
            pass
        if self.figura.canvas:
            self.figura.canvas.draw_idle()

    def set_ventana(self, centro: float, ancho: float):
        """Ajusta el centro y ancho de la ventana Hounsfield y redibuja."""
        self.centro = float(centro)
        self.ancho = max(float(ancho), 1.0)
        if self.slider_centro is not None:
            self.slider_centro.eventson = False
            self.slider_centro.set_val(self.centro)
            self.slider_centro.eventson = True
        if self.slider_ancho is not None:
            self.slider_ancho.eventson = False
            self.slider_ancho.set_val(self.ancho)
            self.slider_ancho.eventson = True
        self._actualizar_contraste()
        if self.on_cambio_contraste:
            self.on_cambio_contraste(self.centro, self.ancho)

    def reset_ventana(self) -> Tuple[float, float]:
        """Restaura el contraste al rango completo original del volumen."""
        if self.volumen is not None:
            minimo = float(self.volumen.min())
            maximo = float(self.volumen.max())
            centro = (minimo + maximo) / 2.0
            ancho = float(maximo - minimo) if maximo > minimo else 1.0
            self.set_ventana(centro, ancho)
            return centro, ancho
        return self.centro, self.ancho

    def ir_a_corte(self, eje: str, indice: int):
        """Mueve la visualización al corte especificado en el eje indicado.

        Parámetros:
            eje: Plano ortogonal a modificar ('axial', 'coronal' o 'sagital').
            indice: Índice entero del corte dentro de las dimensiones del volumen.
        """
        if self.volumen is None:
            return

        eje_norm = eje.strip().lower()

        if eje_norm in ("axial", "z"):
            indice = int(np.clip(indice, 0, self.nz - 1))
            self.idx_z = indice
            if self.slider_z is not None and int(self.slider_z.val) != indice:
                self.slider_z.eventson = False
                self.slider_z.set_val(indice)
                self.slider_z.eventson = True

            # 1. Actualizar imagen axial
            corte_axial = aplicar_ventana(self.volumen[self.idx_z, :, :], self.centro, self.ancho)
            self.im_axial.set_data(corte_axial)
            self._actualizar_titulo_axial()

            # 2. Actualizar líneas horizontales en Coronal y Sagital (marcan plano Z)
            if self.linea_cor_z is not None:
                self.linea_cor_z.set_ydata([self.idx_z, self.idx_z])
            if self.linea_sag_z is not None:
                self.linea_sag_z.set_ydata([self.idx_z, self.idx_z])

        elif eje_norm in ("coronal", "y"):
            indice = int(np.clip(indice, 0, self.ny - 1))
            self.idx_y = indice
            if self.slider_y is not None and int(self.slider_y.val) != indice:
                self.slider_y.eventson = False
                self.slider_y.set_val(indice)
                self.slider_y.eventson = True

            # 1. Actualizar imagen coronal
            corte_coronal = aplicar_ventana(self.volumen[:, self.idx_y, :], self.centro, self.ancho)
            self.im_coronal.set_data(corte_coronal)
            self._actualizar_titulo_coronal()

            # 2. Actualizar líneas guía (horizontal en Axial, vertical en Sagital)
            if self.linea_ax_y is not None:
                self.linea_ax_y.set_ydata([self.idx_y, self.idx_y])
            if self.linea_sag_y is not None:
                self.linea_sag_y.set_xdata([self.idx_y, self.idx_y])

        elif eje_norm in ("sagital", "sagittal", "x"):
            indice = int(np.clip(indice, 0, self.nx - 1))
            self.idx_x = indice
            if self.slider_x is not None and int(self.slider_x.val) != indice:
                self.slider_x.eventson = False
                self.slider_x.set_val(indice)
                self.slider_x.eventson = True

            # 1. Actualizar imagen sagital
            corte_sagital = aplicar_ventana(self.volumen[:, :, self.idx_x], self.centro, self.ancho)
            self.im_sagital.set_data(corte_sagital)
            self._actualizar_titulo_sagital()

            # 2. Actualizar líneas guía (vertical en Axial, vertical en Coronal)
            if self.linea_ax_x is not None:
                self.linea_ax_x.set_xdata([self.idx_x, self.idx_x])
            if self.linea_cor_x is not None:
                self.linea_cor_x.set_xdata([self.idx_x, self.idx_x])

        else:
            raise ValueError(f"Eje no reconocido: '{eje}'. Debe ser 'axial', 'coronal' o 'sagital'.")

        if self.on_cambio_corte:
            self.on_cambio_corte(eje_norm, indice)

        self.figura.canvas.draw_idle()

    def _actualizar_contraste(self):
        """Actualiza la ventana de contraste en las tres vistas ortogonales."""
        if self.volumen is None:
            return

        if self.slider_centro is not None:
            self.centro = float(self.slider_centro.val)
        if self.slider_ancho is not None:
            self.ancho = float(self.slider_ancho.val)
        vmin = self.centro - (self.ancho / 2.0)
        vmax = self.centro + (self.ancho / 2.0)

        # Actualizar corte axial
        corte_axial = aplicar_ventana(self.volumen[self.idx_z, :, :], self.centro, self.ancho)
        self.im_axial.set_data(corte_axial)
        self.im_axial.set_clim(vmin=vmin, vmax=vmax)

        # Actualizar corte coronal
        corte_coronal = aplicar_ventana(self.volumen[:, self.idx_y, :], self.centro, self.ancho)
        self.im_coronal.set_data(corte_coronal)
        self.im_coronal.set_clim(vmin=vmin, vmax=vmax)

        # Actualizar corte sagital
        corte_sagital = aplicar_ventana(self.volumen[:, :, self.idx_x], self.centro, self.ancho)
        self.im_sagital.set_data(corte_sagital)
        self.im_sagital.set_clim(vmin=vmin, vmax=vmax)

        self._actualizar_franja_ventana()
        self.figura.canvas.draw_idle()

    def _actualizar_titulo_axial(self):
        if self.ax_axial is not None:
            pos_mm = float(self.idx_z) * float(self.dz)
            self.ax_axial.set_title(
                f"Axial\nZ {self.idx_z} / {self.nz - 1} · {pos_mm:.1f} mm",
                fontsize=10,
                fontweight="bold"
            )

    def _actualizar_titulo_coronal(self):
        if self.ax_coronal is not None:
            pos_mm = float(self.idx_y) * float(self.dy)
            self.ax_coronal.set_title(
                f"Coronal\nY {self.idx_y} / {self.ny - 1} · {pos_mm:.1f} mm",
                fontsize=10,
                fontweight="bold"
            )

    def _actualizar_titulo_sagital(self):
        if self.ax_sagital is not None:
            pos_mm = float(self.idx_x) * float(self.dx)
            self.ax_sagital.set_title(
                f"Sagital\nX {self.idx_x} / {self.nx - 1} · {pos_mm:.1f} mm",
                fontsize=10,
                fontweight="bold"
            )

    # --- Histograma y distribución de los paneles (app) ----------------------------

    def _crear_histograma(self):
        """Histograma de densidades del volumen, con la ventana actual y los umbrales marcados.

        Muestra de dónde sale cada preset: el pico grande es el tejido blando y la cola
        derecha, hueso, dientes y metal. Se calcula con 1 de cada 8 vóxeles (rápido).
        """
        self.ax_hist = self.figura.add_subplot(2, 2, 4)
        muestra = self.volumen[::2, ::2, ::2].ravel()
        self.ax_hist.hist(muestra, bins=160, color="#64748b", log=True)
        self.ax_hist.set_title("Densidades del estudio", fontsize=10, fontweight="bold")
        self.ax_hist.tick_params(labelsize=7)
        self.ax_hist.set_yticks([])
        self.ax_hist.set_yticks([], minor=True)    # la escala log agrega marcas menores
        for spine in ("top", "right", "left"):
            self.ax_hist.spines[spine].set_visible(False)
        # figura.clear() ya borró los artistas del estudio anterior: no hay que quitarlos
        self._franja_ventana = None
        self._artistas_marcas = []
        self._actualizar_franja_ventana()
        self._dibujar_marcas()

    def marcar_densidades(self, marcas: dict):
        """Marca en el histograma los umbrales de los presets: {nombre: (densidad, color)}."""
        self.marcas = dict(marcas)
        self._dibujar_marcas()
        self.figura.canvas.draw_idle()

    def _dibujar_marcas(self):
        if self.ax_hist is None:
            return
        for artista in getattr(self, "_artistas_marcas", []):
            artista.remove()
        self._artistas_marcas = []
        x0, x1 = self.ax_hist.get_xlim()
        for i, (nombre, (valor, color)) in enumerate(sorted(self.marcas.items(), key=lambda m: m[1][0])):
            if not x0 <= valor <= x1:
                continue
            self._artistas_marcas.append(self.ax_hist.axvline(valor, color=color, linewidth=1.4))
            self._artistas_marcas.append(self.ax_hist.text(
                valor, 0.97 - 0.13 * (i % 2), f" {nombre}", color=color, fontsize=7,
                transform=self.ax_hist.get_xaxis_transform(), va="top"))

    def _actualizar_franja_ventana(self):
        if self.ax_hist is None:
            return
        if self._franja_ventana is not None:
            self._franja_ventana.remove()
        x0, x1 = self.ax_hist.get_xlim()
        self._franja_ventana = self.ax_hist.axvspan(
            self.centro - self.ancho / 2, self.centro + self.ancho / 2, color="#38bdf8", alpha=0.15)
        self.ax_hist.set_xlim(x0, x1)

    def _distribuir_paneles(self):
        """Ubica los paneles según la forma del lienzo, sin dejar franjas vacías.

        Ancho (vista 2D sola): los tres cortes en fila y el histograma debajo, en la franja
        que antes quedaba vacía. Angosto (vista dividida): cuadrícula 2 × 2.
        """
        ancho, alto = self.figura.get_size_inches()
        cortes = (self.ax_axial, self.ax_coronal, self.ax_sagital)
        if ancho / max(alto, 1e-6) >= 1.9:
            for i, ax in enumerate(cortes):
                ax.set_position([0.01 + i / 3, 0.30, 1 / 3 - 0.02, 0.60])
            if self.ax_hist is not None:
                self.ax_hist.set_position([0.06, 0.07, 0.88, 0.14])
        else:
            cajas = ([0.02, 0.53, 0.46, 0.38], [0.52, 0.53, 0.46, 0.38], [0.02, 0.04, 0.46, 0.38])
            for ax, caja in zip(cortes, cajas):
                ax.set_position(caja)
            if self.ax_hist is not None:
                self.ax_hist.set_position([0.56, 0.10, 0.40, 0.30])

    def _on_click(self, event):
        """Permite hacer clic sobre cualquier plano para posicionar los otros dos cortes.

        Un clic en el histograma centra la ventana de contraste en esa densidad.
        """
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return
        if event.inaxes == self.ax_hist:
            self.set_ventana(event.xdata, self.ancho)
            return

        if event.inaxes == self.ax_axial:
            self.ir_a_corte("sagital", int(round(event.xdata)))
            self.ir_a_corte("coronal", int(round(event.ydata)))
        elif event.inaxes == self.ax_coronal:
            self.ir_a_corte("sagital", int(round(event.xdata)))
            self.ir_a_corte("axial", int(round(event.ydata)))
        elif event.inaxes == self.ax_sagital:
            self.ir_a_corte("coronal", int(round(event.xdata)))
            self.ir_a_corte("axial", int(round(event.ydata)))


def explorar_cortes(
    volumen: np.ndarray,
    espaciado: Tuple[float, float, float],
    aspect: str | float = "anatomico"
) -> VisorCortes:
    """Muestra el visor ortogonal interactivo (Axial, Coronal, Sagital) con sliders de navegación y contraste."""
    fig = plt.figure(figsize=(14, 7.5))
    visor = VisorCortes(fig, aspect=aspect, crear_sliders=True)
    visor.mostrar((volumen, espaciado))
    plt.show()
    return visor
