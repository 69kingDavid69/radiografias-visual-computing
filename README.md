# Explorador CBCT — de la tomografía dental al modelo 3D

Proyecto de Visual Computing · Universidad Nacional de Colombia, Sede Medellín · 2026-2
Equipo: David (datos y pipeline) · Juan Gómez (visor 2D e interfaz) · Emanuel Aristizábal
(render 3D) · Nicolás Quintana (investigación y datos) · Profesor: Marco Paluszny

> **Pregunta de investigación.** ¿De qué manera podemos desarrollar una interfaz gráfica
> que transforme los datos volumétricos de una tomografía dental (CBCT) en un modelo 3D
> interactivo, aislando estructuras específicas según su densidad?

Una radiografía es plana. Un CBCT es un **cubo de densidades** hecho de cientos de cortes.
Este programa lo abre y ofrece dos herramientas:

1. **Navegación multicorte (2D):** vistas axial, coronal y sagital con líneas guía,
   control de contraste (ventana/nivel) y posición en milímetros.
2. **Reconstrucción 3D por densidad:** elige una estructura (hueso, dientes, esmalte,
   metal…) y el programa dibuja solo esa superficie, con colores de tejido, para rotarla,
   acercarla y compararla. Incluye una vista de implante (hueso transparente + metal).

**Página del proyecto:** https://69kingdavid69.github.io/radiografias-visual-computing/ ·
[Arquitectura](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md) ·
[Bitácora de desarrollo](docs/bitacora-desarrollo.md) · [Investigación](docs/investigacion/README.md)

---

## Instalación

Requiere **Python 3.11 o más nuevo** (probado con 3.13 en macOS) y una tarjeta gráfica con
OpenGL para la vista 3D.

