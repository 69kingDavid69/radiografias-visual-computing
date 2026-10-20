"""Tests de src/carga.py. Correr con: .venv/bin/python -m pytest -q"""
import random
import shutil

import numpy as np
import pydicom
import pytest
import SimpleITK as sitk
from pydicom.data import get_testdata_file

from src.carga import Estudio, calcular_dz, cargar_estudio

# Espaciado distinto en cada eje a propósito: si algún eje se invierte, el test falla.
ESPACIADO_XYZ = (0.3, 0.4, 0.5)


def _esfera():
    z, y, x = np.mgrid[:20, :30, :40]
    return (1000 - 30 * np.sqrt((z - 10) ** 2 + (y - 15) ** 2 + (x - 20) ** 2)).astype(np.float32)


@pytest.mark.parametrize("nombre", ["muestra.nii.gz", "muestra.gipl.gz", "muestra.mha"])
def test_volumen_sitk_mantiene_orden_de_ejes(tmp_path, nombre):
    imagen = sitk.GetImageFromArray(_esfera())
    imagen.SetSpacing(ESPACIADO_XYZ)
    sitk.WriteImage(imagen, str(tmp_path / nombre))

    estudio = cargar_estudio(tmp_path / nombre, carpeta_cache=tmp_path / "cache")

    assert isinstance(estudio, Estudio)
    assert estudio.id == "muestra"
    assert estudio.volumen.shape == (20, 30, 40)            # (z, y, x)
    assert estudio.espaciado == pytest.approx((0.5, 0.4, 0.3))  # (dz, dy, dx)
    assert estudio.volumen[10, 15, 20] == pytest.approx(1000)


def test_volumen_no_se_cachea(tmp_path):
    imagen = sitk.GetImageFromArray(_esfera())
    ruta = tmp_path / "muestra.nii.gz"
    sitk.WriteImage(imagen, str(ruta))
    cargar_estudio(ruta, carpeta_cache=tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_cache_dicom_se_reutiliza(tmp_path):
    carpeta = tmp_path / "serie"
    carpeta.mkdir()
    shutil.copy(get_testdata_file("CT_small.dcm"), carpeta)
    cache = tmp_path / "cache"

    primero = cargar_estudio(carpeta, carpeta_cache=cache)
    assert (cache / "serie.npz").exists()
    segundo = cargar_estudio(carpeta, carpeta_cache=cache)

    np.testing.assert_array_equal(primero.volumen, segundo.volumen)
    assert segundo.espaciado == primero.espaciado
    assert segundo.metadatos["formato"] == "DICOM"


def _serie_dicom(carpeta, posiciones_z):
    """Escribe una serie DICOM sintética con los archivos en orden aleatorio.

    Cada corte i tiene todos sus píxeles en i * 10, para poder verificar el orden.
    """
    base = pydicom.dcmread(get_testdata_file("CT_small.dcm"))
    nombres = [f"img_{n:03d}.dcm" for n in range(len(posiciones_z))]
    random.Random(0).shuffle(nombres)
    for i, (z, nombre) in enumerate(zip(posiciones_z, nombres)):
        ds = base.copy()
        ds.ImagePositionPatient = [0, 0, z]
        ds.PixelData = np.full_like(base.pixel_array, i * 10).tobytes()
        ds.save_as(carpeta / nombre)


def test_serie_dicom_se_ordena_por_z(tmp_path):
    _serie_dicom(tmp_path, [0.0, 2.5, 5.0, 7.5, 10.0])
    estudio = cargar_estudio(tmp_path, usar_cache=False)

    assert estudio.volumen.shape[0] == 5
    columna = estudio.volumen[:, 0, 0]
    assert np.all(np.diff(columna) > 0), "los cortes no quedaron ordenados por z"
    assert estudio.espaciado[0] == pytest.approx(2.5)


def test_dicom_reescala_a_densidad(tmp_path):
    shutil.copy(get_testdata_file("CT_small.dcm"), tmp_path)
    estudio = cargar_estudio(tmp_path, usar_cache=False)
    assert estudio.metadatos["formato"] == "DICOM"
    assert estudio.volumen.min() == pytest.approx(-896)   # ya en densidad, no el valor crudo


def test_carpeta_vacia(tmp_path):
    with pytest.raises(FileNotFoundError):
        cargar_estudio(tmp_path, usar_cache=False)


def test_formato_no_soportado(tmp_path):
    ruta = tmp_path / "foto.png"
    ruta.write_bytes(b"no es un volumen")
    with pytest.raises(ValueError):
        cargar_estudio(ruta, usar_cache=False)


# --- calcular_dz (la parte de David) ---

def test_dz_uniforme():
    assert calcular_dz([0.0, 0.5, 1.0, 1.5]) == pytest.approx(0.5)


def test_dz_uniforme_sin_advertencia(recwarn):
    calcular_dz([10.0, 10.3, 10.6, 10.9])
    assert len(recwarn) == 0


def test_dz_con_corte_faltante_advierte():
    with pytest.warns(UserWarning):
        dz = calcular_dz([0.0, 0.5, 1.0, 2.0, 2.5])   # falta el corte en 1.5
    assert dz == pytest.approx(0.5)


def test_dz_con_corte_repetido_advierte():
    with pytest.warns(UserWarning):
        calcular_dz([0.0, 0.5, 0.5, 1.0])
