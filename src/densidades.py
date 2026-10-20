"""Rangos de densidad para aislar estructuras de un CBCT dental.

Cada preset es "nombre": (mínimo, máximo) en las unidades del volumen cargado.
`render_3d.superficie_por_banda` lo dibuja así:
  - máximo = INF  → todo lo que supera el mínimo (isosuperficie de siempre);
  - máximo finito → solo la banda entre los dos valores (p. ej. esmalte sin el metal).

Las unidades dependen del equipo: la muestra de 3D Slicer está en grises del equipo
(0–3874), ToothFairy3 en Hounsfield. Valores y fuentes en
docs/investigacion/densidades.md (§2.1 y §2.2).
"""
INF = float("inf")

RANGOS_DENSIDAD = {
    # TODO(David): definir los presets y su formato por dataset (ver la explicación en el chat).
}
