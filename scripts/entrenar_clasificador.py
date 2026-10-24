"""Clasificador por vóxel (Random Forest) para separar diente de no-diente.

El preset "dientes" es un clasificador de un solo parámetro (un umbral). Este script
entrena uno con varias características por vóxel, para que aprenda también contexto y
forma, y lo compara con el método de la app en los estudios etiquetados de STS.

Características (en mm, para que no dependan de la resolución):
  densidad · densidad suavizada a 0,5 / 1,5 / 3 mm · contraste local (densidad − entorno
  de 3 mm) · magnitud del gradiente (bordes) · altura respecto de la arcada · distancia
  al esmalte más cercano.

Evaluación: dejando un paciente fuera (se entrena con los demás y se mide el Dice en el
que el modelo no vio). Se trabaja a media resolución (1 de cada 2 vóxeles por eje) para
que entre en 8 GB de RAM.

Uso:
    python scripts/entrenar_clasificador.py data/raw/sts3d
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.carga import cargar_estudio                      # noqa: E402
from src.densidades import presets_para                   # noqa: E402
from src.region import arcada_dental, piezas_con_esmalte  # noqa: E402

REDUCCION = 2
CANDIDATO_MIN = 400          # HU: por debajo nunca es diente (tejido blando, aire)
MUESTRAS_POR_CLASE = 20_000
NOMBRES = ["densidad", "suave_0.5mm", "suave_1.5mm", "suave_3mm", "contraste_local",
           "gradiente", "altura_arcada_mm", "dist_esmalte_mm"]
CACHE = RAIZ / "data" / "processed" / "clasificador"


def volumen_y_caracteristicas(ruta_img, ruta_mascara):
    """Zona dental a media resolución con sus características por vóxel (sin aplanar).

    Devuelve un dict con: v (densidad), m (máscara del experto), cand (vóxeles
    candidatos), caracteristicas (lista de volúmenes, en el orden de NOMBRES), base
    (predicción del método de la app) y espaciado.
    """
    e = cargar_estudio(ruta_img)
    p = presets_para(e)
    umbral, esmalte = p["dientes"][0], p["esmalte"][0]
    z0, z1 = arcada_dental(e.volumen, e.espaciado, esmalte)
    r = REDUCCION
    v = e.volumen[z0:z1][::r, ::r, ::r]
    esp = tuple(s * r for s in e.espaciado)
    m = (sitk.GetArrayFromImage(sitk.ReadImage(str(ruta_mascara)))[z0:z1][::r, ::r, ::r] == 1)

    vox = lambda mm: tuple(mm / s for s in esp)          # sigma en mm → vóxeles por eje
    s05 = ndimage.gaussian_filter(v, vox(0.5))
    s15 = ndimage.gaussian_filter(v, vox(1.5))
    s3 = ndimage.gaussian_filter(v, vox(3.0))
    grad = ndimage.gaussian_gradient_magnitude(v, vox(1.0))
    centro = (v.shape[0] - 1) / 2
    altura = (np.arange(v.shape[0]) - centro)[:, None, None] * esp[0] * np.ones_like(v)
    dist_esm = ndimage.distance_transform_edt(v < esmalte, sampling=esp)

    base = (v >= umbral) & piezas_con_esmalte(v, umbral, esmalte, minimo_esmalte=10)
    return {"v": v, "m": m, "cand": v >= CANDIDATO_MIN, "espaciado": esp, "base": base,
            "caracteristicas": [v, s05, s15, s3, v - s3, grad, altura, dist_esm]}


def preparar(ruta_img, ruta_mascara):
    """Características de los vóxeles candidatos de la zona dental, su etiqueta y la
    predicción del método actual de la app (para comparar). Se guardan en caché."""
    cache = CACHE / f"{ruta_img.name.split('.')[0]}.npz"
    if cache.exists():
        d = np.load(cache)
        return d["X"].astype(np.float32), d["y"], d["base"]

    d = volumen_y_caracteristicas(ruta_img, ruta_mascara)
    cand = d["cand"]
    X = np.stack([f[cand] for f in d["caracteristicas"]], axis=1)
    y, base = d["m"][cand], d["base"][cand]
    # Las máscaras traen un borde que cae en aire (fuera de los candidatos): se cuenta
    # aparte para que el Dice incluya los dientes que ningún método puede marcar.
    faltantes = int((d["m"] & ~cand).sum())
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, X=X.astype(np.float16), y=y, base=base, faltantes=faltantes)
    return X, y, base


def dice(pred, real, faltantes=0):
    return 2 * (pred & real).sum() / (pred.sum() + real.sum() + faltantes)


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("carpeta", type=Path)
    a.add_argument("--csv", type=Path, default=RAIZ / "results" / "clasificador_lopo.csv")
    args = a.parse_args()

    estudios = sorted(p for p in args.carpeta.glob("ROI_L_*.nii.gz") if "_mascara" not in p.name)
    datos = {}
    for img in estudios:
        t = time.time()
        datos[img.name.split(".")[0]] = preparar(img, img.with_name(img.name.replace(".nii.gz", "_mascara.nii.gz")))
        X, y, _ = datos[img.name.split(".")[0]]
        print(f"{img.name}: {len(y):,} candidatos, {y.mean():.0%} diente ({time.time() - t:.1f} s)", flush=True)

    rng = np.random.default_rng(0)

    def muestra(X, y):
        pos, neg = np.flatnonzero(y), np.flatnonzero(~y)
        sel = np.concatenate([rng.choice(pos, min(len(pos), MUESTRAS_POR_CLASE), replace=False),
                              rng.choice(neg, min(len(neg), MUESTRAS_POR_CLASE), replace=False)])
        return X[sel], y[sel]

    filas = []
    for nombre in datos:                                  # dejar un paciente fuera
        partes = [muestra(*datos[n][:2]) for n in datos if n != nombre]
        Xtr = np.concatenate([p[0] for p in partes]); ytr = np.concatenate([p[1] for p in partes])
        rf = RandomForestClassifier(n_estimators=60, max_depth=18, min_samples_leaf=20,
                                    n_jobs=-1, random_state=0).fit(Xtr, ytr)
        X, y, base = datos[nombre]
        falt = int(np.load(CACHE / f"{nombre}.npz")["faltantes"])
        pred = rf.predict_proba(X)[:, 1] >= 0.5
        fila = {"estudio": nombre, "dice_app": round(float(dice(base, y, falt)), 3),
                "dice_clasificador": round(float(dice(pred, y, falt)), 3)}
        filas.append(fila)
        print(fila, flush=True)

    rf = RandomForestClassifier(n_estimators=60, max_depth=18, min_samples_leaf=20, n_jobs=-1,
                                random_state=0)
    partes = [muestra(*datos[n][:2]) for n in datos]
    rf.fit(np.concatenate([p[0] for p in partes]), np.concatenate([p[1] for p in partes]))
    importancia = sorted(zip(NOMBRES, rf.feature_importances_), key=lambda t: -t[1])

    app = [f["dice_app"] for f in filas]; clf = [f["dice_clasificador"] for f in filas]
    print(f"\nDice (mediana, {len(filas)} pacientes, dejando cada uno fuera): app {np.median(app):.3f} "
          f"→ clasificador {np.median(clf):.3f} | mejora en {sum(c > b for b, c in zip(app, clf))}/{len(filas)}")
    print("Importancia de las características:", ", ".join(f"{n} {i:.2f}" for n, i in importancia))
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    print(f"guardado en {args.csv}")


if __name__ == "__main__":
    main()
