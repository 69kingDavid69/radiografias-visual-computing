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

## 2026-10-19 (noche) — PR #3 fusionado y prueba del camino 3D con datos reales

**Estado de GitHub:** el PR #3 (trabajo de Juan) lo fusionó David. El PR #4 (`feat/estudio`) está abierto y espera la revisión de un compañero.

**Medición** con la muestra de Slicer: `cargar_estudio` → `a_pyvista` → `contour`, en el portátil de David.

| `reduccion` | Umbral | Tiempo de `contour` | Triángulos |
|---|---|---|---|
| 1 (completa) | 700 (hueso y dientes) | 0.34 s | 1 404 078 |
| 1 (completa) | 1000 (hueso denso y dientes) | 0.24 s | 423 332 |
| 2 | 700 | 0.04 s | 323 336 |
| 2 | 1000 | 0.03 s | 95 832 |

- La carga del `.gipl.gz` toma 0.22 s.
- **Conclusión:** en este volumen el cuello de botella no es calcular la malla (incluso a resolución completa está por debajo de la meta de 0.5 s), sino **dibujar** 1.4 millones de triángulos al rotar. La `reduccion` por defecto se debe elegir midiendo los FPS al rotar, no el tiempo de `contour`.
- **Detalle para la demo:** la cámara por defecto deja el cráneo de lado. Hay que fijar una vista frontal inicial en `render_3d.py`.

---

## 2026-10-19 (noche) — Presets por banda de densidad: decisión B3

**Problema:** el render dibuja **una** isosuperficie, `contour([umbral])`, que muestra todo lo que supera el umbral. Un preset de "esmalte" no puede excluir el metal de los brackets, que es más denso.

**Opciones probadas** con la muestra de Slicer y el preset de esmalte 1250–2000, con `reduccion=2`. La figura está en [results/comparacion_presets.png](../results/comparacion_presets.png).

| Opción | Técnica | Tiempo | Resultado |
|---|---|---|---|
| A | `contour([1250])` | 0.05 s | Esmalte y metal juntos |
| B1 | `contour([1250, 2000])` | 0.06 s | **Igual que A:** la cáscara de 2000 queda encerrada dentro de la de 1250 |
| B2 | `threshold((1250, 2000))` | 0.57 s | Quita el metal, pero se ve en bloques (vóxeles sin interpolar) y es 10 veces más lento |
| **B3** | máscara 0/1 de la banda + `contour([0.5])` | 0.06 s | **Quita el metal** con una superficie suave; algo de ruido en los bordes |
| C | `add_volume` (render volumétrico) | 0.24 s | Otro paradigma; hay que ajustar a mano la curva de opacidad |

**Decisión: B3.** Es la única opción que *aísla* una banda de densidad, que es lo que plantea la pregunta de investigación, y cuesta lo mismo que lo actual.
- Se implementó como `render_3d.superficie_por_banda(volumen, espaciado, minimo, maximo, reduccion)`.
- Con `maximo` en `None` o `INF` usa el `contour` sobre la densidad real, que da una superficie más suave porque interpola. La máscara se usa solo cuando hay que cortar por arriba.
- El ruido de los bordes de B3 queda para el filtro de volumen (fase 2, `filtros.py`).

**Hallazgo de cámara:** la vista frontal de la muestra es `view_xz()` (sin `negative`). Se identificó renderizando las seis vistas de los ejes.

**Verificación:** `tests/test_render_3d.py` usa un volumen con un "diente" de densidad 1500 y un "bracket" de 3000. La banda 1250–2000 excluye el bracket, sin máximo lo incluye (con `None` y con `INF`), una banda vacía no falla y `reduccion=2` conserva la posición en mm. **18/18 tests en verde.**

---

## 2026-10-19 (noche) — Presets por escala de densidad

**Problema:** las unidades de densidad dependen del equipo. En la muestra de Slicer, 2000 deja **solo metal**; en Hounsfield, 2000 debería dejar el esmalte. Un único juego de presets aislaría la estructura equivocada en uno de los dos datasets.

**Decisión de David:** un diccionario de presets **por escala**, `RANGOS_DENSIDAD = {"slicer": {...}, "hounsfield": {...}}`. La escala se deduce del formato del estudio:

| Formato | Escala | Por qué |
|---|---|---|
| GIPL | `slicer` | En el proyecto, el único GIPL es la muestra de Slicer |
| NII | `hounsfield` | ToothFairy3 está normalizado a HU |
| DICOM | *sin presets* | Según el equipo puede venir en HU o en grises propios: hay que indicarlo con `estudio.metadatos["escala"]` |

- `densidades.escala_de(estudio)` usa primero `metadatos["escala"]` (si se indica a mano) y si no, el formato.
- `densidades.presets_para(estudio)` devuelve `{}` si no se conoce la escala. Así la app muestra solo la barra libre en vez de presets con números de otro equipo.

**Esmalte con y sin metal (corrección).** Claude propuso cerrar el esmalte de `slicer` en `(1250, 2000)` para quitar los brackets. David lo cuestionó y se descartó por cuatro razones:
1. Clínicamente, el metal importa: **si el paciente tiene un implante metálico, la idea es poder verlo en relación con la encía y el hueso** (David).
2. Donde estaba el metal la superficie queda con huecos.
3. Cortar en 2000 quita el metal, pero no sus artefactos (rayas, endurecimiento del haz).
4. 2000 se midió como "por encima solo hay metal", no como frontera validada entre esmalte y metal.

**Resultado:** el preset `"esmalte": (1250, INF)` conserva el valor de Nicolás, y se agrega `"esmalte_sin_metal": (1250, 2000)` como alternativa explícita, para comparar los dos en la demo. Los valores en Hounsfield quedan como los propuso Nicolás, **pendientes de validar** con las etiquetas de ToothFairy3.

