"""Orientación del paciente: hacia dónde crece cada eje del volumen.

La orientación es una cadena de tres letras (x, y, z) con el lado del paciente hacia el
que CRECE cada eje, en la convención de ITK/DICOM: "LPS" = x crece hacia la izquierda
(Left) del paciente, y hacia atrás (Posterior) y z hacia arriba (Superior). Con ella la
app pone letras en las vistas 2D y un cubo en la 3D, para no tener que adivinar de qué
lado está lo que se ve.
"""
import numpy as np

# Letra ITK → texto en español. "Iz" e "Inf" se distinguen porque "I" sola sería ambigua.
TEXTO = {"L": "Iz", "R": "D", "A": "Ant", "P": "Post", "S": "Sup", "I": "Inf"}
OPUESTA = {"L": "R", "R": "L", "A": "P", "P": "A", "S": "I", "I": "S"}


def orientacion_de_direccion(direccion):
    """Orientación ("LPS", "RAS"…) a partir de los 9 cosenos directores, por filas.

    Es la `direction` de SimpleITK: las columnas son los vectores de los ejes x, y, z del
    volumen en coordenadas LPS del paciente.
    """
    import SimpleITK as sitk
    return sitk.DICOMOrientImageFilter_GetOrientationFromDirectionCosines(
        tuple(float(c) for c in direccion))


def direccion_de_dicom(orientacion_imagen):
    """Cosenos directores (9, por filas) de una serie DICOM axial a partir de su
    ImageOrientationPatient (6 valores: dirección de las filas y de las columnas).

    El eje z de nuestros volúmenes crece a lo largo de la normal (fila × columna), porque
    la carga ordena los cortes por posición a lo largo de ella.
    """
    fila = np.asarray(orientacion_imagen[:3], dtype=float)
    columna = np.asarray(orientacion_imagen[3:6], dtype=float)
    normal = np.cross(fila, columna)
    return tuple(np.stack([fila, columna, normal], axis=1).ravel())


def texto(letra):
    return TEXTO[letra]


def etiquetas_corte(orientacion, plano):
    """(izquierda, derecha, arriba, abajo) de un corte, en letras ITK.

    Se dibujan como en el visor: axial = volumen[z] con y hacia abajo; coronal = volumen[:, y]
    y sagital = volumen[:, :, x] con z hacia arriba.
    """
    ox, oy, oz = orientacion
    if plano == "axial":       # filas = y (la fila 0 arriba), columnas = x
        return OPUESTA[ox], ox, OPUESTA[oy], oy
    if plano == "coronal":     # columnas = x, z hacia arriba
        return OPUESTA[ox], ox, oz, OPUESTA[oz]
    if plano == "sagital":     # columnas = y, z hacia arriba
        return OPUESTA[oy], oy, oz, OPUESTA[oz]
    raise ValueError(f"Plano desconocido: {plano}")
