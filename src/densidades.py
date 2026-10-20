"""Rangos de densidad para aislar estructuras de un CBCT dental.

Cada preset es "nombre": (mínimo, máximo) en las unidades del volumen cargado.
`render_3d.superficie_por_banda` lo dibuja así:
  - máximo = INF  → todo lo que supera el mínimo (isosuperficie de siempre);
  - máximo finito → solo la banda entre los dos valores (p. ej. esmalte sin el metal).

Los valores dependen de la escala de densidad del equipo, por eso hay un juego de
presets por escala. Fuentes: docs/investigacion/densidades.md (§2.1 y §2.2).
"""
INF = float("inf")

RANGOS_DENSIDAD = {
    # Muestra CBCT de 3D Slicer: grises del equipo (0–3874), NO Hounsfield.
    # Medidos sobre el render el 15/10 (densidades.md §2.1).
    "slicer": {
        "hueso":   (700, INF),     # cráneo, maxilares y dientes
        "dientes": (1000, INF),    # hueso más denso + dientes con sus raíces
        "esmalte": (1250, 2000),   # coronas, SIN el metal de los brackets (> 2000)
        "metal":   (2000, INF),    # solo los brackets de ortodoncia
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

# Qué escala tiene cada formato de archivo en los datasets del proyecto.
# DICOM no está: según el equipo puede venir en Hounsfield o en grises propios,
# así que para DICOM hay que indicar la escala a mano en estudio.metadatos["escala"].
ESCALA_POR_FORMATO = {
    "GIPL": "slicer",
    "NII": "hounsfield",
}


def escala_de(estudio):
    """Escala de densidad del estudio ("slicer", "hounsfield"…) o None si no se sabe.

    Gana lo que diga estudio.metadatos["escala"]; si no, se deduce del formato.
    """
    return estudio.metadatos.get("escala") or ESCALA_POR_FORMATO.get(
        estudio.metadatos.get("formato"))


def presets_para(estudio):
    """Presets que corresponden al estudio. Si no se conoce su escala devuelve {}:
    la app muestra entonces solo la barra libre, en lugar de presets con números
    de otro equipo que aislarían la estructura equivocada."""
    return RANGOS_DENSIDAD.get(escala_de(estudio), {})
