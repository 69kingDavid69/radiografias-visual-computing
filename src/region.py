"""Regiones del volumen que la densidad sola no puede separar.

El hueso cortical denso del cráneo tiene la misma densidad que la dentina: en el
estudio Post solo el 34 % de lo que supera el umbral de "dientes" está en la boca.
Para aislar los dientes se agrega la ubicación: la arcada dental es la franja de
alturas (z) donde se concentra el esmalte.
"""
import numpy as np
from scipy import ndimage

# ±22 mm alrededor del centro: corona y raíz de ambas arcadas. Medido con 11 pacientes
# de STS: conserva el 99,5 % del diente etiquetado (mediana; peor caso 94 %). Con ±25 mm
# entraba la base de la mandíbula; con ±20 mm se cortaban raíces (peor caso 90 %).
MARGEN_ARCADA_MM = 22


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


def piezas_con_esmalte(volumen, umbral, esmalte_min, esmalte_max=np.inf, minimo_esmalte=50,
                       metal=None, halo_metal_vox=2, fraccion_minima=0.02):
    """Máscara de los dientes: piezas conectadas (densidad ≥ umbral) con esmalte.

    Un diente es un objeto continuo de la corona a la raíz, y su corona tiene esmalte;
    los fragmentos sueltos de hueso cortical no. Pasos:
      1. Si se da `metal`, se quita todo lo que lo supera más un halo de
         `halo_metal_vox` vóxeles: en el borde del metal (tornillos, placas, brackets)
         el volumen parcial imita densidades de esmalte. Los brackets pegados al diente
         se van; el diente queda.
      2. Se etiquetan las piezas conectadas y se conservan las que tienen al menos
         `minimo_esmalte` vóxeles de esmalte...
      3. ...y miden al menos `fraccion_minima` de la pieza más grande (los dientes van
         unidos en la arcada; los restos de hueso del borde de la franja son chicos).
    """
    candidato = volumen >= umbral
    if metal is not None:
        candidato &= ~ndimage.binary_dilation(volumen > metal, iterations=halo_metal_vox)
    etiquetas, n = ndimage.label(candidato)
    if n == 0:
        return np.zeros(volumen.shape, dtype=bool)
    indices = np.arange(1, n + 1)
    esmalte = (volumen >= esmalte_min) & (volumen <= esmalte_max) & candidato
    con_esmalte = ndimage.sum(esmalte, etiquetas, indices) >= minimo_esmalte
    if not con_esmalte.any():
        return np.zeros(volumen.shape, dtype=bool)
    tamano = ndimage.sum(candidato, etiquetas, indices)
    grandes = tamano >= fraccion_minima * tamano[con_esmalte].max()
    return np.isin(etiquetas, indices[con_esmalte & grandes])

