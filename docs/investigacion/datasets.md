# Datos del proyecto: qué tomografías usa el programa

Responsable: Nicolás (investigación y datos). Revisado el 15/10/2026. Cierra la
**decisión abierta #2** de [ARCHITECTURE.md](../ARCHITECTURE.md) y la Fase 0 de
[planes/investigacion-nicolas.md](../planes/investigacion-nicolas.md).

## 1. Decisión: los datasets que se usan

| # | Dataset | Para qué lo usa el proyecto | Formato | Unidades | Acceso | Estado |
|---|---|---|---|---|---|---|
| **1** | **Muestra CBCT dental de 3D Slicer** (`PreDentalSurgery`) | **Desarrollo y demo de la exposición del 26/10.** Es pequeño (24 MB) y se baja en segundos | GIPL (`.gipl.gz`), 1 volumen de 360×360×330 vóxeles de 0.5 mm | Grises del equipo, **no** Hounsfield (0 a 3874) | Enlace directo, sin registro | ✅ Descargado y probado con nuestro código el 15/10 |
| **2** | **ToothFairy3** (Universidad de Módena) | **Dataset principal del informe:** rangos de densidad en Hounsfield, validados con las etiquetas de cada estructura | NIfTI (`.nii.gz`), 532 volúmenes de 0.3 mm, con 77 etiquetas | **Hounsfield** | Gratis, **requiere crear cuenta** | ⏳ Falta crear la cuenta y descargar |
| 3 | **Missing teeth CBCT** (ScienceDB) | **Opcional:** comparar tres equipos CBCT distintos y probar el camino DICOM de `carga.py` | DICOM (`.dcm`), 158 pacientes | Grises de cada equipo | Público (CC BY 4.0) | Opcional; 22 GB en un solo ZIP |

**En una frase:** se desarrolla y se hace la demo con la muestra de Slicer; los
resultados y los rangos de densidad del informe salen de ToothFairy3; ScienceDB
solo se usa si sobra tiempo.

**Plan B** si nadie puede crear la cuenta de ToothFairy3 a tiempo: la propia
muestra de Slicer alcanza para la demo y para mostrar la limitación principal (el
CBCT no está en Hounsfield). En el informe se reporta así.

## 2. Por qué estos y no otros (explicado simple)

Una **tomografía CBCT dental** es un "cubo" 3D de densidades de la cabeza del
paciente (ver [marco-teorico.md](marco-teorico.md)). Para el programa necesitamos
tomografías que cumplan cinco condiciones:

1. Ser **dentales**: de un CBCT de maxilares, no de un CT genérico de cráneo.
2. Ser **públicas** y con licencia que permita uso académico.
3. Estar **anonimizadas**: sin nombre ni documento del paciente.
4. Traer el **tamaño del vóxel** en mm; sin él, el modelo 3D sale deformado.
5. Estar en un formato que el programa pueda leer.

| Dataset | Por qué lo elegimos |
|---|---|
| Muestra de Slicer | Es la forma más rápida de tener un CBCT dental real funcionando. Ya comprobamos que se ven el cráneo, los maxilares, los dientes con sus raíces y unos brackets de ortodoncia. Además, sus grises **no** están en Hounsfield, y eso nos sirve para mostrar en vivo el problema principal del CBCT. |
| ToothFairy3 | Sus valores están **en Hounsfield** y todos los volúmenes tienen el mismo vóxel, así que un rango como "esmalte ≥ 2000 HU" significa lo mismo en todos. Trae **etiquetas**: para cada vóxel dice si es maxilar, cuál diente o pulpa. Con eso podemos **medir** la densidad real de cada estructura y justificar los rangos con datos, no solo con la literatura. |
| ScienceDB | Es DICOM, el formato que ya lee `carga.py`, y viene de **tres equipos distintos**. Sirve para mostrar que cada equipo da números distintos para la misma anatomía. |

## 3. Ficha de cada dataset

### 3.1 Muestra CBCT dental de 3D Slicer

