"""Dientes del laboratorio 3D a resolución completa.

Uso (desde la raíz, después de scripts/generar_web.py):
    python scripts/pulir_modelos.py

generar_web.py calcula los presets con 1 de cada 2 vóxeles; para los dientes eso deja una malla
de pocos triángulos. Aquí web/modelos/dientes.ply se reemplaza por la malla de detalle
(resolución completa), sin las piezas sueltas pequeñas y con suavizado Taubin.
No necesita la tomografía: trabaja sobre los .ply ya generados.
"""
from pathlib import Path

import numpy as np
import pyvista as pv

MODELOS = Path(__file__).resolve().parents[1] / "web" / "modelos"
MAX_TRIANGULOS = 90_000
FRACCION_MINIMA = 0.004     # piezas con menos de esta fracción de los triángulos se quitan


def main():
    malla = pv.read(MODELOS / "dientes_detalle.ply")
    piezas = malla.connectivity("all")
    ids, cuenta = np.unique(piezas.cell_data["RegionId"], return_counts=True)
    grandes = ids[cuenta >= FRACCION_MINIMA * malla.n_cells]
    malla = piezas.extract_cells(np.isin(piezas.cell_data["RegionId"], grandes))
    malla = malla.extract_surface(algorithm="dataset_surface").triangulate()
    malla = malla.smooth_taubin(n_iter=40, pass_band=0.04)
    if malla.n_cells > MAX_TRIANGULOS:
        malla = malla.decimate(1 - MAX_TRIANGULOS / malla.n_cells)
    malla.clear_data()
    malla.points = malla.points.astype(np.float32)
    malla.save(MODELOS / "dientes.ply", binary=True)
    print(f"dientes: {malla.n_cells} triángulos")


if __name__ == "__main__":
    main()
