"""Rangos de densidad para aislar estructuras de un CBCT dental.

Cada preset es "nombre": (mínimo, máximo) en las unidades del volumen cargado.
`render_3d.superficie_por_banda` lo dibuja así:
  - máximo = INF  → todo lo que supera el mínimo (isosuperficie de siempre);
  - máximo finito → solo la banda entre los dos valores (p. ej. esmalte sin el metal).

Los valores dependen de la escala de densidad, por eso hay un juego de presets por
escala. Los estudios sin escala declarada se normalizan a "slicer" (src/escala.py). Fuentes: docs/investigacion/densidades.md (§2.1 y §2.2).
"""
INF = float("inf")

RANGOS_DENSIDAD = {
    # Muestra CBCT de 3D Slicer: grises del equipo (0–3874), NO Hounsfield.
    # Medidos sobre el render el 15/10 (densidades.md §2.1).
    "slicer": {
        "hueso":   (700, INF),     # cráneo, maxilares y dientes
        "dientes": (1000, INF),    # hueso más denso + dientes con sus raíces
        "esmalte": (1250, INF),    # coronas; también brackets, implantes y algo de cortical
        # Misma banda sin el metal (> 2000). Deja huecos donde estaba el metal y no
        # quita sus artefactos: sirve para comparar con "esmalte" en la demo.
        "esmalte_sin_metal": (1250, 2000),
        "metal":   (2000, INF),    # solo metal: brackets en esta muestra; implantes en otros estudios
    },
    # Datasets calibrados en Hounsfield (ToothFairy3). Propuesta de la literatura,
    # falta validarla con las etiquetas de ToothFairy3 (densidades.md §2.2 y §5).
    "hounsfield": {
        "tejido_blando": (-200, 150),   # encía, lengua, músculo; ruidoso en CBCT
        "hueso":         (150, INF),    # todo el hueso + dientes
        "hueso_denso":   (850, INF),    # hueso cortical + dientes
        "dientes":       (1300, INF),   # dentina + esmalte (y restauraciones)
        "esmalte":       (2000, INF),   # coronas (y metal o resinas radiopacas)
    },
}

# Sigma del filtro gaussiano (mm) por estructura, medido con la muestra Pre (bitácora
# 19/10). Va por estructura y no por escala: el sigma depende del grosor anatómico, y
# una capa delgada como el esmalte se borra si sigma es grande. 0 = sin suavizar.
SUAVIZADO_MM = {
    "hueso": 0.5,              # 1292 → 380 pedazos sueltos sin perder detalle
    "dientes": 0.5,            # 503 → 177 pedazos, las raíces se conservan
    "esmalte": 0.0,            # con 0.5 la capa pierde la mitad de la superficie
    "esmalte_sin_metal": 0.0,  # con 1.0 desaparece
    "metal": 0.0,              # suavizar encoge brackets e implantes
}


def suavizado_para(nombre):
    """Sigma en mm para un preset; los presets sin medir no se suavizan."""
    return SUAVIZADO_MM.get(nombre, 0.0)


def escala_de(estudio):
    """Escala de densidad del estudio ("slicer", "hounsfield"…) o None si no se sabe.

    La asigna `escala.asignar_escala` al cargar: la declarada en data/estudios.json o
    "slicer" si el estudio se normalizó por el histograma.
    """
    return estudio.metadatos.get("escala")


def presets_para(estudio):
    """Presets que corresponden al estudio. Si no se conoce su escala devuelve {}:
    la app muestra entonces solo la barra libre, en lugar de presets con números
    de otro equipo que aislarían la estructura equivocada."""
    return RANGOS_DENSIDAD.get(escala_de(estudio), {})
