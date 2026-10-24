"""Prueba la vista de fractura con estudios de varias partes del cuerpo.

Cada argumento es una carpeta con pares `*-imagen.*` / `*-etiqueta.*` o un estudio suelto
(archivo de volumen o carpeta DICOM, sin etiquetas). Para cada estudio mide qué parte del
hueso conserva la máscara de `src/region.py` (hueso del paciente, sin camilla) y, con las etiquetas de los expertos, cuánto de
lo que ellos marcaron como fractura sigue en pantalla; después dibuja el hueso por delante,
por detrás y, si hay etiquetas, un acercamiento a la fractura más grande, todo en un solo
montaje por estudio.

Uso (desde la raíz del repositorio):
    python -m scripts.probar_fracturas data/raw/fracturas/pelvis data/raw/fracturas/costillas \\
        data/raw/cq500/CQ500CT397_hueso
"""
import argparse
import csv
import time
from pathlib import Path

import numpy as np
import pyvista as pv
import SimpleITK as sitk
from PIL import Image
from scipy import ndimage

from src.carga import cargar_estudio
from src.densidades import UMBRAL_FRACTURA, UMBRAL_TEJIDO
from src.region import hueso_del_paciente
from src.render_3d import Render3D

RAIZ = Path(__file__).resolve().parent.parent
FONDO = "#181818"


def etiquetas_de(ruta_imagen, forma):
    """Etiquetas de los expertos (arreglo z, y, x) o None si el estudio no las trae."""
    ruta = next(iter(ruta_imagen.parent.glob(ruta_imagen.name.replace("-imagen", "-etiqueta").split(".")[0] + ".*")), None)
    if ruta is None:
        return None
    etiquetas = sitk.GetArrayFromImage(sitk.ReadImage(str(ruta)))
    return etiquetas if etiquetas.shape == forma else None


def medir(estudio, etiquetas):
    """Cuánto hueso conserva la máscara y cuánto de lo marcado por los expertos."""
    v = estudio.volumen
    umbral = UMBRAL_FRACTURA["hounsfield"]
    hueso = v >= umbral
    t0 = time.perf_counter()
    mascara = hueso_del_paciente(v, umbral, estudio.espaciado, UMBRAL_TEJIDO["hounsfield"])
    fila = {"estudio": estudio.id, "voxeles_millones": round(v.size / 1e6),
            "hueso_300HU": int(hueso.sum()), "conservado_pct": round(100 * mascara.sum() / hueso.sum(), 1),
            "mascara_s": round(time.perf_counter() - t0, 1)}
    if etiquetas is not None:
        marcado = (etiquetas > 0) & hueso
        fila["marcado_experto"] = int(marcado.sum())
        fila["marcado_conservado_pct"] = round(100 * (mascara & marcado).sum() / max(1, marcado.sum()), 1)
        # Fragmentos (instancias) del experto que quedan casi enteros: ≥ 90 % de sus vóxeles de hueso.
        perdidos = 0
        ids = np.unique(etiquetas[marcado])
        for i in ids:
            parte = marcado & (etiquetas == i)
            if (mascara & parte).sum() < 0.9 * parte.sum():
                perdidos += 1
        fila["fragmentos"] = len(ids)
        fila["fragmentos_perdidos"] = perdidos
    return fila


def centro_de_la_fractura(etiquetas, espaciado):
    """Centro (x, y, z) en mm de la región marcada más grande, o None."""
    if etiquetas is None or not (etiquetas > 0).any():
        return None
    piezas, n = ndimage.label(etiquetas > 0)
    mayor = int(np.bincount(piezas.ravel())[1:].argmax()) + 1
    z, y, x = ndimage.center_of_mass(piezas == mayor)
    return (x * espaciado[2], y * espaciado[1], z * espaciado[0])


def dibujar(estudio, centro, salida):
    """Dibuja el hueso por delante, por detrás y (con `centro`) de cerca; guarda un montaje.

    Devuelve (triángulos, segundos que tardó la vista de fractura).
    """
    pl = pv.Plotter(off_screen=True, window_size=(1500, 1000))
    pl.set_background(FONDO)
    render = Render3D(pl)
    render.mostrar(estudio, reduccion=1)
    t0 = time.perf_counter()
    render.aplicar_fractura()
    segundos = time.perf_counter() - t0

    def captura():
        for _ in range(3):             # el relieve (SSAO) se arma en el primer cuadro
            pl.render()
        return np.asarray(pl.screenshot(return_img=True))

    vistas = []
    for giro in (0, 180):
        render._vista_frontal()
        pl.reset_camera()
        pl.camera.azimuth = giro
        vistas.append(captura())
    if centro is not None:
        render._vista_frontal()
        pl.reset_camera()
        pl.camera.focal_point = centro
        pl.camera.position = (centro[0], centro[1] - 160, centro[2])     # 16 cm delante de la fractura
        pl.camera.up = (0, 0, 1)
        vistas.append(captura())
    triangulos = render.ultima_medicion["triangulos"]
    pl.close()
    montaje = np.concatenate([np.asarray(Image.fromarray(v).resize((700, 467))) for v in vistas], axis=1)
    Image.fromarray(montaje).save(salida / f"{estudio.id}_montaje.png", optimize=True)
    return triangulos, segundos


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("carpetas", nargs="+", type=Path)
    a.add_argument("--salida", type=Path, default=RAIZ / "results" / "fracturas")
    args = a.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)

    rutas = []
    for entrada in args.carpetas:
        pares = sorted(entrada.glob("*-imagen.*")) if entrada.is_dir() else []
        rutas += pares or [entrada]          # carpeta de pares, o un estudio suelto

    filas = []
    for ruta in rutas:
        estudio = cargar_estudio(ruta)
        etiquetas = etiquetas_de(ruta, estudio.volumen.shape) if "-imagen" in ruta.name else None
        fila = medir(estudio, etiquetas)
        fila["triangulos"], fila["dibujo_s"] = dibujar(
            estudio, centro_de_la_fractura(etiquetas, estudio.espaciado), args.salida)
        fila["dibujo_s"] = round(fila["dibujo_s"], 1)
        filas.append(fila)
        print(fila, flush=True)

    campos = sorted({k for f in filas for k in f}, key=lambda k: (k != "estudio", k))
    with open(args.salida / "resumen.csv", "w", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"guardado en {args.salida}")


if __name__ == "__main__":
    main()
