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


# --- Render3D ---------------------------------------------------------------

def _render_con(estudio_o_tupla):
    import pyvista as pv
    from src.render_3d import Render3D
    r = Render3D(pv.Plotter(off_screen=True))
    r.mostrar(estudio_o_tupla, reduccion=1)
    return r


def _estudio_slicer():
    from src.carga import Estudio
    return Estudio(id="x", volumen=_dos_bloques(), espaciado=ESPACIADO, metadatos={"escala": "slicer"})


def _actor_bounds(r, nombre):
    return r.pl.actors[nombre].GetBounds()


def test_render3d_arranca_en_hueso_y_de_frente():
    r = _render_con(_estudio_slicer())
    assert r.preset_actual == "hueso"
    assert r.umbral_actual == 700
    assert r.pl.camera.up == pytest.approx((0, 0, 1))     # view_xz: z hacia arriba


def test_render3d_preset_aisla_la_banda():
    r = _render_con(_estudio_slicer())
    r.aplicar_preset("esmalte_sin_metal")
    assert _actor_bounds(r, "estructura")[1] < 10        # el bracket (x > 12.5 mm) quedó fuera
    r.aplicar_preset("metal")
    assert _actor_bounds(r, "estructura")[0] > 10        # solo el bracket


def test_render3d_capas_y_vuelta_a_un_preset():
    r = _render_con(_estudio_slicer())
    r.aplicar_capas([("hueso", 0.2), ("metal", 1.0)])
    assert {"capa_hueso", "capa_metal"} <= set(r.pl.actors)
    assert r.pl.actors["capa_hueso"].GetProperty().GetOpacity() == pytest.approx(0.2)
    r.aplicar_preset("dientes")
    assert "capa_hueso" not in r.pl.actors and "capa_metal" not in r.pl.actors


def test_render3d_preset_desconocido_explica_cuales_hay():
    r = _render_con(_estudio_slicer())
    with pytest.raises(KeyError, match="esmalte_sin_metal"):
        r.aplicar_preset("no_existe")


def test_render3d_sin_escala_usa_la_barra_libre():
    r = _render_con((_dos_bloques(), ESPACIADO))
    assert r.presets == {} and r.preset_actual is None
    assert r.umbral_actual == pytest.approx(0.6 * 3000)
    with pytest.raises(KeyError, match="desconocida"):
        r.aplicar_preset("hueso")
