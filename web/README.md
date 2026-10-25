# Página web del proyecto

Página que explica el proyecto con la tomografía real y modelos 3D interactivos. Se
publica sola en GitHub Pages con `.github/workflows/pages.yml` cada vez que cambia
algo en `web/`:

**https://69kingdavid69.github.io/radiografias-visual-computing/**

> **Para qué sirve en el proyecto.** Explica el proyecto completo con la tomografía real
> y elementos que se pueden mover: el problema, los datos, el programa, la densidad, la
> extracción de superficies y los resultados. Las mallas y los datos salen del mismo
> código del programa: `src/carga.py`, `src/densidades.py` y
> `src/render_3d.superficie_por_banda`. El texto se apoya en
> [docs/investigacion/](../docs/investigacion/README.md).

## Secciones

Las flechas → / ← del teclado pasan de sección; el botón **Código** de la barra lleva al repositorio.

| Sección | Qué muestra |
|---|---|
| Portada | Pregunta de investigación y el cráneo 3D girando |
| 1 · Problema | Radiografía (píxeles) frente a tomografía (vóxeles), con datos reales |
| 2 · CBCT | Haz en abanico vs. haz en cono; tabla CT vs. CBCT |
| 3 · Datos | Datasets elegidos y descartados; cómo viene un DICOM |
| 4 · Programa | Flujo de módulos, capturas de la app y cómo abrirla |
| 5 · Cortes | Visor de tres planos con ventana/nivel y lectura de cada vóxel |
| 6 · Densidad | Escala Hounsfield, anatomía del diente y normalización por picos |
| 7 · Umbral | Barra de umbral sobre un corte real + histograma |
| 8 · Malla | Marching squares en vivo y el cubo de marching cubes |
| 9 · 3D | Laboratorio: estructuras, luz, FPS, suavizado y plano de corte |
| 10 · Resultados | Cifras, calibración con 11 pacientes, tiempos y limitaciones |
| 11 · Fracturas | Vista de fractura en cráneo, pelvis, costillas y columna; cómo se midió y qué no se ve |
| Equipo | Quién hizo qué, documentos de investigación y referencias |

## Estructura

```
web/
  index.html, estilos.css     página (tema oscuro, mismos colores que la app Qt)
  js/principal.js             carga los datos y arranca cada sección
  js/cortes.js                secciones 1–3 (cortes, umbral, histograma, marching squares)
  js/lab3d.js                 visores 3D (portada y laboratorio)
  datos/cortes.png            cortes axiales en una sola imagen (1 de cada 2 vóxeles, valor/16)
  datos/meta.json             forma, histograma, presets y datos de los modelos
  modelos/*.ply               una malla por preset (hueso, dientes, esmalte, esmalte sin metal, metal) + detalle de los dientes
  vendor/three/               three.js 0.160.0 (MIT), incluido para no depender de internet
  img/icono.png               ícono de la app
  img/app_*.jpg               capturas de la app para la sección "Programa"
  img/*.png, img/*.svg        ilustraciones calculadas con datos reales (scripts/generar_ilustraciones.py
                              y scripts/ilustracion_pixel_voxel.py)
  img/equipo/                 fotos de perfil de GitHub del equipo
```

## Verla en local o sin internet

Los módulos JavaScript no funcionan abriendo el archivo con doble clic; hay que
servir la carpeta:

```bash
python -m http.server 8000 --directory web
```

Luego se abre `http://localhost:8000`. Todo (three.js incluido) está dentro de
`web/`, así que funciona sin conexión.

## Regenerar los datos

Con la muestra en `data/raw/PreDentalSurgery.gipl.gz`:

```bash
python scripts/generar_web.py
python scripts/generar_ilustraciones.py   # opcional: results/calibracion_sts.csv para la gráfica de calibración
```

Vuelve a crear `web/datos/` y `web/modelos/` con los presets actuales de
`src/densidades.py`. Si cambian los presets o el suavizado, se corre de nuevo y se
sube el resultado.

**Privacidad:** el script nunca genera la superficie de la piel, porque reconstruye la
cara del paciente. Solo se publican hueso, dientes, esmalte y metal.