**Verificación:** `tests/test_densidades.py` cubre GIPL → slicer, NII → hounsfield, DICOM → sin presets, escala explícita por encima del formato, mínimo < máximo en todos los rangos, que `esmalte` conserva un bracket de 3000 y que `esmalte_sin_metal` lo excluye. Con la muestra real: `GIPL → slicer → [hueso, dientes, esmalte, esmalte_sin_metal, metal]`.

---

## 2026-10-19 (noche) — Flujo de PRs apilados

- **PR #4** (`feat/estudio` → `main`): carga universal, `calcular_dz`, app Qt conectada y bitácora. Revisor: **Juan**, porque cambia su `app_qt.py`.
- **PR #5** (`feat/presets-banda` → `feat/estudio`): B3 y presets por escala. Revisores: **Emanuel** (render) y **Nicolás** (rangos).
- El #5 está **apilado** sobre el #4: su base es `feat/estudio`, así que solo muestra sus propios commits y se revisa por separado. Cuando el #4 entre a `main`, el #5 se cambia a base `main`.
- Regla del equipo: nadie fusiona su propio PR sin la aprobación de otro integrante.

---

## 2026-10-19 (noche) — PRs #4 y #5 fusionados; el #5 cayó en la rama equivocada

- El #4 entró a `main` y el #5 se fusionó **en `feat/estudio`** (su base apilada), porque no se alcanzó a cambiar la base a `main` antes de fusionar.
- **Cómo se detectó:** después de fusionar se verificó `main`. Faltaban `superficie_por_banda`, `tests/test_densidades.py` y `results/comparacion_presets.png`, y corrían 13 tests en lugar de 26.
- **Corrección:** PR #6 `feat/estudio` → `main`, con el mismo contenido ya revisado en el #5 y sin conflictos.
- **Lección para el equipo:** con PRs apilados, se cambia la base del de arriba *antes* de fusionarlo. Otra opción es abrir directamente contra `main` cuando el PR de abajo ya entró.

---

## 2026-10-19 (noche) — Filtro gaussiano antes de marching cubes

**Qué se hizo**
- `src/filtros.py` con `suavizar(volumen, espaciado, sigma_mm)`. Usa `SmoothingRecursiveGaussian` de SimpleITK con el **sigma en milímetros**, y SimpleITK aplica el espaciado de cada eje.
- `superficie_por_banda(..., suavizado_mm=0.0)`: el gaussiano se aplica sobre la densidad si el preset no tiene máximo, y sobre la máscara 0/1 si lo tiene.
- **Primero se reduce y después se suaviza:** con `reduccion=2` es 8 veces menos trabajo, y el gaussiano además funciona como filtro anti-*aliasing*.

**Medición** con la muestra de Slicer, `reduccion=2`. "Pedazos" = regiones conectadas de la superficie. La figura está en [results/suavizado.png](../results/suavizado.png).

| Preset | sigma (mm) | Tiempo | Triángulos | Pedazos |
|---|---|---|---|---|
| hueso | 0 | 0.07 s | 323 336 | 1292 |
| hueso | 0.5 | 0.13 s | 268 196 | 380 |
| hueso | 1.0 | 0.11 s | 191 236 | 86 |
| hueso | 1.5 | 0.11 s | 143 272 | 37 |
| esmalte_sin_metal | 0 | 0.05 s | 26 152 | 308 |
| esmalte_sin_metal | 0.5 | 0.08 s | 25 512 | 228 |
| esmalte_sin_metal | 1.0 | 0.08 s | 1 732 | 28 |
| esmalte_sin_metal | 1.5 | 0.08 s | 292 | 2 |

**Lectura**
- **Hueso:** sigma 0.5 elimina el 70 % de los pedazos sueltos sin perder detalle. Con 1.0 desaparecen además los **anillos** de la frente (artefacto típico del CBCT), pero empieza a abrirse el hueso fino de las órbitas y el tabique. Con 1.5 se pierde el maxilar.
- **Esmalte sin metal:** con 1.0 o más **desaparece**. Suavizar una máscara y cortar en 0.5 equivale a una "votación" en un vecindario del tamaño de sigma: una estructura más delgada que unos 2 sigma pierde la votación y se borra. El esmalte es una capa delgada, de alrededor de 1 vóxel con `reduccion=2`.
- **Conclusión:** el sigma depende del grosor de la estructura. Un valor global no sirve: debe ser **por preset**, y en los presets con máscara tiene que ser menor que el grosor de la estructura.

**Verificación:** `tests/test_filtros.py` cubre:
- sigma 0 no cambia nada;
- la forma y el promedio se conservan y el ruido baja;
- **el sigma se aplica en mm por eje:** con vóxeles de 1 × 0.5 × 0.25 mm, un impulso se ensancha 2 vóxeles en z y 8 en x. Si el espaciado se invirtiera, el test fallaría;
- el filtro reduce los pedazos sueltos de un bloque con ruido.

**30/30 tests en verde.**

---

## 2026-10-19 (noche) — Suavizado de dientes, esmalte y metal; segundo estudio con otra escala

**Medición en el estudio Pre** (`reduccion=2`, vóxel efectivo de 1 mm). Figura en [results/suavizado_dientes.png](../results/suavizado_dientes.png).

| Preset | sigma 0 | 0.25 mm | 0.5 mm | 1.0 mm |
|---|---|---|---|---|
| dientes: triángulos / pedazos | 95 832 / 503 | 96 688 / 516 | 70 432 / **177** | 34 792 / 54 |
| esmalte: triángulos / pedazos | 25 528 / 213 | 25 876 / 219 | 11 260 / 140 | 4 100 / 22 |
| metal: triángulos / pedazos | 2 548 / 44 | 2 560 / 44 | 1 588 / 26 | 124 / 2 |

- **dientes:** con 0.5 mm, los pedazos sueltos bajan a un tercio y **las raíces se conservan**.
- **esmalte:** con 0.5 mm las coronas quedan más limpias, pero la superficie pierde más de la mitad de los triángulos y se adelgaza.
- **metal:** el suavizado **encoge** los brackets, y con 1.0 mm casi desaparecen. Para ver un implante conviene no suavizar.
- **sigma 0.25 mm no hace nada.** Con `reduccion=2` el vóxel efectivo mide 1 mm, y un sigma de un cuarto de vóxel casi no mezcla vecinos. **El sigma útil depende del vóxel efectivo**, no solo del original.

