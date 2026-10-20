# Bitácora de desarrollo

Registro de lo que se construyó, en qué orden y **por qué**. Es la materia prima del
documento final que explicará el proyecto en detalle. Cada entrada dice qué cambió,
qué decisión se tomó y cómo se verificó.

Documentos relacionados: [ARCHITECTURE.md](ARCHITECTURE.md) (diseño) ·
[ROADMAP.md](ROADMAP.md) (plan) · [investigacion/](investigacion/README.md) (marco teórico y datos).

---

## 2026-09-28 — Arranque del proyecto

**Qué se hizo**
- Repositorio privado `69kingDavid69/radiografias-visual-computing`. Es privado porque el proyecto maneja imágenes médicas.
- `.gitignore` que excluye `data/raw/`, `data/processed/`, `*.dcm` y `*.nii*`.
- Propuesta definida: **explorador de cortes tomográficos (CBCT dental) y renderizado 3D por densidad.**
  - *Pregunta de investigación:* ¿cómo transformar los datos volumétricos de un CBCT en un modelo 3D interactivo que aísle estructuras según su densidad?
  - *Herramienta 1:* navegación multicorte en 2D con deslizador.
  - *Herramienta 2:* reconstrucción 3D por umbral (*thresholding*), con una barra de sensibilidad.
- Primer esqueleto de código con tres módulos: `carga.py` (DICOM → volumen), `visor_cortes.py` (matplotlib + Slider) y `render_3d.py` (PyVista + `contour`).
- Documentos `ARCHITECTURE.md` y `ROADMAP.md`, y un plan de construcción por persona en `docs/planes/`.

**Equipo**

| Rol | Persona | GitHub |
|---|---|---|
| Dev 1 — datos y pipeline, integración | David | `69kingDavid69` |
| Dev 2 — visor 2D e interfaz | Juan Gómez | `juanj-g` |
| Dev 3 — render 3D | Emanuel Aristizábal | `emanuel02ss` |
| Investigación y datos | Nicolás Quintana | `NothingLogic` |

**Decisiones**
- **Python + NumPy + pydicom + PyVista (VTK).** `contour()` de PyVista implementa *marching cubes*, y su `add_slider_widget` da la barra de sensibilidad, con rotación, zoom e iluminación ya incluidos.
- **Volumen en orden (z, y, x).** Es el orden natural cuando se apilan cortes. VTK recorre x primero, por eso al pasar a PyVista se usan `shape[::-1]` y `spacing[::-1]`.
- **Contratos entre módulos.** `Estudio` (David), `VisorCortes` (Juan) y `Render3D` (Emanuel) se fijaron desde el principio para poder trabajar en paralelo. `VisorCortes` y `Render3D` reciben la figura o el *plotter* desde afuera para poder meterlos después en una ventana Qt.

**Verificación**
- Esfera sintética de radio 10 vóxeles con espaciado (0.5, 0.4, 0.4) mm: la isosuperficie quedó centrada en la posición esperada en mm. Eso confirma que la conversión (z, y, x) → VTK no invierte ejes.

---

## 2026-10-15 — Investigación y datos (Nicolás) · PR #1

**Qué se hizo:** `docs/investigacion/` con datasets, rangos de densidad, marco teórico, borrador del informe, plan de la exposición y guion de pruebas con usuarios. Además, `scripts/histograma_densidades.py` y `scripts/verificar_anonimizacion.py`.

**Decisión #2 (dataset), cerrada**

| Dataset | Uso | Formato | Unidades |
|---|---|---|---|
| Muestra CBCT dental de 3D Slicer (`PreDentalSurgery`) | Desarrollo y demo del 26/10 | GIPL, 360×360×330, vóxel 0.5 mm | Grises del equipo (0–3874), **no** Hounsfield |
| ToothFairy3 (U. de Módena) | Rangos validados para el informe | NIfTI, 532 volúmenes, 77 etiquetas | Hounsfield |
| Missing teeth CBCT (ScienceDB) | Opcional: comparar equipos y probar DICOM | DICOM | Grises de cada equipo |

**Hallazgo clave:** el CBCT **no está calibrado en Hounsfield**, así que un umbral de "hueso" no sirve para todos los equipos. Umbrales medidos en la muestra de Slicer:
- 700 → hueso y dientes;
- 1000 → hueso denso y dientes;
- 1250 → coronas, metal y cortical;
- 2000 → solo el metal de los brackets.

**Consecuencia para el código:** ninguno de los dos datasets principales es DICOM, así que hizo falta un lector de GIPL y NIfTI (entrada del 19/10).

---

## 2026-10-1x — Render 3D (Emanuel) · PR #2

**Qué se hizo**
- `add_slider_widget(..., interaction_event="end")`: la isosuperficie se recalcula solo al **soltar** la barra, no en cada píxel del arrastre.
- `scripts/benchmark_render.py` y `results/tiempos.csv`.

**Pendiente detectado:** el benchmark corrió sobre un volumen sintético de 32×64×64 (131 mil vóxeles). Hay que repetirlo con la muestra de Slicer (360×360×330, unos 43 millones de vóxeles) para elegir la `reduccion` por defecto con datos reales.

