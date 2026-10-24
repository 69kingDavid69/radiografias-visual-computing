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


def test_render3d_dientes_limitados_a_la_arcada_y_vista_de_blandos():
    import pyvista as pv
    from src.carga import Estudio
    from src.render_3d import CAPAS_BLANDAS, Render3D
    v = np.zeros((120, 30, 30), dtype=np.float32)
    v[5:15, 5:25, 5:25] = 1100            # "cráneo" denso
    v[80:95, 10:20, 10:20] = 1100         # dientes
    v[86:89, 10:20, 10:20] = 1400         # esmalte
    v[40:70, 3:27, 3:27] = np.where(v[40:70, 3:27, 3:27] == 0, 420, v[40:70, 3:27, 3:27])  # "músculo"
    v[40:70, 3:27, 3:5] = 330             # "grasa" en un costado
    r = Render3D(pv.Plotter(off_screen=True))
    r.mostrar(Estudio(id="x", volumen=v, espaciado=ESPACIADO, metadatos={"escala": "slicer"}), reduccion=1)
    assert r.arcada is not None
    r.aplicar_preset("dientes")
    assert _actor_bounds(r, "estructura")[4] > 35       # sin el "cráneo" de arriba (z < 8 mm)
    r.aplicar_capas(CAPAS_BLANDAS, corte_sagital=True)
    assert {"capa_grasa", "capa_musculo"} <= set(r.pl.actors)
    # La mitad que queda es x < centro; la cámara debe estar del lado del corte (+x),
    # mirando el interior y no la cara de perfil.
    assert max(b.GetBounds()[1] for b in (r.pl.actors["capa_grasa"], r.pl.actors["capa_musculo"])) <= 30 * 0.5 / 2 + 0.5
    assert r.pl.camera.position[0] > r.pl.camera.focal_point[0]
    r.aplicar_preset("hueso")
    assert r.pl.camera.up == pytest.approx((0, 0, 1)) and r._vista_lateral is False


def test_banda_se_interpola_y_no_sale_escalonada():
    # Con una máscara 0/1 cada vértice cae justo a mitad de camino entre dos vóxeles
    # (la superficie sale en escalones). Con el campo continuo cae donde la densidad
    # cruza el límite: en cualquier punto del borde entre vóxeles.
    z, y, x = np.mgrid[:30, :30, :30]
    r = np.sqrt((z - 15) ** 2 + (y - 15) ** 2 + (x - 15) ** 2)
    v = (2000 - 100 * r).astype(np.float32)          # densidad que baja suave hacia afuera
    sup = superficie_por_banda(v, (1.0, 1.0, 1.0), 1250, 1700, reduccion=1)
    frac = np.abs(np.asarray(sup.points) % 1.0 - 0.5)
    en_mitades = (frac < 1e-3).all(axis=1).mean()
    assert sup.n_points > 0
    assert en_mitades < 0.1, f"{en_mitades:.0%} de los vértices en mitades exactas: superficie escalonada"


def test_pulido_taubin_no_encoge_la_superficie():
    z, y, x = np.mgrid[:30, :30, :30]
    r = np.sqrt((z - 15) ** 2 + (y - 15) ** 2 + (x - 15) ** 2)
    v = (2000 - 100 * r).astype(np.float32)
    sin = superficie_por_banda(v, (1.0, 1.0, 1.0), 1000, reduccion=1)
    con = superficie_por_banda(v, (1.0, 1.0, 1.0), 1000, reduccion=1, pulido=20)
    ancho = lambda s: s.bounds[1] - s.bounds[0]
    assert ancho(con) == pytest.approx(ancho(sin), rel=0.03)


# --- Opciones de visualización (preguntas 2 a 5 de la propuesta) -----------

def test_cambiar_de_preset_reencuadra_la_camara():
    r = _render_con(_estudio_slicer())
    r.pl.camera.zoom(8)                       # el usuario se acercó mucho
    lejos = r.pl.camera.distance
    r.aplicar_preset("metal")
    assert r.pl.camera.distance != pytest.approx(lejos), "la cámara no se reencuadró"
    x0, x1 = _actor_bounds(r, "estructura")[:2]
    assert r.pl.camera.focal_point[0] == pytest.approx((x0 + x1) / 2, abs=0.5)


def test_phong_y_plano():
    r = _render_con(_estudio_slicer())
    assert r.pl.actors["estructura"].prop.interpolation.name.lower() == "phong"
    r.set_phong(False)
    assert r.pl.actors["estructura"].prop.interpolation.name.lower() == "flat"
    r.aplicar_preset("metal")                 # lo nuevo respeta la opción
    assert r.pl.actors["estructura"].prop.interpolation.name.lower() == "flat"


def test_taubin_redibuja_la_misma_estructura():
    r = _render_con(_estudio_slicer())
    r.aplicar_preset("metal")
    antes = r.pl.actors["estructura"].mapper.dataset.points.copy()
    r.set_suavizar_malla(True)
    assert r.preset_actual == "metal"
    despues = r.pl.actors["estructura"].mapper.dataset.points
    assert despues.shape == antes.shape
    assert not np.allclose(despues, antes), "Taubin no movió ningún vértice"
    # Taubin no encoge: el tamaño del bracket se conserva (±10 %)
    tam = lambda p: p.max(axis=0) - p.min(axis=0)
    assert tam(despues) == pytest.approx(tam(antes), rel=0.1)


def test_plano_de_corte_se_aplica_y_se_quita():
    r = _render_con(_estudio_slicer())
    r.activar_corte("x")
    mapper = r.pl.actors["estructura"].mapper
    assert r.corte_activo and mapper.GetNumberOfClippingPlanes() == 1
    r.aplicar_preset("metal")                 # también a lo que se dibuja después
    assert r.pl.actors["estructura"].mapper.GetNumberOfClippingPlanes() == 1
    r.desactivar_corte()
    assert not r.corte_activo
    assert r.pl.actors["estructura"].mapper.GetNumberOfClippingPlanes() == 0


def test_medicion_cuenta_triangulos():
    r = _render_con(_estudio_slicer())
    r.aplicar_preset("metal")
    medicion = r.ultima_medicion
    assert medicion["triangulos"] == r.pl.actors["estructura"].mapper.dataset.n_cells > 0
    assert medicion["ms"] >= 0
    r.set_umbral(5000)                        # por encima de todo: no hay malla
    assert r.ultima_medicion["triangulos"] == 0


def test_reduccion_automatica_segun_el_tamano():
    from src.render_3d import reduccion_para
    assert reduccion_para((330, 360, 360)) == 2          # el Post: como siempre
    assert reduccion_para((400, 512, 512)) == 3          # cabeza completa de STS
    assert reduccion_para((20, 20, 40), minima=1) == 1   # volúmenes chicos: sin cambio


def test_umbral_libre_usa_el_color_del_tejido():
    from src.densidades import color_para
    r = _render_con(_estudio_slicer())
    r.set_umbral(2500)                                   # zona de metal
    assert r._color_para_umbral(2500) == color_para("metal")
    assert r._color_para_umbral(-5000) == "ivory"