**Segundo estudio: `PostDentalSurgery.gipl.gz`.** Es la muestra oficial de 3D Slicer del mismo paciente después de la cirugía ortognática: 33.8 MB, SHA-256 `4cdc3dc3…7bbd` verificado.
- **Está en otra escala, aunque también es GIPL y viene de la misma fuente.**

  | Estudio | Aire (pico) | Tejido blando (pico) | Rango |
  |---|---|---|---|
  | Pre | 0 | ~410 | 0 a 3 874 |
  | Post | ~−2 206 | ~−4 | −2 254 a 16 889 |

- En ninguno el aire está en −1000, así que ninguno es Hounsfield.
- Con los dos picos se estimó una conversión lineal, `Pre ≈ 0.186 · Post + 411`. Con ella, el umbral de hueso (700 en Pre → 1554 en Post) da un cráneo correcto en Post, y el umbral de metal (2000 → 8543) muestra pequeñas piezas de metal alrededor del maxilar, compatibles con la fijación de la cirugía.
- **Consecuencia:** la regla "formato GIPL → escala `slicer`" (`densidades.ESCALA_POR_FORMATO`) **es incorrecta**. Le aplicaría a Post presets de otra escala, que es justo el error silencioso que se quería evitar. Hay que decidir cómo se asigna la escala a cada estudio (decisión abierta).

**Búsqueda de más datos abiertos (19/10).** No apareció ningún CBCT dental en DICOM, pequeño y sin registro. El candidato más útil es **STS 3D Tooth** (Hugging Face, CC-BY-4.0, 371 volúmenes en NIfTI). Los demás piden cuenta o credenciales (ToothFairy, FDTooth y Multimodal en PhysioNet) o solo traen mallas STL (OpenJaw).

---

## 2026-10-19 (noche) — Escala por estudio (opción 3) y sigma por preset

**Decisiones de David**
1. **Escala de densidad, opción 3:** primero la escala **declarada** en `data/estudios.json` y, si no hay, **normalización automática por picos del histograma**. Reemplaza la regla "formato → escala", que falló con el estudio Post.
2. **Sigma por preset**, con los valores recomendados después de medir: hueso 0.5 mm, dientes 0.5 mm, esmalte 0, esmalte_sin_metal 0 y metal 0.

**Cómo funciona la normalización (`src/escala.py`)**
- En un CBCT de cabeza casi todos los vóxeles son **aire** o **tejido blando**, así que esos dos picos aparecen en cualquier equipo.
- **Aire** = el pico más alto por debajo de la mediana. **Tejido blando** = el pico más alto a más de un cuarto del camino entre el aire y el percentil 99.9. El histograma se calcula sobre 1 de cada 8 vóxeles y se suaviza con una ventana de 5 bins.
- Con los dos puntos se arma una recta que los lleva a la referencia (escala `slicer`: aire 0, blando 410). Es como calibrar un termómetro con dos puntos fijos.
- Si los picos quedan casi pegados (menos del 10 % del rango), no se normaliza: el estudio queda **sin escala**, con una advertencia, y la app muestra solo la barra libre.
- Si la escala está declarada, el volumen **no se toca**. Esa es la vía para los datasets calibrados en Hounsfield, como ToothFairy3: `{"<id>": {"escala": "hounsfield"}}`.
- `cargar_estudio(..., normalizar=True)` aplica todo al final de la carga. Los tests de lectura usan `normalizar=False` para verificar los valores crudos del archivo.

**Verificación con datos reales**

| Estudio | Pico de aire | Pico de blando | a | b | Hueso | Dientes | Metal |
|---|---|---|---|---|---|---|---|
| Pre | 1 | 410 | 1.001 | −1 | 268 500 tri. / 381 ped. | 70 824 / 175 | 2 560 / 44 |
| Post | −2240 | −14 | 0.184 | 413 | 241 054 / 306 | 33 796 / 141 | 1 552 / 49 |

- En el Pre la normalización es casi la identidad (ya estaba en la referencia). En el Post coincide con la conversión estimada a mano (0.186 y 411), pero ahora se calcula sola. Toma unos 0.4 s, carga incluida.
- **Con la misma tabla de presets**, el Post muestra en rojo las **placas y tornillos de fijación** de la cirugía alrededor del maxilar y la mandíbula, y el Pre muestra los brackets. Figura en [results/implante_pre_post.png](../results/implante_pre_post.png): hueso 20 % opaco y metal sin suavizar. Es la vista de implante que propuso David.

**Tests:** `tests/test_escala.py` cubre:
- los picos de un volumen sintético;
- la normalización desde tres escalas: la de referencia, la tipo Post y **Hounsfield**. En Hounsfield, un hueso de 776 HU cae en 700, el umbral de "hueso", lo que sugiere que la escala de la muestra Pre es casi una versión lineal de HU;
- que una escala declarada manda y deja el volumen intacto;
- que un histograma sin forma queda sin escala;
- que `cargar_estudio` normaliza por defecto.

Además, `test_densidades.py` fija los sigmas medidos. **37/37 tests en verde.**

---

## 2026-10-21 — Integración del trabajo de Juan y Emanuel

**Estado al empezar:** el PR #7 se había fusionado el 19/10 sin revisión de Emanuel ni de Nicolás. Cambió la escala de los valores que reciben la app y el render, así que se les avisó.

