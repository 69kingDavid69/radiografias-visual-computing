# Roadmap

Plan por fases y por persona. Arquitectura y decisiones técnicas: [ARCHITECTURE.md](ARCHITECTURE.md).
Las duraciones son relativas; las fechas se fijan cuando el profesor confirme la entrega.

## Equipo y roles

| Rol | Persona | Dueño de |
|---|---|---|
| **Dev 1 — Datos y pipeline** | David | `src/carga.py`, `src/main.py`, integración, repo y revisión de PRs |
| **Dev 2 — Visor 2D e interfaz** | _por asignar_ | `src/visor_cortes.py`, ventana unificada (fase 3) |
| **Dev 3 — Render 3D** | _por asignar_ | `src/render_3d.py`, rendimiento, iluminación |
| **Investigación y datos** | _por asignar_ | datasets CBCT, rangos de densidad, marco teórico, informe |

Los rangos de `src/densidades.py` los proponen en conjunto **Investigación**
(lo que dice la literatura) y **Dev 3** (lo que se ve en el render).

## Forma de trabajo

- Una rama por tarea (`feat/visor-contraste`, `fix/espaciado-z`, …) y un PR a `main`
  con una revisión de otra persona.
- Las imágenes médicas nunca van al repo: cada uno las guarda en `data/raw/`.
- Una reunión corta por semana para revisar este roadmap y marcar casillas.

---

## Fase 0 — Vertical slice (1 semana)

- [x] Repo, estructura de carpetas, `.gitignore` de datos médicos — Dev 1
- [x] Esqueleto: carga DICOM → visor 2D → isosuperficie 3D con barra — Dev 1
- [x] Prueba con volumen sintético (esfera) y DICOM de ejemplo de pydicom — Dev 1
- [ ] Cada dev clona, crea el `.venv` y corre `--modo cortes` y `--modo 3d` — todos
- [ ] Lista de 2–3 datasets CBCT dentales candidatos con licencia y forma de acceso — Investigación

**Hito:** los tres devs ven un modelo 3D en su computador.

## Fase 1 — Datos reales (1–2 semanas)

- [ ] Descargar el dataset elegido y verificar que está anonimizado — Investigación
- [ ] Cargar estudios reales: orientación, espaciado z, caso multiframe — Dev 1
- [ ] Caché del volumen en `data/processed/*.npy` para no releer los DICOM — Dev 1
- [ ] Visor 2D: control de ventana/nivel (contraste) y número de corte en mm — Dev 2
- [ ] Vistas coronal y sagital además de la axial — Dev 2
- [ ] Render 3D: recalcular solo al soltar la barra; medir tiempos con `reduccion` 1, 2 y 4 — Dev 3

**Hito:** se recorre un CBCT dental real en 2D y se ve la mandíbula en 3D.

## Fase 2 — Aislar estructuras por densidad (2 semanas)

- [ ] Histograma de densidades de cada estudio; identificar los picos de aire, tejido blando, hueso y esmalte — Investigación + Dev 3
- [ ] Llenar `RANGOS_DENSIDAD` y justificar cada rango con fuentes — Investigación + Dev 3
- [ ] Presets en la vista 3D (botones o menú) — Dev 3
- [ ] Filtro de ruido opcional antes del umbral (scikit-image) — Dev 1
- [ ] Opacidad por estructura: hueso semitransparente y esmalte sólido — Dev 3

**Hito:** con un clic se ve solo el hueso o solo el esmalte.

## Fase 3 — Interfaz única (2 semanas)

- [ ] Cerrar la decisión abierta #1 (Qt vs. web) — equipo
- [ ] Ventana con panel 2D y panel 3D lado a lado — Dev 2
- [ ] Selector de carpeta de estudio desde la interfaz, sin línea de comandos — Dev 2 + Dev 1
- [ ] Integrar presets y barra de sensibilidad en la ventana — Dev 3
- [ ] Probar la app con usuarios que no la construyeron (compañeros de salud, si hay) — Investigación

**Hito:** una persona sin terminal abre un estudio y explora 2D y 3D.

## Fase 4 — Cierre (1 semana)

- [ ] Capturas y figuras en `results/` — Dev 3
- [ ] Informe: pregunta de investigación, método (marching cubes, umbrales), resultados y limitaciones — Investigación (con secciones técnicas de cada dev)
- [ ] Guion y ensayo de la demo en vivo — todos
- [ ] README final con instrucciones de instalación y uso — Dev 1

**Hito:** entrega al profesor Paluszny.

---

## Opcional (si sobra tiempo)

- Exportar la superficie a STL para imprimir en 3D o abrir en Blender.
- Medir distancias en el modelo 3D (por ejemplo, el ancho de un diente en mm).
- Renderizado volumétrico directo (`add_volume`) como alternativa a la isosuperficie.
