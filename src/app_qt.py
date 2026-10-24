"""Interfaz gráfica profesional para el visor tomográfico CBCT en PySide6.

Permite alternar entre la navegación multicorte 2D ortogonal (Axial, Coronal, Sagital)
y el entorno de reconstrucción 3D, integrando VisorCortes de Matplotlib en un entorno
médico con tema oscuro, QSplitter interactivo, sliders orgánicos y presets Hounsfield.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
from contextlib import contextmanager

# Ensure the project root is on PYTHONPATH for relative imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from typing import Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)

# QtInteractor for 3D rendering
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pathlib import Path

from src.carga import EXTENSIONES_VOLUMEN, cargar_estudio
from src.densidades import EXPERIMENTALES
from src.render_3d import CAPAS_BLANDAS, CAPAS_IMPLANTE, Render3D
from src.densidades import color_para, unidad_de, ventana_para
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
    padding: 6px 14px;
    spacing: 10px;
}

/* Botón de Cargar Estudio DICOM */
QPushButton.btn-cargar {
    background-color: #1e293b;
    color: #38bdf8;
    border: 1px solid #0284c7;
    border-radius: 6px;
    padding: 7px 15px;
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
    padding: 7px 16px;
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

/* ==========================================================================
   DIVISOR AJUSTABLE (QSPLITTER)
   ========================================================================== */
QSplitter::handle:horizontal {
    background-color: #2a2a2d;
    border-left: 1px solid #1e1e1e;
    border-right: 1px solid #1e1e1e;
    width: 8px;
}

QSplitter::handle:horizontal:hover {
    background-color: #007acc;
}

QSplitter::handle:horizontal:pressed {
    background-color: #38bdf8;
}

/* ==========================================================================
   TARJETAS Y PANELES PREMIUM (#252526, border-radius: 10px)
   ========================================================================== */
QFrame#PanelControles {
    background-color: #252526;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 10px 14px;
}

QFrame#Tarjeta3D {
    background-color: #252526;
    border: 1px solid #383838;
    border-radius: 10px;
    padding: 30px;
}

/* Botones rápidos de Presets Hounsfield */
QPushButton.btn-preset {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton.btn-preset:hover {
    background-color: #2e3034;
    color: #ffffff;
    border: 1px solid #0284c7;
}

QPushButton.btn-preset:pressed {
    background-color: #0e639c;
    color: #ffffff;
}

QPushButton.btn-preset:checked {
    background-color: #0e639c;
    color: #ffffff;
    border: 1px solid #38bdf8;
}

/* ==========================================================================
   SLIDERS ORGÁNICOS TIPO PÍLDORA (MODERN HEALTHCARE UI)
   ========================================================================== */
QSlider:horizontal {
    min-height: 24px;
    max-height: 24px;
}

QSlider::groove:horizontal {
    border: none;
    height: 12px;
    background-color: #1a1a1c;
    border-radius: 6px;
}

QSlider::sub-page:horizontal {
    border-radius: 6px;
    height: 12px;
}

/* Canales cargados distintivos por plano y ventana */
QSlider#SliderZ::sub-page:horizontal {
    background-color: #e74c3c;
    border-radius: 6px;
}

QSlider#SliderY::sub-page:horizontal {
    background-color: #2ecc71;
    border-radius: 6px;
}

QSlider#SliderX::sub-page:horizontal {
    background-color: #3498db;
    border-radius: 6px;
}

QSlider#SliderCentro::sub-page:horizontal {
    background-color: #9b59b6;
    border-radius: 6px;
}

QSlider#SliderAncho::sub-page:horizontal {
    background-color: #e67e22;
    border-radius: 6px;
}

QSlider::add-page:horizontal {
    background-color: #333338;
    border-radius: 6px;
    height: 12px;
}

/* Píldora / Manija (Handle) */
QSlider::handle:horizontal {
    background-color: #ffffff;
    border: 2px solid #1e1e1e;
    width: 18px;
    height: 18px;
    margin: -3px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #38bdf8;
    border: 2px solid #ffffff;
}

QSlider::handle:horizontal:pressed {
    background-color: #0284c7;
    border: 2px solid #e0f2fe;
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


def crear_icono_medico() -> QIcon:
    """Genera un QIcon médico profesional con cruz brillante y silueta dental simplificada."""
    tamanos = [16, 24, 32, 48, 64, 128, 256]
    icono = QIcon()

    for tam in tamanos:
        pix = QPixmap(tam, tam)
        pix.fill(Qt.GlobalColor.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        escala = tam / 128.0

        # Fondo: Escudo redondeado con gradiente azul pizarra oscuro
        rect_fondo = QRectF(4 * escala, 4 * escala, 120 * escala, 120 * escala)
        grad_fondo = QLinearGradient(0, 0, tam, tam)
        grad_fondo.setColorAt(0.0, QColor("#091322"))
        grad_fondo.setColorAt(0.5, QColor("#0f172a"))
        grad_fondo.setColorAt(1.0, QColor("#1e293b"))
        p.setBrush(QBrush(grad_fondo))
        p.setPen(QPen(QColor("#0284c7"), max(1.5, 2.5 * escala)))
        p.drawRoundedRect(rect_fondo, 26 * escala, 26 * escala)

        # Cruz médica radiante en cian (#38bdf8 / #00f2fe)
        grad_cruz = QLinearGradient(0, 20 * escala, 0, 108 * escala)
        grad_cruz.setColorAt(0.0, QColor("#38bdf8"))
        grad_cruz.setColorAt(1.0, QColor("#0284c7"))
        p.setBrush(QBrush(grad_cruz))
        p.setPen(Qt.PenStyle.NoPen)

        ancho_barra = 28 * escala
        radio_cruz = 6 * escala
        p.drawRoundedRect(
            QRectF((128 - 28) / 2 * escala, 24 * escala, ancho_barra, 80 * escala),
            radio_cruz,
            radio_cruz,
        )
        p.drawRoundedRect(
            QRectF(24 * escala, (128 - 28) / 2 * escala, 80 * escala, ancho_barra),
            radio_cruz,
            radio_cruz,
        )

        # Silueta dental estilizada en el núcleo de la cruz
        if tam >= 32:
            path_diente = QPainterPath()
            cx = 64 * escala
            cy = 64 * escala
            w_d = 20 * escala
            h_d = 22 * escala

            path_diente.moveTo(cx - w_d * 0.45, cy - h_d * 0.4)
            path_diente.quadTo(cx - w_d * 0.25, cy - h_d * 0.55, cx, cy - h_d * 0.35)
            path_diente.quadTo(cx + w_d * 0.25, cy - h_d * 0.55, cx + w_d * 0.45, cy - h_d * 0.4)
            path_diente.quadTo(cx + w_d * 0.5, cy + h_d * 0.1, cx + w_d * 0.3, cy + h_d * 0.45)
            path_diente.quadTo(cx, cy + h_d * 0.2, cx - w_d * 0.3, cy + h_d * 0.45)
            path_diente.quadTo(cx - w_d * 0.5, cy + h_d * 0.1, cx - w_d * 0.45, cy - h_d * 0.4)

            p.setBrush(QBrush(QColor("#ffffff")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(path_diente)
        else:
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawEllipse(QRectF(52 * escala, 52 * escala, 24 * escala, 24 * escala))

        p.end()
        icono.addPixmap(pix)

    return icono


def aviso_espaciado(espaciado, forma) -> str:
    """Aviso para la barra de estado si el archivo parece no traer el tamaño real del vóxel.

    Exactamente 1 × 1 × 1 mm en un volumen grande suele ser el valor por defecto de un
    archivo que perdió el espaciado (pasa en parte de STS-3D-Tooth): la forma se ve bien,
    pero las medidas en mm y el suavizado por estructura no corresponden.
    """
    if max(forma) >= 300 and all(abs(float(e) - 1.0) < 1e-6 for e in espaciado):
        return " | ⚠ Vóxel de 1 × 1 × 1 mm: el archivo quizá no trae el tamaño real; las medidas en mm no son fiables"
    return ""


def generar_volumen_sintetico() -> Tuple[np.ndarray, Tuple[float, float, float]]:
    """Genera un fantoma volumétrico sintético en caso de que no exista el estudio DICOM en disco."""
    z, y, x = np.ogrid[-40:40:80j, -50:50:100j, -50:50:100j]
    r = np.sqrt(x**2 + y**2 + z**2)

    volumen = np.zeros((80, 100, 100), dtype=np.float32) - 1000.0  # Aire
    volumen[r <= 45] = 40.0    # Tejido blando
    volumen[r <= 30] = 800.0   # Hueso cortical
    volumen[r <= 15] = 1800.0  # Esmalte dental / alta densidad

    espaciado = (1.0, 0.5, 0.5)
    return volumen, espaciado


class MainWindow(QMainWindow):
    """Ventana principal que gestiona las vistas 2D y 3D del estudio tomográfico."""

    def __init__(self, ruta_dicom: str = "data/raw/PreDentalSurgery.gipl.gz", parent: QWidget | None = None):
        super().__init__(parent)
        self.ruta_dicom = ruta_dicom

        self.setWindowTitle("Explorador Tomográfico CBCT — Visual Computing")
        self.resize(1380, 880)
        self.setMinimumSize(950, 620)

        # Asignar ícono personalizado médico de la aplicación
        self.icono_app = crear_icono_medico()
        self.setWindowIcon(self.icono_app)

        # Configurar tema oscuro médico de Matplotlib
        configurar_estilo_matplotlib()

        # Componentes del visor 2D y 3D
        self.canvas_2d: FigureCanvasQTAgg | None = None
        self.visor_cortes: VisorCortes | None = None
        self.widget_2d: QWidget | None = None
        self.panel_3d: QtInteractor | None = None
        self.splitter: QSplitter | None = None
        self.panel_controles: QFrame | None = None
        # Motor de render 3D que será inicializado después de cargar datos.
        self.render3d: Render3D | None = None
        # Contenedor del panel 3D: barra de estructuras + QtInteractor
        self.contenedor_3d: QWidget | None = None
        self.barra_presets_3d: QHBoxLayout | None = None
        self.grupo_presets_3d: QButtonGroup | None = None
        # Controles del 3D: umbral libre, luz, suavizado, plano de corte y rendimiento
        self.slider_umbral_3d: QSlider | None = None
        self.lbl_umbral_3d: QLabel | None = None
        self.btn_phong: QPushButton | None = None
        self.btn_taubin: QPushButton | None = None
        self.btn_corte: QPushButton | None = None
        self.lbl_rendimiento: QLabel | None = None

        # Botones de navegación y vistas
        self.btn_cargar: QPushButton | None = None
        self.btn_2d: QPushButton | None = None
        self.btn_3d: QPushButton | None = None
        self.btn_dividido: QPushButton | None = None
        self.grupo_vistas: QButtonGroup | None = None

        # Controles interactivos QSlider
        self.slider_z: QSlider | None = None
        self.slider_y: QSlider | None = None
        self.slider_x: QSlider | None = None
        self.escala: str | None = None   # escala de densidad del estudio cargado
        self.slider_centro: QSlider | None = None
        self.slider_ancho: QSlider | None = None

        # Etiquetas de valores en tiempo real
        self.lbl_val_z: QLabel | None = None
        self.lbl_val_y: QLabel | None = None
        self.lbl_val_x: QLabel | None = None
        self.lbl_val_centro: QLabel | None = None
        self.lbl_val_ancho: QLabel | None = None

        self._inicializar_ui()
        self._cargar_datos_y_visor()

    def _inicializar_ui(self):
        """Construye la barra superior, el splitter horizontal y los contenedores de vistas."""
        # 1. Barra superior de navegación (Top Toolbar)
        toolbar = QToolBar("Herramientas de Visualización", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        lbl_logo = QLabel("<b>EXPLORADOR CBCT</b>")
        lbl_logo.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold; margin-right: 15px;")
        toolbar.addWidget(lbl_logo)

        # Botón para Cargar Otra Tomografía DICOM
        self.btn_cargar = QPushButton("📁 Cargar Estudio")
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

        # 2. Contenedor Principal con QSplitter horizontal
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        layout_principal = QVBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        self.setCentralWidget(central_widget)

        # QSplitter horizontal entre el contenedor 2D y el contenedor 3D
        self.splitter = QSplitter(Qt.Orientation.Horizontal, central_widget)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setOpaqueResize(True)
        self.splitter.setHandleWidth(8)
        self.splitter.splitterMoved.connect(self._al_mover_divisor)
        layout_principal.addWidget(self.splitter)

        # Contenedor para el Visor 2D (Cortes)
        self.widget_2d = QWidget(self.splitter)
        layout_2d = QVBoxLayout(self.widget_2d)
        layout_2d.setContentsMargins(6, 6, 6, 6)
        layout_2d.setSpacing(6)

        # Canvas Matplotlib para los 3 cortes ortogonales
        figura = Figure(facecolor="#1e1e1e")
        self.canvas_2d = FigureCanvasQTAgg(figura)
        self.canvas_2d.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout_2d.addWidget(self.canvas_2d, stretch=1)

        # Tarjeta/Panel de controles 2D (Sliders orgánicos + Presets Hounsfield)
        self.panel_controles = self._crear_panel_controles_2d(self.widget_2d)
        layout_2d.addWidget(self.panel_controles, stretch=0)

        # Contenedor del panel 3D interactivo: barra de estructuras arriba, render abajo
        self.contenedor_3d = QWidget(self.splitter)
        layout_3d = QVBoxLayout(self.contenedor_3d)
        layout_3d.setContentsMargins(0, 0, 0, 0)
        layout_3d.setSpacing(6)
        # La barra de estructuras va en un área con desplazamiento horizontal: en la
        # vista dividida el panel es angosto y los botones se cortaban.
        barra = QWidget()
        # Sin hoja de estilos propia: una local tapaba el estilo "checked" de los botones
        barra.setAutoFillBackground(False)
        self.barra_presets_3d = QHBoxLayout(barra)
        self.barra_presets_3d.setContentsMargins(8, 6, 8, 0)
        self.barra_presets_3d.setSpacing(6)
        desplazable = QScrollArea(self.contenedor_3d)
        desplazable.setWidget(barra)
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QFrame.Shape.NoFrame)
        desplazable.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        desplazable.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        desplazable.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        desplazable.setFixedHeight(barra.sizeHint().height() + 34)
        desplazable.viewport().setAutoFillBackground(False)
        layout_3d.addWidget(desplazable)
        layout_3d.addLayout(self._crear_controles_3d())
        self.panel_3d = self._crear_panel_3d(self.contenedor_3d)
        layout_3d.addWidget(self.panel_3d, stretch=1)

        self.splitter.addWidget(self.widget_2d)
        self.splitter.addWidget(self.contenedor_3d)

        # 3. Barra de estado
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Listo.")

        # Por defecto iniciar en Vista 2D (Cortes)
        self.btn_2d.setChecked(True)
        self.mostrar_modo_2d()

    def _crear_panel_controles_2d(self, parent: QWidget) -> QFrame:
        """Crea el panel/tarjeta con sliders orgánicos tipo píldora y presets Hounsfield."""
        panel = QFrame(parent)
        panel.setObjectName("PanelControles")

        layout_panel = QVBoxLayout(panel)
        layout_panel.setContentsMargins(12, 10, 12, 10)
        layout_panel.setSpacing(8)

        # Fila superior: Título del panel y Botones de Presets Hounsfield
        fila_presets = QHBoxLayout()
        fila_presets.setSpacing(10)

        lbl_titulo_seccion = QLabel("<b>🎛️ NAVEGACIÓN MULTICORTE & VENTANA DE CONTRASTE</b>")
        lbl_titulo_seccion.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        fila_presets.addWidget(lbl_titulo_seccion)
        fila_presets.addStretch()

        # Botones de ventana: los valores dependen de la escala del estudio (densidades.VENTANAS_2D)
        btn_preset_dientes = QPushButton("🦷 Dientes / Hueso")
        btn_preset_dientes.setProperty("class", "btn-preset")
        btn_preset_dientes.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_preset_dientes.setToolTip("Ventana dental/ósea (1000/3000 HU, convertida a la escala del estudio)")
        btn_preset_dientes.clicked.connect(lambda: self.aplicar_preset_por_nombre("dientes_hueso"))
        fila_presets.addWidget(btn_preset_dientes)

        btn_preset_blando = QPushButton("🧠 Tejido Blando")
        btn_preset_blando.setProperty("class", "btn-preset")
        btn_preset_blando.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_preset_blando.setToolTip("Ventana de tejido blando (40/400 HU, convertida a la escala del estudio)")
        btn_preset_blando.clicked.connect(lambda: self.aplicar_preset_por_nombre("tejido_blando"))
        fila_presets.addWidget(btn_preset_blando)

        btn_preset_reset = QPushButton("🔄 Reset Ventana")
        btn_preset_reset.setProperty("class", "btn-preset")
        btn_preset_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_preset_reset.setToolTip("Restaurar ventana al rango dinámico completo del estudio")
        btn_preset_reset.clicked.connect(self.reset_ventana)
        fila_presets.addWidget(btn_preset_reset)

        layout_panel.addLayout(fila_presets)

        # Disposición en 2 columnas: Columna izquierda (Cortes Z, Y, X) y Columna derecha (Centro, Ancho)
        fila_sliders = QHBoxLayout()
        fila_sliders.setSpacing(24)

        # --- Columna 1: Navegación de Cortes Ortogonales (Z, Y, X) ---
        col_cortes = QVBoxLayout()
        col_cortes.setSpacing(4)

        # Slider Corte Z (Axial - Rojo #e74c3c)
        fila_z_lbl = QHBoxLayout()
        lbl_z = QLabel("<span style='color: #e74c3c; font-size: 14px;'>●</span> <b>Corte Axial (Z):</b>")
        lbl_z.setStyleSheet("font-size: 12px; color: #ffffff;")
        self.lbl_val_z = QLabel("0 / 0 (0.0 mm)")
        self.lbl_val_z.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 11px;")
        fila_z_lbl.addWidget(lbl_z)
        fila_z_lbl.addStretch()
        fila_z_lbl.addWidget(self.lbl_val_z)
        col_cortes.addLayout(fila_z_lbl)

        self.slider_z = QSlider(Qt.Orientation.Horizontal)
        self.slider_z.setObjectName("SliderZ")
        self.slider_z.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_z.valueChanged.connect(self._al_mover_slider_z)
        col_cortes.addWidget(self.slider_z)

        # Slider Corte Y (Coronal - Verde #2ecc71)
        fila_y_lbl = QHBoxLayout()
        lbl_y = QLabel("<span style='color: #2ecc71; font-size: 14px;'>●</span> <b>Corte Coronal (Y):</b>")
        lbl_y.setStyleSheet("font-size: 12px; color: #ffffff;")
        self.lbl_val_y = QLabel("0 / 0 (0.0 mm)")
        self.lbl_val_y.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 11px;")
        fila_y_lbl.addWidget(lbl_y)
        fila_y_lbl.addStretch()
        fila_y_lbl.addWidget(self.lbl_val_y)
        col_cortes.addLayout(fila_y_lbl)

        self.slider_y = QSlider(Qt.Orientation.Horizontal)
        self.slider_y.setObjectName("SliderY")
        self.slider_y.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_y.valueChanged.connect(self._al_mover_slider_y)
        col_cortes.addWidget(self.slider_y)

        # Slider Corte X (Sagital - Azul #3498db)
        fila_x_lbl = QHBoxLayout()
        lbl_x = QLabel("<span style='color: #3498db; font-size: 14px;'>●</span> <b>Corte Sagital (X):</b>")
        lbl_x.setStyleSheet("font-size: 12px; color: #ffffff;")
        self.lbl_val_x = QLabel("0 / 0 (0.0 mm)")
        self.lbl_val_x.setStyleSheet("color: #3498db; font-weight: bold; font-size: 11px;")
        fila_x_lbl.addWidget(lbl_x)
        fila_x_lbl.addStretch()
        fila_x_lbl.addWidget(self.lbl_val_x)
        col_cortes.addLayout(fila_x_lbl)

        self.slider_x = QSlider(Qt.Orientation.Horizontal)
        self.slider_x.setObjectName("SliderX")
        self.slider_x.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_x.valueChanged.connect(self._al_mover_slider_x)
        col_cortes.addWidget(self.slider_x)

        fila_sliders.addLayout(col_cortes, stretch=1)

        # --- Columna 2: Ventana y Nivel Hounsfield (Centro, Ancho) ---
        col_ventana = QVBoxLayout()
        col_ventana.setSpacing(4)

        # Slider Centro (Level - Púrpura #9b59b6)
        fila_c_lbl = QHBoxLayout()
        lbl_c = QLabel("<span style='color: #9b59b6; font-size: 14px;'>●</span> <b>Centro (Window Level):</b>")
        lbl_c.setStyleSheet("font-size: 12px; color: #ffffff;")
        self.lbl_val_centro = QLabel("0")
        self.lbl_val_centro.setStyleSheet("color: #9b59b6; font-weight: bold; font-size: 11px;")
        fila_c_lbl.addWidget(lbl_c)
        fila_c_lbl.addStretch()
        fila_c_lbl.addWidget(self.lbl_val_centro)
        col_ventana.addLayout(fila_c_lbl)

        self.slider_centro = QSlider(Qt.Orientation.Horizontal)
        self.slider_centro.setObjectName("SliderCentro")
        self.slider_centro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_centro.valueChanged.connect(self._al_mover_slider_centro)
        col_ventana.addWidget(self.slider_centro)

        # Slider Ancho (Width - Naranja #e67e22)
        fila_a_lbl = QHBoxLayout()
        lbl_a = QLabel("<span style='color: #e67e22; font-size: 14px;'>●</span> <b>Ancho (Window Width):</b>")
        lbl_a.setStyleSheet("font-size: 12px; color: #ffffff;")
        self.lbl_val_ancho = QLabel("0")
        self.lbl_val_ancho.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 11px;")
        fila_a_lbl.addWidget(lbl_a)
        fila_a_lbl.addStretch()
        fila_a_lbl.addWidget(self.lbl_val_ancho)
        col_ventana.addLayout(fila_a_lbl)

        self.slider_ancho = QSlider(Qt.Orientation.Horizontal)
        self.slider_ancho.setObjectName("SliderAncho")
        self.slider_ancho.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_ancho.valueChanged.connect(self._al_mover_slider_ancho)
        col_ventana.addWidget(self.slider_ancho)

        # Espacio inferior para balancear visualmente
        col_ventana.addSpacing(14)
        fila_sliders.addLayout(col_ventana, stretch=1)

        layout_panel.addLayout(fila_sliders)
        return panel

    def _crear_panel_3d(self, parent: QWidget) -> QtInteractor:
        """Crea el panel 3D usando QtInteractor.
        Returns the QtInteractor widget which contains the VTK render window.
        """
        interactor = QtInteractor(parent)
        interactor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Fondo del tema oscuro de la app (el de VTK por defecto es blanco)
        interactor.set_background("#181818")
        return interactor

    def _crear_controles_3d(self) -> QHBoxLayout:
        """Fila bajo las estructuras: umbral libre, Phong, Taubin, plano de corte y rendimiento.

        Responde en vivo las preguntas de la propuesta: la barra muestra cómo la densidad
        elegida se vuelve malla (1), Phong/plano la iluminación (2), el contador el costo
        (3), Taubin el suavizado (4) y el plano de corte el clipping (5).
        """
        fila = QHBoxLayout()
        fila.setContentsMargins(8, 0, 8, 0)
        fila.setSpacing(6)

        titulo = QLabel("Umbral:")
        titulo.setStyleSheet("color: #9aa7b6; font-size: 12px; font-weight: bold;")
        fila.addWidget(titulo)
        self.slider_umbral_3d = QSlider(Qt.Orientation.Horizontal)
        self.slider_umbral_3d.setObjectName("SliderCentro")
        self.slider_umbral_3d.setMinimumWidth(120)
        self.slider_umbral_3d.setToolTip("Densidad libre: la malla se recalcula al soltar la barra")
        # Recalcular en cada paso del arrastre congelaría la app: solo se muestra el valor
        # mientras se arrastra y se recalcula al soltar (o con las flechas del teclado).
        self.slider_umbral_3d.setTracking(False)
        self.slider_umbral_3d.sliderMoved.connect(self._actualizar_etiqueta_umbral_3d)
        self.slider_umbral_3d.valueChanged.connect(self._al_cambiar_umbral_3d)
        fila.addWidget(self.slider_umbral_3d, stretch=1)
        self.lbl_umbral_3d = QLabel("—")
        self.lbl_umbral_3d.setMinimumWidth(48)
        self.lbl_umbral_3d.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        fila.addWidget(self.lbl_umbral_3d)

        def interruptor(texto, ayuda, activo, al_cambiar):
            boton = QPushButton(texto)
            boton.setProperty("class", "btn-preset")
            boton.setCheckable(True)
            boton.setChecked(activo)
            boton.setToolTip(ayuda)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.toggled.connect(al_cambiar)
            fila.addWidget(boton)
            return boton

        self.btn_phong = interruptor("Phong", "Sombreado Phong (suave) o plano (se ven los triángulos)",
                                     True, self._al_cambiar_phong)
        self.btn_taubin = interruptor("Taubin", "Suavizado Taubin de la malla: quita el escalonado sin encogerla",
                                      False, self._al_cambiar_taubin)
        self.btn_corte = interruptor("Corte", "Plano de corte: arrástralo; el interior se ve en rojo",
                                     False, self._al_cambiar_corte)

        self.lbl_rendimiento = QLabel("")
        self.lbl_rendimiento.setToolTip("Triángulos de la malla y tiempo del último cálculo")
        self.lbl_rendimiento.setStyleSheet("color: #9aa7b6; font-size: 11px;")
        fila.addWidget(self.lbl_rendimiento)
        return fila

    @contextmanager
    def _ocupado(self, mensaje: str):
        """Cursor de espera y aviso en la barra de estado mientras dura un cálculo largo."""
        self.statusBar.showMessage(mensaje)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()      # que el aviso se pinte antes de bloquear
        try:
            yield
        finally:
            QApplication.restoreOverrideCursor()

    def _mostrar_en_3d(self, estudio_o_tupla):
        """Dibuja el estudio en el panel 3D y arma la barra de estructuras.

        Con un Estudio, Render3D conoce su escala, arranca en el preset "hueso" y ofrece
        los presets de esa escala; con una tupla (volumen sintético) solo hay umbral libre.
        """
        if self.render3d is None:
            self.render3d = Render3D(self.panel_3d)
        self.render3d.mostrar(estudio_o_tupla)
        self._reconstruir_barra_presets_3d()
        # El estudio nuevo arranca sin plano de corte (Render3D.mostrar lo quita)
        self.btn_corte.blockSignals(True)
        self.btn_corte.setChecked(False)
        self.btn_corte.blockSignals(False)
        volumen = self.render3d.volumen
        self.slider_umbral_3d.blockSignals(True)
        self.slider_umbral_3d.setRange(int(np.floor(volumen.min())), int(np.ceil(volumen.max())))
        self.slider_umbral_3d.setSingleStep(10)
        self.slider_umbral_3d.setPageStep(100)
        self.slider_umbral_3d.blockSignals(False)
        self._sincronizar_controles_3d()
        self.panel_3d.render()

    def _sincronizar_controles_3d(self):
        """Lleva la barra de umbral y el contador de rendimiento al estado de Render3D."""
        if self.render3d is None or self.render3d.umbral_actual is None:
            return
        valor = int(round(self.render3d.umbral_actual))
        self.slider_umbral_3d.blockSignals(True)
        self.slider_umbral_3d.setValue(valor)
        self.slider_umbral_3d.blockSignals(False)
        self._actualizar_etiqueta_umbral_3d(valor)
        medicion = self.render3d.ultima_medicion
        self.lbl_rendimiento.setText(f"{medicion['triangulos']:,} triáng. · {medicion['ms']:.0f} ms"
                                     .replace(",", "."))

    def _actualizar_etiqueta_umbral_3d(self, valor: int):
        self.lbl_umbral_3d.setText(f"{valor} {unidad_de(self.escala)}".strip())

    def _al_cambiar_umbral_3d(self, valor: int):
        if self.render3d is None:
            return
        with self._ocupado(f"Calculando la superficie en {valor}…"):
            self.render3d.set_umbral(valor)
            self.panel_3d.render()
        # El umbral libre no corresponde a ningún botón de estructura
        if self.grupo_presets_3d is not None:
            self.grupo_presets_3d.setExclusive(False)
            for boton in self.grupo_presets_3d.buttons():
                boton.setChecked(False)
            self.grupo_presets_3d.setExclusive(True)
        self._sincronizar_controles_3d()
        self.statusBar.showMessage(f"Umbral libre 3D: {valor} {unidad_de(self.escala)}".strip())

    def _al_cambiar_phong(self, activo: bool):
        if self.render3d is None:
            return
        self.render3d.set_phong(activo)
        self.panel_3d.render()
        self.statusBar.showMessage("Sombreado Phong" if activo else "Sombreado plano: un tono por triángulo")

    def _al_cambiar_taubin(self, activo: bool):
        if self.render3d is None:
            return
        with self._ocupado("Suavizando la malla…" if activo else "Quitando el suavizado…"):
            self.render3d.set_suavizar_malla(activo)
            self.panel_3d.render()
        self._sincronizar_controles_3d()
        self.statusBar.showMessage("Suavizado Taubin activo" if activo else "Suavizado Taubin desactivado")

    def _al_cambiar_corte(self, activo: bool):
        if self.render3d is None or self.render3d.malla is None:
            return
        if activo:
            self.render3d.activar_corte()
            self.statusBar.showMessage("Plano de corte: arrastra el plano o su flecha; el interior se ve en rojo")
        else:
            self.render3d.desactivar_corte()
            self.statusBar.showMessage("Plano de corte desactivado")
        self.panel_3d.render()

    def _marcar_presets_en_histograma(self):
        """Marca en el histograma 2D dónde empieza cada estructura (los umbrales del 3D)."""
        if self.render3d is None:
            return
        self.visor_cortes.marcar_densidades({
            nombre.replace("_", " "): (minimo, color_para(nombre))
            for nombre, (minimo, _) in self.render3d.presets.items()
            if nombre not in EXPERIMENTALES and nombre != "esmalte_sin_metal"})

    def _ir_a_arcada(self):
        """Lleva el corte axial al centro de la arcada dental (no a la mitad del volumen).

        La mitad del volumen suele caer en la nariz o los senos; el centro de la arcada
        es la altura con más esmalte, que Render3D ya calculó para sus presets.
        """
        if self.render3d is None or self.render3d.arcada is None:
            return
        z0, z1 = self.render3d.arcada
        self.visor_cortes.ir_a_corte("axial", (z0 + z1) // 2)

    def _reconstruir_barra_presets_3d(self):
        """Un botón por preset del estudio cargado, más "Implante" si hay hueso y metal."""
        while self.barra_presets_3d.count():
            item = self.barra_presets_3d.takeAt(0)
            widget = item.widget()
            if widget:
                # deleteLater solo borra al volver al bucle de eventos: hasta entonces el
                # botón viejo seguía visible debajo del nuevo. Se saca de la barra ya.
                widget.setParent(None)
                widget.deleteLater()
        self.grupo_presets_3d = QButtonGroup(self)
        self.grupo_presets_3d.setExclusive(True)

        presets = list(self.render3d.presets)
        if not presets:
            aviso = QLabel("Escala desconocida: sin presets 3D")
            aviso.setStyleSheet("color: #9aa7b6; font-size: 12px;")
            self.barra_presets_3d.addWidget(aviso)
            self.barra_presets_3d.addStretch()
            return

        titulo = QLabel("Estructura 3D:")
        titulo.setStyleSheet("color: #9aa7b6; font-size: 12px; font-weight: bold;")
        self.barra_presets_3d.addWidget(titulo)
        cortos = {"esmalte_sin_metal": "Sin metal", "hueso_denso": "Hueso denso"}
        opciones = [(n, cortos.get(n, n.replace("_", " ").capitalize()))
                    for n in presets if n not in EXPERIMENTALES]
        if all(n in presets for n, _ in CAPAS_IMPLANTE):
            opciones.append(("implante", "Implante"))
        if all(n in presets for n, _ in CAPAS_BLANDAS):
            opciones.append(("blandos", "Blandos (exp.)"))
        for nombre, texto in opciones:
            boton = QPushButton(texto)
            boton.setProperty("class", "btn-preset")
            boton.setCheckable(True)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            if nombre == "blandos":
                boton.setToolTip("Experimental: músculo y grasa con media cabeza (corte sagital)")
            boton.setChecked(nombre == self.render3d.preset_actual)
            boton.clicked.connect(lambda _=False, n=nombre: self._aplicar_preset_3d(n))
            self.grupo_presets_3d.addButton(boton)
            self.barra_presets_3d.addWidget(boton)
        self.barra_presets_3d.addStretch()

    def _aplicar_preset_3d(self, nombre: str):
        if self.render3d is None:
            return
        texto = nombre.replace("_", " ")
        try:
            with self._ocupado(f"Calculando {texto}…"):
                if nombre == "implante":
                    self.render3d.aplicar_capas()
                elif nombre == "blandos":
                    self.render3d.aplicar_capas(CAPAS_BLANDAS, corte_sagital=True)
                else:
                    self.render3d.aplicar_preset(nombre)
                self.panel_3d.render()
        except Exception as e:
            QMessageBox.warning(self, "Error en la vista 3D", f"No se pudo dibujar '{texto}'.\n\nDetalle: {e}")
            self.statusBar.showMessage(f"Error en la vista 3D: {e}")
            return
        self._sincronizar_controles_3d()
        self.statusBar.showMessage(f"Estructura 3D: {texto}")

    def _abrir_dialogo_cargar_dicom(self):
        """Abre un diálogo para elegir un archivo de volumen o un corte DICOM.

        Si se elige un .dcm se carga la carpeta completa de esa serie.
        """
        dir_inicial = os.path.dirname(self.ruta_dicom) or "data/raw"
        if not os.path.isdir(dir_inicial):
            dir_inicial = os.getcwd()

        patrones = " ".join(f"*{ext}" for ext in EXTENSIONES_VOLUMEN)
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar estudio (volumen o un corte de la serie DICOM)",
            dir_inicial,
            f"Estudios ({patrones} *.dcm);;Volúmenes ({patrones});;Serie DICOM (*.dcm);;Todos (*)",
        )

        if ruta:
            if ruta.lower().endswith(".dcm"):
                ruta = str(Path(ruta).parent)
            self.cargar_nuevo_estudio(ruta)

    def cargar_nuevo_estudio(self, ruta_carpeta: str):
        """Carga un estudio (carpeta DICOM o archivo de volumen) y actualiza el visor."""
        try:
            with self._ocupado(f"Cargando {Path(ruta_carpeta).name}… (puede tardar unos segundos)"):
                estudio = cargar_estudio(ruta_carpeta)
                volumen, espaciado = estudio.volumen, estudio.espaciado
                self.ruta_dicom = ruta_carpeta
                self.escala = estudio.metadatos.get("escala")

                # Actualizar VisorCortes manteniendo relación de aspecto exacta
                self.visor_cortes.mostrar((volumen, espaciado))
                # Y el modelo 3D con el estudio completo (escala y presets)
                self._mostrar_en_3d(estudio)
                self._ir_a_arcada()
                self._marcar_presets_en_histograma()
                self._sincronizar_sliders_con_datos()
                self.visor_cortes.reajustar_tamano()

            msg_estado = (
                f"Estudio cargado: {ruta_carpeta} | "
                f"Volumen: {volumen.shape} (Z, Y, X) | "
                f"Espaciado: {espaciado[0]:.2f} x {espaciado[1]:.2f} x {espaciado[2]:.2f} mm"
                + aviso_espaciado(espaciado, volumen.shape)
            )
            self.statusBar.showMessage(msg_estado)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error al cargar estudio",
                f"No se pudo cargar el estudio desde:\n{ruta_carpeta}\n\nDetalle: {e}",
            )
            self.statusBar.showMessage(f"Error al cargar estudio: {e}")

    def _cargar_datos_y_visor(self):
        """Carga el estudio tomográfico inicial e inicializa el VisorCortes de Matplotlib."""
        figura = self.canvas_2d.figure
        self.visor_cortes = VisorCortes(figura, aspect="anatomico", crear_sliders=False)

        # Sincronización bidireccional desde clics en el visor de Matplotlib hacia los QSliders
        self.visor_cortes.on_cambio_corte = self._al_cambiar_corte_desde_visor
        self.visor_cortes.on_cambio_contraste = self._al_cambiar_contraste_desde_visor

        try:
            if not os.path.exists(self.ruta_dicom):
                raise FileNotFoundError(f"Ruta no encontrada: {self.ruta_dicom}")

            estudio = cargar_estudio(self.ruta_dicom)
            volumen, espaciado = estudio.volumen, estudio.espaciado
            self.escala = estudio.metadatos.get("escala")
            para_3d = estudio
            msg_estado = (
                f"Estudio cargado: {self.ruta_dicom} | "
                f"Volumen: {volumen.shape} (Z, Y, X) | "
                f"Espaciado: {espaciado[0]:.2f} x {espaciado[1]:.2f} x {espaciado[2]:.2f} mm"
                + aviso_espaciado(espaciado, volumen.shape)
            )
            self.statusBar.showMessage(msg_estado)
        except Exception as e:
            volumen, espaciado = generar_volumen_sintetico()
            para_3d = (volumen, espaciado)
            msg_alerta = (
                f"Aviso: No se pudo cargar '{self.ruta_dicom}' ({e}). "
                f"Mostrando volumen sintético de prueba."
            )
            self.statusBar.showMessage(msg_alerta)

        # Mostrar el volumen en ambos visores. Al 3D va el Estudio completo, no la tupla:
        # sin su escala Render3D no tiene presets y el umbral de respaldo cae en el metal.
        self.visor_cortes.mostrar((volumen, espaciado))
        self._mostrar_en_3d(para_3d)
        self._ir_a_arcada()
        self._marcar_presets_en_histograma()
        self._sincronizar_sliders_con_datos()
        self.visor_cortes.reajustar_tamano()

    def _sincronizar_sliders_con_datos(self):
        """Ajusta los rangos y valores de los QSliders según las dimensiones y densidad del volumen."""
        if not self.visor_cortes or self.visor_cortes.volumen is None:
            return

        nz, ny, nx = self.visor_cortes.nz, self.visor_cortes.ny, self.visor_cortes.nx
        vol = self.visor_cortes.volumen
        min_hu = int(np.floor(vol.min()))
        max_hu = int(np.ceil(vol.max()))
        rango_hu = max_hu - min_hu if max_hu > min_hu else 100

        # Rango de cortes anatómicos
        self.slider_z.blockSignals(True)
        self.slider_z.setRange(0, max(nz - 1, 0))
        self.slider_z.setValue(self.visor_cortes.idx_z)
        self.slider_z.blockSignals(False)
        self._actualizar_etiqueta_z(self.visor_cortes.idx_z)

        self.slider_y.blockSignals(True)
        self.slider_y.setRange(0, max(ny - 1, 0))
        self.slider_y.setValue(self.visor_cortes.idx_y)
        self.slider_y.blockSignals(False)
        self._actualizar_etiqueta_y(self.visor_cortes.idx_y)

        self.slider_x.blockSignals(True)
        self.slider_x.setRange(0, max(nx - 1, 0))
        self.slider_x.setValue(self.visor_cortes.idx_x)
        self.slider_x.blockSignals(False)
        self._actualizar_etiqueta_x(self.visor_cortes.idx_x)

        # Rango de ventana y nivel (con margen para permitir presets médicos)
        min_slider_c = min(min_hu - 200, -1024)
        max_slider_c = max(max_hu + 500, 3071)
        max_slider_a = max(int(rango_hu * 1.5), 4000)

        self.slider_centro.blockSignals(True)
        self.slider_centro.setRange(min_slider_c, max_slider_c)
        self.slider_centro.setValue(int(round(self.visor_cortes.centro)))
        self.slider_centro.blockSignals(False)
        self._actualizar_etiqueta_centro(int(round(self.visor_cortes.centro)))

        self.slider_ancho.blockSignals(True)
        self.slider_ancho.setRange(1, max_slider_a)
        self.slider_ancho.setValue(int(round(self.visor_cortes.ancho)))
        self.slider_ancho.blockSignals(False)
        self._actualizar_etiqueta_ancho(int(round(self.visor_cortes.ancho)))

    # ==========================================================================
    # EVENTOS DE SLIDERS Y SINCRONIZACIÓN
    # ==========================================================================

    def _al_mover_slider_z(self, val: int):
        if self.visor_cortes:
            self.visor_cortes.ir_a_corte("axial", val)
        self._actualizar_etiqueta_z(val)

    def _al_mover_slider_y(self, val: int):
        if self.visor_cortes:
            self.visor_cortes.ir_a_corte("coronal", val)
        self._actualizar_etiqueta_y(val)

    def _al_mover_slider_x(self, val: int):
        if self.visor_cortes:
            self.visor_cortes.ir_a_corte("sagital", val)
        self._actualizar_etiqueta_x(val)

    def _al_mover_slider_centro(self, val: int):
        if self.visor_cortes and self.slider_ancho:
            self.visor_cortes.set_ventana(val, self.slider_ancho.value())
        self._actualizar_etiqueta_centro(val)

    def _al_mover_slider_ancho(self, val: int):
        if self.visor_cortes and self.slider_centro:
            self.visor_cortes.set_ventana(self.slider_centro.value(), val)
        self._actualizar_etiqueta_ancho(val)

    def _actualizar_etiqueta_z(self, idx: int):
        if self.visor_cortes:
            pos_mm = idx * self.visor_cortes.dz
            self.lbl_val_z.setText(f"{idx} / {self.visor_cortes.nz - 1} ({pos_mm:.1f} mm)")

    def _actualizar_etiqueta_y(self, idx: int):
        if self.visor_cortes:
            pos_mm = idx * self.visor_cortes.dy
            self.lbl_val_y.setText(f"{idx} / {self.visor_cortes.ny - 1} ({pos_mm:.1f} mm)")

    def _actualizar_etiqueta_x(self, idx: int):
        if self.visor_cortes:
            pos_mm = idx * self.visor_cortes.dx
            self.lbl_val_x.setText(f"{idx} / {self.visor_cortes.nx - 1} ({pos_mm:.1f} mm)")

    def _actualizar_etiqueta_centro(self, val: int):
        self.lbl_val_centro.setText(f"{val} {unidad_de(self.escala)}")

    def _actualizar_etiqueta_ancho(self, val: int):
        self.lbl_val_ancho.setText(f"{val} {unidad_de(self.escala)}")

    def _al_cambiar_corte_desde_visor(self, eje: str, indice: int):
        """Callback invocado cuando el usuario hace clic dentro de Matplotlib."""
        if eje in ("axial", "z") and self.slider_z:
            self.slider_z.blockSignals(True)
            self.slider_z.setValue(indice)
            self.slider_z.blockSignals(False)
            self._actualizar_etiqueta_z(indice)
        elif eje in ("coronal", "y") and self.slider_y:
            self.slider_y.blockSignals(True)
            self.slider_y.setValue(indice)
            self.slider_y.blockSignals(False)
            self._actualizar_etiqueta_y(indice)
        elif eje in ("sagital", "sagittal", "x") and self.slider_x:
            self.slider_x.blockSignals(True)
            self.slider_x.setValue(indice)
            self.slider_x.blockSignals(False)
            self._actualizar_etiqueta_x(indice)

    def _al_cambiar_contraste_desde_visor(self, centro: float, ancho: float):
        """Callback invocado cuando se actualiza la ventana externamente."""
        c_int = int(round(centro))
        a_int = int(round(ancho))
        if self.slider_centro:
            self.slider_centro.blockSignals(True)
            self.slider_centro.setValue(c_int)
            self.slider_centro.blockSignals(False)
            self._actualizar_etiqueta_centro(c_int)
        if self.slider_ancho:
            self.slider_ancho.blockSignals(True)
            self.slider_ancho.setValue(a_int)
            self.slider_ancho.blockSignals(False)
            self._actualizar_etiqueta_ancho(a_int)

    # ==========================================================================
    # PRESETS HOUNSFIELD
    # ==========================================================================

    def aplicar_preset_ventana(self, centro: int, ancho: int):
        """Aplica un preset Hounsfield estándar ajustando sliders y redibujando."""
        if self.slider_centro:
            if centro < self.slider_centro.minimum():
                self.slider_centro.setMinimum(centro - 200)
            if centro > self.slider_centro.maximum():
                self.slider_centro.setMaximum(centro + 200)
            self.slider_centro.setValue(centro)

        if self.slider_ancho:
            if ancho > self.slider_ancho.maximum():
                self.slider_ancho.setMaximum(ancho + 500)
            self.slider_ancho.setValue(ancho)

        if self.visor_cortes:
            self.visor_cortes.set_ventana(centro, ancho)

        self._actualizar_etiqueta_centro(centro)
        self._actualizar_etiqueta_ancho(ancho)
        u = unidad_de(self.escala)
        self.statusBar.showMessage(f"Preset aplicado: Centro {centro} {u}, Ancho {ancho} {u}")

    def aplicar_preset_por_nombre(self, nombre: str):
        """Aplica una ventana de densidades.VENTANAS_2D en la escala del estudio cargado."""
        ventana = ventana_para(self.escala, nombre)
        if ventana is None:
            self.statusBar.showMessage("Escala del estudio desconocida: ajusta la ventana a mano")
            return
        self.aplicar_preset_ventana(*ventana)

    def reset_ventana(self):
        """Restablece los sliders y el contraste al rango completo del estudio."""
        if not self.visor_cortes:
            return
        centro, ancho = self.visor_cortes.reset_ventana()
        c_int = int(round(centro))
        a_int = int(round(ancho))
        if self.slider_centro:
            self.slider_centro.setValue(c_int)
        if self.slider_ancho:
            self.slider_ancho.setValue(a_int)
        self._actualizar_etiqueta_centro(c_int)
        self._actualizar_etiqueta_ancho(a_int)
        u = unidad_de(self.escala)
        self.statusBar.showMessage(f"Ventana reiniciada: Centro {c_int} {u}, Ancho {a_int} {u}")

    # ==========================================================================
    # MANEJO DE VISTAS Y DIVISOR (QSPLITTER)
    # ==========================================================================

    def _al_mover_divisor(self, pos: int, index: int):
        """Reajusta la figura anatómica al arrastrar libremente la barra del splitter."""
        if self.visor_cortes:
            self.visor_cortes.reajustar_tamano()

    def resizeEvent(self, event):
        """Reajusta la distribución geométrica exacta al redimensionar la ventana."""
        super().resizeEvent(event)
        if self.visor_cortes:
            self.visor_cortes.reajustar_tamano()

    def mostrar_modo_2d(self):
        """Modo 2D: Expande el VisorCortes a pantalla completa."""
        self.widget_2d.setVisible(True)
        self.contenedor_3d.setVisible(False)
        self.btn_2d.setChecked(True)
        if self.visor_cortes:
            self.visor_cortes.reajustar_tamano()

    def mostrar_modo_3d(self):
        """Modo 3D: Muestra el contenedor de reconstrucción 3D."""
        self.widget_2d.setVisible(False)
        self.contenedor_3d.setVisible(True)
        self.btn_3d.setChecked(True)

    def mostrar_modo_dividido(self):
        """Modo Dividido: Distribuye el ancho libremente con el QSplitter."""
        self.widget_2d.setVisible(True)
        self.contenedor_3d.setVisible(True)
        self.btn_dividido.setChecked(True)

        ancho_total = max(self.splitter.width(), self.width(), 900)
        mitad = ancho_total // 2
        self.splitter.setSizes([mitad, mitad])

        if self.visor_cortes:
            self.visor_cortes.reajustar_tamano()


# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================

def main():
    # Asignar AppUserModelID en Windows para icono en la barra de tareas
    try:
        myappid = "visualcomputing.cbct.medicalviewer.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Interfaz Gráfica Profesional PySide6 para Tomografías CBCT"
    )
    parser.add_argument(
        "carpeta",
        nargs="?",
        default="data/raw/PreDentalSurgery.gipl.gz",
        help="Carpeta DICOM o archivo .gipl.gz / .nii.gz del estudio (por defecto: la muestra de Slicer)",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO_TEMA_OSCURO)

    # Asignar ícono personalizado médico a nivel de aplicación
    icono_app = crear_icono_medico()
    app.setWindowIcon(icono_app)

    ventana = MainWindow(ruta_dicom=args.carpeta)
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
