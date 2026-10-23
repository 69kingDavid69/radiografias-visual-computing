"""Regiones del volumen que la densidad sola no puede separar.

El hueso cortical denso del cráneo tiene la misma densidad que la dentina: en el
estudio Post solo el 34 % de lo que supera el umbral de "dientes" está en la boca.
Para aislar los dientes se agrega la ubicación: la arcada dental es la franja de
alturas (z) donde se concentra el esmalte.
"""
import numpy as np
from scipy import ndimage

MARGEN_ARCADA_MM = 25          # ±25 mm alrededor del centro: corona y raíz de ambas arcadas


def arcada_dental(volumen, espaciado, umbral_esmalte, margen_mm=MARGEN_ARCADA_MM):
    """(z0, z1) de la franja de la arcada dental, o None si no hay esmalte.

    El centro es la altura con más vóxeles por encima del umbral de esmalte (perfil
    suavizado con una ventana de ~5 mm para que un corte aislado no lo desvíe).
    Supone que el eje z del volumen es el vertical del paciente.
    """
    dz = espaciado[0]
    perfil = (volumen >= umbral_esmalte).sum(axis=(1, 2)).astype(float)
    if perfil.sum() == 0:
        return None
    ventana = max(1, int(round(5 / dz)))
    perfil = np.convolve(perfil, np.ones(ventana) / ventana, mode="same")
    centro = int(np.argmax(perfil))
    margen = int(round(margen_mm / dz))
    return max(0, centro - margen), min(volumen.shape[0], centro + margen + 1)


def piezas_con_esmalte(volumen, umbral, esmalte_min, esmalte_max=np.inf, minimo_esmalte=50):
    """Máscara de las piezas conectadas (densidad ≥ umbral) que tienen esmalte.

    Un diente es un objeto continuo de la corona a la raíz, y su corona tiene esmalte;
    los fragmentos sueltos de hueso cortical no. Se etiquetan las piezas conectadas por
    encima del umbral y se conservan las que tienen al menos `minimo_esmalte` vóxeles en
    el rango del esmalte. Límite: el metal (tornillos, placas, brackets) también tiene
    densidades de esmalte en su borde (volumen parcial), así que no se descarta.
    """
    etiquetas, n = ndimage.label(volumen >= umbral)
    if n == 0:
        return np.zeros(volumen.shape, dtype=bool)
    esmalte = (volumen >= esmalte_min) & (volumen <= esmalte_max)
    cuenta = np.bincount(etiquetas[esmalte], minlength=n + 1)
    cuenta[0] = 0                                 # el fondo no es una pieza
    return np.isin(etiquetas, np.flatnonzero(cuenta >= minimo_esmalte))

