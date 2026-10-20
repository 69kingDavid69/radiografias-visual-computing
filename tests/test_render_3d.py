"""Tests de src/render_3d.py. Correr con: .venv/bin/python -m pytest -q"""
import numpy as np
import pytest

from src.render_3d import superficie_por_banda

ESPACIADO = (0.5, 0.5, 0.5)


def _dos_bloques():
    """Volumen con un "diente" (densidad 1500) a la izquierda y un "bracket" (3000) a la derecha."""
    v = np.zeros((20, 20, 40), dtype=np.float32)
    v[5:15, 5:15, 3:13] = 1500     # x de 1.5 a 6.5 mm
    v[5:15, 5:15, 25:35] = 3000    # x de 12.5 a 17.5 mm
    return v


def test_banda_excluye_lo_que_supera_el_maximo():
    sup = superficie_por_banda(_dos_bloques(), ESPACIADO, 1250, 2000, reduccion=1)
    xmin, xmax = sup.bounds[0], sup.bounds[1]
    assert sup.n_points > 0
    assert xmax < 10, f"la superficie llega a x={xmax:.1f} mm: incluyó el bracket"
    assert xmin == pytest.approx(1.25, abs=0.5)


@pytest.mark.parametrize("maximo", [None, float("inf")])
def test_sin_maximo_incluye_todo_lo_que_supera_el_minimo(maximo):
    sup = superficie_por_banda(_dos_bloques(), ESPACIADO, 1250, maximo, reduccion=1)
    assert sup.bounds[1] > 15, "sin máximo también debería verse el bracket"


def test_banda_vacia_no_falla():
    sup = superficie_por_banda(_dos_bloques(), ESPACIADO, 5000, 6000, reduccion=1)
    assert sup.n_points == 0


def test_reduccion_conserva_posicion_en_mm():
    completa = superficie_por_banda(_dos_bloques(), ESPACIADO, 1250, 2000, reduccion=1)
    reducida = superficie_por_banda(_dos_bloques(), ESPACIADO, 1250, 2000, reduccion=2)
    assert reducida.center == pytest.approx(completa.center, abs=1.0)
