"""Regiones del volumen que la densidad sola no puede separar.

El hueso cortical denso del cráneo tiene la misma densidad que la dentina: en el
estudio Post solo el 34 % de lo que supera el umbral de "dientes" está en la boca.
Para aislar los dientes se agrega la ubicación: la arcada dental es la franja de
alturas (z) donde se concentra el esmalte.
"""
import numpy as np

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
