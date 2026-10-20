"""Escala de densidad de cada estudio: declarada o normalizada por el histograma.

El CBCT no está calibrado: dos estudios del mismo equipo pueden traer números
distintos para la misma anatomía (la muestra Pre de 3D Slicer tiene el aire en 0 y
la Post en ~−2200). Para que un mismo juego de presets sirva en todos se usan dos
caminos, en este orden:

1. **Escala declarada.** Si el estudio aparece en `data/estudios.json`, esa escala
   manda y el volumen no se toca. Ejemplo del archivo:
       {"ToothFairy3_042": {"escala": "hounsfield"}}
2. **Normalización por picos.** Si no, se buscan en el histograma los picos de aire y
   de tejido blando (casi todos los vóxeles de un CBCT de cabeza son una de las dos
   cosas) y se reescala linealmente para que caigan donde están en la escala de
   referencia ("slicer": aire 0, tejido blando 410). Dos puntos fijos determinan la
   recta, como al calibrar un termómetro con el hielo y el agua hirviendo.

Si los picos no son confiables el estudio queda sin escala, y la app muestra solo la
barra libre en lugar de presets que aislarían la estructura equivocada.
"""
import json
import warnings
from pathlib import Path

import numpy as np

REGISTRO = Path(__file__).resolve().parent.parent / "data" / "estudios.json"
REFERENCIA = {"escala": "slicer", "aire": 0.0, "blando": 410.0}


def picos_aire_y_blando(volumen, bins=1024):
    """(aire, blando): densidad de los picos de aire y de tejido blando, o None.

    El aire es el pico más alto entre los valores menores o iguales a la mediana;
    el tejido blando, el pico más alto en la parte alta del rango (a más de un
    cuarto del camino entre el aire y el percentil 99.9).
    """
    muestra = volumen[::2, ::2, ::2]           # 8 veces menos datos, el histograma no cambia
    lo, hi = np.percentile(muestra, [0.1, 99.9])
    if hi <= lo:
        return None
    conteos, bordes = np.histogram(muestra, bins=bins, range=(lo, hi))
    conteos = np.convolve(conteos, np.ones(5) / 5, mode="same")   # quita el serrucho del histograma
    centros = (bordes[:-1] + bordes[1:]) / 2

    mediana = np.median(muestra)
    aire = centros[np.argmax(np.where(bordes[:-1] <= mediana, conteos, -1))]
    corte = aire + 0.25 * (hi - aire)
    if not (centros > corte).any():
        return None
    blando = centros[np.argmax(np.where(centros > corte, conteos, -1))]

    # Si los picos quedan casi pegados, el histograma no tiene la forma esperada.
    if blando - aire < 0.1 * (hi - lo):
        return None
    return float(aire), float(blando)


def asignar_escala(estudio, registro=REGISTRO):
    """Llena estudio.metadatos["escala"] y, si hace falta, normaliza estudio.volumen."""
    declarada = _leer_registro(registro).get(estudio.id, {}).get("escala")
    if declarada:
        estudio.metadatos.update(escala=declarada, normalizacion=None)
        return estudio

    picos = picos_aire_y_blando(estudio.volumen)
    if picos is None:
        warnings.warn(f"{estudio.id}: no se encontraron los picos de aire y tejido blando; "
                      "el estudio queda sin escala (solo barra libre). Se puede declarar en "
                      f"{REGISTRO.name}.")
        estudio.metadatos.update(escala=None, normalizacion=None)
        return estudio

    aire, blando = picos
    a = (REFERENCIA["blando"] - REFERENCIA["aire"]) / (blando - aire)
    b = REFERENCIA["aire"] - a * aire
    estudio.volumen = (estudio.volumen * a + b).astype(np.float32)
    estudio.metadatos.update(
        escala=REFERENCIA["escala"],
        normalizacion={"aire": aire, "blando": blando, "a": a, "b": b},
        rango=(float(estudio.volumen.min()), float(estudio.volumen.max())),
    )
    return estudio


def _leer_registro(registro):
    registro = Path(registro)
    if not registro.exists():
        return {}
    return json.loads(registro.read_text(encoding="utf-8"))
