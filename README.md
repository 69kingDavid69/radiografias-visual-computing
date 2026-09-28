# Explorador de cortes tomográficos y renderizado 3D por densidad

Proyecto de Visual Computing — Universidad Nacional de Colombia, Sede Medellín (2026-2).

**Pregunta de investigación:** ¿De qué manera podemos desarrollar una interfaz gráfica
que transforme los datos volumétricos de una tomografía dental (CBCT) en un modelo 3D
interactivo, aislando estructuras específicas según su densidad?

Una radiografía es plana (2D). Una tomografía dental es un "cubo" 3D hecho de cientos
de cortes apilados. El programa carga un estudio DICOM y ofrece dos herramientas:

1. **Navegación multicorte:** un deslizador para recorrer las capas del diente y la
   mandíbula en 2D.
2. **Reconstrucción 3D por umbral:** una barra de sensibilidad que vuelve transparentes
   los tejidos blandos y deja visibles el hueso y el esmalte, en un modelo que se puede
   rotar, acercar e iluminar.

📐 [Arquitectura](docs/ARCHITECTURE.md) · 🗺️ [Roadmap y roles](docs/ROADMAP.md)

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python -m src.main data/raw/<estudio> --modo cortes   # visor 2D
python -m src.main data/raw/<estudio> --modo 3d       # modelo 3D con umbral
```

## Estructura

```
src/carga.py          lee la serie DICOM → volumen (z, y, x) + espaciado en mm
src/visor_cortes.py   herramienta 1: cortes 2D con deslizador
src/render_3d.py      herramienta 2: isosuperficie 3D con barra de umbral
src/densidades.py     rangos de densidad por estructura (hueso, esmalte, …)
docs/                 arquitectura y roadmap
data/raw/             estudios DICOM (NO se suben a GitHub)
results/              capturas y figuras para el informe
```

## Datos

Los estudios médicos no se versionan. Cada integrante los guarda en `data/raw/`.
Usar solo datasets públicos y anonimizados.
