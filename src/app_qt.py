"""Interfaz gráfica profesional para el visor tomográfico CBCT en PySide6.

Permite alternar entre la navegación multicorte 2D ortogonal (Axial, Coronal, Sagital)
y el entorno de reconstrucción 3D, integrando VisorCortes de Matplotlib en un entorno
médico con tema oscuro y carga dinámica de estudios DICOM.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.carga import cargar_serie_dicom
from src.visor_cortes import (
    COLOR_ANCHO,
    COLOR_AXIAL,
    COLOR_CENTRO,
    COLOR_CORONAL,
    COLOR_SAGITAL,
    VisorCortes,
)

# ==============================================================================
# ESTILOS VISUALES (TEMA MÉDICO OSCURO - QSS)
# ==============================================================================

ESTILO_TEMA_OSCURO = """
QMainWindow, QWidget#CentralWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Barra Superior de Herramientas */
QToolBar {
    background-color: #252526;
    border-bottom: 1px solid #333333;
    padding: 6px 12px;
    spacing: 10px;
}

/* Botón de Cargar Estudio DICOM */
QPushButton.btn-cargar {
    background-color: #1e293b;
    color: #38bdf8;
    border: 1px solid #0284c7;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
}

QPushButton.btn-cargar:hover {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
}

QPushButton.btn-cargar:pressed {
    background-color: #0369a1;
}

/* Botones Conmutables de Vista */
QPushButton.btn-vista {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
}

QPushButton.btn-vista:hover {
    background-color: #38393d;
    color: #ffffff;
    border: 1px solid #007acc;
}

QPushButton.btn-vista:checked {
    background-color: #0e639c;
    color: #ffffff;
    border: 1px solid #1177bb;
}

QPushButton.btn-vista:pressed {
    background-color: #005a9e;
}

/* Separador de Toolbar */
QToolBar::separator {
    background-color: #383838;
    width: 1px;
    margin: 4px 8px;
}

/* Divisor Ajustable */
QSplitter::handle {
    background-color: #2d2d2d;
    width: 3px;
    height: 3px;
}

QSplitter::handle:hover {
    background-color: #007acc;
}

/* Tarjeta del Panel 3D */
QFrame#Tarjeta3D {
    background-color: #252526;
    border: 1px solid #383838;
    border-radius: 12px;
    padding: 30px;
}

