# Plan de construcción — Emanuel Aristizábal (Dev 3: render 3D)

**Soy dueño de:** `src/render_3d.py`, `scripts/benchmark_render.py` y, junto con
Nicolás, `src/densidades.py`.
**Dependo de:** David (`Estudio`) y Nicolás (rangos de densidad).
**Entrego a:** Juan, que monta mi vista en la app.

## Contrato que expongo

```python
class Render3D:
    def __init__(self, plotter: pv.Plotter): ...        # Plotter o QtInteractor
    def mostrar(self, estudio: Estudio, reduccion: int = 2): ...
    def set_umbral(self, valor: float): ...
    def aplicar_preset(self, nombre: str): ...            # clave de RANGOS_DENSIDAD
    def captura(self, ruta: str): ...
```

Recibe el `plotter` desde afuera para que Juan le pase el `QtInteractor` de la app.

---

## Fase 0 — Vertical slice
- [ ] Clonar, crear `.venv`, correr `--modo 3d`.
- [ ] Leer `src/render_3d.py` y entender `contour()`: es marching cubes, que
  convierte el umbral en una malla de triángulos.
- [ ] Probar con `pyvista.examples.download_head()` para tener un volumen grande
  mientras llegan los datos reales.

**Hecho cuando:** mueves la barra y la superficie cambia.

## Fase 1 — Rendimiento · rama `feat/render-rapido`
1. [x] Recalcular solo al soltar la barra:
   `add_slider_widget(..., interaction_event="end")`.
2. [x] `scripts/benchmark_render.py`: mide el tiempo de `contour()` y el número de
   triángulos con `reduccion` = 1, 2 y 4 sobre un estudio real, y lo guarda en
   `results/tiempos.csv`.
3. [x] Elegir la `reduccion` por defecto con esos números: seleccionada **`reduccion = 2`**
   (reduce los vóxeles a 1/8, tiempo $< 0.5$ s en tomografía real conservando detalle anatómico).
4. [x] Refactorizar a la clase `Render3D` del contrato (implementada en `src/render_3d.py`).

**Hecho cuando:** la tabla de tiempos está en `results/` y el render responde
fluido en el computador más lento del equipo.

## Fase 2 — Aislar estructuras · rama `feat/presets`
1. Con Nicolás: histograma del volumen (`np.histogram`, eje y logarítmico) para
   ubicar los picos de aire, tejido blando, hueso y esmalte. Guardar la figura en `results/`.
2. Llenar `RANGOS_DENSIDAD` con los rangos acordados.
3. **Presets:** botones en la ventana 3D o teclas `1`–`4` (`pl.add_key_event`).
4. **Opacidad por estructura:** una superficie por estructura, cada una con su
   color y opacidad (hueso 0.3 color marfil, esmalte 1.0 blanco).
5. **Calidad visual:** suavizar la malla (`superficie.smooth_taubin()`) y
   ajustar la luz (`pl.enable_lightkit()`, `specular`).

**Hecho cuando:** con una tecla se ve solo el hueso y con otra solo el esmalte, y
los dientes se distinguen del maxilar.

## Fase 3 — Integración
- [x] Probar `Render3D` dentro de la app de Juan (`QtInteractor`).
- [x] Conectar el selector de preset y la barra de umbral de la app a
  `aplicar_preset` y `set_umbral`.

**Hecho cuando:** el panel 3D funciona dentro de la ventana única.

## Fase 4 — Cierre
- [ ] Capturas de cada preset con `captura()` en `results/`.
- [ ] (Opcional) Exportar STL: `superficie.save("results/mandibula.stl")` y
  abrirlo en Blender o compararlo con el húmero de clase.
- [ ] Sección técnica del informe: marching cubes, umbralización y rendimiento.
- [ ] Conducir la parte 3D de la demo.

