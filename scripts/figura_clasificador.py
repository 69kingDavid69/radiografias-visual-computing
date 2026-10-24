"""Figura: experto vs. método de la app vs. clasificador, en un corte del mismo paciente.

El clasificador se entrena SIN el paciente que se muestra (como en la evaluación
dejando uno fuera), así que la figura no hace trampa. El corte axial se elige donde el
método de la app marca más hueso como diente.

Uso (después de scripts/entrenar_clasificador.py, que deja la caché de características):
    python scripts/figura_clasificador.py data/raw/sts3d --paciente ROI_L_011
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                         # noqa: E402
import numpy as np                                      # noqa: E402
from matplotlib.patches import Patch                    # noqa: E402
from sklearn.ensemble import RandomForestClassifier     # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from entrenar_clasificador import (CACHE, MUESTRAS_POR_CLASE, RAIZ,  # noqa: E402
                                   volumen_y_caracteristicas)

DIENTE, FALSO, FALTA = "#F0E1B7", "#F28C28", "#4C9BE8"   # correcto · marcó hueso · no marcó diente
FONDO, TEXTO = "#0E131A", "#E7EDF4"


def entrenar_sin(paciente):
    rng = np.random.default_rng(0)
    Xs, ys = [], []
    for f in sorted(CACHE.glob("ROI_L_*.npz")):
        if f.stem == paciente:
            continue
        d = np.load(f)
        X, y = d["X"].astype(np.float32), d["y"]
        pos, neg = np.flatnonzero(y), np.flatnonzero(~y)
        sel = np.concatenate([rng.choice(pos, min(len(pos), MUESTRAS_POR_CLASE), replace=False),
                              rng.choice(neg, min(len(neg), MUESTRAS_POR_CLASE), replace=False)])
        Xs.append(X[sel]); ys.append(y[sel])
    if not Xs:
        raise SystemExit("No hay caché: corre primero scripts/entrenar_clasificador.py")
    return RandomForestClassifier(n_estimators=60, max_depth=18, min_samples_leaf=20, n_jobs=-1,
                                  random_state=0).fit(np.concatenate(Xs), np.concatenate(ys))


def dice(pred, real):
    return 2 * (pred & real).sum() / (pred.sum() + real.sum())


def capa(pred, real):
    """Imagen RGBA: correcto en color diente, falso positivo en naranja, faltante en azul."""
    rgba = np.zeros(pred.shape + (4,))
    for mascara, color in ((pred & real, DIENTE), (pred & ~real, FALSO), (~pred & real, FALTA)):
        rgba[mascara] = matplotlib.colors.to_rgba(color, 0.85)
    return rgba


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("carpeta", type=Path)
    a.add_argument("--paciente", default="ROI_L_011")
    a.add_argument("--salida", type=Path, default=RAIZ / "results" / "clasificador_comparacion.png")
    args = a.parse_args()

    rf = entrenar_sin(args.paciente)
    img = args.carpeta / f"{args.paciente}.nii.gz"
    d = volumen_y_caracteristicas(img, img.with_name(f"{args.paciente}_mascara.nii.gz"))
    v, m, cand, base = d["v"], d["m"], d["cand"], d["base"]
    X = np.stack([f[cand] for f in d["caracteristicas"]], axis=1)
    clf = np.zeros_like(m)
    clf[cand] = rf.predict_proba(X)[:, 1] >= 0.5

    # Dos cortes: donde la app marca más hueso como diente (raíces) y donde hay más diente.
    z_raices = int(np.argmax(((base & ~m).sum(axis=(1, 2))) * (m.sum(axis=(1, 2)) > 0)))
    z_diente = int(np.argmax(m.sum(axis=(1, 2))))
    filas = [(z_raices, "raíces: más hueso alveolar alrededor"), (z_diente, "corte con más diente")]

    fig, ejes = plt.subplots(2, 3, figsize=(15, 10.6), facecolor=FONDO)
    for (z, nombre_corte), fila in zip(filas, ejes):
        ys, xs = np.nonzero(m[z] | base[z] | clf[z])
        y0, y1 = max(0, ys.min() - 15), min(v.shape[1], ys.max() + 15)
        x0, x1 = max(0, xs.min() - 15), min(v.shape[2], xs.max() + 15)
        recorte = (slice(y0, y1), slice(x0, x1))
        gris = np.clip((v[z][recorte] + 300) / 2800, 0, 1)
        paneles = [("Experto (máscara de STS)", None),
                   (f"Método actual · Dice {dice(base, m):.2f}", base),
                   (f"Clasificador · Dice {dice(clf, m):.2f}", clf)]
        for eje, (titulo, pred) in zip(fila, paneles):
            eje.imshow(gris, cmap="gray", interpolation="nearest")
            if pred is None:
                rgba = np.zeros(m.shape + (4,)); rgba[m] = matplotlib.colors.to_rgba(DIENTE, 0.85)
            else:
                rgba = capa(pred, m)
            eje.imshow(rgba[z][recorte], interpolation="nearest")
            eje.set_title(titulo if fila is ejes[0] else "", color=TEXTO, fontsize=15, pad=10)
            eje.axis("off")
        fila[0].text(-0.04, 0.5, nombre_corte, transform=fila[0].transAxes, rotation=90,
                     va="center", ha="right", color="#9AA7B6", fontsize=12)
    fig.legend(handles=[Patch(color=DIENTE, label="Diente (correcto)"),
                        Patch(color=FALSO, label="Marcó hueso como diente"),
                        Patch(color=FALTA, label="Diente que no marcó")],
               loc="lower center", ncol=3, frameon=False, labelcolor=TEXTO, fontsize=13)
    fig.suptitle(f"{args.paciente} · Dice de todo el volumen · el clasificador no vio a este paciente al entrenar",
                 color="#9AA7B6", fontsize=12, y=0.99)
    fig.tight_layout(rect=(0.02, 0.05, 1, 0.97))
    z = filas
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.salida, dpi=150, facecolor=FONDO)
    print(f"cortes z={[f[0] for f in filas]} | Dice volumen: app {dice(base, m):.3f}, clasificador {dice(clf, m):.3f} | {args.salida}")


if __name__ == "__main__":
    main()
