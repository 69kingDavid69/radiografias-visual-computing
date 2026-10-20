"""Tests de src/filtros.py. Correr con: .venv/bin/python -m pytest -q"""
import numpy as np
import pytest

from src.filtros import suavizar
from src.render_3d import superficie_por_banda


def test_sigma_cero_no_cambia_nada():
    v = np.random.default_rng(0).normal(size=(8, 8, 8)).astype(np.float32)
    assert suavizar(v, (1, 1, 1), 0) is v


def test_conserva_forma_y_reduce_ruido():
    v = np.random.default_rng(0).normal(1000, 100, size=(30, 30, 30)).astype(np.float32)
    s = suavizar(v, (0.5, 0.5, 0.5), 1.0)
    assert s.shape == v.shape
    assert s.mean() == pytest.approx(v.mean(), rel=0.01)
    assert s.std() < v.std() / 3


def test_sigma_es_en_milimetros_por_eje():
    # Vóxel de 1 mm en z y 0.25 mm en x: el mismo sigma en mm debe abarcar
    # 4 veces más vóxeles en x que en z. Si el espaciado se invirtiera, sería al revés.
    v = np.zeros((41, 41, 41), dtype=np.float32)
    v[20, 20, 20] = 1.0
    s = suavizar(v, (1.0, 0.5, 0.25), 2.0)
    idx = np.arange(41) - 20
    perfil_z, perfil_x = s[:, 20, 20], s[20, 20, :]
    ancho_z = np.sqrt((perfil_z * idx**2).sum() / perfil_z.sum())   # en vóxeles
    ancho_x = np.sqrt((perfil_x * idx**2).sum() / perfil_x.sum())
    assert ancho_z == pytest.approx(2.0, rel=0.2)    # 2 mm / 1 mm
    assert ancho_x == pytest.approx(8.0, rel=0.2)    # 2 mm / 0.25 mm


def test_suavizado_reduce_pedazos_sueltos():
    rng = np.random.default_rng(0)
    v = np.zeros((40, 40, 40), dtype=np.float32)
    v[10:30, 10:30, 10:30] = 1000                       # un bloque de "hueso"
    v += rng.normal(0, 300, size=v.shape).astype(np.float32)  # ruido que crea islas

    def pedazos(sup):
        return int(sup.connectivity().point_data["RegionId"].max()) + 1

    sin = superficie_por_banda(v, (0.5, 0.5, 0.5), 700, reduccion=1)
    con = superficie_por_banda(v, (0.5, 0.5, 0.5), 700, reduccion=1, suavizado_mm=0.5)
    assert pedazos(con) < pedazos(sin) / 5
