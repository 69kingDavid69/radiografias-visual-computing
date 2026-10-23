"""Tests de src/densidades.py. Correr con: .venv/bin/python -m pytest -q"""
import numpy as np
import pytest

from src.carga import Estudio
from src.densidades import RANGOS_DENSIDAD, escala_de, presets_para, suavizado_para
from src.render_3d import superficie_por_banda


def _estudio(escala):
    return Estudio(id="x", volumen=np.zeros((2, 2, 2), np.float32),
                   espaciado=(1, 1, 1), metadatos={"escala": escala})


@pytest.mark.parametrize("escala", list(RANGOS_DENSIDAD))
def test_cada_escala_usa_sus_presets(escala):
    assert presets_para(_estudio(escala)) is RANGOS_DENSIDAD[escala]


def test_sin_escala_no_hay_presets():
    assert escala_de(_estudio(None)) is None
    assert presets_para(_estudio(None)) == {}


def test_sigmas_medidos():
    # Valores decididos el 19/10 con la muestra Pre (bitácora): no cambiarlos sin medir.
    assert suavizado_para("hueso") == 0.5
    assert suavizado_para("dientes") == 0.5
    for delgado in ("esmalte", "esmalte_sin_metal", "metal"):
        assert suavizado_para(delgado) == 0.0, f"{delgado} es delgado: suavizarlo lo borra"
    assert suavizado_para("preset_sin_medir") == 0.0


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


def test_ventanas_2d_convertidas_a_la_escala_normalizada():
    from src.densidades import VENTANAS_2D, ventana_para
    # El tejido blando (40 HU) cae en 410, donde escala.py pone el pico de tejido blando.
    assert ventana_para("slicer", "tejido_blando")[0] == 410
    assert ventana_para("hounsfield", "tejido_blando") == (40, 400)
    assert set(VENTANAS_2D["slicer"]) == set(VENTANAS_2D["hounsfield"])
    assert ventana_para(None, "tejido_blando") is None


def test_colores_de_la_pagina_web_coinciden_con_los_de_python():
    # La página (JS y CSS) repite los colores de COLORES_TEJIDO: si alguien cambia uno
    # solo de los lados, la app y la página mostrarían tejidos de colores distintos.
    import re
    from pathlib import Path
    from src.densidades import COLORES_TEJIDO
    web = Path(__file__).resolve().parent.parent / "web"
    js = (web / "js" / "lab3d.js").read_text(encoding="utf-8")
    colores_js = dict(re.findall(r"(\w+): 0x([0-9a-fA-F]{6})", re.search(r"const COLOR = \{([^}]*)\}", js).group(1)))
    css = (web / "estilos.css").read_text(encoding="utf-8")
    for nombre in ("hueso", "dientes", "esmalte", "metal"):
        esperado = COLORES_TEJIDO[nombre].lower()
        assert "#" + colores_js[nombre].lower() == esperado, f"lab3d.js: {nombre}"
        assert re.search(rf"--{nombre}:\s*{esperado}", css.lower()), f"estilos.css: --{nombre}"


def test_tejidos_siguen_la_curva_de_slicer_y_el_metal_se_distingue():
    # Más densidad, más claro (como la curva CT-Bone de Slicer); el metal es frío
    # (más azul que rojo) para no confundirse con el hueso, que es cálido.
    from src.densidades import COLORES_TEJIDO
    def rgb(h):
        return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    def luminosidad(h):
        r, g, b = rgb(h)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    orden = ["tejido_blando", "hueso", "dientes", "esmalte"]
    valores = [luminosidad(COLORES_TEJIDO[n]) for n in orden]
    assert valores == sorted(valores)
    r, _, b = rgb(COLORES_TEJIDO["metal"])
    assert b > r
    r, _, b = rgb(COLORES_TEJIDO["hueso"])
    assert r > b


def test_registro_de_estudios_usa_escalas_conocidas():
    import json
    from pathlib import Path
    registro = json.loads((Path(__file__).resolve().parent.parent / "data" / "estudios.json").read_text())
    for id_estudio, datos in registro.items():
        assert datos["escala"] in RANGOS_DENSIDAD, f"{id_estudio}: escala desconocida"


def test_dientes_en_hounsfield_calibrado_con_sts():
    # Valor medido con 11 pacientes etiquetados (results/calibracion_sts.csv): óptimo
    # de Dice ~816 HU. La propuesta de la literatura (1300 HU) dejaba fuera más de la
    # mitad del diente. No cambiarlo sin volver a correr scripts/calibrar_presets.py.
    assert RANGOS_DENSIDAD["hounsfield"]["dientes"][0] == 820
    assert RANGOS_DENSIDAD["hounsfield"]["esmalte"][0] == 2000
