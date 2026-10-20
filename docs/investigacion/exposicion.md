# Exposición — 26 de octubre de 2026

> **Para qué sirve en el proyecto.** Define qué tiene que funcionar para la
> exposición, cómo se reparte el trabajo hasta esa fecha y cómo se usan los 10
> minutos. Ajusta el [ROADMAP](../ROADMAP.md) al tiempo disponible: el roadmap
> completo (fases 0–4) no cabe antes del 26/10. Estado tomado el 15/10/2026.

**Formato:** 10 minutos por proyecto. El profesor Paluszny pregunta sobre temas como
los de la propuesta (Hounsfield → malla, iluminación, rendimiento, suavizado y plano
de corte), y puede preguntarle a cualquier integrante. Las respuestas técnicas están
en [preguntas-clave.md](preguntas-clave.md).

## 1. Alcance mínimo para el 26

| Debe funcionar | Módulo / responsable | Estado al 15/10 |
|---|---|---|
| Cargar un **CBCT dental real** (muestra de Slicer o ToothFairy3) | `carga.py` — David | Solo lee DICOM; falta un lector con SimpleITK (hay código de ejemplo probado en [datasets.md](datasets.md#5-cómo-se-leen-en-el-programa)) |
| Visor 2D con tres vistas y contraste | `visor_cortes.py` — Juan | Hecho en la rama `feat/visor-contraste`, sin PR todavía |
| Vista 3D con barra de umbral | `render_3d.py` — Emanuel | `a_pyvista` + `contour` probados con la muestra real; falta conectarlos al nuevo lector en `main.py` |
| Presets hueso / dientes / esmalte | `densidades.py` — Nicolás + Emanuel | Valores medidos para la muestra en [densidades.md §2.1](densidades.md#21-para-la-muestra-de-3d-slicer-demo-del-2610--medidos); propuesta en HU para ToothFairy3 |
| Plano de corte (pregunta 5) | `render_3d.py` — Emanuel | Falta en la aplicación; `pl.add_mesh_clip_plane(superficie)` probado |
| Suavizado Taubin (pregunta 4) | `render_3d.py` — Emanuel | Falta en la aplicación; `superficie.smooth_taubin()` probado |
| `flying_edges` y tabla de tiempos (pregunta 3) | `render_3d.py` — Emanuel | Tiempos medidos con la muestra ([preguntas-clave.md](preguntas-clave.md)); faltan los FPS en el computador de la demo |
| Figuras para las diapositivas | Investigación — Nicolás | Listas en `results/investigacion/` |
| Capturas de respaldo de la aplicación | Emanuel + Juan | Pendiente |

**No hace falta para el 26:** la ventana Qt unificada (fase 3) ni las pruebas con
usuarios. Se presentan como trabajo en curso.

## 2. Calendario

| Fecha | Qué | Quién |
|---|---|---|
| **Vie 16** | Reunión corta: aprobar los datasets, repartir este plan, revisar los PR abiertos | Todos |
| Vie 16 | Descargar la muestra de Slicer (24 MB) y crear la cuenta de ToothFairy3 | Nicolás |
| Sáb 17 – Dom 18 | Lector con SimpleITK en `carga.py`; correr la aplicación con el CBCT real | David |
| Sáb 17 – Lun 19 | Correr `histograma_densidades.py` en ToothFairy3 (con `--etiquetas`) y ajustar los presets en HU | Nicolás + Emanuel |
| Sáb 17 – Mar 20 | Plano de corte, Taubin, `flying_edges` y medición de FPS | Emanuel |
| Mar 20 – Mié 21 | Diapositivas (6–8) | Nicolás las arma; cada uno aporta su parte |
| Jue 22 | Capturas y video corto de respaldo de la demo | Emanuel + Juan |
| **Vie 23** | **Ensayo 1** cronometrado + ronda de preguntas de práctica | Todos |
| Dom 25 | Ensayo 2; se congela el código | Todos |
| **Lun 26** | Exposición | Todos |

## 3. Guion de 10 minutos

Supuesto: unos 6 minutos de presentación con demo y 4 de preguntas. Se ajusta si el
profesor indica otro formato.

| Tiempo | Quién | Qué se dice / muestra |
|---|---|---|
| 0:00–1:00 | **Nicolás** | Problema: la radiografía es 2D y superpone; el CBCT es un cubo de cortes. Pregunta de investigación. Datos usados. |
| 1:00–1:45 | **David** | Pipeline en una diapositiva: DICOM → reescalado → volumen + espaciado → 2D y 3D. |
| 1:45–3:00 | **Juan** | **Demo 2D:** recorrer cortes, tres vistas, contraste (ventana/nivel) para separar esmalte de dentina. |
| 3:00–5:00 | **Emanuel** | **Demo 3D:** barra de umbral (hueso → dientes → esmalte), rotar, plano vs. Phong, **plano de corte** por un molar. |
| 5:00–6:00 | **Nicolás** | Resultados y limitaciones con las figuras de `results/investigacion/`: el histograma muestra que el CBCT no está en HU (0–3874); umbrales 700 / 1000 / 1250 / 2000; el metal supera al esmalte; hay solapamiento hueso–esmalte. Respuesta a la pregunta. |
| 6:00–10:00 | Todos | Preguntas. |

### Temas por integrante

Si el profesor no dirige la pregunta a alguien en particular, responde quien conoce
mejor el tema. Como puede preguntarle a cualquiera, **todo el equipo** debe conocer
las cinco respuestas de [preguntas-clave.md](preguntas-clave.md).

| Tema | Principal | Apoyo |
|---|---|---|
| Hounsfield → malla, marching cubes | Emanuel | Nicolás (HU y CBCT) |
| Iluminación Phong/Gouraud, sombras | Emanuel | Nicolás |
| Rendimiento, FPS, optimización | Emanuel | David (submuestreo y caché) |
| Suavizado | Emanuel | David (filtro de volumen) |
| Plano de corte | Emanuel | Juan (vistas 2D) |
| DICOM, espaciado, carga | David | Nicolás |
| Datos, densidades, anatomía, limitaciones, privacidad | Nicolás | — |
| Interfaz, ventana/nivel | Juan | — |

## 4. Diapositivas (6–8)

1. Título, equipo y pregunta de investigación.
2. Radiografía 2D vs. CBCT 3D (un corte y un volumen).
3. Datos: muestra de Slicer y ToothFairy3, vóxel de 0.3–0.5 mm, anonimización.
4. Pipeline (diagrama de ARCHITECTURE.md simplificado).
5. Marching cubes en un dibujo: cubo de 8 esquinas → triángulos.
6. Histograma de densidades con los umbrales de los presets.
7. Resultados: superficie en 4 umbrales y tabla de tiempos.
8. Limitaciones y trabajo futuro.

## 5. Plan B si la demo falla

- **Capturas y un video de 60 s** de la demo guardados en el mismo computador.
- El volumen ya en caché (`data/processed`) para no depender de la carga.
- Probar el computador y el proyector antes de la clase.
