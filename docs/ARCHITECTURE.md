# Arquitectura — Explorador de cortes tomográficos y renderizado 3D por densidad

> **Pregunta de investigación.** ¿De qué manera podemos desarrollar una interfaz
> gráfica que transforme los datos volumétricos de una tomografía dental (CBCT)
> en un modelo 3D interactivo, aislando estructuras específicas según su densidad?

Proyecto de Visual Computing — Universidad Nacional de Colombia, Sede Medellín (2026-2).
Equipo: tres desarrolladores y una persona a cargo de investigación y datos
(roles en [ROADMAP.md](ROADMAP.md): David, Juan Gómez, Emanuel Aristizábal y Nicolás).

---

## 1. Flujo funcional del MVP

1. El usuario abre el programa y elige la carpeta de un estudio tomográfico dental
   (los cortes DICOM que exporta el equipo CBCT).
2. El programa lee todos los cortes, los ordena por altura y los apila en un
   "cubo" 3D de densidades. Muestra un resumen: número de cortes, tamaño del
   vóxel en mm y rango de densidades.
3. **Navegación multicorte (2D).** El usuario ve un corte axial en escala de
   grises y lo recorre con un deslizador, capa por capa, desde la base de la
   mandíbula hasta las coronas dentales.
4. **Reconstrucción 3D por umbral.** El usuario pasa a la vista 3D. Una barra de
   sensibilidad fija la densidad mínima visible: al subirla, la piel y las
   encías (tejido blando) desaparecen y quedan solo el hueso maxilar y el
   esmalte dental.
5. El usuario rota, acerca e ilumina el modelo 3D con el mouse.
6. Como atajo, el usuario puede elegir un preset ("hueso", "esmalte", …) que
   ajusta la barra al rango de densidad de esa estructura.

## 2. Diagrama de arquitectura

Es una aplicación de escritorio local en Python: no hay servidor, base de datos
ni red. Los datos del paciente no salen del computador.

```
                     ┌──────────────────────────────┐
  data/raw/<estudio> │  Serie DICOM (cortes .dcm)   │  equipo CBCT / dataset público
                     └──────────────┬───────────────┘
                                    │ lectura de archivos (pydicom)
                                    ▼
                     ┌──────────────────────────────┐
                     │  src/carga.py                │  ordena cortes por z,
                     │  cargar_serie_dicom()        │  reescala a densidad,
                     │  → volumen (z,y,x), espaciado│  calcula vóxel en mm
                     └──────┬───────────────┬───────┘
                            │ numpy array   │ numpy array
               ┌────────────▼─────┐   ┌─────▼──────────────────────┐
               │ src/visor_cortes │   │ src/render_3d.py           │
               │ matplotlib +     │   │ numpy → pv.ImageData       │
               │ Slider           │   │ contour(umbral) = marching │
               │ (herramienta 1)  │   │ cubes → malla de superficie│
               └────────┬─────────┘   │ PyVista/VTK + slider       │
                        │             │ (herramienta 2)            │
                        │             └─────▲──────────────┬───────┘
                        │                   │ presets      │
                        │             ┌─────┴────────────┐ │
                        │             │ src/densidades.py│ │
                        │             │ RANGOS_DENSIDAD  │ │
                        │             └──────────────────┘ │
                        ▼                                  ▼
               ┌───────────────────────────────────────────────────┐
               │ Interfaz: hoy dos ventanas lanzadas desde         │
               │ src/main.py (CLI). Fase 3: una sola ventana Qt     │
               │ con ambas vistas (pyvistaqt) — decisión abierta #1 │
               └───────────────────────────────────────────────────┘
```

## 3. Reutilización de código existente

_No hay código previo; todo se construye desde cero._ Como referencia del curso
está el modelo 3D de ejemplo del húmero (`.stl`) de la sesión de Computación
Gráfica: sirve para comparar el resultado de nuestra reconstrucción con una malla
ya hecha.

## 4. Modelo de datos

No hay base de datos. Todo vive en memoria mientras el programa corre:

```python
volumen: np.ndarray        # float32, forma (z, y, x) — densidad por vóxel
espaciado: tuple           # (dz, dy, dx) en mm — tamaño físico del vóxel
malla: pv.ImageData        # el mismo volumen como rejilla VTK, campo "densidad"
superficie: pv.PolyData    # isosuperficie en el umbral elegido (triángulos)
RANGOS_DENSIDAD: dict      # {"hueso": (min, max), ...} presets por estructura
```

En disco:

```
data/raw/<id_estudio>/*.dcm     entrada, NUNCA se versiona (.gitignore)
data/processed/                 volúmenes .npy cacheados (opcional, fase 2)
results/                        capturas y figuras para el informe
```

## 5. Stack tecnológico recomendado