```bash
git clone https://github.com/69kingDavid69/radiografias-visual-computing.git
cd radiografias-visual-computing
python3 -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Datos

Los estudios médicos **no se suben al repositorio** (`data/raw/` está en `.gitignore`).
Cada integrante los descarga en `data/raw/`. Usamos solo datos públicos y anonimizados.

**Muestras de 3D Slicer** (CBCT dental de un mismo paciente antes y después de una cirugía;
las usa la demo):

```bash
mkdir -p data/raw
curl -L -o data/raw/PreDentalSurgery.gipl.gz  https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/7bfa16945629c319a439f414cfb7edddd2a97ba97753e12eede3b56a0eb09968
curl -L -o data/raw/PostDentalSurgery.gipl.gz https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/4cdc3dc35519bb57daeef4e5df89c00849750e778809e94971d3876f95cc7bbd
```

El nombre del enlace es el SHA-256 del archivo: se puede verificar con `shasum -a 256`.

**STS-3D-Tooth** (CBCT con dientes etiquetados, CC-BY-4.0): recortes `ROI_L_*.nii.gz` y sus
máscaras desde [Hugging Face](https://huggingface.co/datasets/MedOtter/STS-3D-Tooth) en
`data/raw/sts3d/` (la máscara con el sufijo `_mascara.nii.gz`). Los usamos para calibrar los
umbrales (ver Scripts).

Formatos que se abren: carpeta DICOM, `.gipl.gz`, `.nii.gz`, `.mha`, `.mhd` y `.nrrd`.

## Uso

### La aplicación

```bash
python -m src.app_qt data/raw/PostDentalSurgery.gipl.gz
```

Sin argumento abre `data/raw/PreDentalSurgery.gipl.gz`. Con **Cargar estudio** se abre otro
archivo, o un `.dcm` para cargar toda su carpeta. Arriba se elige la vista **2D**, **3D** o
**Dividida**:

- **2D:** sliders de corte y de contraste; botones *Dientes / Hueso* y *Tejido blando*. En el
  borde de cada corte van las letras de orientación del paciente (*D*, *Iz*, *Ant*, *Post*,
  *Sup*, *Inf*), leídas del encabezado del archivo; en 3D, un cubo en la esquina hace lo mismo.
- **2D:** debajo de los cortes, un **histograma de densidades** con la ventana de contraste
  y el inicio de cada estructura marcados; un clic en él centra el contraste en esa densidad.
- **3D:** barra *Estructura 3D* con *Hueso, Dientes, Esmalte, Sin metal, Metal, Implante*,
  *Blandos (exp.)* (este último con corte sagital, para no mostrar la cara) y *Fractura*
  (hueso a resolución completa, sin suavizar y sin la camilla; tarda unos segundos). Se rota con el
  mouse y se acerca con la rueda. Debajo, un control por cada pregunta de la propuesta:

  | Control | Qué hace | Pregunta |
  |---|---|---|
  | Umbral | Densidad libre; la malla se recalcula al soltar la barra | 1. Densidad → malla |
  | Phong | Sombreado suave o plano (se ven los triángulos) | 2. Iluminación |
  | N triáng. · ms | Tamaño de la malla y tiempo del cálculo | 3. Rendimiento |
  | Taubin | Suaviza el escalonado sin encoger la malla | 4. Suavizado |
  | Corte | Plano de corte que se arrastra; el interior se ve en rojo | 5. Clipping plane |
  | Relieve | Oclusión ambiental (SSAO): oscurece grietas y huecos; la vista *Fractura* lo enciende | — |

  Con estudios grandes el 3D baja la resolución solo (nivel de detalle automático).

### Línea de comandos (sin interfaz)

```bash
python -m src.main data/raw/PostDentalSurgery.gipl.gz --modo cortes       # visor 2D
python -m src.main data/raw/PostDentalSurgery.gipl.gz --modo 3d           # visor 3D
python -m src.main data/raw/PostDentalSurgery.gipl.gz --modo 3d --reduccion 1   # resolución completa
```

En `--modo 3d`: teclas **1–5** para las estructuras, **i** para la vista de implante, **m**
para tejidos blandos (experimental) y la barra para un umbral libre.

### La página web en local

Los módulos de JavaScript no funcionan abriendo el archivo con doble clic: hay que servir
la carpeta.

```bash
python3 -m http.server 8000 --directory web
```

y abrir http://localhost:8000 (funciona sin internet; *three.js* va incluido). La página se
publica sola en GitHub Pages al fusionar cambios de `web/` en `main` (si no se actualiza,
en **Actions → Publicar página web → Run workflow**).

## Cómo funciona

```
archivo (DICOM, GIPL, NIfTI…)
  → carga         src/carga.py      densidad, orden de los cortes, vóxel en mm
  → escala        src/escala.py     escala declarada o normalizada por el histograma
  → Estudio       volumen (z, y, x) + espaciado + metadatos
  → 2D            src/visor_cortes.py  tres vistas y contraste
  → 3D            src/render_3d.py     preset → región → suavizado → marching cubes
