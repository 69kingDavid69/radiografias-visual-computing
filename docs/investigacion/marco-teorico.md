# Marco teórico

> **Para qué sirve en el proyecto.** Explica la teoría detrás de cada módulo:
> - por qué `carga.py` ordena y reescala los cortes (§2);
> - qué hace `contour()` en `render_3d.py` (§7) y cómo se ilumina, suaviza y
>   optimiza la malla (§8–§11);
> - por qué los presets de `densidades.py` dependen del equipo (§4–§5);
> - qué hace la ventana/nivel del visor 2D (§6).
>
> Es la base de las secciones "Marco teórico" y "Método" del [informe](informe.md).
> Las referencias numeradas están al final, y hay un [glosario](#glosario) con los
> términos técnicos.

## Resumen en palabras simples

1. Una **radiografía** es una sola foto plana con rayos X; las estructuras se
   superponen. Una **tomografía** toma cientos de imágenes alrededor de la cabeza y
   con ellas calcula un **cubo 3D** de densidades. Cada cubito de ese cubo es un
   **vóxel** (el "píxel 3D").
2. En odontología se usa el **CBCT** (tomografía de haz cónico): más barata y con
   menos radiación que un CT de hospital, pero con más ruido y con **números de
   densidad que cambian de un equipo a otro** (no están calibrados en Hounsfield).
3. Los equipos guardan el estudio en **DICOM**: muchos archivos, uno por corte, con
   datos como el tamaño del vóxel en mm.
4. Para **aislar** una estructura se usa un **umbral**: se ve solo lo que tenga
   densidad mayor que cierto valor. Como el esmalte es más denso que el hueso, y el
   hueso más que la encía, subir el umbral va "pelando" capas.
5. Para dibujar en 3D lo que pasa el umbral, el algoritmo **marching cubes** recorre
   el cubo de 8 en 8 vóxeles y pone **triángulos** donde la densidad cruza el umbral.
   El resultado es una **malla** que la tarjeta gráfica dibuja.
6. Para que la malla se vea como un objeto real se le aplica **iluminación**
   (sombreado Phong, brillos, sombras). Para que no se vea escalonada se **suaviza**
   (Taubin). Para que se mueva fluido se reduce el número de triángulos. Y con un
   **plano de corte** se puede ver el interior del diente.

---

## 1. Qué es un CBCT y en qué se diferencia de un CT médico

Una **radiografía** proyecta todo sobre un plano: es una sola imagen 2D en la que las
estructuras se superponen. Una **tomografía** toma muchas proyecciones desde ángulos
distintos y con ellas **reconstruye** un **volumen 3D** dividido en **vóxeles**. Cada
vóxel guarda cuánto **atenúa** (frena) los rayos X el material que hay en ese punto.

La **tomografía computarizada de haz cónico** (CBCT, *cone-beam computed tomography*)
es la variante que se usa en odontología [1]:

| | CT médico (multicorte, MDCT) | CBCT dental |
|---|---|---|
| Haz de rayos X | En abanico, delgado; el paciente avanza por el anillo | En **cono**: cubre toda la región de una vez |
| Detector | Filas de detectores | Un **panel plano** 2D |
| Adquisición | Muchas vueltas en espiral | **Una sola rotación** alrededor de la cabeza |
| Reconstrucción | Retroproyección filtrada o iterativa | Normalmente el algoritmo **FDK** (Feldkamp-Davis-Kress) [2] |
| Vóxel | Suele ser más largo en z que en x-y | **Isotrópico** (igual en los tres ejes) y pequeño, ~0.1–0.5 mm |
| Dosis de radiación | Más alta | Más baja |
| Contraste del tejido blando | Bueno | Pobre (más ruido y dispersión) |
| Valores de gris | **Calibrados en Hounsfield** | **No calibrados**: varían entre equipos y protocolos (§4) |

Lo que esto implica para el proyecto:

1. El vóxel pequeño y igual en los tres ejes es ideal para ver dientes en 3D.
2. El tejido blando (encía, lengua, piel) sale ruidoso: se puede separar del hueso con
   un umbral, pero la frontera no es limpia.
3. Un umbral fijo no sirve para todos los equipos (riesgo #3 de la arquitectura).

**Artefactos típicos** (defectos de la imagen) que se ven en el render:

- **Metal** (amalgamas, coronas, implantes, brackets): produce rayas brillantes y
  oscuras. En la superficie 3D aparecen como picos o agujeros. Además, el metal
  supera la densidad del esmalte, así que el preset "esmalte" también lo muestra.
  Lo comprobamos con la muestra de Slicer, que tiene brackets.
- **Endurecimiento del haz**: zonas oscuras entre dos estructuras muy densas.
- **Dispersión y ruido**: al umbralizar quedan "pedacitos sueltos".
- **Movimiento** del paciente: bordes dobles.

## 2. El formato DICOM

DICOM (*Digital Imaging and Communications in Medicine*) es el estándar de los
equipos médicos [3]. Un estudio CBCT suele exportarse como **una carpeta con cientos
de archivos `.dcm`**, uno por **corte** axial. Otros equipos guardan todo en **un
solo archivo multiframe**.

Cada archivo tiene una **cabecera** con etiquetas y la **matriz de píxeles**. Las
etiquetas que usa `src/carga.py`:

| Etiqueta | Qué es | Para qué se usa |
|---|---|---|
| `PixelData` | Los valores guardados del corte | La imagen |
| `ImagePositionPatient` | Posición (x, y, z) en mm de la esquina del corte | **Ordenar los cortes** por altura, porque los archivos no vienen en orden |
| `PixelSpacing` | Tamaño del píxel (fila, columna) en mm | `dy`, `dx` del vóxel |
| `SliceThickness` / `SpacingBetweenSlices` | Grosor o separación entre cortes | `dz` cuando no se puede calcular con las posiciones |
| `RescaleSlope`, `RescaleIntercept` | Pendiente e intercepto | Pasar del valor guardado a la densidad |
| `ImageOrientationPatient` | Dirección de filas y columnas | Saber si el corte es axial puro |

**Reescalado.** El número guardado en el archivo no es la densidad. Se convierte así:

```
densidad = valor_guardado × RescaleSlope + RescaleIntercept
```

Por ejemplo, el archivo de prueba `CT_small.dcm` de pydicom tiene pendiente 1 e
intercepto −1024: un valor guardado de 1024 corresponde a 0 HU (agua).

**Espaciado.** El tamaño físico del vóxel `(dz, dy, dx)` es indispensable: sin él, el
modelo 3D sale estirado y las distancias en mm son falsas. `dz` se calcula con la
diferencia de `ImagePositionPatient[2]` entre cortes consecutivos.

**Datos del paciente.** La cabecera puede traer `PatientName`, `PatientID`,
`PatientBirthDate`, la institución y fechas. Por eso los DICOM nunca se suben a
GitHub y hay que verificar que estén anonimizados con
`scripts/verificar_anonimizacion.py`.

**Otros formatos.** Los datasets de investigación suelen convertir el DICOM a
**NIfTI** (`.nii.gz`: un solo archivo con el volumen y una matriz que da el espaciado
y la orientación), **MHA** o **GIPL**. Estos formatos no guardan datos del paciente.
ToothFairy3 usa NIfTI y la muestra de Slicer usa GIPL ([datasets.md](datasets.md)).

## 3. Anatomía mínima

En un diente, de afuera hacia adentro (los porcentajes de mineral son valores de
texto de histología dental; las densidades medidas están en [4]):

| Estructura | Qué es | Densidad relativa |
|---|---|---|
| **Esmalte** | Capa externa de la corona (la parte visible del diente). Es el tejido más mineralizado del cuerpo (~96 % mineral en peso) | La **más alta** |
| **Dentina** | Cuerpo del diente, debajo del esmalte y en la raíz (~70 % mineral) | Alta, menor que el esmalte |
| **Pulpa** | Cavidad central con nervios y vasos (tejido blando) | Baja, parecida al tejido blando |
| **Cemento** | Capa delgada que cubre la raíz | Parecida al hueso; casi no se distingue en CBCT |
| **Ligamento periodontal** | Espacio delgado entre la raíz y el hueso | Baja; se ve como una línea oscura |

En los maxilares (la mandíbula abajo y el maxilar arriba):

| Estructura | Qué es | Densidad relativa |
|---|---|---|
| **Hueso cortical** | Capa externa compacta del hueso | Alta; puede acercarse a la dentina |
| **Hueso trabecular (esponjoso)** | Interior del hueso, en forma de red | Media; varía mucho según la zona |
| **Conducto alveolar inferior** | Canal dentro de la mandíbula por donde pasa el nervio | Baja; ToothFairy lo etiqueta |
| **Seno maxilar** | Cavidad con aire encima de los molares superiores | Muy baja (aire) |

El orden de densidad es:

**aire < tejido blando ≈ pulpa < hueso trabecular < hueso cortical ≈ dentina < esmalte < metal**

Hay **solapamiento** entre hueso cortical y dentina, y entre esmalte y algunos
materiales de restauración. Por eso un umbral único no aísla perfectamente una
estructura ([densidades.md](densidades.md)).

## 4. Unidades Hounsfield y por qué el CBCT no está calibrado

En el CT médico, cada vóxel se expresa en **unidades Hounsfield (HU)**, una escala
lineal del coeficiente de atenuación μ, referida al agua y al aire:

```
HU = 1000 × (μ − μ_agua) / (μ_agua − μ_aire)
```

Así, en cualquier tomógrafo calibrado el **agua vale 0 HU** y el **aire −1000 HU**.
El hueso tiene valores positivos de cientos a más de mil, y el esmalte pasa de 2000
([densidades.md §3](densidades.md#3-lo-que-dice-la-literatura-valores-en-hu)).

En el CBCT los equipos también entregan números (a veces llamados "HU"), pero **no son
comparables entre equipos** [6, 7, 8, 9], porque:

- la geometría de haz cónico produce **mucha más radiación dispersa**;
- el **campo de visión** limitado deja tejido por fuera que también atenúa
  (truncamiento);
- el **endurecimiento del haz** y la reconstrucción FDK aproximada cambian el valor
  según la **posición** del objeto dentro del campo de visión;
- cada fabricante aplica sus propias correcciones.

La evidencia principal:

- **Pauwels et al. (2013)** escanearon el mismo objeto de prueba (fantoma) en **13
  equipos CBCT** y un CT médico. La correlación con el CT era razonable, pero los
  errores eran grandes al usar los grises como medida [7].
- **Pauwels et al. (2015)**, revisión en *Dentomaxillofacial Radiology*: por ahora
  **se debe evitar el uso cuantitativo de los grises del CBCT**, por limitaciones
  propias de la técnica (campo pequeño, mucha dispersión y algoritmos de
  reconstrucción) [6].
- **Mah, Reeves y McDavid (2010)** propusieron convertir los grises a HU con un objeto
  de referencia y una regresión lineal; funciona, pero hay que calibrar cada
  equipo [8].
- **Ruiz-Imbert y Cascante-Sequeira (2021)**, revisión en español: los valores de gris
  dependen de factores técnicos, varían entre equipos y **no deben extrapolarse de un
  equipo a otro** [9].

**Lo comprobamos con datos.** La muestra CBCT dental de 3D Slicer tiene valores de 0 a
3874, con el aire en 0 y no en −1000: sus números no son HU. Un umbral de "2000 para
esmalte" ahí solo muestra los brackets de metal
([densidades.md §4](densidades.md#4-rangos-medidos-en-la-muestra-de-3d-slicer)).

**Consecuencia para el proyecto.** ToothFairy3 entrega sus volúmenes en escala
Hounsfield (normalizada por los autores) [5], así que dentro de ese dataset un umbral
fijo sí tiene sentido. Para otros equipos los presets deben ser **relativos a cada
estudio** (por ejemplo, percentiles del histograma). Es una conclusión que el informe
presenta como resultado.

## 5. Umbralización

**Umbralizar** es decidir, vóxel por vóxel, si pertenece o no a una estructura,
comparando su densidad con un valor límite:

```
visible(v) = densidad(v) ≥ umbral                  # umbral simple
visible(v) = mínimo ≤ densidad(v) ≤ máximo         # rango
```

- Es el método de segmentación (separar estructuras) más simple y rápido, y una
  persona lo puede controlar con una barra. Es la "barra de sensibilidad" de la
  propuesta.
- **Limitaciones:** no usa la forma ni los vecinos del vóxel. Por eso el ruido genera
  pedazos sueltos, y las estructuras con densidades solapadas no se separan con un
  solo número.
- **Cómo elegir el umbral:**
  - con la literatura (rangos en HU);
  - leyendo los **picos del histograma**, el gráfico de cuántos vóxeles hay de cada
    densidad;
  - automáticamente con el método de **Otsu** [10], que elige el umbral que mejor
    separa dos grupos del histograma; su versión multinivel separa varios grupos.
    En nuestra prueba, Otsu separó bien aire, piel y tejido blando, pero no los
    dientes, porque son menos del 1 % de los vóxeles;
  - con **percentiles altos** (por ejemplo, el valor que supera el 99.9 % de los
    vóxeles), que sí funcionaron para hueso y dientes.

El proyecto combina estas formas: la literatura como punto de partida, el histograma
para ajustar en cada estudio y las etiquetas de ToothFairy3 para comprobar.

## 6. Ventana / nivel (visor 2D)

Una pantalla muestra unos 256 tonos de gris, pero el volumen tiene miles de valores.
La **ventana** elige qué parte del rango se muestra:

```
mínimo = centro − ancho / 2,   máximo = centro + ancho / 2
```

Lo que está por debajo se ve negro y lo que está por encima, blanco. Una ventana
estrecha y alta sirve para distinguir **esmalte de dentina**; una ancha, para ver
todo el maxilar. Es lo que hace `aplicar_ventana()` en `src/visor_cortes.py` (rama
`feat/visor-contraste`).

## 7. Marching cubes: de un volumen a una superficie 3D

Para dibujar lo que pasa el umbral se construye una **isosuperficie**: la superficie
donde la densidad es exactamente igual al umbral, como las curvas de nivel de un
mapa pero en 3D. El algoritmo clásico es **marching cubes** (Lorensen y Cline, 1987)
[11]:

1. Se recorre el volumen tomando **cubos de 8 vóxeles vecinos** ("marchando" cubo por
   cubo).
2. Cada esquina queda **adentro** (≥ umbral) o **afuera** (< umbral). Con 8 esquinas
   hay 2⁸ = **256 casos**, que por simetría se reducen a **15 configuraciones**
   básicas.
3. Una **tabla** dice, para cada caso, qué triángulos poner dentro del cubo.
4. La posición exacta de cada vértice sobre una arista se calcula por
   **interpolación lineal** entre las densidades de las dos esquinas. Por eso la
   superficie queda más suave que si se dibujaran cubitos.
5. La **normal** de cada vértice (la dirección hacia "afuera", necesaria para la
   iluminación) se estima con el **gradiente** de la densidad.

El resultado es una **malla de triángulos** que se puede rotar, iluminar y exportar a
STL. En el proyecto lo hace `malla.contour([umbral])` de PyVista/VTK, que permite
elegir el algoritmo: `"contour"` (por defecto), `"marching_cubes"` o
`"flying_edges"`, una versión moderna y multihilo [14].

Algunas configuraciones del cubo son **ambiguas**: admiten dos triangulaciones y, si
se elige mal, quedan agujeros. Variantes posteriores del algoritmo y las
implementaciones actuales lo resuelven.

**Alternativa: renderizado volumétrico directo.** En lugar de construir una
superficie, se lanzan rayos a través del volumen y se acumulan color y opacidad según
una *función de transferencia* (densidad → color y opacidad). Permite ver varias
estructuras semitransparentes a la vez, pero no produce una malla exportable. En
PyVista es `add_volume`.

## 8. Iluminación y sombreado

La forma 3D se percibe por cómo cambia la luz sobre la superficie, y eso depende de
las **normales**.

**Modelo de iluminación de Phong** [12]: el color de un punto es la suma de tres
términos:

```
color = ambiente + difusa · (N · L) + especular · (R · V)^n
```

- **Ambiente:** luz de base, igual en todo el objeto.
- **Difusa (Lambert):** depende del ángulo entre la normal **N** y la dirección de la
  luz **L**. Las caras que miran a la luz son más claras. Es la que da la forma.
- **Especular:** el brillo; depende de la dirección **V** desde la que se mira. El
  exponente *n* controla qué tan concentrado es.

**Dónde se evalúa ese modelo** (interpolación del sombreado):

| Técnica | Cómo funciona | Resultado |
|---|---|---|
| **Plano (flat)** | Una normal por triángulo | Se ven las facetas |
| **Gouraud** (1971) [13] | Luz calculada en los vértices; los colores se interpolan dentro del triángulo | Barato, pero los brillos pequeños se pierden |
| **Phong** (1975) [12] | Se interpolan las normales y la luz se calcula en cada píxel | Brillos nítidos; marca bien curvaturas finas como raíces o irregularidades del hueso |

`render_3d.py` usa `smooth_shading=True`, que en PyVista es **sombreado Phong**.

**Efectos de luz global** que ayudan a percibir la profundidad:

- **Sombras:** una estructura oscurece a otra.
- **Oclusión ambiental (SSAO):** oscurece los huecos (entre raíces, alvéolos) donde
  llega menos luz. Es barata y ayuda mucho a leer relieves.
- **Iluminación de tres puntos:** luz principal, de relleno y de contraluz.

## 9. Suavizado de mallas

La superficie sale **escalonada** porque el volumen está muestreado en una rejilla
de vóxeles y tiene ruido. Se puede suavizar en tres momentos:

1. **Antes de extraer la superficie:** filtrar el volumen (filtro gaussiano o de
   mediana) para quitar ruido.
2. **Sobre la malla:**
   - **Laplaciano:** cada vértice se mueve al promedio de sus vecinos. Suaviza, pero
     **encoge** el objeto. Medido en nuestra prueba: −10 % de volumen.
   - **Taubin** [15]: un filtro "pasa-bajos" que quita las irregularidades pequeñas
     **sin encoger** (−1.3 % en nuestra prueba).
3. **Al dibujar:** el sombreado Phong hace que se vea continuo sin mover la geometría.

Suavizar de más borra detalles reales (bordes del esmalte, puntas de las raíces), así
que se usa el mínimo que quite el ruido.

## 10. Rendimiento: polígonos y FPS

Hay dos costos distintos:

- **Extraer la superficie** depende del número de **vóxeles** y se paga cada vez que
  cambia el umbral.
- **Dibujarla** depende del número de **triángulos** y se paga en cada cuadro mientras
  se rota.

Los **FPS** (cuadros por segundo) miden qué tan fluido se mueve el modelo; desde ~30
FPS se siente fluido. Formas de optimizar:

- **Submuestreo:** tomar 1 de cada 2 vóxeles por eje deja 1/8 de vóxeles y ~1/4 de
  triángulos, porque la superficie crece con el área. Medido: de 423 mil a 96 mil
  triángulos.
- **Recalcular solo al soltar la barra.**
- **Flying edges** en vez de marching cubes: 4–5 veces más rápido en nuestra prueba.
- **Decimación** [16]: simplificar la malla quitando triángulos donde casi no cambia
  la forma.

Detalle y tabla de tiempos en
[preguntas-clave.md](preguntas-clave.md#3-qué-impacto-tiene-en-el-rendimiento-fps-renderizar-miles-de-polígonos-y-cómo-se-optimiza).

## 11. Plano de corte (clipping plane)

Un **plano de corte** divide el espacio en dos y oculta todo lo que queda de un lado.
Como la isosuperficie es una "cáscara", al cortarla se ve por dentro. Si el umbral
está por encima de la densidad de la pulpa, **la cámara pulpar aparece como una
superficie interna** del diente. También se puede mostrar sobre el plano el corte 2D
con sus grises, uniendo las dos herramientas del proyecto. En PyVista:
`add_mesh_clip_plane` (interactivo) o `clip` (fijo).

## 12. Cómo se conecta con la pregunta de investigación

> ¿De qué manera podemos desarrollar una interfaz gráfica que transforme los datos
> volumétricos de una tomografía dental (CBCT) en un modelo 3D interactivo, aislando
> estructuras específicas según su densidad?

| Parte de la pregunta | Concepto | Módulo |
|---|---|---|
| "datos volumétricos de una tomografía" | DICOM/NIfTI → volumen `(z, y, x)` + espaciado | `carga.py` |
| "interfaz gráfica" | Visor multicorte, ventana/nivel | `visor_cortes.py` |
| "modelo 3D interactivo" | Marching cubes, iluminación, suavizado, cámara, plano de corte | `render_3d.py` |
| "aislando estructuras según su densidad" | Umbralización, histograma, presets | `densidades.py` |
| Limitación principal | Grises del CBCT no calibrados | Informe, limitaciones |

---

## Glosario

| Término | Significado |
|---|---|
| **Vóxel** | "Píxel 3D": un cubito del volumen con un valor de densidad |
| **Corte** | Una imagen 2D del volumen. **Axial**: horizontal, como mirar desde arriba. **Coronal**: de frente. **Sagital**: de lado |
| **Atenuación** | Cuánto frena un material los rayos X |
| **Hounsfield (HU)** | Escala de densidad del CT médico: agua = 0, aire = −1000 |
| **CBCT** | Tomografía de haz cónico, la tomografía dental |
| **DICOM / NIfTI / GIPL** | Formatos de archivo de imágenes médicas |
| **Espaciado** | Tamaño del vóxel en mm `(dz, dy, dx)` |
| **Umbral** | Valor de densidad a partir del cual algo se ve |
| **Histograma** | Gráfico de cuántos vóxeles hay de cada densidad |
| **Isosuperficie** | Superficie donde la densidad es igual al umbral |
| **Malla** | Conjunto de triángulos que forman la superficie 3D |
| **Normal** | Dirección perpendicular a la superficie; se usa para iluminar |
| **Marching cubes** | Algoritmo que convierte el volumen en malla |
| **Phong / Gouraud** | Formas de calcular la luz sobre la malla |
| **Taubin / Laplaciano** | Formas de suavizar la malla |
| **Decimación** | Quitar triángulos para que la malla sea más liviana |
| **FPS** | Cuadros por segundo; qué tan fluido se mueve el modelo |
| **Artefacto** | Defecto de la imagen que no es anatomía real (por ejemplo, rayas por metal) |
| **Volumen parcial** | Un vóxel del borde mezcla dos tejidos y queda con un valor intermedio |

## Referencias

1. Scarfe W.C., Farman A.G. (2008). What is cone-beam CT and how does it work?
   *Dental Clinics of North America*, 52(4), 707–730.
   https://doi.org/10.1016/j.cden.2008.05.005
2. Feldkamp L.A., Davis L.C., Kress J.W. (1984). Practical cone-beam algorithm.
   *Journal of the Optical Society of America A*, 1(6), 612–619.
3. NEMA. *DICOM Standard*. https://www.dicomstandard.org/
4. Reshetnikov A., Shaikhattarova N., Mazurok M., Kasatkina N. (2024). Dental tissue
   density in healthy children based on radiological data: retrospective analysis.
   *JMIRx Med*, 5, e56759. https://doi.org/10.2196/56759
5. ToothFairy3 dataset (Universidad de Módena y Reggio Emilia). "Format: NIfTI ·
   Scale: Hounsfield". https://ditto.ing.unimore.it/toothfairy3 (consultado el
   15/10/2026).
6. Pauwels R., Jacobs R., Singer S.R., Mupparapu M. (2015). CBCT-based bone quality
   assessment: are Hounsfield units applicable? *Dentomaxillofacial Radiology*,
   44(1), 20140238. https://doi.org/10.1259/dmfr.20140238
7. Pauwels R., Nackaerts O., Bellaiche N., et al. (2013). Variability of dental cone
   beam CT grey values for density estimations. *British Journal of Radiology*,
   86(1021), 20120135. https://doi.org/10.1259/bjr.20120135
8. Mah P., Reeves T.E., McDavid W.D. (2010). Deriving Hounsfield units using grey
   levels in cone beam computed tomography. *Dentomaxillofacial Radiology*, 39(6),
   323–335. https://doi.org/10.1259/dmfr/19603304
9. Ruiz-Imbert A.C., Cascante-Sequeira D. (2021). Valores de densidad en la escala de
   grises en tomografía computarizada de haz cónico: alcances y limitaciones.
   *Odovtos – International Journal of Dental Sciences*, 23(2).
   https://doi.org/10.15517/ijds.2021.45106
10. Otsu N. (1979). A threshold selection method from gray-level histograms. *IEEE
    Transactions on Systems, Man, and Cybernetics*, 9(1), 62–66.
11. Lorensen W.E., Cline H.E. (1987). Marching cubes: a high resolution 3D surface
    construction algorithm. *ACM SIGGRAPH Computer Graphics*, 21(4), 163–169.
    https://doi.org/10.1145/37402.37422
12. Phong B.T. (1975). Illumination for computer generated pictures. *Communications
    of the ACM*, 18(6), 311–317.
13. Gouraud H. (1971). Continuous shading of curved surfaces. *IEEE Transactions on
    Computers*, C-20(6), 623–629.
14. Schroeder W., Maynard R., Geveci B. (2015). Flying edges: a high-performance
    scalable isocontouring algorithm. *IEEE 5th Symposium on Large Data Analysis
    and Visualization (LDAV)*.
15. Taubin G. (1995). A signal processing approach to fair surface design.
    *SIGGRAPH '95*, 351–358.
16. Garland M., Heckbert P.S. (1997). Surface simplification using quadric error
    metrics. *SIGGRAPH '97*, 209–216.