| Capa | Tecnología | Razón |
|---|---|---|
| Lenguaje | Python 3.13 (decidido) | Es el lenguaje de Fundamentos de Programación; todo el equipo lo conoce. |
| Lectura DICOM | pydicom (decidido) | Lee cortes y metadatos (posición, espaciado, reescalado) sin dependencias pesadas. |
| Volumen | NumPy (decidido) | Un CBCT es un arreglo 3D; recortar, submuestrear y umbralizar son una línea cada una. |
| Visor 2D | matplotlib + `widgets.Slider` (decidido para el MVP) | Es lo más simple para mostrar un corte con un deslizador. |
| Render 3D | PyVista sobre VTK (decidido) | `contour()` implementa marching cubes, y `add_slider_widget` da la barra de sensibilidad con rotación, zoom e iluminación ya incluidos. |
| Interfaz unificada | pyvistaqt + PySide6 (sugerido) | Mete el visor 2D y el 3D en una sola ventana con paneles. |
| Procesamiento extra | scikit-image (sugerido) | Filtros para reducir ruido antes del umbral (el CBCT es más ruidoso que un CT médico). |
| Datos de prueba | dataset público CBCT anonimizado (sugerido) | Los busca la persona de investigación; ver decisión abierta #2. |
| Control de versiones | Git + GitHub público (sin datos de pacientes: `data/raw/` no se versiona) | `69kingDavid69/radiografias-visual-computing`. |

## 6. Plan de construcción por fases

Resumen; el detalle por persona está en [ROADMAP.md](ROADMAP.md).

| Fase | Duración | Entregable |
|---|---|---|
| 0 — Vertical slice | 1 semana | `python -m src.main <carpeta> --modo 3d` abre un estudio real y muestra la isosuperficie con la barra. **Estado: esqueleto hecho y probado con datos sintéticos.** |
| 1 — Datos reales | 1–2 semanas | Un dataset CBCT dental cargando bien (orientación, espaciado, multiframe); visor 2D con ventana/nivel de contraste. |
| 2 — Densidades | 2 semanas | Presets en `RANGOS_DENSIDAD` validados sobre los estudios; filtro de ruido; render fluido (submuestreo o caché). |
| 3 — Interfaz única | 2 semanas | Una ventana con los cortes 2D y el modelo 3D lado a lado, selector de estudio y de preset. |
| 4 — Cierre | 1 semana | Capturas, informe que responde la pregunta de investigación y demo en vivo. |

## 7. MCPs y Skills útiles para construir esto

**MCPs disponibles en el entorno**

| MCP | Para qué sirve en este proyecto |
|---|---|
| PubMed / bioRxiv (bio-research) | Investigación: artículos sobre segmentación por umbral en CBCT y rangos de densidad dental. |
| Consensus (bio-research) | Búsqueda rápida de evidencia para el marco teórico del informe. |
| Blender | Abrir mallas exportadas (STL) para comparar con el húmero de clase o preparar renders para el informe. |
| Navegador integrado | Revisar la documentación de PyVista/pydicom y las páginas de los datasets. |

**Skills**

| Skill | Aporte |
|---|---|
| `scrape` | Bajar documentación y fichas de datasets completas para el equipo. |
| `graphify` | Mapa del código cuando el proyecto crezca. |
| `dataviz` | Histogramas de densidad para justificar los umbrales en el informe. |
| `segundo-cerebro` | Registrar decisiones del proyecto en el vault de la carrera. |
| Custom propuesta: `nuevo-estudio` | Validar una carpeta DICOM (anonimización, cortes faltantes, espaciado) antes de usarla. |

## 8. Riesgos y decisiones abiertas

1. **Decisión abierta — interfaz final.** Opciones: (a) dos ventanas separadas
   como hoy; (b) una ventana Qt con pyvistaqt; (c) una app web con `trame`.
   Recomendación: (b) en la fase 3.
2. **Decisión — dataset (propuesta de investigación, 15/10).** Debe ser CBCT
   **dental**, público y anonimizado. Ver
   [investigacion/datasets.md](investigacion/datasets.md):
   - desarrollo y demo: **muestra CBCT de 3D Slicer** (GIPL, 24 MB, sin registro,
     ya probada con nuestro código);
   - resultados del informe: **ToothFairy3** (NIfTI, en HU, 0.3 mm, 77 etiquetas;
     pide cuenta);
   - opcional: el dataset DICOM de ScienceDB (3 equipos).

   Se descartaron CTooth, PhysioNet y STS-Tooth. Implica un lector con SimpleITK en
   `carga.py`.
3. **Riesgo — el CBCT no está en Hounsfield.** A diferencia del CT médico, los
   valores de gris del CBCT varían entre equipos, así que un umbral fijo no sirve
   para todos. *Mitigación:* presets por estudio o relativos al histograma.
   Confirmado con la muestra de 3D Slicer (valores de 0 a 3874); ver
   [investigacion/densidades.md](investigacion/densidades.md).
4. **Riesgo — rendimiento.** Un volumen de 512³ tiene unos 134 millones de
   vóxeles, y `contour()` se vuelve lento al arrastrar la barra. *Mitigación:*
   `reduccion=2` por defecto, recalcular al soltar la barra y cachear el volumen.
5. **Riesgo — privacidad.** Los DICOM traen nombre y documento del paciente.
   *Mitigación:* `data/raw` fuera de git y solo datos anonimizados.
6. **Riesgo — archivos multiframe.** Algunos equipos exportan todo el estudio en
   un solo archivo. `carga.py` ya contempla ese caso, pero el espaciado en z puede
   venir en otras etiquetas. *Mitigación:* probar con al menos dos fuentes distintas.
7. **Decisión abierta — exportar STL.** ¿Se guarda la malla para impresión 3D o
   Blender? Es barato (`superficie.save("x.stl")`), pero no está en la propuesta.
8. **Decisión abierta — formato de entrega.** Falta confirmar con el profesor
   Paluszny si se entrega informe, demo o ambos, y las fechas.
