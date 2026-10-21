# Exposición — 26 de octubre de 2026

> **Para qué sirve en el proyecto.** Define qué tiene que funcionar para la
> exposición, cómo se reparte el trabajo hasta esa fecha y cómo se usan los 10
> minutos. Ajusta el [ROADMAP](../ROADMAP.md) al tiempo disponible: el roadmap
> completo (fases 0–4) no cabe antes del 26/10. Estado actualizado el 21/10/2026.

**Formato:** 10 minutos por proyecto. El profesor Paluszny pregunta sobre temas como
los de la propuesta (Hounsfield → malla, iluminación, rendimiento, suavizado y plano
de corte), y puede preguntarle a cualquier integrante. Las respuestas técnicas están
en [preguntas-clave.md](preguntas-clave.md).

**Página web del proyecto:** https://69kingdavid69.github.io/radiografias-visual-computing/
(código en [`web/`](../../web/README.md)). Muestra la teoría con la tomografía real y
modelos 3D que se pueden girar. Reemplaza las diapositivas de teoría.

## 1. Alcance para el 26

| Debe funcionar | Módulo / responsable | Estado al 21/10 |
|---|---|---|
| Cargar un **CBCT dental real** (muestra de Slicer, ToothFairy3 o DICOM) | `carga.py` — David | ✅ Hecho: `cargar_estudio` con SimpleITK, caché y normalización de escala (PR #4 y #7) |
| Visor 2D con tres vistas y contraste | `visor_cortes.py`, `app_qt.py` — Juan | ✅ Hecho dentro de la app Qt, con botones de ventana por escala (PR #3 y #8) |
| Vista 3D con presets de estructura | `render_3d.py` — Emanuel | ✅ En la ventana 3D aparte (`python -m src.main … --modo 3d`): teclas 1–5 para los presets e `i` para la vista de implante (PR #9). ⚠️ El panel 3D **dentro de la app Qt** sigue siendo una tarjeta de "integración prevista" |
| Presets hueso / dientes / esmalte / metal | `densidades.py` | ✅ En el código, con los valores de [densidades.md §2.1](densidades.md#21-para-la-muestra-de-3d-slicer-demo-del-2610--medidos) |
| Plano de corte (pregunta 5) | `render_3d.py` — Emanuel | ⚠️ Falta en la aplicación. Se muestra en la **página web** (pestaña "Corte") |
| Phong vs. plano y suavizado Taubin (preguntas 2 y 4) | `render_3d.py` — Emanuel | ⚠️ Falta en la aplicación. Se muestra en la **página web** (pestañas "Luz" y "Suavizado") |
| `flying_edges` y tiempos (pregunta 3) | `render_3d.py` — Emanuel | Tiempos medidos ([preguntas-clave.md](preguntas-clave.md)); faltan los FPS en el computador de la demo. La página muestra FPS en vivo |
| Página web con la teoría | `web/` — Nicolás | ✅ Hecha; se publica sola con GitHub Pages (`.github/workflows/pages.yml`, David) |
| Capturas y video de respaldo de la aplicación | Emanuel + Juan | Pendiente |

**No hace falta para el 26:** las pruebas con usuarios ni la validación con
ToothFairy3. Se presentan como trabajo en curso.

## 2. Calendario (desde el 21/10)

| Fecha | Qué | Quién |
|---|---|---|
| Mié 21 – Jue 22 | Si alcanza: panel 3D dentro de la app Qt (`Render3D` con `QtInteractor`). Si no, la demo 3D se hace en la ventana aparte | Emanuel (+ David) |
| Jue 22 | Revisar la página web en el computador de la exposición | Nicolás |
| Jue 22 | Capturas y video corto de respaldo de la app | Emanuel + Juan |
| **Vie 23** | **Ensayo 1** cronometrado + ronda de preguntas de práctica | Todos |
| Dom 25 | Ensayo 2; se congela el código | Todos |
| **Lun 26** | Exposición | Todos |

## 3. Guion de 10 minutos

Supuesto: unos 6 minutos de presentación con demo y 4 de preguntas. Se ajusta si el
profesor indica otro formato.

| Tiempo | Quién | Qué se dice / muestra |
|---|---|---|
| 0:00–1:00 | **Nicolás** | **Página web, portada y sección 1:** la radiografía es 2D y superpone; el CBCT es un cubo de vóxeles (se pasa el ratón por un corte y se lee la densidad). Pregunta de investigación. Datos usados. |
| 1:00–1:45 | **David** | Pipeline en una diapositiva: archivo (GIPL, NIfTI o DICOM) → carga (densidad, orden de cortes, vóxel en mm) → **escala** (picos de aire y tejido blando → una recta) → `Estudio` → 2D (cortes) y 3D (preset, σ y marching cubes). Diapositiva y guion de 45 s: https://claude.ai/artifact/NVTS1dRJ2QBUYN95hnP1Kf (privada hasta que David la comparta). |
| 1:45–3:00 | **Juan** | **Demo 2D en la app:** recorrer cortes, tres vistas, contraste (ventana/nivel) para separar esmalte de dentina. |
| 3:00–4:30 | **Emanuel** | **Demo 3D en el programa:** presets hueso → dientes → esmalte → metal y vista de implante; rotar. |
| 4:30–6:00 | **Nicolás** | **Página web, secciones 2, 3 y 5:** barra de umbral con el histograma (el CBCT no está en HU: 0–3874), *marching squares* en vivo y hallazgos. Respuesta a la pregunta. |
| 6:00–10:00 | Todos | Preguntas. Para luz, suavizado, corte o rendimiento se responde **mostrando** la pestaña correspondiente del laboratorio 3D de la página. |

### Temas por integrante

Si el profesor no dirige la pregunta a alguien en particular, responde quien conoce
mejor el tema. Como puede preguntarle a cualquiera, **todo el equipo** debe conocer
las cinco respuestas de [preguntas-clave.md](preguntas-clave.md).

| Tema | Principal | Apoyo | Dónde mostrarlo |
|---|---|---|---|
| Hounsfield → malla, marching cubes | Emanuel | Nicolás (HU y CBCT) | Página: secciones 2 y 3 |
| Iluminación Phong/Gouraud, sombras | Emanuel | Nicolás | Página: laboratorio → Luz |
| Rendimiento, FPS, optimización | Emanuel | David (submuestreo y caché) | Página: laboratorio → Rendimiento y Hallazgos |
| Suavizado | Emanuel | David (filtro de volumen) | Página: laboratorio → Suavizado |
| Plano de corte | Emanuel | Juan (vistas 2D) | Página: laboratorio → Corte |
| DICOM, espaciado, carga, escala | David | Nicolás | Diapositiva de David |
| Datos, densidades, anatomía, limitaciones, privacidad | Nicolás | — | Página: secciones 1, 2 y 5 |
| Interfaz, ventana/nivel | Juan | — | App Qt y página: sección 1 |

## 4. Material de apoyo

- **Página web** (teoría y modelos 3D): reemplaza las diapositivas de teoría.
- **Diapositiva del pipeline** de David (enlace en el guion).
- **App Qt y ventana 3D** para la demo en vivo.

## 5. Plan B si algo falla

- **Sin internet:** la página funciona en local con
  `python -m http.server 8000 --directory web` (todo, three.js incluido, está dentro de `web/`).
- **Si falla la app:** capturas y un video de 60 s de la demo guardados en el mismo computador.
- El volumen ya en caché (`data/processed`) para no depender de la carga.
- Probar el computador y el proyector antes de la clase.
