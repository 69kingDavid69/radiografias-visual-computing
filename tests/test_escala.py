"""Tests de src/escala.py. Correr con: .venv/bin/python -m pytest -q"""
import json

import numpy as np
import pytest
import SimpleITK as sitk

from src.carga import Estudio, cargar_estudio
from src.escala import REFERENCIA, asignar_escala, picos_aire_y_blando


def _cabeza(aire, blando, hueso, seed=0):
    """Volumen tipo CBCT de cabeza en una escala cualquiera: mucho aire, una "cabeza"
    de tejido blando y un núcleo de hueso, con un poco de ruido."""
    rng = np.random.default_rng(seed)
    v = np.full((40, 40, 40), aire, dtype=np.float32)
    v[5:35, 5:35, 5:35] = blando
    v[15:25, 15:25, 15:25] = hueso
    ruido = 0.02 * abs(blando - aire)
    return v + rng.normal(0, ruido, size=v.shape).astype(np.float32)


def _estudio(volumen, id="x"):
    return Estudio(id=id, volumen=volumen, espaciado=(0.5, 0.5, 0.5), metadatos={"formato": "GIPL"})


def test_encuentra_los_picos():
    aire, blando = picos_aire_y_blando(_cabeza(-2200, 0, 1600))
    assert aire == pytest.approx(-2200, abs=60)
    assert blando == pytest.approx(0, abs=60)


@pytest.mark.parametrize("aire,blando,hueso", [
    (0, 410, 700),          # ya en la escala de referencia (como la muestra Pre)
    (-2200, 0, 1550),       # como la muestra Post
    (-1000, 40, 776),       # Hounsfield
])
def test_normaliza_a_la_referencia(aire, blando, hueso):
    e = asignar_escala(_estudio(_cabeza(aire, blando, hueso)), registro="/no/existe.json")
    v = e.volumen
    assert e.metadatos["escala"] == REFERENCIA["escala"]
    assert np.median(v[0:3, 0:3, 0:3]) == pytest.approx(REFERENCIA["aire"], abs=25)      # aire
    assert np.median(v[6:12, 6:12, 6:12]) == pytest.approx(REFERENCIA["blando"], abs=25)  # blando
    # El hueso cae cerca de 700, el umbral de "hueso" en la escala slicer.
    assert np.median(v[17:23, 17:23, 17:23]) == pytest.approx(700, abs=60)


def test_escala_declarada_gana_y_no_toca_el_volumen(tmp_path):
    registro = tmp_path / "estudios.json"
    registro.write_text(json.dumps({"tf3_001": {"escala": "hounsfield"}}))
    original = _cabeza(-1000, 40, 776)
    e = asignar_escala(_estudio(original.copy(), id="tf3_001"), registro=registro)
    assert e.metadatos["escala"] == "hounsfield"
    assert e.metadatos["normalizacion"] is None
    np.testing.assert_array_equal(e.volumen, original)


def test_histograma_sin_forma_queda_sin_escala():
    plano = np.full((20, 20, 20), 500, dtype=np.float32)
    with pytest.warns(UserWarning):
        e = asignar_escala(_estudio(plano), registro="/no/existe.json")
    assert e.metadatos["escala"] is None


def test_cargar_estudio_normaliza_por_defecto(tmp_path):
    imagen = sitk.GetImageFromArray(_cabeza(-2200, 0, 1550))
    sitk.WriteImage(imagen, str(tmp_path / "post.nii.gz"))
    e = cargar_estudio(tmp_path / "post.nii.gz", registro=tmp_path / "vacio.json")
    assert e.metadatos["escala"] == "slicer"
    assert e.metadatos["normalizacion"]["a"] == pytest.approx(410 / 2200, rel=0.05)
