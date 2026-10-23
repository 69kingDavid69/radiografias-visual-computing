"""Calibra el umbral de "dientes" con estudios etiquetados (STS-3D-Tooth).

Para cada estudio con máscara de dientes:
  1. lo carga y lo normaliza igual que la app (src/carga.py + src/escala.py);
  2. se queda con la zona dental: las capas donde hay diente según la máscara, ±10 mm;
  3. para cada umbral posible mide el coeficiente Dice entre "densidad ≥ umbral" y la
     máscara (1 = coinciden exacto, 0 = nada en común) y se queda con el mejor.

Con histogramas acumulados se evalúan todos los umbrales en una sola pasada.

Uso:
    python scripts/calibrar_presets.py data/raw/sts3d            # todos los ROI_L_*.nii.gz
    python scripts/calibrar_presets.py data/raw/sts3d --csv results/calibracion_sts.csv

Las máscaras de STS traen la etiqueta 1 = dientes; la etiqueta 4 es un artefacto (una
capa de 512 × 512 con valor 2) y se ignora.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.carga import cargar_estudio            # noqa: E402
from src.densidades import RANGOS_DENSIDAD      # noqa: E402

UMBRALES = np.arange(400, 2001, 5)              # en la escala normalizada ("slicer")
MARGEN_MM = 10


def calibrar(ruta_imagen, ruta_mascara):
    estudio = cargar_estudio(ruta_imagen)
    v = estudio.volumen
    m = sitk.GetArrayFromImage(sitk.ReadImage(str(ruta_mascara))) == 1
    zs = np.flatnonzero(m.any(axis=(1, 2)))
    margen = int(round(MARGEN_MM / estudio.espaciado[0]))
    z0, z1 = max(0, zs[0] - margen), min(v.shape[0], zs[-1] + margen + 1)
    v, m = v[z0:z1], m[z0:z1]

    # Histogramas de densidad dentro y fuera de los dientes, acumulados desde arriba:
    # para cada umbral t, cuántos vóxeles de diente y de no-diente quedan con v ≥ t.
    bordes = np.append(UMBRALES, np.inf)
    dentro = np.histogram(v[m], bins=bordes)[0][::-1].cumsum()[::-1]
    fuera = np.histogram(v[~m], bins=bordes)[0][::-1].cumsum()[::-1]
    total_dientes = m.sum()
    dice = 2 * dentro / (total_dientes + dentro + fuera)
    i = int(np.argmax(dice))
    actual = RANGOS_DENSIDAD["slicer"]["dientes"][0]
    j = int(np.searchsorted(UMBRALES, actual))
    dientes = v[m & (v > 200)]                   # sin el borde de la anotación que cae en aire
    return {
        "estudio": estudio.id,
        "a": round(estudio.metadatos["normalizacion"]["a"], 3),
        "b": round(estudio.metadatos["normalizacion"]["b"], 1),
        "umbral_optimo": int(UMBRALES[i]),
        "dice_optimo": round(float(dice[i]), 3),
        f"dice_con_{actual}": round(float(dice[j]), 3),
        "dientes_p25": int(np.percentile(dientes, 25)),
        "dientes_p50": int(np.median(dientes)),
        "dientes_p75": int(np.percentile(dientes, 75)),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("carpeta", type=Path)
    p.add_argument("--csv", type=Path)
    args = p.parse_args()
    filas = []
    for img in sorted(args.carpeta.glob("ROI_L_*.nii.gz")):
        if img.name.endswith("_mascara.nii.gz"):
            continue
        mascara = img.with_name(img.name.replace(".nii.gz", "_mascara.nii.gz"))
        if not mascara.exists():
            print(f"sin máscara: {img.name}", file=sys.stderr)
            continue
        fila = calibrar(img, mascara)
        filas.append(fila)
        print(fila, flush=True)
    if not filas:
        raise SystemExit("No se encontraron estudios con máscara.")
    optimos = [f["umbral_optimo"] for f in filas]
    print(f"\n{len(filas)} estudios | umbral óptimo: mediana {np.median(optimos):.0f}, "
          f"rango {min(optimos)}–{max(optimos)} | Dice óptimo mediana "
          f"{np.median([f['dice_optimo'] for f in filas]):.3f}")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        print(f"guardado en {args.csv}")


if __name__ == "__main__":
    main()
