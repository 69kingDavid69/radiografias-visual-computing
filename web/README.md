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

| Sección | Qué muestra | Pregunta que responde |
|---|---|---|
| 1 · Vóxeles | Cortes axial, coronal y sagital con ventana/nivel y lectura de cada vóxel | Qué es un vóxel y un CBCT |
| 2 · Umbral | Barra de umbral sobre un corte real + histograma con los presets | Cómo se traduce la escala de grises |
| 3 · Malla | *Marching squares* en vivo sobre un diente (la versión 2D de *marching cubes*) | Cómo se pasa de grises a una malla |
| 4 · Modelo 3D | Presets en 3D, plano vs. Phong, Laplaciano vs. Taubin, plano de corte, FPS | Iluminación, suavizado, plano de corte y rendimiento |
| 5 · Hallazgos | Cifras medidas y limitaciones | Resultados |

## Estructura

```
web/
  index.html, estilos.css     página (tema oscuro, mismos colores que la app Qt)
  js/principal.js             carga los datos y arranca cada sección
  js/cortes.js                secciones 1–3 (cortes, umbral, histograma, marching squares)
  js/lab3d.js                 visores 3D (portada y laboratorio)
  datos/cortes.png            cortes axiales en una sola imagen (1 de cada 2 vóxeles, valor/16)
  datos/meta.json             forma, histograma, presets y datos de los modelos
  modelos/*.ply               una malla por preset + detalle de los dientes
  vendor/three/               three.js 0.160.0 (MIT), incluido para no depender de internet
  img/icono.png               ícono de la app
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
```

Vuelve a crear `web/datos/` y `web/modelos/` con los presets actuales de
`src/densidades.py`. Si cambian los presets o el suavizado, se corre de nuevo y se
sube el resultado.

**Privacidad:** el script nunca genera la superficie de la piel, porque reconstruye la
cara del paciente. Solo se publican hueso, dientes, esmalte y metal.
