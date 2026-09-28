# Plan de construcción — Juan Gómez (Dev 2: visor 2D e interfaz)

**Soy dueño de:** `src/visor_cortes.py` y `src/app.py` (la ventana unificada).
**Dependo de:** David (`Estudio`) y Emanuel (`Render3D`, en la fase 3).
**Entrego a:** todo el equipo, porque la interfaz es lo que se ve en la demo.

## Contrato que expongo

```python
class VisorCortes:
    def __init__(self, figura: matplotlib.figure.Figure): ...
    def mostrar(self, estudio: Estudio): ...
    def ir_a_corte(self, eje: str, indice: int): ...   # eje: "axial" | "coronal" | "sagital"
```

Recibe una `Figure` en vez de crear su propia ventana, para poder meterlo dentro
de la app Qt en la fase 3.

---

## Fase 0 — Vertical slice
- [ ] Aceptar la invitación, clonar, crear `.venv` e instalar `requirements.txt`.
- [ ] Correr `python -m src.main <carpeta> --modo cortes` con el DICOM de ejemplo.
- [ ] Leer `src/visor_cortes.py` completo y entender cómo `Slider.on_changed` redibuja.

**Hecho cuando:** ves el corte y el deslizador se mueve.

## Fase 1 — Visor 2D completo · rama `feat/visor-contraste`
1. **Ventana/nivel (contraste):** función `aplicar_ventana(corte, centro, ancho)`
   que recorta los valores a `[centro − ancho/2, centro + ancho/2]`. Dos sliders
   más (centro y ancho), o arrastrar con el mouse como en los visores médicos.
2. Título con número de corte **y** posición en mm (`indice * dz`).
3. **Tres vistas:** axial `volumen[z]`, coronal `volumen[:, y, :]` y sagital
   `volumen[:, :, x]`, cada una con su slider. Ojo con la proporción: en coronal y
   sagital hay que usar `aspect = dz / dx`, o la imagen sale estirada.
4. **Líneas guía:** en cada vista, líneas que marcan dónde están los otros dos
   cortes (con `ax.axhline` / `ax.axvline`).
5. Refactorizar a la clase `VisorCortes` del contrato.

**Hecho cuando:** en un CBCT real se reconoce un diente en las tres vistas, sin
deformación, y el contraste deja distinguir esmalte de dentina.

## Fase 2 — Apoyo
- [ ] Probar el visor con los estudios que consiga Nicolás y anotar los casos
  raros (cortes negros, orientación invertida).
- [ ] Prototipo de la app en Qt (rama `spike/qt`): una ventana con un
  `FigureCanvasQTAgg` a la izquierda y un `pyvistaqt.QtInteractor` a la derecha.
  Sirve para cerrar la decisión #1 con datos.

**Hecho cuando:** el prototipo abre en los computadores del equipo (Mac y Windows, si hay).

## Fase 3 — Ventana unificada · rama `feat/app`
1. `src/app.py` con PySide6. Distribución:
   - barra superior: **Abrir estudio**, selector de **preset**, casilla **Suavizar**;
   - panel izquierdo: `VisorCortes`;
   - panel derecho: `Render3D` de Emanuel;
   - barra inferior: tamaño del volumen, vóxel en mm, tiempo de carga.
2. "Abrir estudio" abre `QFileDialog` para elegir una carpeta y usa la carga en
   hilo que hace David.
3. Atajos de teclado: flechas para cambiar de corte, `R` para reiniciar la cámara 3D.

**Hecho cuando:** alguien que no escribió el código abre un estudio y explora
2D y 3D sin usar la terminal.

## Fase 4 — Cierre
- [ ] Capturas de la interfaz para el informe y el README.
- [ ] Sección técnica del informe: diseño de la interfaz y vistas ortogonales.
- [ ] Conducir la parte 2D de la demo.
