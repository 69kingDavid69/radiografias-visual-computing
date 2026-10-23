# Página web del proyecto

Página que explica el proyecto con la tomografía real y modelos 3D interactivos. Se
publica sola en GitHub Pages con `.github/workflows/pages.yml` cada vez que cambia
algo en `web/`:

**https://69kingdavid69.github.io/radiografias-visual-computing/**

> **Para qué sirve en el proyecto.** Es el apoyo visual de la exposición y responde
> las cinco preguntas técnicas de la propuesta con elementos que se pueden mover. Las
> mallas y los datos salen del mismo código del programa: `src/carga.py`,
> `src/densidades.py` y `src/render_3d.superficie_por_banda`. El texto se apoya en
> [docs/investigacion/](../docs/investigacion/README.md).

## Secciones

La página sigue el orden de la exposición del 26/10. Cada sección dice quién la expone. Las flechas → / ← del teclado pasan de sección.

| Sección | Qué muestra | Expone |
|---|---|---|
| Portada | Pregunta de investigación, cráneo 3D girando y ruta de la exposición | — |
| 1 · Problema | Radiografía simulada (proyección del volumen) vs. un corte de la tomografía | Nicolás |
| 2 · CBCT | Ilustración haz en abanico vs. haz en cono; tabla CT vs. CBCT | Nicolás |
| 3 · Datos | Datasets elegidos y descartados; cómo viene un DICOM y la anonimización | Nicolás / David |
| 4 · Programa | Flujo de módulos, capturas de la app y cómo abrirla | David |
| 5 · Cortes | Visor de tres planos con ventana/nivel y lectura de cada vóxel | Juan |
| 6 · Densidad | Escala Hounsfield con rangos de la literatura, anatomía del diente, normalización por picos | Nicolás |
| 7 · Umbral | Barra de umbral sobre un corte real + histograma con los presets (P1) | Nicolás |
| 8 · Malla | Marching squares en vivo y el cubo de marching cubes (P1) | Emanuel |
| 9 · 3D | Laboratorio: estructuras, P2 luz, P3 FPS, P4 suavizado, P5 corte | Emanuel |
| 10 · Resultados | Cifras, calibración con 11 pacientes, tiempos y limitaciones | Nicolás |
| 11 · Conclusión | Respuesta a la pregunta de investigación | Nicolás |
| Preguntas | Las 5 preguntas con respuesta corta; abren su pestaña del laboratorio | Todos |

**`guion.html`**: guion de cada integrante, qué aprender y preguntas probables. Se imprime a PDF desde el navegador (versión clara para papel).
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
  img/*.png, img/*.svg        ilustraciones calculadas con datos reales (scripts/generar_ilustraciones.py)
  guion.html                  guion y guía de estudio del equipo
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
