"""Prueba de humo de la aplicación Qt (src/app_qt.py) sin mostrar ventanas.

Arma la ventana con el volumen sintético de respaldo y recorre los controles del 3D.
Se salta si no está PySide6/pyvistaqt (por ejemplo, en un entorno solo de pipeline).
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyvistaqt")


avisos = []


@pytest.fixture(scope="module")
def ventana():
    from PySide6.QtWidgets import QApplication
    import src.app_qt as app_qt
    from src.app_qt import MainWindow
    # Un diálogo modal colgaría la prueba: los avisos se guardan en vez de mostrarse
    app_qt.QMessageBox.warning = staticmethod(lambda *args: avisos.append(args[1:]))
    app = QApplication.instance() or QApplication([])
    w = MainWindow(ruta_dicom="no/existe.gipl.gz")      # cae al volumen sintético
    yield w
    w.panel_3d.close()
    w.close()
    app.processEvents()


def test_arranca_con_volumen_sintetico(ventana):
    assert ventana.visor_cortes.volumen is not None
    assert ventana.render3d is not None and ventana.render3d.malla is not None
    assert "sintético" in ventana.statusBar.currentMessage()


def test_barra_de_umbral_recalcula_la_malla(ventana):
    slider = ventana.slider_umbral_3d
    valor = (slider.minimum() + slider.maximum()) // 3
    slider.setValue(valor)
    assert ventana.render3d.umbral_actual == valor
    assert ventana.lbl_rendimiento.text().endswith("ms")


def test_interruptores_del_3d(ventana):
    ventana.btn_phong.setChecked(False)
    assert ventana.render3d.phong is False
    ventana.btn_taubin.setChecked(True)
    assert ventana.render3d.suavizar_malla is True
    ventana.btn_corte.setChecked(True)
    assert ventana.render3d.corte_activo
    ventana.btn_corte.setChecked(False)
    assert not ventana.render3d.corte_activo


def test_histograma_con_ventana_y_umbrales(ventana):
    visor = ventana.visor_cortes
    assert visor.ax_hist is not None
    visor.marcar_densidades({"prueba": (visor.centro, "#ff0000")})
    assert visor._artistas_marcas, "no se dibujó la marca del umbral"
    visor.set_ventana(visor.centro + 10, 200)
    franja = visor._franja_ventana
    assert franja.get_width() == 200
    assert franja.get_x() == visor.centro - 100


def test_aviso_de_espaciado_sospechoso():
    from src.app_qt import aviso_espaciado
    assert "⚠" in aviso_espaciado((1.0, 1.0, 1.0), (400, 512, 512))
    assert aviso_espaciado((0.5, 0.5, 0.5), (330, 360, 360)) == ""
    assert aviso_espaciado((1.0, 1.0, 1.0), (20, 20, 40)) == ""    # volumen de prueba


def test_cargar_un_segundo_estudio(ventana, tmp_path):
    import numpy as np
    import SimpleITK as sitk
    volumen = np.zeros((40, 50, 50), dtype=np.int16)
    volumen[10:30, 15:35, 15:35] = 1500
    imagen = sitk.GetImageFromArray(volumen)
    imagen.SetSpacing((0.4, 0.4, 0.4))
    ruta = tmp_path / "segundo.nii.gz"
    sitk.WriteImage(imagen, str(ruta))
    ventana.visor_cortes.marcar_densidades({"prueba": (100.0, "#ff0000")})
    ventana.cargar_nuevo_estudio(str(ruta))
    assert ventana.statusBar.currentMessage().startswith("Estudio cargado"), avisos
    assert ventana.visor_cortes.volumen.shape == (40, 50, 50)
    assert ventana.render3d.volumen.shape == (40, 50, 50)
    # Los botones del estudio anterior no quedan debajo de los nuevos
    from PySide6.QtWidgets import QPushButton
    barra = ventana.barra_presets_3d.parentWidget()
    assert len(barra.findChildren(QPushButton)) == len(ventana.grupo_presets_3d.buttons())
