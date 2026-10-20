"""Carga de un estudio tomográfico como un volumen 3D.

Formatos soportados:
  - carpeta con una serie DICOM (cortes .dcm o un archivo multiframe);
  - archivo de volumen: GIPL (muestra de 3D Slicer), NIfTI (ToothFairy3), MHA/MHD, NRRD.

El resto del programa solo usa `cargar_estudio()` y la clase `Estudio`.
"""
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pydicom
import SimpleITK as sitk
from pydicom.errors import InvalidDicomError

EXTENSIONES_VOLUMEN = (".gipl.gz", ".gipl", ".nii.gz", ".nii", ".mha", ".mhd", ".nrrd")
CARPETA_CACHE = Path(__file__).resolve().parent.parent / "data" / "processed"


@dataclass
class Estudio:
    id: str                      # nombre del archivo o carpeta, sin extensión
    volumen: np.ndarray          # float32 (z, y, x) en unidades de densidad
    espaciado: tuple             # (dz, dy, dx) en mm
    metadatos: dict = field(default_factory=dict)   # formato, forma, rango… (sin datos del paciente)


def cargar_estudio(ruta, usar_cache=True, carpeta_cache=CARPETA_CACHE):
    """Carga un estudio desde una carpeta DICOM o un archivo de volumen.

    Las carpetas DICOM se guardan en caché (`data/processed/<id>.npz`), porque abrir
    cientos de cortes es lento; se releen si el original es más nuevo que la caché.
    Los archivos de volumen no se cachean: un .gipl.gz de 24 MB se lee en ~0.2 s y
    su caché sin comprimir ocuparía ~170 MB.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}")
    id_estudio = _id_estudio(ruta)
    cache = Path(carpeta_cache) / f"{id_estudio}.npz"

    usar_cache = usar_cache and ruta.is_dir()
    if usar_cache and cache.exists() and cache.stat().st_mtime >= ruta.stat().st_mtime:
        with np.load(cache) as datos:
            volumen = datos["volumen"]
            espaciado = tuple(float(s) for s in datos["espaciado"])
            formato = str(datos["formato"])
    else:
        if ruta.is_dir():
            volumen, espaciado = cargar_serie_dicom(ruta)
            formato = "DICOM"
        elif ruta.name.lower().endswith(EXTENSIONES_VOLUMEN):
            volumen, espaciado = cargar_volumen(ruta)
            formato = _extension(ruta).lstrip(".").split(".")[0].upper()
        else:
            raise ValueError(f"Formato no soportado: {ruta.name} "
                             f"(se aceptan carpetas DICOM y {', '.join(EXTENSIONES_VOLUMEN)})")
        if usar_cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez(cache, volumen=volumen, espaciado=np.array(espaciado), formato=formato)

    return Estudio(
        id=id_estudio,
        volumen=volumen,
        espaciado=espaciado,
        metadatos={
            "formato": formato,
            "forma": volumen.shape,
            "rango": (float(volumen.min()), float(volumen.max())),
            "origen": str(ruta),
        },
    )


def cargar_volumen(ruta):
    """Lee un archivo de volumen (GIPL, NIfTI, MHA, NRRD) con SimpleITK.

    Devuelve (volumen, espaciado) con volumen (z, y, x) y espaciado (dz, dy, dx).
    """
    imagen = sitk.ReadImage(str(ruta))
    # GetArrayFromImage ya entrega (z, y, x); GetSpacing entrega (x, y, z).
    volumen = sitk.GetArrayFromImage(imagen).astype(np.float32)
    espaciado = tuple(float(s) for s in reversed(imagen.GetSpacing()))
    return volumen, espaciado


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

    if len(cortes) == 1 and cortes[0].pixel_array.ndim == 3:
        # Algunos equipos CBCT exportan todo el estudio en un solo archivo multiframe.
        primero = cortes[0]
        volumen = primero.pixel_array.astype(np.float32)
        dy, dx, dz = _espaciado_multiframe(primero)
    else:
        # Los archivos no vienen en orden: se ordenan por la altura (z) de cada corte.
        # `primero` se toma DESPUÉS de ordenar (bug encontrado por Juan en feat/visor-contraste).
        cortes.sort(key=lambda ds: float(ds.ImagePositionPatient[2]))
        primero = cortes[0]
        dy, dx = map(float, primero.PixelSpacing)
        volumen = np.stack([ds.pixel_array for ds in cortes]).astype(np.float32)
        if len(cortes) > 1:
            dz = calcular_dz([float(ds.ImagePositionPatient[2]) for ds in cortes])
        else:
            dz = float(getattr(primero, "SliceThickness", dx))

    # El valor guardado en el archivo no es la densidad: hay que reescalarlo.
    pendiente = float(getattr(primero, "RescaleSlope", 1))
    intercepto = float(getattr(primero, "RescaleIntercept", 0))
    return volumen * pendiente + intercepto, (dz, dy, dx)


def calcular_dz(posiciones_z):
    """Espaciado entre cortes (mm) a partir de la altura z de cada corte, ya ordenada.

    Si los cortes no están igualmente separados (faltan cortes o hay repetidos),
    emite `warnings.warn(...)` para que el usuario sepa que el 3D puede salir deformado.
    """
    diferencias = np.diff(np.asarray(posiciones_z, dtype=float))
    # La mediana no se mueve si falta un corte; el promedio sí.
    dz = float(np.median(diferencias))
    if dz <= 0:
        raise ValueError("Los cortes están repetidos: no se puede calcular el espaciado en z")
    # rtol absorbe el redondeo de los decimales del DICOM; un corte faltante o repetido
    # se desvía un 100 % y no pasa.
    if not np.allclose(diferencias, dz, rtol=0.01, atol=1e-3):
        warnings.warn(f"Separación entre cortes no uniforme (dz ≈ {dz:.3f} mm): "
                      "puede faltar o repetirse algún corte y el 3D saldría deformado.")
    return dz


def _espaciado_multiframe(ds):
    """(dy, dx, dz) de un DICOM multiframe; el espaciado puede venir en dos lugares."""
    try:
        medidas = ds.SharedFunctionalGroupsSequence[0].PixelMeasuresSequence[0]
        dy, dx = map(float, medidas.PixelSpacing)
        dz = float(getattr(medidas, "SpacingBetweenSlices", None)
                   or getattr(medidas, "SliceThickness"))
        return dy, dx, dz
    except (AttributeError, IndexError):
        dy, dx = map(float, ds.PixelSpacing)
        return dy, dx, float(getattr(ds, "SliceThickness", dx))


def _extension(ruta):
    nombre = ruta.name.lower()
    return next((ext for ext in EXTENSIONES_VOLUMEN if nombre.endswith(ext)), ruta.suffix)


def _id_estudio(ruta):
    if ruta.is_dir():
        return ruta.name
    return ruta.name[: len(ruta.name) - len(_extension(ruta))]
