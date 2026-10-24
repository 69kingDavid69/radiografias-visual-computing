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
        # EXPERIMENTALES. En el CBCT la grasa no forma un pico propio en el histograma: es
        # un "hombro" a la izquierda del pico del tejido blando (≈ 410). El corte en 375
        # queda ~1,5 veces el ruido (≈ 18 u) por debajo del pico. No es una segmentación
        # de músculos: es la parte más densa del tejido blando contra la menos densa. En el
        # estudio Post, "musculo" también incluye el cerebro y la lengua (densidad parecida).
        "grasa":   (280, 375),
        "musculo": (375, 600),
    },
    # Datasets calibrados en Hounsfield (STS-3D-Tooth, ToothFairy3). Propuesta de la
    # literatura (densidades.md §2.2), corregida con 11 pacientes etiquetados de STS
    # (scripts/calibrar_presets.py, results/calibracion_sts.csv, bitácora 22/10).
    "hounsfield": {
        "tejido_blando": (-200, 150),   # encía, lengua, músculo; ruidoso en CBCT
        "hueso":         (150, INF),    # todo el hueso + dientes
        "hueso_denso":   (850, INF),    # hueso cortical + dientes
        "dientes":       (820, INF),    # medido: óptimo de Dice ~816 HU (609–1084); antes 1300
        "esmalte":       (2000, INF),   # confirmado: el 10 % más denso del diente empieza en ~2010 HU
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
    "grasa": 1.0,              # tejido blando: ruido ~18 u, sin suavizar se ve granulado
    "musculo": 1.0,
    "tejido_blando": 1.0,
}


def suavizado_para(nombre):
    """Sigma en mm para un preset; los presets sin medir no se suavizan."""
    return SUAVIZADO_MM.get(nombre, 0.0)


# Umbral de la vista de fractura (ver Render3D.aplicar_fractura). Con 150 HU el borde del
# hueso queda difuso y se llena de ruido en la mandíbula; con 300 HU la línea de fractura
# y los bordes se ven nítidos. En la escala "slicer" no se midió: se usa el del preset "hueso".
UMBRAL_FRACTURA = {"hounsfield": 300}

# Por debajo de este valor es aire (no cuerpo): a medio camino entre el aire y el tejido blando.
# En "slicer" el aire está en 0 y el tejido blando en 410 (src/escala.py).
UMBRAL_TEJIDO = {"hounsfield": -400, "slicer": 205}


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


# Ventanas de contraste del visor 2D (centro, ancho). Las de Hounsfield son las de
# radiología que eligió Juan; las de la escala "slicer" son las mismas convertidas con
# la recta que deja el aire (−1000 HU) en 0 y el tejido blando (40 HU) en 410, la misma
# referencia a la que src/escala.py normaliza cada estudio.
VENTANAS_HU = {
    "dientes_hueso": (1000, 3000),
    "tejido_blando": (40, 400),
}
_PENDIENTE_HU = 410 / (40 - (-1000))          # 0.394 unidades por HU


def _hu_a_slicer(centro, ancho):
    return round(_PENDIENTE_HU * (centro + 1000)), round(_PENDIENTE_HU * ancho)


VENTANAS_2D = {
    "hounsfield": VENTANAS_HU,
    "slicer": {nombre: _hu_a_slicer(*v) for nombre, v in VENTANAS_HU.items()},
}


def ventana_para(estudio_o_escala, nombre):
    """(centro, ancho) de una ventana 2D en la escala del estudio, o None si no se conoce."""
    escala = (estudio_o_escala if isinstance(estudio_o_escala, (str, type(None)))
              else escala_de(estudio_o_escala))
    return VENTANAS_2D.get(escala, {}).get(nombre)


def unidad_de(escala):
    """Etiqueta de unidades para mostrar en la interfaz."""
    return "HU" if escala == "hounsfield" else "u. norm."


# Color de cada estructura en 3D. Los tejidos salen de la curva de color "CT-Bone" de
# 3D Slicer (presets.xml del módulo Volume Rendering): cada preset se pasa a su
# equivalente en HU con la recta de src/escala.py (HU = (u − 394) / 0,394) y se
# interpola en la curva: rojizo en tejido blando, amarillo cálido en el hueso y cada vez
# más blanco al subir la densidad. El metal queda fuera de esa curva (pasa de 3071 HU):
# se usa el plateado frío del titanio, que además se distingue del hueso cálido en la
# vista de implante. La app (Render3D) y la página (web/js/lab3d.js, web/estilos.css)
# usan estos valores; tests/test_densidades.py verifica que no se desincronicen.
COLORES_TEJIDO = {
    "tejido_blando": "#BB454F",   # ≈ 0 HU
    "hueso":         "#E8D393",   # 700 u ≈ 776 HU
    "hueso_denso":   "#E9D497",   # 850 HU (preset en Hounsfield)
    "dientes":       "#F0E1B7",   # 1000 u ≈ 1537 HU
    "esmalte":       "#F6EED5",   # 1250 u ≈ 2171 HU
    "esmalte_sin_metal": "#F6EED5",
    "metal":         "#C9D1D9",   # titanio pulido: plateado frío
    "grasa":         "#E3B04B",   # grasa: amarillo anaranjado, distinto del hueso
    "musculo":       "#A8323E",   # músculo: rojo
}

# Presets que la app no ofrece sueltos: solo en la vista de tejidos blandos con corte
# sagital (Render3D.CAPAS_BLANDAS), porque la grasa o el tejido blando de frente
# reconstruyen la cara.
EXPERIMENTALES = {"grasa", "musculo", "tejido_blando"}

# Presets que se limitan a la arcada dental (src/region.py): por densidad sola incluyen
# el hueso cortical del cráneo, que es tan denso como la dentina.
EN_ARCADA = {"dientes", "esmalte", "esmalte_sin_metal"}


def color_para(nombre):
    """Color del tejido de un preset; los que no tienen color propio salen en marfil."""
    return COLORES_TEJIDO.get(nombre, "#EEE4C6")

