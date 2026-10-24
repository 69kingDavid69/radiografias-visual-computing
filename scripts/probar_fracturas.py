"""Prueba la vista de fractura con estudios de varias partes del cuerpo.

Cada argumento es una carpeta con pares `*-imagen.*` / `*-etiqueta.*` (o `*-vertebras.*`), o un estudio suelto
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
    """(etiquetas, de_columna) con lo que los expertos marcaron como fractura, o (None, False).

    Hay dos formas: un archivo `*-etiqueta.*` con los fragmentos (pelvis, costillas) o un
    `*-vertebras.*` con una máscara por vértebra, de la que se toman las vértebras con fractura
    según `data/fracturas_columna.csv` (grado de Genant de la planilla de Löffler et al.).
    """
    base = ruta_imagen.name.split("-imagen")[0]
    ruta = next(iter(ruta_imagen.parent.glob(f"{base}-etiqueta.*")), None)
    if ruta is not None:
        etiquetas = sitk.GetArrayFromImage(sitk.ReadImage(str(ruta)))
        return (etiquetas, False) if etiquetas.shape == forma else (None, False)
    ruta = next(iter(ruta_imagen.parent.glob(f"{base}-vertebras.*")), None)
    if ruta is None:
        return None, False
    with open(RAIZ / "data" / "fracturas_columna.csv") as f:
        rotas = [int(fila["etiqueta"]) for fila in csv.DictReader(f) if fila["estudio"] == base]
    mascara = sitk.GetArrayFromImage(sitk.ReadImage(str(ruta)))
    if mascara.shape != forma or not rotas:
        return None, False
    return np.where(np.isin(mascara, rotas), mascara, 0), True


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
        # Fragmento del experto perdido: conserva menos de la mitad de sus vóxeles de hueso. (No se
        # exige el 90 %: en tomografías ruidosas los vóxeles aislados se descartan a propósito.)
        perdidos = 0
        ids = np.unique(etiquetas[marcado])
        for i in ids:
            parte = marcado & (etiquetas == i)
            if (mascara & parte).sum() < 0.5 * parte.sum():
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


def corte_sagital(estudio, centro, alto=1500, ancho=2250):
    """Corte sagital del estudio por `centro` (x, y, z en mm), con la cabeza arriba y el frente a la izquierda.

    Sirve con cualquier orientación guardada: busca qué eje es derecha-izquierda, cuál
    arriba-abajo y cuál adelante-atrás, y respeta el espaciado de cada uno.
    """
    letras = estudio.metadatos.get("orientacion") or "LPS"
    eje = {("x", "y", "z")[i]: i for i in range(3)}
    lateral = next(i for i, l in enumerate(letras) if l in "LR")
    vertical = next(i for i, l in enumerate(letras) if l in "SI")
    anteroposterior = next(i for i, l in enumerate(letras) if l in "AP")
    numpy_eje = lambda i: 2 - i                      # el volumen es (z, y, x)
    esp = estudio.espaciado
    v = np.moveaxis(estudio.volumen, [numpy_eje(lateral), numpy_eje(vertical), numpy_eje(anteroposterior)], [0, 1, 2])
    mm = lambda i: esp[numpy_eje(i)]
    corte = v[int(round(centro[lateral] / mm(lateral)))]
    if letras[vertical] == "S":
        corte = corte[::-1]                          # que lo superior quede arriba
    if letras[anteroposterior] == "A":
        corte = corte[:, ::-1]                       # que el frente quede a la izquierda
    gris = (np.clip((corte + 400) / 1400, 0, 1) * 255).astype(np.uint8)
    imagen = Image.fromarray(gris).resize((max(1, int(corte.shape[1] * mm(anteroposterior) * 4)),
                                           max(1, int(corte.shape[0] * mm(vertical) * 4))))
    imagen.thumbnail((ancho, alto))
    lienzo = Image.new("L", (1500, 1000))
    lienzo.paste(imagen.resize((int(imagen.width * 1000 / imagen.height), 1000)) if imagen.height else imagen, (0, 0))
    return np.asarray(lienzo.convert("RGB"))


def dibujar(estudio, centro, salida, de_lado=False):
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
    if centro is not None and de_lado:
        # Una compresión vertebral no se ve en la superficie 3D (el hueso osteoporótico es
        # poroso y las costillas tapan): se pone el corte sagital en el que la ven los radiólogos.
        vistas.append(corte_sagital(estudio, centro))
    elif centro is not None:
        # Acercamiento a 16 cm de la fractura, de frente.
        delante, arriba = render.direcciones()
        render._vista_frontal()
        pl.reset_camera()
        pl.camera.focal_point = centro
        pl.camera.position = tuple(np.asarray(centro) + 160 * np.asarray(delante))
        pl.camera.up = arriba
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
        etiquetas, de_columna = etiquetas_de(ruta, estudio.volumen.shape) if "-imagen" in ruta.name else (None, False)
        fila = medir(estudio, etiquetas)
        fila["triangulos"], fila["dibujo_s"] = dibujar(
            estudio, centro_de_la_fractura(etiquetas, estudio.espaciado), args.salida, de_columna)
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