---

## 2026-10-1x — Visor ortogonal y app Qt (Juan) · PR #3

**Qué se hizo**
- `VisorCortes` con vistas **axial, coronal y sagital**, líneas guía entre vistas, control de **ventana/nivel** (centro y ancho) y posición del corte en mm.
- `src/app_qt.py`: ventana PySide6 con tema oscuro, botón para cargar estudio y modos 2D, 3D y dividido. El panel 3D todavía es un *placeholder*.
- **Bug encontrado** en `carga.py`: `primero` se tomaba *antes* de ordenar los cortes, así que el espaciado en z se calculaba entre dos cortes que no eran vecinos.

---

## 2026-10-19 — Carga universal e integración (David)

**Qué se hizo**
1. **Integración:** se fusionaron los PRs #1 y #2 con *squash*, un commit limpio por PR. Antes de fusionar el #1 se revisó que las figuras no mostraran la piel ni la cara del paciente.
2. **Rama de integración de Juan (`integra/juan-visor-qt`, PR #3):** combina `feat/visor-contraste` y `spike/qt`, quita `scratch/` (archivos de prueba) y agrega PySide6 a `requirements.txt`.
3. **`cargar_estudio()` y `Estudio`** en `carga.py`:
   - lee carpetas DICOM con pydicom, y archivos GIPL, NIfTI, MHA, MHD y NRRD con **SimpleITK**;
   - devuelve `Estudio(id, volumen, espaciado, metadatos)`, así que el resto del programa no necesita saber el formato;
   - incluye el fix de Juan y lee el espaciado de los DICOM *multiframe* desde `SharedFunctionalGroupsSequence`.
4. **La app Qt usa `cargar_estudio`.** Un solo diálogo abre un archivo de volumen, o un `.dcm` (en ese caso carga su carpeta). El estudio por defecto es la muestra de Slicer.
5. **Tests** en `tests/test_carga.py` con pytest.

**Decisiones**
- **SimpleITK para los volúmenes.** Un solo `sitk.ReadImage` lee GIPL, NIfTI, MHA y NRRD según la extensión. `GetArrayFromImage` ya devuelve (z, y, x), pero `GetSpacing()` devuelve (x, y, z) y por eso se invierte.
- **Caché solo para carpetas DICOM, decidido con una medición.** La caché del GIPL ocupaba **171 MB** (float32 sin comprimir), mientras que leer el `.gipl.gz` de 24 MB toma unos **0.2 s**. Abrir cientos de archivos DICOM sí es lento, así que ahí la caché se justifica.
- **`calcular_dz()`** calcula el espaciado entre cortes. Estaba asignado a David; los criterios se acordaron con él y, a su pedido, la implementación final la escribió Claude para no frenar la integración:
  - `dz` es la **mediana** de `np.diff(z)`, porque así un corte faltante no lo altera;
  - la separación cuenta como uniforme si cada diferencia está dentro de `rtol=0.01, atol=1e-3` del dz. Eso tolera el redondeo de los decimales del DICOM, pero no un corte faltante o repetido, que se desvían un 100 %;
  - si los cortes no son uniformes, emite `warnings.warn`, y si `dz == 0` lanza `ValueError`, porque un dz de 0 aplasta el modelo 3D en un plano.

**Verificación**
- Muestra de Slicer: SHA-256 `7bfa1694…eb09968`, igual al que publica Slicer.
- La app Qt abre la muestra en 1 s: 330×360×360 vóxeles de 0.5 mm, con las tres vistas bien orientadas, y en la sagital se ven los brackets.
- Tests que pasan: orden de ejes con un espaciado distinto en cada eje (GIPL, NIfTI, MHA), serie DICOM con los archivos desordenados a propósito, reescalado a densidad (mínimo −896 en `CT_small.dcm`), caché de DICOM, volumen sin caché, carpeta vacía y formato no soportado.
- `calcular_dz`: separación uniforme, uniforme con redondeo (0.3 mm), corte faltante (advierte y devuelve 0.5) y corte repetido (advierte). **Resultado: 13/13 tests en verde.**

**Proceso**
- Crear o fusionar un PR propio sin revisión de otra persona quedó bloqueado por la configuración de permisos. Es coherente con la regla del roadmap de que cada PR lo revise otro integrante. Fusionar el PR #3 también quedó bloqueado, aunque el usuario lo pidió: el PR lo fusiona David desde GitHub.

---

## Próximas entradas
- [x] `calcular_dz` implementado y los 13 tests en verde.
- [ ] PR #3 revisado por Juan y fusionado; PR de `feat/estudio`.
- [ ] Panel 3D real dentro de la app Qt (`Render3D` de Emanuel).
- [ ] Benchmark sobre la muestra real y `reduccion` por defecto.
- [ ] `RANGOS_DENSIDAD` con los umbrales de la muestra de Slicer y de ToothFairy3.
- [ ] Exposición del 26/10.
