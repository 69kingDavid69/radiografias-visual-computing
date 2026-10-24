"""Tests de src/region.py y del límite por arcada. Correr con: .venv/bin/python -m pytest -q"""
import numpy as np
import pytest

from src.region import arcada_dental
from src.render_3d import superficie_por_banda

ESP = (0.5, 0.5, 0.5)


def _craneo_y_dientes():
    """Volumen de 120 capas (60 mm): "cráneo" denso arriba (z 5–15) y "dientes" abajo
    (z 80–95) con una franja de esmalte en el medio de los dientes (z 86–89)."""
    v = np.zeros((120, 30, 30), dtype=np.float32)
    v[5:15, 5:25, 5:25] = 1100       # hueso cortical tan denso como la dentina
    v[80:95, 10:20, 10:20] = 1100    # dientes
    v[86:89, 10:20, 10:20] = 1400    # esmalte
    return v


def test_arcada_centrada_en_el_esmalte():
    z0, z1 = arcada_dental(_craneo_y_dientes(), ESP, 1250, margen_mm=10)
    assert z0 <= 80 and z1 >= 95          # cubre los dientes
    assert z0 > 15                        # deja fuera el "cráneo"


def test_sin_esmalte_no_hay_arcada():
    assert arcada_dental(np.zeros((10, 5, 5), np.float32), ESP, 1250) is None


def test_rango_z_quita_el_craneo_y_conserva_la_posicion():
    v = _craneo_y_dientes()
    todo = superficie_por_banda(v, ESP, 1000, reduccion=1)
    arcada = arcada_dental(v, ESP, 1250, margen_mm=10)
    solo = superficie_por_banda(v, ESP, 1000, reduccion=1, rango_z=arcada)
    assert todo.bounds[4] < 10            # sin límite aparece el "cráneo" (z ≈ 2,5–7 mm)
    assert solo.bounds[4] > 35            # con límite, solo los dientes (z ≈ 40–47 mm)
    assert solo.bounds[5] == pytest.approx(todo.bounds[5], abs=1.0)   # misma posición en mm


def test_piezas_con_esmalte_descarta_fragmentos_sueltos():
    from src.region import piezas_con_esmalte
    v = np.zeros((40, 30, 30), dtype=np.float32)
    v[20:30, 10:20, 10:20] = 1100          # diente (dentina)
    v[20:22, 10:20, 10:20] = 1400          # su corona con esmalte
    v[5:9, 3:7, 3:7] = 1100                # fragmento suelto de hueso, sin esmalte
    keep = piezas_con_esmalte(v, 1000, 1250, 2000, minimo_esmalte=10)
    assert keep[25, 15, 15] and keep[21, 15, 15]   # el diente completo (raíz y corona)
    assert not keep[6, 5, 5]                        # el fragmento no


def test_piezas_con_esmalte_quita_metal_y_restos_chicos():
    from src.region import piezas_con_esmalte
    v = np.zeros((40, 40, 40), dtype=np.float32)
    v[20:32, 10:30, 10:30] = 1100          # arcada (dentina)
    v[20:22, 10:30, 10:30] = 1400          # coronas con esmalte
    v[20:22, 9, 15:20] = 3000              # bracket pegado a la corona
    v[3:6, 3:6, 3:6] = 3000                # tornillo suelto (metal)...
    v[2:7, 2:7, 2:7] = np.where(v[2:7, 2:7, 2:7] == 0, 1500, v[2:7, 2:7, 2:7])  # ...con halo tipo esmalte
    v[35:37, 35:37, 35:37] = 1400          # resto chico con "esmalte" (hueso cortical denso)
    keep = piezas_con_esmalte(v, 1000, 1250, 2000, minimo_esmalte=5, metal=2000)
    assert keep[26, 20, 20]                # el diente se conserva
    assert not keep[3:7, 3:7, 3:7].any()   # el tornillo y su halo no
    assert not keep[35:37, 35:37, 35:37].any()   # el resto chico no


def _cuerpo_con_camilla():
    """Aire (-1000), una "cabeza" de tejido (0 HU) con hueso (1000) y una placa delgada de 500 HU que la rodea."""
    v = np.full((40, 60, 60), -1000, dtype=np.float32)
    v[5:35, 10:50, 10:50] = 0               # cuerpo: 30 × 40 × 40 vóxeles de 1 mm
    v[10:30, 20:40, 20:40] = 1000           # hueso grande
    v[12:18, 15:21, 12:18] = 1000           # fragmento suelto, dentro del cuerpo y lejos del hueso grande
    v[5:35, 52:55, 5:55] = 500              # soporte: placa de 3 mm, separada del cuerpo por aire
    v[5:35, 8:10, 10:50] = 500              # ...y otra pegada al cuerpo
    v[20, 5, 5] = 1000                      # ruido suelto de 1 vóxel
    return v


def test_hueso_del_paciente_quita_el_soporte_y_conserva_todos_los_fragmentos():
    from src.region import hueso_del_paciente
    v = _cuerpo_con_camilla()
    keep = hueso_del_paciente(v, 300, (1, 1, 1), umbral_tejido=-400, minimo_voxeles=10)
    assert keep[20, 30, 30]                  # hueso grande
    assert keep[14, 18, 14]                  # el fragmento, aunque no toque al hueso grande
    assert not keep[20, 53, 30]              # soporte separado
    assert not keep[20, 9, 30]               # soporte pegado a la piel: nunca baja de 6 mm
    assert not keep[20, 5, 5]                # ruido


def test_cuerpo_ignora_el_aire_y_rellena_los_pulmones():
    from src.region import cuerpo
    v = np.full((20, 60, 60), -1000, dtype=np.float32)
    v[:, 10:50, 10:50] = 0
    v[:, 25:35, 25:35] = -800                # pulmón: aire dentro del cuerpo
    mascara = cuerpo(v, (1, 1, 1), umbral_tejido=-400)
    assert mascara[10, 30, 30], "el pulmón es parte del cuerpo"
    assert not mascara[10, 2, 2], "el aire de afuera no"


def test_hueso_del_paciente_sin_hueso():
    from src.region import hueso_del_paciente
    v = np.full((10, 20, 20), -1000, dtype=np.float32)
    v[:, 5:15, 5:15] = 0
    assert not hueso_del_paciente(v, 300, (1, 1, 1), umbral_tejido=-400).any()