/* Barra de Estado */
QStatusBar {
    background-color: #181818;
    color: #8f8f8f;
    border-top: 1px solid #282828;
    font-size: 11px;
    padding: 4px 8px;
}
"""


def configurar_estilo_matplotlib():
    """Ajusta los parámetros globales de Matplotlib para armonizar con el tema oscuro (#1e1e1e)."""
    plt.rcParams.update({
        "figure.facecolor": "#1e1e1e",
        "axes.facecolor": "#1e1e1e",
        "savefig.facecolor": "#1e1e1e",
        "text.color": "#e0e0e0",
        "axes.labelcolor": "#e0e0e0",
        "axes.titlecolor": "#ffffff",
        "xtick.color": "#aaaaaa",
        "ytick.color": "#aaaaaa",
        "axes.edgecolor": "#333333",
    })


def generar_volumen_sintetico() -> Tuple[np.ndarray, Tuple[float, float, float]]:
    """Genera un fantoma volumétrico sintético en caso de que no exista el estudio DICOM en disco.

    Crea una esfera con diferentes densidades emulando hueso y tejido blando para
    permitir la interacción y verificación visual inmediata de la interfaz.
    """
    z, y, x = np.ogrid[-40:40:80j, -50:50:100j, -50:50:100j]
    r = np.sqrt(x**2 + y**2 + z**2)

    volumen = np.zeros((80, 100, 100), dtype=np.float32) - 1000.0  # Densidad de aire
    volumen[r <= 45] = 40.0   # Tejido blando
    volumen[r <= 30] = 800.0  # Hueso cortical
    volumen[r <= 15] = 1800.0 # Esmalte dental / estructura de alta densidad

    espaciado = (1.0, 0.5, 0.5)
    return volumen, espaciado


class MainWindow(QMainWindow):
    """Ventana principal que gestiona las vistas 2D y 3D del estudio tomográfico."""

    def __init__(self, ruta_dicom: str = "data/raw/K01", parent: QWidget | None = None):
        super().__init__(parent)
        self.ruta_dicom = ruta_dicom

        self.setWindowTitle("Explorador Tomográfico CBCT — Visual Computing")
        self.resize(1350, 850)
        self.setMinimumSize(900, 600)

        # Configurar tema oscuro médico de Matplotlib
        configurar_estilo_matplotlib()

        # Componentes principales
        self.canvas_2d: FigureCanvasQTAgg | None = None
        self.visor_cortes: VisorCortes | None = None
        self.widget_2d: QWidget | None = None
        self.panel_3d: QWidget | None = None
        self.splitter: QSplitter | None = None

        # Botones de navegación y vistas
        self.btn_cargar: QPushButton | None = None
        self.btn_2d: QPushButton | None = None
        self.btn_3d: QPushButton | None = None
        self.btn_dividido: QPushButton | None = None
        self.grupo_vistas: QButtonGroup | None = None

        self._inicializar_ui()
        self._cargar_datos_y_visor()

    def _inicializar_ui(self):
        """Construye la barra superior y los contenedores de las vistas."""
        # 1. Barra superior de navegación (Top Toolbar)
        toolbar = QToolBar("Herramientas de Visualización", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        lbl_logo = QLabel("<b>CBCT MEDICAL VIEWER</b>")
        lbl_logo.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold; margin-right: 15px;")
        toolbar.addWidget(lbl_logo)

        # Botón para Cargar Otra Tomografía DICOM
        self.btn_cargar = QPushButton("📁 Cargar Estudio DICOM")
        self.btn_cargar.setProperty("class", "btn-cargar")
        self.btn_cargar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cargar.clicked.connect(self._abrir_dialogo_cargar_dicom)
        toolbar.addWidget(self.btn_cargar)

        toolbar.addSeparator()

        # Botones conmutables de vista
        self.btn_2d = QPushButton("Vista 2D (Cortes)")
        self.btn_3d = QPushButton("Vista 3D (Modelo)")
        self.btn_dividido = QPushButton("Vista Dividida (2D + 3D)")

        for btn in (self.btn_2d, self.btn_3d, self.btn_dividido):
            btn.setProperty("class", "btn-vista")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.grupo_vistas = QButtonGroup(self)
        self.grupo_vistas.setExclusive(True)
        self.grupo_vistas.addButton(self.btn_2d)
        self.grupo_vistas.addButton(self.btn_3d)
        self.grupo_vistas.addButton(self.btn_dividido)

        toolbar.addWidget(self.btn_2d)
        toolbar.addWidget(self.btn_3d)
        toolbar.addWidget(self.btn_dividido)

        # Conectar eventos de cambio de vista
        self.btn_2d.clicked.connect(self.mostrar_modo_2d)
        self.btn_3d.clicked.connect(self.mostrar_modo_3d)
        self.btn_dividido.clicked.connect(self.mostrar_modo_dividido)

        # 2. Contenedor Principal (QSplitter para flexibilidad)
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        layout_principal = QVBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        self.setCentralWidget(central_widget)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, central_widget)
        layout_principal.addWidget(self.splitter)

        # Contenedor para el Visor 2D (Cortes)
        self.widget_2d = QWidget(self.splitter)
        layout_2d = QVBoxLayout(self.widget_2d)
        layout_2d.setContentsMargins(4, 4, 4, 4)
        layout_2d.setSpacing(0)

        # Contenedor de reserva para el Panel 3D
        self.panel_3d = self._crear_panel_3d_placeholder(self.splitter)

        self.splitter.addWidget(self.widget_2d)
        self.splitter.addWidget(self.panel_3d)

        # 3. Barra de estado
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Listo.")

        # Por defecto iniciar en Vista 2D (Cortes)
        self.btn_2d.setChecked(True)
        self.mostrar_modo_2d()

    def _crear_panel_3d_placeholder(self, parent: QWidget) -> QWidget:
        """Crea el panel de reserva elegante para la reconstrucción 3D de Emanuel."""
        panel = QWidget(parent)
        layout_centro = QVBoxLayout(panel)
        layout_centro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_centro.setContentsMargins(20, 20, 20, 20)

        tarjeta = QFrame(panel)
        tarjeta.setObjectName("Tarjeta3D")
        tarjeta.setMaximumWidth(600)
        tarjeta.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        layout_tarjeta = QVBoxLayout(tarjeta)
        layout_tarjeta.setSpacing(14)
        layout_tarjeta.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icono / Emblema 3D estilizado
        lbl_icono = QLabel("⬡")
        lbl_icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icono.setStyleSheet("font-size: 58px; color: #38bdf8; line-height: 1;")

        # Título especificado
        lbl_titulo = QLabel("Panel 3D - Renderizado de Volúmenes (Emanuel)")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        lbl_titulo.setWordWrap(True)

        # Subtítulo y estado
        lbl_subtitulo = QLabel(
            "Módulo de reconstrucción tridimensional por isosuperficies y marcha de cubos (Marching Cubes)."
        )
        lbl_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitulo.setStyleSheet("font-size: 13px; color: #a0a0a0; margin-bottom: 6px;")
        lbl_subtitulo.setWordWrap(True)

        # Badges tecnológicos
        layout_badges = QHBoxLayout()
        layout_badges.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_badges.setSpacing(8)

        for texto in ("PyVista", "VTK", "Isosuperficie", "Filtrado Hounsfield"):
            badge = QLabel(texto)
            badge.setStyleSheet(
                "background-color: #1e293b; color: #38bdf8; border: 1px solid #0284c7; "
                "border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: 600;"
            )
            layout_badges.addWidget(badge)

        lbl_info = QLabel("Integración prevista para la Fase 2 y 3 del proyecto.")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic;")

        layout_tarjeta.addWidget(lbl_icono)
        layout_tarjeta.addWidget(lbl_titulo)
        layout_tarjeta.addWidget(lbl_subtitulo)
        layout_tarjeta.addLayout(layout_badges)
        layout_tarjeta.addWidget(lbl_info)

        layout_centro.addWidget(tarjeta)
        return panel

    def _abrir_dialogo_cargar_dicom(self):
        """Abre un diálogo interactivo para seleccionar la carpeta de un estudio tomográfico."""
        dir_inicial = self.ruta_dicom if os.path.exists(self.ruta_dicom) else "data/raw"
        if not os.path.exists(dir_inicial):
            dir_inicial = os.getcwd()

        carpeta = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Carpeta con Estudio DICOM",
            dir_inicial,
            QFileDialog.Option.ShowDirsOnly,
        )

        if carpeta:
            self.cargar_nuevo_estudio(carpeta)

    def cargar_nuevo_estudio(self, ruta_carpeta: str):
        """Carga un nuevo estudio DICOM desde la ruta especificada y actualiza el visor."""
        try:
            volumen, espaciado = cargar_serie_dicom(ruta_carpeta)
            self.ruta_dicom = ruta_carpeta

            # Actualizar el visor con el nuevo volumen y espaciado
            self.visor_cortes.mostrar((volumen, espaciado))
            self._estilizar_sliders_matplotlib()
            if self.canvas_2d:
                self.canvas_2d.draw_idle()

            msg_estado = (
                f"Estudio cargado: {ruta_carpeta} | "
                f"Volumen: {volumen.shape} (Z, Y, X) | "
                f"Espaciado: {espaciado[0]:.2f} x {espaciado[1]:.2f} x {espaciado[2]:.2f} mm"
            )
            self.statusBar.showMessage(msg_estado)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error al cargar estudio DICOM",
                f"No se pudo cargar la serie DICOM desde:\n{ruta_carpeta}\n\nDetalle: {e}",
            )
            self.statusBar.showMessage(f"Error al cargar estudio: {e}")

    def _cargar_datos_y_visor(self):
        """Carga el estudio tomográfico inicial e inicializa el VisorCortes de Matplotlib."""
        figura = Figure(facecolor="#1e1e1e")
        self.canvas_2d = FigureCanvasQTAgg(figura)
        self.canvas_2d.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.widget_2d.layout().addWidget(self.canvas_2d)

        self.visor_cortes = VisorCortes(figura, aspect="auto")

        # Intentar cargar la serie DICOM de la ruta especificada
        try:
            if not os.path.exists(self.ruta_dicom):
                raise FileNotFoundError(f"Ruta no encontrada: {self.ruta_dicom}")

            volumen, espaciado = cargar_serie_dicom(self.ruta_dicom)
            msg_estado = (
                f"Estudio cargado: {self.ruta_dicom} | "
                f"Volumen: {volumen.shape} (Z, Y, X) | "
                f"Espaciado: {espaciado[0]:.2f} x {espaciado[1]:.2f} x {espaciado[2]:.2f} mm"
            )
            self.statusBar.showMessage(msg_estado)

        except Exception as e:
            # Fallback elegante si aún no se han descargado o colocado los archivos DICOM
            volumen, espaciado = generar_volumen_sintetico()
            msg_alerta = (
                f"Aviso: No se pudo cargar '{self.ruta_dicom}' ({e}). "
                f"Mostrando volumen sintético de prueba."
            )
            self.statusBar.showMessage(msg_alerta)

        # Mostrar los cortes ortogonales en el visor
        self.visor_cortes.mostrar((volumen, espaciado))

        # Ajuste de estilo oscuro a los sliders generados por VisorCortes
        self._estilizar_sliders_matplotlib()
        self.canvas_2d.draw_idle()

    def _estilizar_sliders_matplotlib(self):
        """Aplica estilo oscuro y restaura los colores distintivos de cada slider."""
        if not self.visor_cortes:
            return

        config_sliders = [
            (self.visor_cortes.slider_z, COLOR_AXIAL),       # Axial (Z) - Rojo (#e74c3c)
            (self.visor_cortes.slider_y, COLOR_CORONAL),     # Coronal (Y) - Verde (#2ecc71)
            (self.visor_cortes.slider_x, COLOR_SAGITAL),     # Sagital (X) - Azul (#3498db)
            (self.visor_cortes.slider_centro, COLOR_CENTRO), # Window Level - Púrpura (#9b59b6)
            (self.visor_cortes.slider_ancho, COLOR_ANCHO),   # Window Width - Naranja (#e67e22)
        ]

        for s, color_barra in config_sliders:
            if s is None:
                continue
            s.ax.set_facecolor("#252526")
            s.label.set_color("#ffffff")
            s.label.set_fontsize(9)
            s.valtext.set_color("#e0e0e0")
            s.valtext.set_fontsize(9)
            if hasattr(s, "poly") and s.poly is not None:
                s.poly.set_facecolor(color_barra)

    # ==========================================================================
    # MANEJO DE VISTAS (MODO 2D, MODO 3D, MODO DIVIDIDO)
    # ==========================================================================

    def mostrar_modo_2d(self):
        """Modo 2D: Expande el VisorCortes a pantalla completa."""
        self.widget_2d.setVisible(True)
        self.panel_3d.setVisible(False)
        self.btn_2d.setChecked(True)
        if self.canvas_2d:
            self.canvas_2d.draw_idle()

    def mostrar_modo_3d(self):
        """Modo 3D: Muestra el contenedor de reserva del Panel 3D."""
        self.widget_2d.setVisible(False)
        self.panel_3d.setVisible(True)
        self.btn_3d.setChecked(True)

    def mostrar_modo_dividido(self):
        """Modo Dividido: Muestra el VisorCortes a la izquierda y el Panel 3D a la derecha."""
        self.widget_2d.setVisible(True)
        self.panel_3d.setVisible(True)
        self.btn_dividido.setChecked(True)

        # Repartir el ancho del splitter equitativamente (50% / 50%)
        ancho_total = max(self.width(), 800)
        mitad = ancho_total // 2
        self.splitter.setSizes([mitad, mitad])

        if self.canvas_2d:
            self.canvas_2d.draw_idle()


# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Interfaz Gráfica Profesional PySide6 para Tomografías CBCT"
    )
    parser.add_argument(
        "carpeta",
        nargs="?",
        default="data/raw/K01",
        help="Ruta a la carpeta con cortes DICOM del estudio (por defecto: data/raw/K01)",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO_TEMA_OSCURO)

    ventana = MainWindow(ruta_dicom=args.carpeta)
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
