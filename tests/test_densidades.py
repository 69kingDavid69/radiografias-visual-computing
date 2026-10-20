"""Tests de src/densidades.py. Correr con: .venv/bin/python -m pytest -q"""
import numpy as np
import pytest

from src.carga import Estudio
from src.densidades import RANGOS_DENSIDAD, escala_de, presets_para
from src.render_3d import superficie_por_banda


def _estudio(formato, **extra):
    return Estudio(id="x", volumen=np.zeros((2, 2, 2), np.float32),
                   espaciado=(1, 1, 1), metadatos={"formato": formato, **extra})


def test_gipl_usa_presets_de_slicer():
    assert presets_para(_estudio("GIPL")) is RANGOS_DENSIDAD["slicer"]


def test_nifti_usa_presets_en_hounsfield():
    assert presets_para(_estudio("NII")) is RANGOS_DENSIDAD["hounsfield"]


def test_dicom_sin_escala_no_tiene_presets():
    assert escala_de(_estudio("DICOM")) is None
    assert presets_para(_estudio("DICOM")) == {}


def test_escala_explicita_gana_al_formato():
    assert presets_para(_estudio("DICOM", escala="hounsfield")) is RANGOS_DENSIDAD["hounsfield"]


@pytest.mark.parametrize("escala", list(RANGOS_DENSIDAD))
def test_rangos_bien_formados(escala):
    for nombre, (minimo, maximo) in RANGOS_DENSIDAD[escala].items():
        assert minimo < maximo, f"{escala}/{nombre}: el mínimo no es menor que el máximo"


def _corona_y_bracket():
    v = np.zeros((20, 20, 40), dtype=np.float32)
    v[5:15, 5:15, 3:13] = 1600     # corona (x de 1.5 a 6.5 mm)
    v[5:15, 5:15, 25:35] = 3000    # bracket o implante (x de 12.5 a 17.5 mm)
    return v


def test_esmalte_de_slicer_conserva_el_metal():
    minimo, maximo = RANGOS_DENSIDAD["slicer"]["esmalte"]
    sup = superficie_por_banda(_corona_y_bracket(), (0.5, 0.5, 0.5), minimo, maximo, reduccion=1)
    assert sup.bounds[1] > 15, "el preset esmalte debe seguir mostrando brackets e implantes"


def test_esmalte_sin_metal_de_slicer_excluye_el_metal():
    minimo, maximo = RANGOS_DENSIDAD["slicer"]["esmalte_sin_metal"]
    sup = superficie_por_banda(_corona_y_bracket(), (0.5, 0.5, 0.5), minimo, maximo, reduccion=1)
    assert sup.n_points > 0 and sup.bounds[1] < 10
