"""Genera los datos de la página web (web/datos y web/modelos) con el código del proyecto.

Uso (desde la raíz del repositorio, con la muestra en data/raw/):
    python scripts/generar_web.py
    python scripts/generar_web.py data/raw/PreDentalSurgery.gipl.gz
    python scripts/pulir_modelos.py      # dientes a resolución completa
    python scripts/generar_molar.py      # molar ilustrativo de la portada

Produce:
  - web/datos/cortes.png: los cortes axiales del volumen (1 de cada 2 vóxeles, valor/16)
    en una sola imagen, para el visor 2D, la barra de umbral y marching squares;
  - web/datos/meta.json: forma, espaciado, histograma, presets, arcada y datos de los modelos;
  - web/modelos/*.ply: una malla por preset, hecha igual que en el programa (Render3D):
    render_3d.superficie_por_banda con el suavizado de densidades.py y, para los presets
    de EN_ARCADA, limitada a la arcada dental de region.arcada_dental; además, una malla
    de detalle de los dientes sin suavizar para las pestañas de luz, suavizado y corte.

Nunca genera la superficie de la piel ni los tejidos blandos: reconstruyen la cara del paciente.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.carga import cargar_estudio                                  # noqa: E402
from src.densidades import EN_ARCADA, presets_para, suavizado_para     # noqa: E402
from src.region import arcada_dental                                   # noqa: E402
from src.render_3d import superficie_por_banda                         # noqa: E402

WEB = RAIZ / "web"
REDUCCION_CORTES = 2
MAX_TRIANGULOS = 90_000          # por preset; lo que pasa de aquí se simplifica (decimate)
MAX_TRIANGULOS_DETALLE = 120_000
PRESETS_WEB = ("hueso", "dientes", "esmalte", "esmalte_sin_metal", "metal")


def guardar_malla(superficie, ruta, centro, maximo):
    superficie = superficie.triangulate()
    original = superficie.n_cells
    if superficie.n_cells > maximo:
        superficie = superficie.decimate(1 - maximo / superficie.n_cells)
    superficie.clear_data()
    superficie.points = (superficie.points - centro).astype(np.float32)
    superficie.save(ruta, binary=True)
    return original, superficie.n_cells


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else RAIZ / "data" / "raw" / "PreDentalSurgery.gipl.gz"
    estudio = cargar_estudio(ruta)
    vol, esp = estudio.volumen, estudio.espaciado
    presets = presets_para(estudio)
    if not presets:
        raise SystemExit("El estudio no tiene escala conocida: no hay presets para generar los modelos.")
    (WEB / "datos").mkdir(parents=True, exist_ok=True)
    (WEB / "modelos").mkdir(parents=True, exist_ok=True)
    for viejo in (WEB / "modelos").glob("*.ply"):
        if viejo.name != "molar.ply":      # el molar lo genera scripts/generar_molar.py
            viejo.unlink()

    # Cortes axiales en una sola imagen (atlas), 8 bits.
    r = REDUCCION_CORTES
    reducido = vol[::r, ::r, ::r]
    nz, ny, nx = reducido.shape
    bytes_ = np.clip(np.round(reducido / 16.0), 0, 255).astype(np.uint8)
    columnas = int(np.ceil(np.sqrt(nz)))
    filas = int(np.ceil(nz / columnas))
    atlas = np.zeros((filas * ny, columnas * nx), np.uint8)
    for k in range(nz):
        f, c = divmod(k, columnas)
        atlas[f * ny:(f + 1) * ny, c * nx:(c + 1) * nx] = bytes_[k]
    Image.fromarray(atlas).save(WEB / "datos" / "cortes.png", optimize=True)

    paso = 25
    conteos, _ = np.histogram(np.clip(vol, 0, 3999), bins=np.arange(0, 4000 + paso, paso))

    # La arcada dental se ubica por el esmalte, igual que Render3D.mostrar.
    arcada = arcada_dental(vol, esp, presets["esmalte"][0])

    # Una malla por preset, centradas todas en el mismo punto (el del hueso).
    centro, modelos = None, {}
    for nombre in PRESETS_WEB:
        if nombre not in presets:
            continue
        minimo, maximo = presets[nombre]
        rango_z = arcada if nombre in EN_ARCADA else None
        sup = superficie_por_banda(vol, esp, minimo, maximo, reduccion=2,
                                   suavizado_mm=suavizado_para(nombre), rango_z=rango_z)
        if centro is None:
            centro = np.array(sup.center)
        original, final = guardar_malla(sup, WEB / "modelos" / f"{nombre}.ply", centro, MAX_TRIANGULOS)
        modelos[nombre] = {"min": minimo, "max": None if np.isinf(maximo) else maximo,
                           "sigma_mm": suavizado_para(nombre), "en_arcada": rango_z is not None,
                           "triangulos_original": int(original), "triangulos_web": int(final)}
        print(f"{nombre}: {original} → {final} triángulos" + (" (arcada)" if rango_z else ""))

    # Detalle de los dientes: arcada, resolución completa y sin suavizar.
    detalle = superficie_por_banda(vol, esp, presets["dientes"][0], None, reduccion=1, rango_z=arcada)
    original, final = guardar_malla(detalle, WEB / "modelos" / "dientes_detalle.ply", centro,
                                    MAX_TRIANGULOS_DETALLE)
    modelos["dientes_detalle"] = {"min": presets["dientes"][0], "en_arcada": True,
                                  "triangulos_original": int(original), "triangulos_web": int(final)}
    print(f"dientes_detalle: {original} → {final} triángulos")

    meta = {
        "estudio": estudio.id,
        "escala": estudio.metadatos.get("escala"),
        "forma_original": list(vol.shape),
        "espaciado_original_mm": list(esp),
        "reduccion": r,
        "forma": [nz, ny, nx],
        "espaciado_mm": [e * r for e in esp],
        "atlas": {"archivo": "cortes.png", "columnas": columnas, "filas": filas, "factor": 16},
        "rango": [float(vol.min()), float(vol.max())],
        "histograma": {"paso": paso, "inicio": 0, "conteos": conteos.tolist()},
        "percentiles": {str(q): float(np.percentile(vol[::2, ::2, ::2], q)) for q in (99, 99.5, 99.9)},
        "presets": {k: [v[0], None if np.isinf(v[1]) else v[1]] for k, v in presets.items()
                    if k in PRESETS_WEB},
        "arcada_z": list(arcada) if arcada else None,
        "modelos": modelos,
        # Corte axial en el centro de la arcada: arranque del visor 2D y de marching squares.
        "corte_dientes": (sum(arcada) // 2 // r) if arcada else nz // 3,
    }
    (WEB / "datos" / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print("Listo: web/datos y web/modelos")


if __name__ == "__main__":
    main()
