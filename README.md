# Radiografías — Visual Computing

Proyecto de Computación Gráfica / Visual Computing (Universidad Nacional de Colombia — Sede Medellín, 2026-2).
Trabajamos con imágenes de radiografías: carga, preprocesamiento, realce de contraste,
detección de umbrales y segmentación.

## Estructura

```
data/raw/         radiografías originales (NO se suben a GitHub)
data/processed/   imágenes procesadas (NO se suben a GitHub)
notebooks/        exploración en Jupyter
src/              código reutilizable del proyecto
results/          figuras y resultados para el informe
```

## Entorno

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Datos

Las imágenes médicas no se versionan. Cada integrante las pone en `data/raw/`.
Usar solo datasets públicos y anonimizados (sin nombres, cédulas ni metadatos DICOM del paciente).
