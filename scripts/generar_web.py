"""Genera los datos de la página web (web/datos y web/modelos) con el código del proyecto.

Uso (desde la raíz del repositorio, con la muestra en data/raw/):
    python scripts/generar_web.py
    python scripts/generar_web.py data/raw/PreDentalSurgery.gipl.gz

Produce:
  - web/datos/cortes.png: los cortes axiales del volumen (1 de cada 2 vóxeles, valor/16)
    en una sola imagen, para el visor 2D, la barra de umbral y marching squares;
  - web/datos/meta.json: forma, espaciado, histograma, presets y datos de los modelos;
  - web/modelos/*.ply: una malla por preset (hueso, dientes, esmalte, metal), hecha con
    render_3d.superficie_por_banda y el suavizado de densidades.py, igual que la app,
    y una malla de detalle de los dientes sin suavizar para la página de suavizado.

Nunca genera la superficie de la piel: reconstruye la cara del paciente.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.carga import cargar_estudio                       # noqa: E402
from src.densidades import presets_para, suavizado_para     # noqa: E402
from src.render_3d import superficie_por_banda              # noqa: E402

WEB = RAIZ / "web"
REDUCCION_CORTES = 2
MAX_TRIANGULOS = 90_000          # por preset; lo que pasa de aquí se simplifica (decimate)
MAX_TRIANGULOS_DETALLE = 120_000
PRESETS_WEB = ("hueso", "dientes", "esmalte", "metal")
CORTES_DETALLE = (60, 135)       # rango z (vóxeles originales) de la arcada dental en la muestra


def guardar_malla(superficie, ruta, centro, maximo, desplazamiento=(0.0, 0.0, 0.0)):
    superficie = superficie.triangulate()
    original = superficie.n_cells
    if superficie.n_cells > maximo:
        superficie = superficie.decimate(1 - maximo / superficie.n_cells)
    superficie.clear_data()
    superficie.points = (superficie.points + np.asarray(desplazamiento) - centro).astype(np.float32)
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

    # Una malla por preset, centradas todas en el mismo punto.
    centro, modelos = None, {}
    for nombre in PRESETS_WEB:
        minimo, maximo = presets[nombre]
        sup = superficie_por_banda(vol, esp, minimo, maximo, reduccion=2,
                                   suavizado_mm=suavizado_para(nombre))
        if centro is None:
            centro = np.array(sup.center)
        original, final = guardar_malla(sup, WEB / "modelos" / f"{nombre}.ply", centro, MAX_TRIANGULOS)
        modelos[nombre] = {"min": minimo, "sigma_mm": suavizado_para(nombre),
                           "triangulos_original": int(original), "triangulos_web": int(final)}
        print(f"{nombre}: {original} → {final} triángulos")

    # Detalle de los dientes, resolución completa y sin suavizar.
    z0, z1 = CORTES_DETALLE
    detalle = superficie_por_banda(vol[z0:z1], esp, presets["dientes"][0], None, reduccion=1)
    original, final = guardar_malla(detalle, WEB / "modelos" / "dientes_detalle.ply", centro,
                                    MAX_TRIANGULOS_DETALLE, desplazamiento=(0.0, 0.0, z0 * esp[0]))
    modelos["dientes_detalle"] = {"min": presets["dientes"][0], "triangulos_original": int(original),
                                  "triangulos_web": int(final)}
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
        "presets": {k: [v[0], None if np.isinf(v[1]) else v[1]] for k, v in presets.items()},
        "modelos": modelos,
        # Corte axial con más dientes: arranque del visor 2D y del widget de marching squares.
        "corte_dientes": int(np.argmax((reducido > 1100).sum(axis=(1, 2)))),
    }
    (WEB / "datos" / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print("Listo: web/datos y web/modelos")


if __name__ == "__main__":
    main()
