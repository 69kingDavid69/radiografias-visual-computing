# Investigación y datos

Esta carpeta reúne la investigación del proyecto: **qué datos usa el programa, qué
rangos de densidad aplica, en qué teoría se apoya y cómo se evalúa**. Corresponde al
rol de investigación y datos del [ROADMAP](../ROADMAP.md) (Nicolás) y alimenta
directamente al código (`src/`), al informe final y a la exposición.

## Resumen

- **Datos:** la muestra CBCT dental de 3D Slicer para el desarrollo y la demo (ya
  probada con el código), y **ToothFairy3** para los resultados del informe.
- **Rangos de densidad:**
  - en la muestra de Slicer (medidos): 700 = hueso, 1000 = dientes, 1250 = esmalte,
    2000 = metal;
  - en ToothFairy3, en Hounsfield (propuesta a validar): 150 = hueso, 1300 = dientes,
    2000 = esmalte.
- **Hallazgo principal:** los grises del CBCT no son unidades Hounsfield; cada equipo
  da números distintos, así que los umbrales se adaptan al estudio.

## Cómo encaja cada documento en el proyecto

| Documento | Qué define | Dónde se usa |
|---|---|---|
| [datasets.md](datasets.md) | Las tomografías que usa el programa, por qué se eligieron y cómo se leen | `src/carga.py` (formato y lector), `data/raw/`, sección "Datos" del informe |
| [densidades.md](densidades.md) | Los rangos de densidad de cada estructura y su justificación | `src/densidades.py` (`RANGOS_DENSIDAD`), presets de `src/render_3d.py` |
| [marco-teorico.md](marco-teorico.md) | La teoría del proyecto: CBCT, DICOM, anatomía, Hounsfield, umbralización, marching cubes, iluminación, suavizado, rendimiento y plano de corte, con glosario | Base técnica de todos los módulos y del informe |
| [preguntas-clave.md](preguntas-clave.md) | Respuestas técnicas a las 5 preguntas de la propuesta, con código PyVista y mediciones | Decisiones de `src/render_3d.py` y la exposición |
| [informe.md](informe.md) | Borrador del informe final | Entrega al profesor |
| [exposicion.md](exposicion.md) | Alcance, calendario y guion de la exposición del 26/10 | Coordinación del equipo |
| [pruebas-usuarios.md](pruebas-usuarios.md) | Protocolo de evaluación con usuarios (5 tareas y SUS) | Fase 3 y sección de resultados del informe |

## Figuras y tablas

En [`results/investigacion/`](../../results/investigacion/), generadas con la muestra
de 3D Slicer y el código del proyecto (`src/render_3d.a_pyvista`):

| Archivo | Muestra |
|---|---|
| `histograma_muestra_slicer.png` | Distribución de densidades y umbrales automáticos |
| `umbrales_muestra_slicer.png` | Superficie 3D con umbrales 700, 1000, 1250 y 2000 |
| `corte_axial_brackets.png` | Corte axial con el metal de ortodoncia marcado en rojo |
| `sombreado_y_suavizado.png` | Sombreado plano vs. Phong y suavizado Laplaciano vs. Taubin |
| `plano_corte.png` | Superficie cortada con un plano |
| `tiempos_muestra_slicer.csv` | Tiempo de extracción y triángulos según algoritmo y submuestreo |

## Scripts

En `scripts/`, probados con DICOM, NIfTI con etiquetas y GIPL. Además de
`requirements.txt` necesitan `SimpleITK` (GIPL/MHA) o `nibabel` (NIfTI).

| Script | Para qué | Etapa del proyecto |
|---|---|---|
| `verificar_anonimizacion.py` | Revisa si los DICOM traen datos del paciente y resume cada estudio (equipo, cortes, vóxel) | Antes de usar cualquier estudio nuevo |
| `histograma_densidades.py` | Histograma, umbrales automáticos, percentiles altos y densidad por estructura etiquetada | Definir y validar `RANGOS_DENSIDAD` |
