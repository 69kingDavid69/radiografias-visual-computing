"""Filtros sobre el volumen antes de extraer la superficie.

El CBCT es más ruidoso que un CT médico: con un umbral, el ruido aparece como
"pedacitos sueltos" y bordes ásperos en la superficie. Suavizar el volumen (o la
máscara de una banda) antes de marching cubes los reduce.
"""
import numpy as np
import SimpleITK as sitk


def suavizar(volumen, espaciado, sigma_mm):
    """Filtro gaussiano con sigma en milímetros.

    volumen: (z, y, x); espaciado: (dz, dy, dx) en mm. Como SimpleITK conoce el
    espaciado, el mismo sigma en mm suaviza igual con vóxeles de 0.3 o de 0.5 mm,
    y también con vóxeles anisotrópicos. sigma_mm <= 0 devuelve el volumen sin cambios.
    """
    if sigma_mm <= 0:
        return volumen
    imagen = sitk.GetImageFromArray(np.asarray(volumen, dtype=np.float32))
    imagen.SetSpacing(tuple(float(s) for s in reversed(espaciado)))   # SimpleITK usa (x, y, z)
    return sitk.GetArrayFromImage(sitk.SmoothingRecursiveGaussian(imagen, sigma_mm))
