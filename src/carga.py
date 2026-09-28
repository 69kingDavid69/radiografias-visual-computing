"""Carga de un estudio tomográfico (serie DICOM) como un volumen 3D."""
from pathlib import Path

import numpy as np
import pydicom
from pydicom.errors import InvalidDicomError


def cargar_serie_dicom(carpeta):
    """Lee los cortes DICOM de una carpeta y los apila en un volumen.

    Devuelve (volumen, espaciado):
      - volumen: arreglo float32 con forma (z, y, x) en unidades de densidad.
      - espaciado: tamaño del vóxel en mm como (dz, dy, dx).
    """
    cortes = []
    for ruta in sorted(Path(carpeta).rglob("*")):
        if not ruta.is_file():
            continue
        try:
            ds = pydicom.dcmread(ruta)
        except InvalidDicomError:
            continue
        if "PixelData" in ds:
            cortes.append(ds)
    if not cortes:
        raise FileNotFoundError(f"No hay cortes DICOM en {carpeta}")

    primero = cortes[0]
    dy, dx = map(float, primero.PixelSpacing)

    if len(cortes) == 1 and primero.pixel_array.ndim == 3:
        # Algunos equipos CBCT exportan todo el estudio en un solo archivo multiframe.
        volumen = primero.pixel_array.astype(np.float32)
        dz = float(getattr(primero, "SliceThickness", dx))
    else:
        # Los archivos no vienen en orden: se ordenan por la altura (z) de cada corte.
        cortes.sort(key=lambda ds: float(ds.ImagePositionPatient[2]))
        volumen = np.stack([ds.pixel_array for ds in cortes]).astype(np.float32)
        if len(cortes) > 1:
            dz = abs(float(cortes[1].ImagePositionPatient[2])
                     - float(primero.ImagePositionPatient[2]))
        else:
            dz = float(getattr(primero, "SliceThickness", 1.0))

    # El valor guardado en el archivo no es la densidad: hay que reescalarlo.
    pendiente = float(getattr(primero, "RescaleSlope", 1))
    intercepto = float(getattr(primero, "RescaleIntercept", 0))
    return volumen * pendiente + intercepto, (dz, dy, dx)