```

- **El CBCT no está calibrado en Hounsfield:** cada equipo da números distintos para la misma
  anatomía. Por eso cada estudio se **normaliza** con dos picos de su histograma (aire → 0,
  tejido blando → 410), o se usa la escala declarada en `data/estudios.json`
  (`{"<id>": {"escala": "hounsfield"}}`). Las capas de relleno del tomógrafo se ignoran.
- **Presets** (`src/densidades.py`): un rango `(mínimo, máximo)` por estructura y por escala.
  Con máximo finito se aísla la banda (p. ej. esmalte sin metal) marcando los vóxeles y
  dibujando su frontera.
- **Región:** dientes y esmalte se limitan a la **arcada dental** (±25 mm de la altura con
  más esmalte), porque el hueso del cráneo es tan denso como la dentina.
- **Suavizado:** filtro gaussiano con sigma en milímetros, según el grosor de cada estructura
  (hueso y dientes 0,5 mm; esmalte y metal sin suavizar).
- **Colores:** de la curva *CT-Bone* de 3D Slicer, interpolada en los HU de cada preset; el
  metal en plateado de titanio.

| Preset | Escala `slicer` (normalizada) | Escala `hounsfield` |
|---|---|---|
| hueso | 700 – ∞ | 150 – ∞ HU |
| dientes | 1000 – ∞ | **820 – ∞ HU** (calibrado con 11 pacientes) |
| esmalte | 1250 – ∞ | 2000 – ∞ HU (confirmado) |
| esmalte sin metal | 1250 – 2000 | — |
| metal | 2000 – ∞ | — |

## Scripts

| Script | Para qué | Comando |
|---|---|---|
| `calibrar_presets.py` | Umbral óptimo de "dientes" (Dice) con estudios etiquetados | `python scripts/calibrar_presets.py data/raw/sts3d --csv results/calibracion_sts.csv` |
| `benchmark_render.py` | Tiempos y triángulos con reducción 1, 2 y 4 | `python -m scripts.benchmark_render data/raw/PreDentalSurgery.gipl.gz` |
| `histograma_densidades.py` | Histograma de densidades y umbrales de Otsu | `python scripts/histograma_densidades.py data/raw/PreDentalSurgery.gipl.gz` |
| `verificar_anonimizacion.py` | Revisa que los DICOM no traigan datos del paciente | `python scripts/verificar_anonimizacion.py data/raw --csv results/estudios.csv` |
| `probar_fracturas.py` | Vista de fractura en estudios con fractura (pelvis, costillas, columna, cráneo): hueso conservado, fragmentos del experto que se pierden y un montaje por estudio | `python -m scripts.probar_fracturas data/raw/fracturas/pelvis data/raw/fracturas/costillas data/raw/fracturas/columna` |
| `generar_web.py` | Regenera los datos y modelos de `web/` (sobrescribe la página) | `python scripts/generar_web.py data/raw/PreDentalSurgery.gipl.gz` |

## Pruebas

```bash
python -m pytest -q
```

91 pruebas: carga y orden de ejes, caché DICOM, espaciado entre cortes, normalización y
capas de relleno, presets y colores (incluida la sincronía con la página web), región de la
arcada, suavizado con sigma en mm, el motor 3D sin ventana (Phong, Taubin, plano de corte,
contador, relieve, cubo de orientación y vista de fractura), la orientación del paciente y una
prueba de humo de la aplicación Qt sin pantalla.

## Estructura

```
src/            programa: carga, escala, densidades, región, filtros, visor 2D, render 3D, app Qt
tests/          pruebas (pytest)
scripts/        calibración, benchmark, histogramas, anonimización, datos de la página
web/            página del proyecto (GitHub Pages)
docs/           arquitectura, roadmap, bitácora, planes por persona e investigación
results/        figuras y tablas para el informe
data/estudios.json   escala declarada de cada estudio (sí va en git)
data/raw/       estudios (NO va en git)
```

## Limitaciones conocidas

- **La densidad sola no separa diente de hueso:** aun calibrado, el preset "dientes"
  coincide con las máscaras de expertos con un Dice de ~0,6, porque el hueso alveolar y
  el cortical de la mandíbula tienen la misma densidad.
- **Los presets no se transfieren entre equipos:** la normalización corrige el aire y el
  tejido blando, pero no las densidades altas. Cada equipo necesita su calibración.
- **Músculo y grasa** no se separan con umbrales en CBCT: la vista de blandos es experimental.
- La vista frontal y la arcada suponen que el eje z del volumen es el vertical del paciente.

Detalle, mediciones y decisiones en la [bitácora](docs/bitacora-desarrollo.md).

## Créditos de los datos

- Muestras CBCT de **3D Slicer** — Fedorov A. et al., *3D Slicer as an Image Computing
  Platform for the Quantitative Imaging Network*, Magnetic Resonance Imaging 30(9), 2012.
- **STS-3D-Tooth** — Wang et al., *Scientific Data* 12, 117 (2025),
  doi:10.1038/s41597-024-04306-9 (CC-BY-4.0).
- **three.js** 0.160.0 (MIT), incluido en `web/vendor/`.
