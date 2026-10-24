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



def _cuerpo_grueso(volumen, espaciado, umbral_tejido, abertura_mm, malla_mm):
    """Máscara del cuerpo en una rejilla gruesa y el paso (en vóxeles) de esa rejilla por eje."""
    paso = tuple(max(1, int(round(malla_mm / e))) for e in espaciado)
    bajo = volumen[::paso[0], ::paso[1], ::paso[2]] > umbral_tejido
    for z in range(bajo.shape[0]):
        bajo[z] = ndimage.binary_fill_holes(bajo[z])
    pasos = max(1, int(round(abertura_mm / (2 * malla_mm))))
    piezas, n = ndimage.label(ndimage.binary_opening(bajo, iterations=pasos))
    if n == 0:
        return np.zeros(bajo.shape, dtype=bool), paso
    return piezas == np.bincount(piezas.ravel())[1:].argmax() + 1, paso


def _ampliar(mascara_gruesa, paso, forma):
    """Lleva una máscara de la rejilla gruesa a la resolución del volumen (cada celda se repite)."""
    for eje, p in enumerate(paso):
        mascara_gruesa = np.repeat(mascara_gruesa, p, axis=eje)
    return mascara_gruesa[:forma[0], :forma[1], :forma[2]]


def cuerpo(volumen, espaciado, umbral_tejido, abertura_mm=8.0, malla_mm=2.0):
    """Máscara del cuerpo del paciente: todo lo que no es aire, sin los objetos delgados que lo rodean.

    El soporte de cabeza y la camilla son placas de pocos milímetros, y por densidad no se
    distinguen del hueso. Lo que sí los distingue es su grosor: se calcula sobre una rejilla
    gruesa (`malla_mm`) lo que supera `umbral_tejido`, se rellenan los huecos de cada corte
    (los pulmones), se hace una apertura morfológica de ~`abertura_mm` que borra lo delgado y se
    queda la pieza más grande. Es una máscara gruesa a propósito (error de ~`malla_mm` en el
    contorno): solo sirve para decidir qué es del paciente. La apertura no quita una placa
    pegada a una cara plana del cuerpo; de eso se encarga `hueso_del_paciente` con la profundidad.
    """
    gruesa, paso = _cuerpo_grueso(volumen, espaciado, umbral_tejido, abertura_mm, malla_mm)
    return _ampliar(gruesa, paso, volumen.shape)


def hueso_del_paciente(volumen, umbral, espaciado, umbral_tejido, minimo_voxeles=100, profundidad_minima_mm=6.0,
                       abertura_mm=8.0, malla_mm=2.0):
    """Máscara del hueso (≥ `umbral`) del paciente, sin el soporte de cabeza ni la camilla.

    Descarta tres cosas: el hueso fuera del cuerpo (`cuerpo`), los trozos de menos de
    `minimo_voxeles` (ruido) y las piezas que nunca pasan de `profundidad_minima_mm` bajo la
    superficie del cuerpo: una correa o una placa pegada a la piel no baja de ahí, mientras que
    cualquier fragmento de hueso, aunque sea chico, tiene piel y grasa encima.

    No se queda con "la pieza más grande": en una fractura conminuta, como las de pelvis, los
    fragmentos son piezas grandes y separadas, y todas son hueso.
    """
    gruesa, paso = _cuerpo_grueso(volumen, espaciado, umbral_tejido, abertura_mm, malla_mm)
    hueso = (volumen >= umbral) & _ampliar(gruesa, paso, volumen.shape)
    etiquetas, n = ndimage.label(hueso)
    if n == 0:
        return hueso
    # Profundidad (mm bajo la superficie del cuerpo) en la rejilla gruesa, a 1 byte por vóxel.
    profundidad = ndimage.distance_transform_edt(gruesa, sampling=[e * p for e, p in zip(espaciado, paso)])
    profundidad = _ampliar(np.minimum(profundidad, 255).astype(np.uint8), paso, volumen.shape)
    indices = np.arange(1, n + 1)
    maxima = ndimage.maximum(profundidad[hueso], etiquetas[hueso], indices)
    tamanos = np.bincount(etiquetas.ravel(), minlength=n + 1)
    conservar = np.zeros(n + 1, dtype=bool)
    conservar[1:] = (tamanos[1:] >= minimo_voxeles) & (maxima >= profundidad_minima_mm)
    return conservar[etiquetas]
