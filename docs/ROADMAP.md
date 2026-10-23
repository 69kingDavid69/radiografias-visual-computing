# Roadmap

Plan por fases y por persona. Arquitectura y decisiones técnicas: [ARCHITECTURE.md](ARCHITECTURE.md).
Las duraciones son relativas; las fechas se fijan cuando el profesor confirme la entrega.

## Equipo y roles

| Rol | Persona | Dueño de |
|---|---|---|
| **Dev 1 — Datos y pipeline** | David | `src/carga.py`, `src/main.py`, integración, repo y revisión de PRs |
| **Dev 2 — Visor 2D e interfaz** | Juan Gómez | `src/visor_cortes.py`, ventana unificada (fase 3) |
| **Dev 3 — Render 3D** | Emanuel Aristizábal | `src/render_3d.py`, rendimiento, iluminación |
| **Investigación y datos** | Nicolás | datasets CBCT, rangos de densidad, marco teórico, informe |

Plan de construcción detallado de cada persona:
[David](planes/dev1-david.md) · [Juan](planes/dev2-juan.md) ·
[Emanuel](planes/dev3-emanuel.md) · [Nicolás](planes/investigacion-nicolas.md)

**Exposición del 26 de octubre:** plan, guion de 10 minutos y respuestas a las
preguntas de la propuesta en [investigacion/exposicion.md](investigacion/exposicion.md)
y [investigacion/preguntas-clave.md](investigacion/preguntas-clave.md).

Los rangos de `src/densidades.py` los proponen en conjunto **Nicolás**
(lo que dice la literatura) y **Emanuel** (lo que se ve en el render).

## Forma de trabajo

- Una rama por tarea (`feat/visor-contraste`, `fix/espaciado-z`, …) y un PR a `main`
  con una revisión de otra persona.
- Las imágenes médicas nunca van al repo: cada uno las guarda en `data/raw/`.
- Una reunión corta por semana para revisar este roadmap y marcar casillas.

---

## Fase 0 — Vertical slice (1 semana)

- [x] Repo, estructura de carpetas, `.gitignore` de datos médicos — David
- [x] Esqueleto: carga DICOM → visor 2D → isosuperficie 3D con barra — David
- [x] Prueba con volumen sintético (esfera) y DICOM de ejemplo de pydicom — David
- [x] Cada dev clona, crea el `.venv` y corre `--modo cortes` y `--modo 3d` — todos (los tres subieron código probado: PRs #2, #3, #13)
- [x] Lista de 2–3 datasets CBCT dentales candidatos con licencia y forma de acceso — Nicolás ([datasets.md](investigacion/datasets.md))

**Hito:** los tres devs ven un modelo 3D en su computador.

## Fase 1 — Datos reales (1–2 semanas)

- [x] Descargar el dataset elegido y verificar que está anonimizado — Nicolás (muestras de Slicer; `scripts/verificar_anonimizacion.py`)
- [x] Cargar estudios reales: orientación, espaciado z, caso multiframe — David (`cargar_estudio`, GIPL/NIfTI/DICOM, PR #4)
- [x] Caché del volumen en `data/processed/*.npz` para no releer los DICOM — David (solo carpetas DICOM: un `.gipl.gz` se lee más rápido que su caché)
- [x] Visor 2D: control de ventana/nivel (contraste) y número de corte en mm — Juan (PR #3)
- [x] Vistas coronal y sagital además de la axial — Juan (PR #3)
- [x] Render 3D: recalcular solo al soltar la barra; medir tiempos con `reduccion` 1, 2 y 4 — Emanuel (PR #2; benchmark con la muestra real en `scripts/benchmark_render.py`)

**Hito:** se recorre un CBCT dental real en 2D y se ve la mandíbula en 3D.

## Fase 2 — Aislar estructuras por densidad (2 semanas)

- [x] Histograma de densidades de cada estudio; identificar los picos de aire, tejido blando, hueso y esmalte — Nicolás + Emanuel (`scripts/histograma_densidades.py`; picos automáticos en `src/escala.py`)
- [x] Llenar `RANGOS_DENSIDAD` y justificar cada rango con fuentes — Nicolás + Emanuel (escala `slicer` medida; `hounsfield` calibrada con 11 pacientes de STS, PR #19)
- [x] Presets en la vista 3D (botones o menú) — Emanuel (`Render3D.aplicar_preset`, teclas en `--modo 3d` y barra *Estructura 3D* en la app: PRs #9, #17)
- [x] Filtro de ruido opcional antes del umbral — David (`src/filtros.py`, gaussiano de SimpleITK con sigma en mm por estructura, PR #7)
- [x] Opacidad por estructura: hueso semitransparente y esmalte sólido — Emanuel (`aplicar_capas`: vista de implante y tejidos blandos, PRs #9, #18)

**Hito:** con un clic se ve solo el hueso o solo el esmalte.

## Fase 3 — Interfaz única (2 semanas)

- [x] Cerrar la decisión abierta #1 (Qt vs. web) — equipo (**las dos**: app de escritorio en Qt y página web de apoyo en GitHub Pages)
- [x] Ventana con panel 2D y panel 3D lado a lado — Juan (vista *Dividida*; panel 3D de Emanuel, PRs #13, #17)
- [x] Selector de carpeta de estudio desde la interfaz, sin línea de comandos — Juan + David (botón *Cargar estudio*: archivo de volumen o un `.dcm`)
- [ ] Integrar presets y barra de sensibilidad en la ventana — Emanuel (presets **hechos**, PR #17; falta la barra de umbral libre dentro de la app: hoy solo está en `--modo 3d`)
- [ ] Aplicar el rediseño de la interfaz (propuesta del 21/10: tema oscuro clínico, panel lateral con escala, presets y contraste, diálogo de abrir estudio con diagnóstico de escala; detalle en [bitacora-desarrollo.md](bitacora-desarrollo.md)) — Juan
- [ ] Probar la app con usuarios que no la construyeron (compañeros de salud, si hay) — Nicolás

**Hito:** una persona sin terminal abre un estudio y explora 2D y 3D.

## Fase 4 — Cierre (1 semana)

- [x] Capturas y figuras en `results/` — Emanuel (figuras de presets, suavizado, colores, implante, STS y calibración; falta el video de respaldo del plan B)
- [ ] Informe: pregunta de investigación, método (marching cubes, umbrales), resultados y limitaciones — Nicolás (con secciones técnicas de cada dev)
- [ ] Guion y ensayo de la demo en vivo — todos
- [x] README final con instrucciones de instalación y uso — David (comandos probados el 23/10)

**Hito:** entrega al profesor Paluszny.

---

## Opcional (si sobra tiempo)

- Exportar la superficie a STL para imprimir en 3D o abrir en Blender.
- Medir distancias en el modelo 3D (por ejemplo, el ancho de un diente en mm).
- Renderizado volumétrico directo (`add_volume`) como alternativa a la isosuperficie.
