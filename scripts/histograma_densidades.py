"""Histograma de densidades de un estudio y densidad por estructura etiquetada.

Uso:
    # Carpeta DICOM (usa src/carga.py)
    python scripts/histograma_densidades.py data/raw/<estudio>

    # Muestra CBCT de 3D Slicer (GIPL) u otro archivo que lea SimpleITK
    python scripts/histograma_densidades.py data/raw/PreDentalSurgery.gipl.gz

    # NIfTI de ToothFairy3 con sus etiquetas
    python scripts/histograma_densidades.py data/raw/tf3/imagesTr/P001_0000.nii.gz \
        --etiquetas data/raw/tf3/labelsTr/P001.nii.gz --dataset-json data/raw/tf3/dataset.json

Salidas en results/:
  - histograma_<estudio>.png: histograma con eje y logarítmico y los umbrales de Otsu;
  - densidad_por_etiqueta_<estudio>.csv: percentiles por estructura (solo con --etiquetas).

Requiere: numpy, matplotlib, scikit-image. Para NIfTI, nibabel; para MHA/GIPL/NRRD, SimpleITK.
Probado el 15/10/2026 con la muestra de 3D Slicer (GIPL), CT_small.dcm de pydicom
y un NIfTI sintético con etiquetas al estilo ToothFairy3.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from skimage.filters import threshold_multiotsu

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PERCENTILES = (5, 25, 50, 75, 95)
# Formatos que se leen con SimpleITK (MHA de ToothFairy2, GIPL de la muestra de 3D Slicer, NRRD).
FORMATOS_SITK = (".mha", ".mhd", ".gipl", ".gipl.gz", ".nrrd")


def cargar_volumen(ruta):
    """Devuelve el volumen como float32. Acepta carpeta DICOM, NIfTI, MHA, GIPL, NRRD o .npy."""
    ruta = Path(ruta)
    nombre = ruta.name.lower()
    if ruta.is_dir():
        from src.carga import cargar_serie_dicom
        volumen, _ = cargar_serie_dicom(ruta)
        return volumen
    if nombre.endswith((".nii", ".nii.gz")):
        try:
            import nibabel as nib
        except ImportError:
            raise SystemExit("Falta nibabel: pip install nibabel")
        return np.asarray(nib.load(str(ruta)).dataobj, dtype=np.float32)
    if nombre.endswith(FORMATOS_SITK):
        try:
            import SimpleITK as sitk
        except ImportError:
            raise SystemExit("Falta SimpleITK: pip install SimpleITK")
        return sitk.GetArrayFromImage(sitk.ReadImage(str(ruta))).astype(np.float32)
    if nombre.endswith(".npy"):
        return np.load(ruta).astype(np.float32)
    raise SystemExit(f"Formato no reconocido: {ruta}")


def nombre_estudio(ruta):
    nombre = Path(ruta).name
    for ext in (".nii.gz", ".nii", ".npy") + FORMATOS_SITK:
        if nombre.lower().endswith(ext):
            return nombre[: -len(ext)]
    return nombre


def nombres_de_etiquetas(dataset_json):
    """Lee {id: nombre} del dataset.json de nnU-Net ({"labels": {"nombre": id, ...}})."""
    if not dataset_json:
        return {}
    with open(dataset_json, encoding="utf-8") as f:
        etiquetas = json.load(f).get("labels", {})
    mapa = {}
    for clave, valor in etiquetas.items():
        # nnU-Net v2 usa {"nombre": id}; v1 usaba {"id": "nombre"}.
        if isinstance(valor, int) or (isinstance(valor, str) and valor.isdigit()):
            mapa[int(valor)] = clave
        else:
            mapa[int(clave)] = valor
    return mapa


def guardar_histograma(volumen, umbrales, destino, titulo):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(volumen.ravel(), bins=512, color="#555555", log=True)
    for u in umbrales:
        ax.axvline(u, color="#e74c3c", linestyle="--", linewidth=1)
        ax.text(u, ax.get_ylim()[1], f" {u:.0f}", color="#e74c3c", va="top", fontsize=8)
    ax.set_xlabel("Densidad (unidades del volumen; HU en ToothFairy)")
    ax.set_ylabel("Número de vóxeles (escala log)")
    ax.set_title(titulo)
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def densidad_por_etiqueta(volumen, etiquetas, nombres):
    filas = []
    for id_etiqueta in np.unique(etiquetas):
        if id_etiqueta == 0:
            continue  # fondo
        valores = volumen[etiquetas == id_etiqueta]
        p = np.percentile(valores, PERCENTILES)
        filas.append({
            "id": int(id_etiqueta),
            "estructura": nombres.get(int(id_etiqueta), ""),
            "voxeles": int(valores.size),
            "media": round(float(valores.mean()), 1),
            **{f"p{q}": round(float(v), 1) for q, v in zip(PERCENTILES, p)},
        })
    return filas


def main():
    parser = argparse.ArgumentParser(description="Histograma de densidades de un estudio CBCT")
    parser.add_argument("estudio", help="Carpeta DICOM o archivo .nii/.nii.gz/.mha/.gipl.gz/.nrrd/.npy")
    parser.add_argument("--etiquetas", help="Volumen de etiquetas del mismo estudio (ToothFairy)")
    parser.add_argument("--dataset-json", help="dataset.json con los nombres de las etiquetas")
    parser.add_argument("--clases", type=int, default=4,
                        help="Clases para Otsu multinivel (4 = aire, blando, hueso, diente)")
    parser.add_argument("--salida", default=str(RAIZ / "results"))
    args = parser.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    nombre = nombre_estudio(args.estudio)

    volumen = cargar_volumen(args.estudio)
    print(f"Volumen {volumen.shape}, densidad de {volumen.min():.0f} a {volumen.max():.0f}")

    # Otsu sobre una muestra para que sea rápido en volúmenes grandes.
    muestra = volumen.ravel()[:: max(1, volumen.size // 2_000_000)]
    umbrales = threshold_multiotsu(muestra, classes=args.clases)
    print("Umbrales de Otsu:", ", ".join(f"{u:.0f}" for u in umbrales))
    # Los dientes son <1 % del volumen: Otsu no los separa; los percentiles altos sirven de preset relativo.
    altos = (99, 99.5, 99.9)
    print("Percentiles altos:", ", ".join(f"p{q}={v:.0f}" for q, v in zip(altos, np.percentile(muestra, altos))))

    png = salida / f"histograma_{nombre}.png"
    guardar_histograma(volumen, umbrales, png, f"Histograma de densidades — {nombre}")
    print(f"Histograma guardado en {png}")

    if args.etiquetas:
        etiquetas = cargar_volumen(args.etiquetas).astype(np.int32)
        if etiquetas.shape != volumen.shape:
            raise SystemExit(f"Las etiquetas {etiquetas.shape} no coinciden con el volumen {volumen.shape}")
        filas = densidad_por_etiqueta(volumen, etiquetas, nombres_de_etiquetas(args.dataset_json))
        ruta_csv = salida / f"densidad_por_etiqueta_{nombre}.csv"
        with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
            escritor.writeheader()
            escritor.writerows(filas)
        print(f"Densidad por estructura guardada en {ruta_csv}")
        for fila in filas:
            print(f"  {fila['estructura'] or fila['id']:<35} p5={fila['p5']:>7}  "
                  f"p50={fila['p50']:>7}  p95={fila['p95']:>7}")


if __name__ == "__main__":
    main()