**Qué se integró** (rama `integra/companeros-21-10`)
- **Nicolás** (`docs/investigacion`): ya estaba en `main` desde el PR #1. La rama aparecía con commits pendientes solo porque se fusionó con *squash*; ningún archivo difiere de `main`.
- **Juan** (`spike/qt`, 20/10): interfaz rediseñada, con sliders tipo píldora, botones de ventana, simetría en la vista dividida e íconos en `assets/`. La fusión entró **sin conflictos** y conservó la carga con `cargar_estudio`.
- **Emanuel** (`feat/optimizar-render`, 19/10): `render_3d.py` refactorizado a la clase **`Render3D`** del contrato (`mostrar`, `set_umbral`, `aplicar_preset` pendiente, `captura`). Hubo **conflicto** con `main`, que había agregado `superficie_por_banda` y el suavizado. Se conservaron las dos cosas: el encabezado, `a_pyvista` y `superficie_por_banda` de `main`, y `Render3D` y `explorar_3d` de Emanuel. En `results/tiempos.csv` se tomó la versión de Emanuel.

**Problema detectado al integrar: ventanas 2D en Hounsfield sobre datos normalizados**
- Los botones de Juan usaban ventanas de radiología en HU: dientes/hueso 1000/3000 y tejido blando 40/400.
- Desde el PR #7 la app recibe la escala normalizada, con el tejido blando en ~410. Con "Tejido Blando" toda la cabeza salía **blanca y saturada**.
- **Solución:** `densidades.VENTANAS_2D` por escala, igual que los presets 3D. En `hounsfield` quedan los valores de Juan; en `slicer` se **calculan** con la recta HU → escala normalizada (aire −1000 HU → 0, tejido blando 40 HU → 410, pendiente 0.394). Resultado: dientes/hueso **788/1183** y tejido blando **410/158**.
- La app guarda la escala del estudio cargado y los botones llaman a `aplicar_preset_por_nombre`. Las etiquetas muestran "HU" o "u. norm." según la escala. Si la escala es desconocida, el botón avisa en lugar de aplicar números equivocados.

**Verificación**
- `Render3D` con el estudio Post: `mostrar` y `set_umbral(700)` funcionan.
- La app abre el Post. El botón "Tejido Blando" muestra contraste en el tejido blando (antes salía saturado) y "Dientes/Hueso" funciona.
- **38/38 tests** (uno nuevo para las ventanas 2D).

**Pendientes para el equipo**
- **Emanuel:** el umbral inicial de `Render3D.mostrar` (60 % del rango) cae en **2113** con el Post normalizado, que ya es zona de metal. Conviene arrancar con el preset `hueso` (700). Falta además `aplicar_preset` con `presets_para` + `superficie_por_banda` + `suavizado_para`, y la cámara `view_xz()`.
- **Juan:** en la captura *offscreen* con tema claro, los nombres de los sliders ("Corte Axial (Z):", "Centro…") se ven casi blancos sobre fondo claro. Hay que revisar el contraste si el sistema no está en modo oscuro.

---

## 2026-10-21 — `Render3D.aplicar_preset` y vista de implante (rama para Emanuel)

**Contexto:** el PR #8 dejó en `main` la clase `Render3D` de Emanuel con `aplicar_preset` vacío. A 5 días de la exposición, David pidió implementarlo en una rama para que Emanuel la revise.

**Qué se hizo** (`feat/render3d-presets`)
- `Render3D.mostrar(estudio)` guarda los presets de la escala del estudio (`presets_para`). **Arranca en el preset `hueso`** y con la cámara **frontal** (`view_xz()`). Si recibe una tupla sin escala, usa el umbral del 60 % de Emanuel.
- `aplicar_preset(nombre)`: usa `superficie_por_banda` con el rango y el sigma de esa estructura (`suavizado_para`). El metal se dibuja en rojo. Si el preset no existe, el error dice cuáles hay.
- `aplicar_capas(capas)`: varios presets a la vez, cada uno con su opacidad. Por defecto es la **vista de implante** de David (hueso al 20 % + metal sólido).
- Los actores llevan nombre y se registran: al cambiar de preset se borra exactamente lo anterior.
- `explorar_3d(..., estudio=)`: teclas **1–5** para los presets, **i** para la vista de implante y la barra libre como antes. `main.py --modo 3d` ya pasa el estudio.
- No se tocó el panel 3D de la app Qt: sigue siendo un *placeholder* (fase 3, Juan + Emanuel). `Render3D` está listo para recibir un `QtInteractor`.

**Verificación**
- 5 tests nuevos con un *plotter* sin ventana:
  - arranca en `hueso` y de frente;
  - `esmalte_sin_metal` excluye el bracket y `metal` deja solo el bracket;
  - las capas tienen su opacidad y desaparecen al volver a un preset;
  - un preset desconocido da un error claro;
  - sin escala se usa la barra libre.
- **43/43 tests.**
- Con el estudio Post ([results/presets_render3d_post.png](../results/presets_render3d_post.png)):

  | Paso | Tiempo |
  |---|---|
  | mostrar | 0.34 s |
  | hueso | 0.27 s |
  | dientes | 0.19 s |
  | esmalte | 0.06 s |
  | esmalte_sin_metal | 0.08 s |
  | metal | 0.06 s |
  | implante | 0.33 s |

**Hallazgo:** en el Post, `esmalte_sin_metal` conserva unas líneas a los lados del maxilar, en la posición de las placas de fijación. Son vóxeles del **borde** del metal que, por **efecto de volumen parcial** (un vóxel que tiene en parte metal y en parte tejido promedia su densidad), quedan entre 1250 y 2000. Confirma con datos la objeción 4 del 19/10: 2000 no es una frontera limpia entre esmalte y metal.

---

## 2026-10-21 — Propuesta de rediseño de la interfaz (fase 3)

**Pedido de David:** una interfaz "más moderna y profesional". Se armó como **diseño** en un lienzo de Claude, sin código: https://claude.ai/artifact/ESXSCmEshA5GDUjZorpGVt. Es **privado** hasta que David lo comparta desde el menú *Share*. Las imágenes son reales: cortes y renders del estudio Post hechos con `Render3D`, solo hueso y metal, sin piel.

