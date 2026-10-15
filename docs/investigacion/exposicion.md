# Exposición — 26 de octubre de 2026

**Formato:** 10 minutos por proyecto. El profesor Paluszny pregunta sobre temas como
los de la propuesta: Hounsfield → malla, iluminación, rendimiento, suavizado y plano
de corte. Respuestas preparadas en [preguntas-clave.md](preguntas-clave.md).

Hoy es jueves 15 de octubre: quedan **11 días**. El roadmap original (fases 0–4) no cabe
completo; este documento dice **qué tiene que estar listo para la exposición** y
cómo repartir los 10 minutos.

## 1. Alcance mínimo para el 26 (lo que se va a mostrar)

| Debe funcionar | Responsable | Estado al 15/10 |
|---|---|---|
| Cargar un **CBCT dental real** (muestra de Slicer o ToothFairy3) | David | Solo DICOM; falta un lector SimpleITK (código de ejemplo probado en [datasets.md](datasets.md)) |
| Visor 2D con tres vistas y contraste | Juan | Hecho en la rama `feat/visor-contraste`, **sin PR** |
| Vista 3D con barra de umbral | Emanuel | `a_pyvista` + `contour` **probados con la muestra real** (15/10); falta conectarlo a `main.py` con el nuevo lector |
| Presets hueso / dientes / esmalte | Nicolás + Emanuel | Valores para la muestra de Slicer probados en [densidades.md §2.1](densidades.md#21-para-la-muestra-de-3d-slicer-demo-del-2610--medidos); en HU para ToothFairy3 |
| Plano de corte (pregunta 5) | Emanuel | No está en la app; `pl.add_mesh_clip_plane(superficie)` probado y funciona |
| Suavizado Taubin activable (pregunta 4) | Emanuel | No está en la app; `superficie.smooth_taubin()` probado |
| Tabla de tiempos `reduccion` 1/2/4 (pregunta 3) | Emanuel | Medida con la muestra en [preguntas-clave.md](preguntas-clave.md); falta medir FPS en la ventana real del computador de la demo |
| Figuras para las diapositivas | Nicolás | En `results/investigacion/`: histograma, umbrales, sombreado, suavizado y plano de corte |
| Capturas de respaldo de la app | Emanuel + Juan | No están |

**No hace falta para el 26:** la ventana Qt unificada (fase 3) ni las pruebas con
usuarios. Se mencionan como trabajo en curso.

## 2. Calendario sugerido

| Fecha | Qué | Quién |
|---|---|---|
| **Vie 16** | Reunión corta: elegir dataset, repartir este plan, fusionar la rama de Juan | Todos |
| Vie 16 | Bajar la muestra de Slicer (24 MB) y crear la cuenta de ToothFairy3 | Nicolás |
| Sáb 17 – Dom 18 | Lector SimpleITK en `carga.py`; correr la app con el CBCT real | David |
| Sáb 17 – Lun 19 | Correr `histograma_densidades.py` con ToothFairy3 (con `--etiquetas`) y ajustar los presets en HU; con la muestra de Slicer ya está hecho | Nicolás + Emanuel |
| Sáb 17 – Mar 20 | Plano de corte, Taubin, flying edges, medición de tiempos | Emanuel |
| Mar 20 – Mié 21 | Diapositivas (6–8) | Nicolás arma; cada uno pone su parte |
| Jue 22 | Capturas y video corto de respaldo de la demo | Emanuel + Juan |
| **Vie 23** | **Ensayo 1** cronometrado + ronda de preguntas de práctica | Todos |
| Dom 25 | Ensayo 2; congelar el código (nada nuevo después de esto) | Todos |
| **Lun 26** | Exposición | Todos |

## 3. Guion de 10 minutos

Supuesto: unos 6 minutos de presentación con demo y 4 de preguntas. Ajustar si el
profesor indica otro formato.

| Tiempo | Quién | Qué decir / mostrar |
|---|---|---|
| 0:00–1:00 | **Nicolás** | Problema: la radiografía es 2D y superpone; el CBCT es un cubo de cortes. Pregunta de investigación. Dataset usado. |
| 1:00–1:45 | **David** | Pipeline en una diapositiva: DICOM → reescalado → volumen + espaciado → 2D y 3D. |
| 1:45–3:00 | **Juan** | **Demo 2D:** recorrer cortes, tres vistas, contraste (ventana/nivel) para separar esmalte de dentina. |
| 3:00–5:00 | **Emanuel** | **Demo 3D:** barra de umbral (hueso → dientes → esmalte), rotar, Phong vs. plano, **plano de corte** por un molar. |
| 5:00–6:00 | **Nicolás** | Resultados y limitaciones, con figuras de `results/investigacion/`: el histograma muestra que el CBCT no está en HU (0–3874); los umbrales 700 / 1000 / 1250 / 2000; el metal (brackets) supera al esmalte; hay solapamiento cortical–esmalte. Respuesta a la pregunta. |
| 6:00–10:00 | Todos | Preguntas. Cada pregunta la responde el "dueño" del tema (tabla siguiente). |

### Quién responde cada pregunta

| Tema | Responde | Apoya |
|---|---|---|
| Hounsfield → malla, marching cubes | Emanuel | Nicolás (HU y CBCT) |
| Iluminación Phong/Gouraud, sombras | Emanuel | — |
| Rendimiento, FPS, optimización | Emanuel | David (submuestreo y caché) |
| Suavizado | Emanuel | David (filtro de volumen) |
| Plano de corte | Emanuel | Juan (vistas 2D) |
| DICOM, espaciado, datos | David | Nicolás |
| Densidades, umbrales, anatomía, privacidad | Nicolás | — |
| Interfaz, ventana/nivel | Juan | — |

Emanuel concentra muchas preguntas: **todos** deben leer
[preguntas-clave.md](preguntas-clave.md) para poder cubrirlo.

## 4. Diapositivas sugeridas (6–8)

1. Título, equipo y pregunta de investigación.
2. Radiografía 2D vs. CBCT 3D (imagen de un corte y de un volumen).
3. Datos: dataset, vóxel de 0.3–0.5 mm, anonimización.
4. Pipeline (diagrama de ARCHITECTURE.md simplificado).
5. Marching cubes en un dibujo: cubo de 8 esquinas → triángulos.
6. Histograma de densidades con los umbrales de los presets.
7. Resultados: capturas de los presets y tabla de tiempos.
8. Limitaciones y trabajo futuro.

## 5. Plan B si la demo falla

- Tener **capturas y un video de 60 s** de la demo en el mismo computador, fuera de
  línea.
- Llevar el volumen ya en caché (`data/processed`) para no depender de la carga.
- Probar el computador y el proyector antes de la clase.
