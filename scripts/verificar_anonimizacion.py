"""Revisa que los estudios DICOM de una carpeta estén anonimizados y resume cada uno.

Uso:
    python scripts/verificar_anonimizacion.py data/raw
    python scripts/verificar_anonimizacion.py data/raw --csv results/estudios.csv

Para cada estudio (cada carpeta que contiene archivos DICOM):
  - lista las etiquetas con datos del paciente y avisa si alguna NO está vacía;
  - anota equipo, número de cortes y tamaño del vóxel (Fase 1, paso 3 del plan de Nicolás).

Solo lee las cabeceras (no los píxeles), así que es rápido aunque el estudio sea grande.
Los archivos NIfTI (.nii/.nii.gz) y MHA no llevan datos del paciente; solo se listan.
Termina con código 1 si algún estudio tiene etiquetas con contenido, para revisarlas a mano.
Probado el 15/10/2026 con CT_small.dcm de pydicom (que sí trae nombre e institución).
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import pydicom
from pydicom.errors import InvalidDicomError

# Etiquetas que pueden identificar al paciente. Las tres primeras son las que pide el plan.
ETIQUETAS_SENSIBLES = [
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "OtherPatientIDs",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "InstitutionName",
    "InstitutionAddress",
    "ReferringPhysicianName",
    "PerformingPhysicianName",
    "OperatorsName",
    "AccessionNumber",
]

# Valores que se consideran anonimizados aunque no estén vacíos.
VALORES_ANONIMOS = {"", "anonymous", "anonymized", "anon", "none", "unknown", "n/a", "na", "0"}


def es_anonimo(valor):
    return str(valor).strip().lower() in VALORES_ANONIMOS


def leer_cabecera(ruta):
    try:
        return pydicom.dcmread(ruta, stop_before_pixels=True)
    except (InvalidDicomError, OSError):
        return None


def revisar(carpeta_raiz):
    """Agrupa los DICOM por carpeta y devuelve un resumen por estudio."""
    por_carpeta = defaultdict(list)
    otros_formatos = []
    for ruta in sorted(Path(carpeta_raiz).rglob("*")):
        if not ruta.is_file():
            continue
        nombre = ruta.name.lower()
        if nombre.endswith((".nii", ".nii.gz", ".mha", ".mhd", ".npy")):
            otros_formatos.append(ruta)
            continue
        ds = leer_cabecera(ruta)
        if ds is not None and "SOPClassUID" in ds:
            por_carpeta[ruta.parent].append(ds)

    resumen = []
    for carpeta, cabeceras in por_carpeta.items():
        sensibles = {}
        for etiqueta in ETIQUETAS_SENSIBLES:
            valores = {str(getattr(ds, etiqueta, "")).strip() for ds in cabeceras}
            no_anonimos = sorted(v for v in valores if not es_anonimo(v))
            if no_anonimos:
                sensibles[etiqueta] = no_anonimos

        primero = cabeceras[0]
        espaciado = getattr(primero, "PixelSpacing", None)
        n_frames = int(getattr(primero, "NumberOfFrames", 1) or 1)
        resumen.append({
            "estudio": str(carpeta.relative_to(carpeta_raiz)) if carpeta != Path(carpeta_raiz) else ".",
            "anonimizado": "sí" if not sensibles else "NO",
            "etiquetas_con_datos": "; ".join(f"{k}={len(v)} valor(es)" for k, v in sensibles.items()),
            "fabricante": str(getattr(primero, "Manufacturer", "")),
            "modelo": str(getattr(primero, "ManufacturerModelName", "")),
            "archivos": len(cabeceras),
            "cortes": n_frames if len(cabeceras) == 1 else len(cabeceras),
            "filas": getattr(primero, "Rows", ""),
            "columnas": getattr(primero, "Columns", ""),
            "pixel_mm": "x".join(f"{float(v):.3f}" for v in espaciado) if espaciado else "",
            "grosor_corte_mm": str(getattr(primero, "SliceThickness", "")),
            "pendiente": str(getattr(primero, "RescaleSlope", "")),
            "intercepto": str(getattr(primero, "RescaleIntercept", "")),
        })
    return resumen, otros_formatos


def main():
    parser = argparse.ArgumentParser(description="Verifica la anonimización de estudios DICOM")
    parser.add_argument("carpeta", help="Carpeta raíz con los estudios (por ejemplo data/raw)")
    parser.add_argument("--csv", help="Guardar el resumen en este archivo CSV")
    args = parser.parse_args()

    resumen, otros = revisar(args.carpeta)
    if not resumen and not otros:
        raise SystemExit(f"No se encontraron estudios en {args.carpeta}")

    for fila in resumen:
        marca = "OK " if fila["anonimizado"] == "sí" else "!! "
        print(f"{marca}{fila['estudio']}: {fila['cortes']} cortes, píxel {fila['pixel_mm']} mm, "
              f"grosor {fila['grosor_corte_mm']} mm, equipo {fila['fabricante']} {fila['modelo']}".rstrip())
        if fila["anonimizado"] == "NO":
            # No se imprimen los valores, solo qué etiquetas tienen datos.
            print(f"    Etiquetas con contenido: {fila['etiquetas_con_datos']}")
            print("    Revisar a mano: si son códigos (p. ej. 'P001') está bien; si son datos reales, no usar.")

    if otros:
        print(f"\n{len(otros)} archivo(s) NIfTI/MHA/NPY: estos formatos no guardan datos del paciente.")

    no_anonimos = [f for f in resumen if f["anonimizado"] == "NO"]
    print(f"\n{len(resumen)} estudio(s) DICOM revisado(s); {len(no_anonimos)} con datos del paciente.")

    if args.csv:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(resumen[0].keys()) if resumen else ["estudio"])
            escritor.writeheader()
            escritor.writerows(resumen)
        print(f"Resumen guardado en {args.csv}")

    if no_anonimos:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
