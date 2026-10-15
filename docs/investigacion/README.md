# Investigación y datos

Carpeta de Nicolás ([plan](../planes/investigacion-nicolas.md)). Actualizada el
15/10/2026.

## Lo esencial en 30 segundos

- **Datos del programa:** la muestra CBCT dental de 3D Slicer para desarrollar y para
  la demo (ya probada), y **ToothFairy3** para los resultados del informe.
  → [datasets.md](datasets.md)
- **Rangos de densidad:** en la muestra de Slicer, 700 = hueso, 1000 = dientes,
  1250 = esmalte, 2000 = metal (medidos). En ToothFairy3 (HU), 150 = hueso,
  1300 = dientes, 2000 = esmalte (propuesta a validar). → [densidades.md](densidades.md)
- **Hallazgo principal:** los grises del CBCT no son unidades Hounsfield; cada equipo
  da números distintos, así que los umbrales deben adaptarse al estudio.

## Documentos

| Documento | Qué contiene |
|---|---|
| [datasets.md](datasets.md) | **Qué tomografías usa el programa** y por qué; fichas, descarga, cómo leerlas y citas obligatorias |
| [densidades.md](densidades.md) | **Rangos de densidad** de cada estructura: los que se usan, de dónde salen (literatura y mediciones) y cómo validarlos |
| [marco-teorico.md](marco-teorico.md) | Teoría completa explicada paso a paso: CBCT, DICOM, anatomía, Hounsfield, umbralización, marching cubes, iluminación, suavizado, rendimiento, plano de corte y glosario |
| [informe.md](informe.md) | **Borrador del informe final**, con las secciones de investigación redactadas y lo que falta marcado por persona |
| [preguntas-clave.md](preguntas-clave.md) | Respuestas a las 5 preguntas de la propuesta para la exposición, con números medidos. **Todos deben leerlo** |
| [exposicion.md](exposicion.md) | Plan hasta la exposición del 26/10: qué debe funcionar, calendario, guion de 10 minutos |
| [pruebas-usuarios.md](pruebas-usuarios.md) | Guion de pruebas con usuarios y cuestionario SUS (fase 3) |

## Figuras y tablas

En [`results/investigacion/`](../../results/investigacion/), hechas con la muestra de
3D Slicer:

- histograma;
- superficies en cuatro umbrales;
- sombreado plano vs. Phong;
- suavizado Laplaciano vs. Taubin;
- plano de corte;
- corte axial con los brackets;
- tiempos de `contour`.

## Scripts

En `scripts/`, probados el 15/10/2026 con DICOM, NIfTI con etiquetas y GIPL. Además
de `requirements.txt` necesitan `SimpleITK` (GIPL/MHA) o `nibabel` (NIfTI).

- `verificar_anonimizacion.py`: revisa si los DICOM traen datos del paciente y
  resume cada estudio (equipo, cortes, vóxel).
- `histograma_densidades.py`: histograma, umbrales automáticos, percentiles altos y
  densidad por estructura etiquetada.
