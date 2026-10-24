"""Tests de src/orientacion.py y de la orientación que lee src/carga.py."""
import numpy as np
import pytest
import SimpleITK as sitk

from src.carga import cargar_estudio
from src.orientacion import (OPUESTA, direccion_de_dicom, etiquetas_corte, orientacion_de_direccion,
                             texto)

IDENTIDAD = (1, 0, 0, 0, 1, 0, 0, 0, 1)


def test_direccion_identidad_es_lps_y_la_invertida_ras():
    assert orientacion_de_direccion(IDENTIDAD) == "LPS"
    assert orientacion_de_direccion((-1, 0, 0, 0, -1, 0, 0, 0, 1)) == "RAS"


def test_dicom_axial_estandar_es_lps_y_con_filas_invertidas_ras():
    assert orientacion_de_direccion(direccion_de_dicom([1, 0, 0, 0, 1, 0])) == "LPS"
    assert orientacion_de_direccion(direccion_de_dicom([-1, 0, 0, 0, -1, 0])) == "RAS"


def test_letras_de_cada_corte_en_lps():
    # Convención radiológica: el lado derecho del paciente queda a la izquierda de la imagen.
    assert etiquetas_corte("LPS", "axial") == ("R", "L", "A", "P")
    assert etiquetas_corte("LPS", "coronal") == ("R", "L", "S", "I")
    assert etiquetas_corte("LPS", "sagital") == ("A", "P", "S", "I")


def test_letras_siguen_a_un_eje_invertido():
    # NIfTI de STS: y crece hacia adelante ("LAS"), así que arriba en el axial es posterior.
    assert etiquetas_corte("LAS", "axial") == ("R", "L", "P", "A")
    assert etiquetas_corte("LAS", "sagital") == ("P", "A", "S", "I")


def test_plano_desconocido():
    with pytest.raises(ValueError):
        etiquetas_corte("LPS", "oblicuo")


def test_texto_en_espanol_y_opuestas():
    assert [texto(letra) for letra in "LRAPSI"] == ["Iz", "D", "Ant", "Post", "Sup", "Inf"]
    assert all(OPUESTA[OPUESTA[l]] == l for l in "LRAPSI")


@pytest.mark.parametrize("nombre, esperada, supuesta", [
    ("a.nii.gz", "RAS", False),
    ("b.mha", "RAS", False),
    ("c.gipl.gz", "LPS", True),     # GIPL no guarda la orientación: la identidad es un supuesto
])
def test_cargar_estudio_lee_la_orientacion(tmp_path, nombre, esperada, supuesta):
    imagen = sitk.GetImageFromArray(np.zeros((4, 5, 6), dtype=np.float32))
    if not supuesta:
        imagen.SetDirection((-1, 0, 0, 0, -1, 0, 0, 0, 1))
    sitk.WriteImage(imagen, str(tmp_path / nombre))
    estudio = cargar_estudio(tmp_path / nombre, normalizar=False)
    assert estudio.metadatos["orientacion"] == esperada
    assert estudio.metadatos["orientacion_supuesta"] is supuesta


def test_dicom_sin_orientacion_da_none(tmp_path):
    from src.carga import leer_orientacion
    assert leer_orientacion(tmp_path) is None