| Campo | Valor |
|---|---|
| Origen | Datos de muestra del proyecto 3D Slicer (módulo *Sample Data → CBCTDentalSurgery*). Según un hilo de 2012 de la comunidad de Slicer, es el CBCT de un adulto antes y después de una cirugía ortognática |
| Archivos | `PreDentalSurgery.gipl.gz` — [descargar](https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/7bfa16945629c319a439f414cfb7edddd2a97ba97753e12eede3b56a0eb09968) (23.6 MB) · `PostDentalSurgery.gipl.gz` — [descargar](https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/4cdc3dc35519bb57daeef4e5df89c00849750e778809e94971d3876f95cc7bbd) (33.8 MB, después de la cirugía) |
| Contenido | 330 cortes de 360×360 píxeles; vóxel de **0.5 mm** en los tres ejes; enteros de 16 bits |
| Valores | De 0 a 3874. Aire = 0. **No es Hounsfield** |
| Licencia | No está escrita junto al archivo. **Usarlo solo para desarrollo y la demo de clase**; los resultados del informe salen de ToothFairy3 |
| Anonimización | No trae datos del paciente (el formato GIPL no tiene campos para eso). **No publicar** la reconstrucción de la piel, porque muestra la cara |
| Verificación (15/10) | El SHA-256 coincide con el publicado por Slicer. Se leyó con SimpleITK y se renderizó con `src/render_3d.a_pyvista`. Resultados en [densidades.md §4](densidades.md#4-rangos-medidos-en-la-muestra-de-3d-slicer) |

### 3.2 ToothFairy3 (dataset principal)

| Campo | Valor |
|---|---|
| Origen | Universidad de Módena y Reggio Emilia (Italia) con Radboud University. Reto ToothFairy3 de MICCAI 2025 — [página del dataset](https://ditto.ing.unimore.it/toothfairy3) · [reto](https://toothfairy3.grand-challenge.org/dataset/) |
| Volúmenes | 532: set A (417, prefijo `P`) y set B (63, prefijo `F`, campo de visión amplio), ambos del mismo equipo; set C (52, prefijo `S`) de otro equipo |
| Formato | NIfTI (`.nii.gz`), organizado como nnU-Net: carpeta de imágenes, carpeta de etiquetas y `dataset.json` con los nombres de las etiquetas |
| Vóxel | 0.3 mm en los tres ejes |
| Valores | **Unidades Hounsfield** |
| Etiquetas | 77 clases (notación FDI): maxilares, cada diente, **la pulpa de los 32 dientes**, conducto alveolar inferior, conductos incisivos y lingual, seno maxilar, faringe, coronas, puentes e implantes |
| Orientación | RPI (no estándar); la página ofrece un script para pasar a LPS |
| Licencia | CC BY-NC-SA 4.0: uso académico sí, no comercial, compartir igual y **citar 3 artículos** (§6) |
| Descarga | Un solo `ToothFairy3.zip` (versión del 30/06/2025). Hay que **crear una cuenta** en el sitio; el tamaño solo se ve con la sesión iniciada |
| Anonimización | La página no lo declara; el formato NIfTI no lleva nombre ni documento del paciente |

### 3.3 Missing teeth CBCT — ScienceDB (opcional)

| Campo | Valor |
|---|---|
| Origen | Hospital Sir Run Run Shaw (Universidad de Zhejiang, China) y otros. Artículo: *Scientific Data* 13:828 (2026) — [artículo](https://doi.org/10.1038/s41597-026-07156-9) · [datos](https://doi.org/10.57760/sciencedb.26465) |
| Volúmenes | 158 pacientes adultos con dientes ausentes (85 con anotación 3D) |
| Equipos | Meyer SS-X9010DPro, Newtom VGi y KaVo OP 3D Vision V17 |
| Formato | DICOM (`.dcm`), anotaciones JSON de 3D Slicer |
| Licencia | CC BY 4.0 |
| Descarga | Pública, sin solicitud de acceso. `Dataset_repaired.zip` de **21.98 GB** (versión 2, 06/08/2026), `Code.zip` y `Visualization cases.zip`. No se probó si el botón pide iniciar sesión |
| Anonimización | Sí: según el artículo, solo quedan sexo y edad |

## 4. Otros datasets revisados y por qué no se usan

| Dataset | Por qué no |
|---|---|
| ToothFairy2 ([página](https://ditto.ing.unimore.it/toothfairy2)) | Son los mismos volúmenes que los sets A y B de ToothFairy3, pero en MHA y con menos etiquetas (42, sin pulpa). ToothFairy3 lo reemplaza |
| ToothFairy v1 ([página](https://ditto.ing.unimore.it/toothfairy/)) | Solo etiqueta el conducto alveolar. Sirve como **plan B en DICOM** (botón "Download Raw Dataset", también pide cuenta) |
| ToothFairy4 | Mismo origen, más reportes clínicos; no aporta nada para este proyecto y es más grande |
| STS-Tooth 3D ([Zenodo](https://zenodo.org/records/10597292)) | Libre (CC BY 4.0), pero parte de sus volúmenes **perdió el tamaño real del vóxel** (todo queda en 1×1×1 mm) y el modelo 3D saldría deformado. Pesa ~31 GB |
| Multimodal dental dataset ([PhysioNet](https://doi.org/10.13026/h1tt-fc69)) | DICOM de buena calidad, pero con **acceso restringido**: pide cuenta acreditada, el curso CITI, un acuerdo de uso y aprobación de los autores |
| CTooth / CTooth+ | No se encontró un enlace de descarga verificable ni una licencia |

## 5. Cómo se leen en el programa

`src/carga.py` hoy solo lee carpetas DICOM. Para la muestra de Slicer y para
ToothFairy3, lo más simple es un lector con **SimpleITK**, que abre GIPL, NIfTI, MHA
y también carpetas DICOM. Código probado con la muestra:

```python
import SimpleITK as sitk

img = sitk.ReadImage("data/raw/PreDentalSurgery.gipl.gz")      # también .nii.gz o .mha
volumen = sitk.GetArrayFromImage(img).astype("float32")           # forma (z, y, x) = (330, 360, 360)
espaciado = tuple(reversed(img.GetSpacing()))                     # (dz, dy, dx) = (0.5, 0.5, 0.5) mm
```

`GetArrayFromImage` ya devuelve el orden `(z, y, x)` que usa el proyecto, y
`GetSpacing()` da el vóxel en orden `(x, y, z)`; por eso se invierte. Hay que agregar
`SimpleITK` a `requirements.txt`. El código de `carga.py` es de David; esto es la
recomendación de investigación.

Para revisar los datos antes de usarlos están los scripts:

```bash
python scripts/verificar_anonimizacion.py data/raw --csv results/estudios.csv
python scripts/histograma_densidades.py data/raw/PreDentalSurgery.gipl.gz
```

## 6. Pasos pendientes

- [x] Revisar datasets y elegir (este documento) — Nicolás.
- [x] Probar la muestra de Slicer con el código del proyecto — Nicolás.
- [ ] Crear la cuenta en [ditto.ing.unimore.it](https://ditto.ing.unimore.it/) y descargar ToothFairy3 — Nicolás.
- [ ] Elegir 3–5 estudios de ToothFairy3 y compartirlos por Drive **solo con el
      equipo**, nunca por GitHub (`data/raw` está en `.gitignore`).
- [ ] Correr `histograma_densidades.py` con `--etiquetas` sobre esos estudios y
      completar [densidades.md](densidades.md) — Nicolás + Emanuel.

## 7. Cómo citar (obligatorio en el informe)

**ToothFairy3** exige citar estos tres (lista de su página, 15/10/2026):

1. Lumetti L., Tan Z.Q., Borghi L., Addison O., Li Y., Rosati G., van Nistelrooij N.,
   Vinayahalingam S., Grana C., Bolelli F. (2026). *ToothFairy3: Scaling CBCT
   Maxillofacial Segmentation to 77 Classes with U-Mamba2.* MICCAI 2026.
2. Bolelli F., Marchesini K., van Nistelrooij N., Lumetti L., Pipoli V., Ficarra E.,
   Vinayahalingam S., Grana C. (2025). *Segmenting Maxillofacial Structures in CBCT
   Volumes.* CVPR 2025. https://doi.org/10.1109/CVPR52734.2025.00494
3. Lumetti L., Pipoli V., Bolelli F., Ficarra E., Grana C. (2024). *Enhancing
   Patch-Based Learning for the Segmentation of the Mandibular Canal.* IEEE Access.
   https://doi.org/10.1109/ACCESS.2024.3408629

**Muestra de 3D Slicer:** citar 3D Slicer — Fedorov A. et al. (2012). 3D Slicer as an
image computing platform for the Quantitative Imaging Network. *Magnetic Resonance
Imaging* 30(9):1323–1341. https://doi.org/10.1016/j.mri.2012.05.001 — e indicar "datos de muestra CBCTDentalSurgery".

**ScienceDB** (si se usa): Feng L., Li Z., Gu Q., Wang Y., Yu X. (2026). *Adults'
dental cone beam computed tomography images dataset for detecting and classifying
missing teeth.* Scientific Data 13:828. https://doi.org/10.1038/s41597-026-07156-9