**Pantallas**
1. **Vista principal.** Barra superior con el estudio, su forma y vóxel, y el modo (Cortes 2D / Dividida / Modelo 3D). Panel lateral con:
   - la escala detectada (picos, a y b);
   - los presets con rango, sigma y tecla (1–5, I);
   - las ventanas de contraste en "u. norm.".

   Además, tres cortes con líneas guía del color de cada eje, el modelo 3D con leyenda en la vista de implante y una barra de estado con el preset activo.
2. **Abrir estudio.** Zona para arrastrar archivos, estudios recientes con su insignia de escala y **diagnóstico de escala** (histograma con los picos y la conversión). Si un estudio no tiene picos, muestra una advertencia con la opción "Declarar como Hounsfield", que es el flujo de `escala.py` y `data/estudios.json`.

**Decisiones de diseño**
- **Fondo grafito oscuro (#0B0F14):** en imagen médica no deslumbra ni le resta contraste a la imagen. Un solo acento cian para lo interactivo, y coral **solo para el metal**, con el mismo significado que en el render.
- **Inter** para la interfaz y **JetBrains Mono** para los números (umbrales, mm, sigma): se leen como datos y no cambian de ancho cuando varían.
- **La escala del estudio siempre está visible.** Hoy la normalización ocurre sin que el usuario lo sepa.
- Cada preset y cada eje tiene un color fijo, que se repite igual en listas, líneas guía y leyendas.
- Accesibilidad: botones reales con `aria-pressed`, etiquetas en los sliders, foco visible y contraste de texto ≥ 4.5:1. Corrige el bajo contraste de los nombres de los sliders que se vio el 21/10 en tema claro.

**Supuestos de la maqueta:** las imágenes son fijas (los sliders se mueven, pero la imagen no cambia), `[TU ESTUDIO]` es un lugar reservado y el histograma del diálogo es esquemático.

**Decisión:** **no se implementa antes de la exposición del 26/10.** Se presenta como siguiente iteración y queda para la **fase 3**. Para implementarlo:
- Juan lo traduce a PySide6: los colores a una hoja **QSS**, el panel lateral a un `QSplitter` o `QDockWidget`, y el panel 3D a `Render3D` con `pyvistaqt.QtInteractor`.
- Los presets y las ventanas se leen de `densidades.py`, sin repetir valores en la interfaz.

---

## 2026-10-21 — Plan de la exposición actualizado y publicación de la página web con GitHub Actions

**Plan de la exposición:** la línea de David (1:00–1:45) describía el pipeline viejo ("DICOM → reescalado → volumen → 2D y 3D"). Ahora dice archivo → carga → **escala** → `Estudio` → 2D y 3D, y enlaza la diapositiva con su guion de 45 s (https://claude.ai/artifact/NVTS1dRJ2QBUYN95hnP1Kf, privada hasta que se comparta).

**Página web para la exposición** (la quiere hacer un integrante del equipo)
- `.github/workflows/pages.yml` publica **solo la carpeta `web/`** en GitHub Pages: `data/`, `src/` y `results/` nunca salen. Se activa al subir a `main` cambios en `web/` o en el workflow, o a mano desde Actions ("Run workflow").
- Usa las acciones oficiales, en las versiones que indica la documentación de GitHub (21/10): `actions/configure-pages@v5`, `actions/upload-pages-artifact@v4` y `actions/deploy-pages@v4`. Permisos mínimos: `pages: write`, `id-token: write` y `contents: read`. Despliega en el entorno `github-pages`.
- `web/index.html` es un **marcador** ("en construcción") para que el primer despliegue tenga algo que publicar. Lo reemplaza la página del equipo.
- Si la página usa un generador (Vite, Astro, MkDocs…), se agrega su paso de build antes de subir y `path` apunta a la carpeta generada (p. ej. `web/dist`).

**Requisitos que no se pueden hacer desde el código**
1. Settings → Pages → Build and deployment → **Source: GitHub Actions**, una sola vez.
2. Con GitHub Free, Pages solo funciona en **repositorios públicos**. El 21/10 el repositorio aparecía **público**, aunque se creó privado el 28/09. Hay que confirmar que fue a propósito. Lo que sale en `main` (código, documentos, figuras de hueso y metal) no tiene datos de pacientes, porque `data/raw/` nunca se versionó.

**Activación (21/10, PR #10 fusionado)**
- David confirmó que **él hizo público el repositorio, a propósito**.
- Pages se activó con la API de GitHub (`POST /repos/…/pages` con `build_type=workflow`), a pedido de David.
- El primer despliegue, que se disparó al fusionar el PR #10, había **fallado** porque Pages todavía no estaba activo. Se volvió a correr: `build ✓`, `deploy ✓`.
- **Sitio en línea:** https://69kingdavid69.github.io/radiografias-visual-computing/ (HTTP 200, muestra el marcador).
- Advertencias del run, no urgentes: las acciones declaran Node 20 y GitHub las corre con Node 24 (subirlas de versión cuando salgan las nuevas), y `ubuntu-latest` migra a Ubuntu 26, lo que no afecta a un sitio estático.

---

## 2026-10-22 — Página de Nicolás y panel 3D de Emanuel en `main`; prueba en localhost

**Fusionados por David (22/10)**
- **#13, Emanuel:** `Render3D` dentro de la app Qt con `pyvistaqt.QtInteractor`. El panel 3D deja de ser un *placeholder*.
- **#12:** bitácora de la activación de Pages.
- **#11, Nicolás:** página web con cortes reales y modelos 3D interactivos (*three.js* incluido en `web/vendor/`). Los modelos salen de `superficie_por_banda` y de los sigmas de `densidades.py`, sin piel. El despliegue corrió solo al fusionar (`build ✓`, `deploy ✓`).

**Problema encontrado al integrar:** `app_qt.py` importa `pyvistaqt`, pero no estaba en `requirements.txt`. Una instalación nueva fallaba al abrir la app. Se agregó a los requisitos (PR `fix/requisitos-pyvistaqt`).

**Prueba en localhost** (`python -m http.server 8000 --directory web`, como indica `web/README.md`)
- La portada y el laboratorio 3D cargan **sin errores en la consola**.
- Todos los recursos responden 200: *three.js*, `meta.json`, `cortes.png`, `hueso.ply`, `metal.ply` y `dientes.ply`.
- El cráneo de la portada y el preset "Dientes" del laboratorio se dibujan.

**App Qt:** sin ventana arranca, carga el estudio Post y crea el `QtInteractor`. El dibujo 3D necesita OpenGL, así que hay que probarlo con una ventana real.

**Pendiente:** decidir si `web/datos/cortes.png` se guarda con ventana ósea, para que el tejido blando no quede publicado (regla de `datasets.md`).

---

## 2026-10-22 — Colores de los tejidos con referencia (3D Slicer)

**Pedido de David:** que los colores correspondan a los de los tejidos, y usar más referencias.

**Problema:** había tres paletas distintas. La página usaba hueso beige, esmalte celeste y metal rojo; la app, todo marfil y metal rojo. Ninguna tenía fuente.

**Referencia:** la curva de color **"CT-Bone"** de 3D Slicer (`presets.xml` del módulo Volume Rendering), el estándar de la herramienta de la que vienen los datos: rojizo en el tejido blando (−16 HU), amarillo cálido en el hueso (641 HU) y blanco a 3071 HU.

**Método:** cada preset se pasó a su equivalente en HU con la recta de `escala.py` (`HU = (u − 394) / 0,394`) y se **interpoló** en la curva:

| Estructura | HU equivalentes | Color |
|---|---|---|
| tejido blando | ≈ 0 | `#BB454F` |
| hueso (700 u) | ≈ 776 | `#E8D393` |
| dientes (1000 u) | ≈ 1537 | `#F0E1B7` |
| esmalte (1250 u) | ≈ 2171 | `#F6EED5` |
| metal | > 3071 (fuera de la curva) | `#C9D1D9`, plateado del titanio |

**Decisiones**
- Una **sola paleta**, `densidades.COLORES_TEJIDO`, que usan `Render3D` y la página (`lab3d.js`, `estilos.css`). Un test compara los valores de Python, JavaScript y CSS.
- El metal se dibuja con **brillo especular alto** (app: `specular` 1.0 y potencia 60; página: `shininess` 90).
- **Costo:** en la vista de implante el titanio plateado contrasta menos que el rojo anterior. Se ve, pero es más tenue. Se eligió el color real; si en la demo hace falta más contraste, se puede bajar la opacidad del hueso.
- El interior rojo de los dientes en el plano de corte de la página es la **pulpa**: conserva el rojo con su propia variable `--pulpa`.

**Verificación:** 45/45 tests y renders de la app con el estudio Post en [results/colores_tejidos_app.png](../results/colores_tejidos_app.png).

---

## 2026-10-22 — Segundo equipo: STS-3D-Tooth y los límites de la normalización

**Pedido de David:** más radiografías. Se descargó **un** estudio etiquetado de **STS-3D-Tooth** (Hugging Face `MedOtter/STS-3D-Tooth`, CC-BY-4.0; Wang et al., *Scientific Data* 12, 117 (2025), doi:10.1038/s41597-024-04306-9): `ROI_L_001.nii.gz` (40,6 MB) y su máscara de dientes (0,5 MB), en `data/raw/sts3d/`, fuera de git. Existe además un subconjunto de **radiografías panorámicas 2D** (`Angelou0516/STS-2D-Tooth`), pero su API no respondió el 22/10.

**El estudio:** 400 × 512 × 512 vóxeles de **0,15 mm**, más de 3 veces más fino que la muestra de Slicer. Viene en **Hounsfield** (aire en −1000).

**Lo que funcionó:** `cargar_estudio` lo leyó sin cambios y la normalización encontró sola los picos: aire −993 y tejido blando −56 (a = 0,438, b = 435), sin avisos.

**Máscara:** la etiqueta 1 son los dientes. La etiqueta 4 es un artefacto: una capa de exactamente 512 × 512 vóxeles con valor 2. La alineación es correcta (voltearla en cualquier eje empeora el resultado). El 7 % de la etiqueta 1 cae en aire, por el borde de la anotación; para medir se descartaron esos vóxeles.

**Hallazgo: cuánto de los dientes etiquetados captura cada preset ya normalizado**

| Preset | Dientes | Resto denso (sobre todo hueso) |
|---|---|---|
| hueso ≥ 700 | 77 % | 6 % |
| dientes ≥ 1000 | **29 %** | 1 % |
| esmalte ≥ 1250 | **4 %** | 0 % |

Render en [results/sts_presets.png](../results/sts_presets.png).

**Lectura**
- La normalización corrige bien los **dos puntos que usa** (aire y tejido blando), pero una recta fijada con dos densidades bajas no reproduce las **densidades altas** de otro equipo. Los dientes de STS quedan en una mediana de 925 (normalizado): bajo el umbral de "dientes", que se midió en la muestra de Slicer.
- Los presets de dientes y esmalte **no se transfieren** entre equipos con esta normalización. Es una limitación para el informe y responde a la pregunta de investigación: aislar estructuras por densidad funciona dentro de un equipo, pero entre equipos hace falta más calibración.
- La vista frontal (`view_xz`) depende de la orientación de la muestra de Slicer: en STS la cara no queda de frente.

**Opciones (por decidir con el equipo; no antes del 26/10)**
1. Un **tercer punto de anclaje** en las densidades altas, por ejemplo el pico del esmalte o un percentil alto.
2. Presets en **percentiles** de cada estudio en lugar de valores fijos.
3. **Calibrar con las etiquetas:** STS (32 estudios etiquetados) y ToothFairy3 traen máscaras. Con varios estudios se puede medir el rango real de los dientes, que era el plan de Nicolás para ToothFairy3.

---

## 2026-10-22 — PR #15 bloqueado y despliegue manual de la página

**PR #15 que no se dejaba fusionar**
- **Síntoma:** GitHub mostraba `mergeable: unknown` y no habilitaba el botón de fusionar. No había protección de rama ni conflictos: en local, la fusión con `main` entraba limpia.
- **Causa:** la rama `feat/colores-tejidos` en GitHub tenía 2 commits (`e6a4743` y `0610845`), pero el PR seguía apuntando al primero. El segundo envío llegó mientras la red estaba inestable y GitHub no actualizó el PR, así que no podía calcular si era fusionable.
- **Solución:** cerrar y reabrir el PR, que obliga a GitHub a releer la rama. Quedó con 2 commits y `mergeable=true` (`clean`), sin perder revisores ni descripción.

**Despliegue de la página que no arrancó solo**
- **Síntoma:** la fusión del #15 (`062998e`) cambió archivos de `web/` (`estilos.css`, `index.html`, `cortes.js`, `lab3d.js`), pero el workflow "Publicar página web" no corrió. El sitio seguía con los colores viejos (metal `#ff6347`).
- **Causa probable:** otro evento perdido de GitHub, igual que el del PR. El último despliegue automático era el de la fusión del #11 (`7372009`).
- **Solución:** se lanzó el workflow **a mano** (`workflow_dispatch`, "Run workflow" sobre `main`): run `39828193981`, `success`, sobre `062998e`.
- **Verificación en el sitio publicado:**
  - `lab3d.js` y `estilos.css` sirven la paleta nueva (metal `#c9d1d9`, hueso `#e8d393`, dientes `#f0e1b7`, esmalte `#f6eed5`, pulpa `#d94a3d`);
  - en el navegador, la vista "Hueso + metal" muestra los brackets en plateado dentro del hueso semitransparente, a 60 FPS y sin errores en la consola.

**Procedimiento para el equipo:** si se fusiona algo de `web/` y el sitio no cambia en unos minutos, revisar en **Actions** si corrió "Publicar página web". Si no corrió, abrir el workflow y usar **Run workflow** sobre `main`. Si un PR se queda en "unknown", cerrarlo y reabrirlo.

---

## 2026-10-22 — Panel 3D de la app: arreglos de integración

**Reporte de David:** con la app abierta, el panel 3D mostraba solo pedacitos sueltos sobre fondo blanco.

**Causas** (en la integración del PR #13)
1. `app_qt.py` llamaba `render3d.mostrar((volumen, espaciado))` con una **tupla** y no con el `Estudio`. `Render3D` no conocía la escala, no tenía presets y usaba el umbral de respaldo (60 % del rango ≈ 2100), que con datos normalizados es **metal**: se veían solo las placas y tornillos del estudio Post.
2. El `QtInteractor` usaba el **fondo blanco** de VTK.
3. Al abrir otro estudio con el botón, **el 3D no se actualizaba**: solo se dibujaba el estudio con el que arrancaba la app.
4. La app no tenía forma de cambiar de estructura; los presets solo existían como teclas en `--modo 3d`.

**Arreglos** (rama `fix/vista-3d-app`)
- `_mostrar_en_3d(estudio)` le pasa el `Estudio` completo. Con el volumen sintético de respaldo se mantiene la tupla, y entonces hay solo umbral libre.
- Fondo `#181818`, el del tema oscuro de la app.
- **Barra "Estructura 3D"** sobre el panel: un botón por preset del estudio más "Implante" si hay hueso y metal. Se arma según la escala de cada estudio, y si la escala es desconocida lo avisa. Se agregó el estilo `:checked` a `btn-preset` para ver cuál está activo.
- `cargar_nuevo_estudio` también actualiza el 3D.
- La visibilidad de los modos 2D, 3D y dividido se aplica al contenedor (barra + render).

**Verificación sin ventana:** arranca en "Hueso" (umbral 700) con 6 botones; "Implante" dibuja dos capas; al abrir Pre y STS el 3D cambia. 45/45 tests. El dibujo con OpenGL se revisa con la app abierta.

---

## 2026-10-22 — Dientes limitados a la arcada, error de normalización y tejidos blandos (experimental)

**Reporte de David:** en la app, el preset "Dientes" marcaba parte del cráneo. También preguntó si se pueden mostrar músculos y tejido blando.

### 1. Error en la normalización: capas de relleno
- Las primeras y últimas capas del estudio Post (**14** en total) y del Pre (**16**) son **relleno constante**: el tomógrafo no midió ahí y todos sus vóxeles valen 0 en crudo.
- En el Post ese 0 cae cerca del tejido blando, así que la normalización tomó el **relleno** como "pico de tejido blando" (−14). Por eso esas capas quedaban en ~413 y aparecían en 3D como **planos** arriba y abajo.
- **Arreglo:** `escala.capas_de_relleno()` detecta las capas constantes; la normalización las **excluye del histograma** y, ya normalizado el volumen, las marca como aire.

  | Estudio | Antes | Después |
  |---|---|---|
  | Post | blando −14 → a = 0,184 | blando **−153** → a = **0,197** (7 % de diferencia) |
  | Pre | a = 1,001 | a = 1,029 |
  | STS | a = 0,438 | a = 0,438 (1 capa de relleno) |

### 2. Dientes limitados a la arcada dental
- **Causa:** el hueso cortical denso del cráneo tiene la densidad de la dentina. En el Post, solo el **34 %** de lo que supera el umbral de "dientes" está en la boca (Pre: 29 %; STS, que ya es un recorte dental: 90 %).
- **Arreglo:** `region.arcada_dental()` busca la altura (z) con más esmalte (perfil suavizado de ~5 mm) y toma **±25 mm** a su alrededor. `superficie_por_banda(..., rango_z=)` limita la superficie a esa franja y mantiene su posición en mm. Se aplica a `dientes`, `esmalte` y `esmalte_sin_metal` (`densidades.EN_ARCADA`).
- **Resultado (Post):** arcada en z 65–166. "Dientes" muestra las dos arcadas con raíces y sin el cráneo, aunque todavía entran las placas y algo de hueso maxilar pegado a las coronas.
- **Supuesto:** el eje z del volumen es el vertical del paciente.

### 3. Tejido blando: "denso / graso" (experimental)
- **Medición:** el ruido del tejido blando, medido en bloques de 6³ vóxeles, es de ~18 u (Post y STS); la diferencia esperada entre grasa y músculo es de ~55 u. Pero el histograma de los bloques tiene **un solo pico** (~405–415): la grasa no forma una población propia, sino un "hombro" entre ~260 y ~380.
- **Presets experimentales** (escala `slicer`): `grasa` 280–375 y `musculo` 375–600. El corte en 375 queda ~1,5 veces el ruido por debajo del pico.
- **Se muestran solo en una vista combinada con corte sagital** (`CAPAS_BLANDAS`: grasa 35 % + músculo + hueso), mirando **desde el lado del corte**, hacia el interior: nunca la cara de frente ni de perfil. No hay botones sueltos (`densidades.EXPERIMENTALES`).
- **Limitación:** "músculo" también incluye el **cerebro y la lengua**, por su densidad parecida. Por eso en la app se llama "Blandos: denso / graso (exp.)". Separar músculos individuales necesitaría segmentación, no umbrales. Además, el CBCT tiene variaciones de brillo según la zona (*cupping*, radiación dispersa) del mismo orden que la diferencia grasa–músculo.

**Verificación:** 50/50 tests. Hay tests nuevos de: capas de relleno, arcada (cubre los dientes y deja fuera el "cráneo"), `rango_z` que conserva la posición, "dientes" sin cráneo en `Render3D`, y la vista de blandos con la cámara del lado del corte. Con el Post real: "dientes" 0,04 s, "esmalte" 0,02 s y blandos 1,7 s. En la app, la barra muestra 7 botones, incluido "Blandos: denso / graso (exp.)".

---

## 2026-10-22 — Calibración del preset "dientes" con 11 pacientes etiquetados (STS)

**Pedido de David:** más radiografías "para entrenar la aplicación". La app usa umbrales, no una red neuronal: el equivalente a entrenarla es **calibrar** los umbrales con estudios etiquetados.

**Datos:** 10 estudios más de STS-3D-Tooth (`ROI_L_002` a `ROI_L_011`, con máscara; ~560 MB, CC-BY-4.0). Con el `ROI_L_001` suman **11 pacientes**, en `data/raw/sts3d/`, fuera de git. Se descargó con reintentos y sin errores.

**Método** (`scripts/calibrar_presets.py`):
- cada estudio se carga y se normaliza como en la app;
- se toma la zona dental (las capas con diente según la máscara, ±10 mm);
- para cada umbral se mide el **Dice** entre "densidad ≥ umbral" y la máscara de dientes. Todos los umbrales se evalúan con histogramas acumulados, en una sola pasada.

Resultados en [results/calibracion_sts.csv](../results/calibracion_sts.csv).

**Resultados**

| | Valor |
|---|---|
| Umbral óptimo (escala normalizada) | mediana **750**, rango 640–865 |
| Umbral óptimo en Hounsfield | mediana **~816 HU**, rango 609–1084 |
| Dice con el umbral óptimo | mediana **0,58** (0,45–0,78) |
| Dice con el preset actual (1000) | 0,22–0,47 |
| Densidad de los dientes | mediana ~1220 HU; el 10 % más denso empieza en ~2010 HU |
| Normalización de STS | a = 0,40–0,44 en los 11: muy estable dentro de un mismo equipo |

**Lectura**
- La propuesta de la literatura para Hounsfield (`dientes` 1300 HU) es **demasiado alta** para este CBCT: el óptimo medido es ~820 HU. El **esmalte en 2000 HU sí se confirma**: coincide con el 10 % más denso del diente.
- El techo de Dice (~0,58) no viene de un mal umbral: dentro de la zona dental, el **hueso alveolar** que rodea las raíces también supera el umbral. Es la misma limitación de fondo: la densidad sola no separa diente de hueso.
- El umbral `dientes` = 1000 de la escala `slicer` se fijó a ojo en la muestra Pre (otro equipo). Para STS el óptimo es ~750. Cada equipo necesita su propia calibración: confirma el hallazgo del 22/10 con 11 pacientes en vez de 1.

---

## Próximas entradas
- [x] `calcular_dz` implementado y los 13 tests en verde.
- [x] PR #3 fusionado.
- [x] PR #4 fusionado en `main`.
- [x] PR #6 (contenido del #5) fusionado en `main`; verificado: 26 tests, app y 5 presets con la muestra real.
- [x] Sigma de suavizado por preset.
- [x] Escala por estudio: declarada en `data/estudios.json` o normalizada por picos del histograma.
- [ ] Probar la normalización con las radiografías que suba David y con un volumen de STS 3D Tooth.
- [ ] Panel 3D real dentro de la app Qt (`Render3D` de Emanuel).
- [ ] FPS al rotar con la muestra real y `reduccion` por defecto (el tiempo de `contour` ya se midió).
- [x] Técnica de presets decidida (B3) e implementada.
- [x] `RANGOS_DENSIDAD` por escala (slicer y hounsfield) y `presets_para(estudio)`.
- [ ] Validar los presets en Hounsfield con las etiquetas de ToothFairy3 (Nicolás + Emanuel).
- [ ] Vista de implante: `metal` opaco + `hueso` o tejido blando semitransparente, para ver el metal en relación con la encía (idea de David; usa la opacidad por estructura de la fase 2, Emanuel).
- [x] Presets en la vista 3D (teclas 1–5 e `i`) y vista frontal: `Render3D.aplicar_preset` / `aplicar_capas` (rama para Emanuel).
- [ ] Panel 3D dentro de la app Qt con `QtInteractor` (Juan + Emanuel).
- [ ] Implementar el rediseño de la interfaz (propuesta del 21/10) después de la exposición (Juan).
- [x] Página web publicada con GitHub Pages; el contenido de `web/` lo hace un compañero.
- [ ] Exposición del 26/10.
