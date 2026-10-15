# Informe — Explorador de cortes tomográficos y renderizado 3D por densidad

**Borrador v0.1 (15/10/2026).** Responsable de integrarlo: Nicolás. Las secciones de
investigación están redactadas. Lo que falta está marcado así:

> ✏️ **Pendiente — Nombre:** qué hay que escribir.

Visual Computing · Universidad Nacional de Colombia, Sede Medellín · 2026-2.
Equipo: David, Juan Gómez, Emanuel Aristizábal y Nicolás. Profesor: Paluszny.
Hay que confirmar con el profesor la extensión, el formato y la fecha de entrega
(decisión abierta #8).

---

## Resumen

Una radiografía dental es una imagen plana en la que las estructuras se superponen;
una tomografía de haz cónico (CBCT) registra, en cambio, un volumen 3D de densidades.
Este trabajo desarrolla una interfaz en Python que carga un estudio CBCT, permite
recorrerlo corte a corte con control de contraste y lo reconstruye en 3D mediante una
isosuperficie (marching cubes) cuyo umbral de densidad el usuario ajusta con una
barra. Así se pueden aislar el hueso, los dientes y el esmalte. Los umbrales se
apoyan en valores publicados en unidades Hounsfield y en mediciones sobre los datos.
Con un CBCT dental real se comprobó que la reconstrucción separa hueso, dientes y
metal de ortodoncia. También se comprobó que los valores de ese equipo **no** están
en Hounsfield, así que los umbrales deben adaptarse a cada estudio.

> ✏️ **Pendiente — Nicolás:** cerrar el resumen con los resultados finales
> (ToothFairy3 y pruebas con usuarios).

## 1. Introducción

En odontología, la radiografía panorámica o periapical sigue siendo la imagen más
común, pero proyecta todo sobre un plano: las raíces, el hueso y las restauraciones
se superponen. La tomografía computarizada de haz cónico (CBCT) resuelve esto
registrando un volumen 3D de cientos de cortes, con vóxeles pequeños y una dosis de
radiación menor que la del CT médico [1]. El reto es que ese volumen es difícil de
explorar: el profesional necesita navegar los cortes y, sobre todo, ver las
estructuras en 3D sin el ruido del tejido blando.

Desde la computación gráfica, el problema reúne varios temas del curso:

- el manejo de datos volumétricos (vóxeles);
- la extracción de superficies (marching cubes);
- la iluminación para percibir profundidad;
- el rendimiento al dibujar cientos de miles de polígonos.

**Pregunta de investigación.** ¿De qué manera podemos desarrollar una interfaz gráfica
que transforme los datos volumétricos de una tomografía dental (CBCT) en un modelo 3D
interactivo, aislando estructuras específicas según su densidad?

**Objetivos:**

1. Cargar un estudio CBCT real con su tamaño de vóxel correcto.
2. Navegar el volumen en 2D (cortes axial, coronal y sagital) con control de contraste.
3. Reconstruir el volumen en 3D con un umbral de densidad ajustable, iluminación,
   suavizado y plano de corte.
4. Proponer y justificar umbrales (presets) para aislar hueso, dientes y esmalte.
5. Evaluar el rendimiento y la usabilidad de la herramienta.

## 2. Marco teórico

Versión completa, con glosario: [marco-teorico.md](marco-teorico.md). Resumen para el
informe:

**2.1 CBCT.** El CBCT usa un haz de rayos X en forma de cono y un detector plano que
giran una sola vez alrededor de la cabeza. El volumen se reconstruye normalmente con
el algoritmo FDK [2]. Frente al CT médico tiene vóxeles isotrópicos más pequeños y
menos dosis, pero más radiación dispersa, más ruido y peor contraste de tejido
blando [1].

**2.2 DICOM y espaciado.** Los equipos exportan el estudio en DICOM, normalmente un
archivo por corte [3]. Para formar el volumen hay que:

- ordenar los cortes por su posición (`ImagePositionPatient`);
- convertir los valores guardados a densidad con `RescaleSlope` y `RescaleIntercept`;
- tomar el tamaño del vóxel en mm, sin el cual el modelo 3D se deforma.

Los datasets de investigación suelen usar NIfTI o MHA, que no guardan datos del
paciente.

**2.3 Unidades Hounsfield y CBCT.** En el CT médico, la densidad se expresa en
unidades Hounsfield (HU), con el agua en 0 y el aire en −1000. En el CBCT, en cambio,
los valores de gris varían según el equipo, el campo de visión y la posición del
objeto. Pauwels et al. compararon 13 equipos y encontraron errores grandes al usar
los grises de forma cuantitativa [7]; su revisión recomienda evitar ese uso [6].
Otros trabajos proponen calibrar cada equipo con objetos de referencia [8, 9].

**2.4 Umbralización.** Aislar una estructura por densidad equivale a mostrar solo los
vóxeles cuyo valor supera un umbral. Es simple e interactivo, pero no usa la forma
ni la vecindad, así que el ruido y las densidades solapadas limitan la separación.
El umbral puede elegirse con la literatura, con el histograma o automáticamente con
Otsu [10].

**2.5 Marching cubes.** El algoritmo recorre el volumen en cubos de 8 vóxeles. Para
cada uno, según qué esquinas superan el umbral (256 casos, 15 configuraciones
básicas), coloca triángulos cuyos vértices se ubican por interpolación lineal [11].
Las normales salen del gradiente de la densidad. *Flying edges* es una variante
moderna, multihilo y más rápida [14].

**2.6 Iluminación, suavizado y rendimiento.**

- **Iluminación:** el modelo de Phong (ambiente + difusa + especular), evaluado por
  píxel con normales interpoladas (sombreado Phong) [12], resalta mejor las
  curvaturas finas que el sombreado Gouraud [13].
- **Suavizado:** el filtro de Taubin suaviza la malla sin encogerla, a diferencia del
  Laplaciano [15].
- **Rendimiento:** el costo de dibujo crece con el número de triángulos; se reduce
  con submuestreo y decimación [16].

## 3. Datos

Detalle completo en [datasets.md](datasets.md).

Se revisaron nueve datasets CBCT dentales públicos con estos criterios: ser dental,
tener licencia académica, estar anonimizado, traer el tamaño del vóxel y tener un
formato legible. Se eligieron dos:

| Dataset | Uso | Características |
|---|---|---|
| Muestra CBCT dental de 3D Slicer (`PreDentalSurgery`) [22] | Desarrollo, demo y prueba de la limitación del CBCT | 1 volumen de 360×360×330 vóxeles de 0.5 mm, formato GIPL, valores de 0 a 3874 (no HU) |
| ToothFairy3 [5] | Resultados y validación de los rangos en HU | 532 volúmenes NIfTI de 0.3 mm en Hounsfield, con 77 etiquetas por estructura (maxilares, dientes, pulpas, conductos) |

Se descartaron PhysioNet (acceso restringido), CTooth (sin descarga verificable) y
STS-Tooth (pierde el tamaño del vóxel). El dataset DICOM de ScienceDB, con tres
equipos distintos, quedó como opcional.

Ningún dato médico se sube al repositorio. La anonimización se verifica con
`scripts/verificar_anonimizacion.py`, y no se publica la reconstrucción de la piel,
porque muestra la cara del paciente.

> ✏️ **Pendiente — Nicolás:** tabla de los 3–5 estudios de ToothFairy3 usados
> (salida de `verificar_anonimizacion.py --csv`).

## 4. Método

### 4.1 Arquitectura

Aplicación de escritorio en Python, sin servidor ni red: los datos no salen del
computador. Flujo:

1. lectura del estudio;
2. volumen `(z, y, x)` con su espaciado en mm;
3. visor 2D (matplotlib) y vista 3D (PyVista/VTK).

Ver el diagrama en [ARCHITECTURE.md](../ARCHITECTURE.md).

> ✏️ **Pendiente — David:** carga DICOM/NIfTI/GIPL, reescalado, espaciado, caché.

### 4.2 Visor 2D

> ✏️ **Pendiente — Juan:**
> - vistas axial, coronal y sagital;
> - proporción `dz/dx`;
> - ventana/nivel (`aplicar_ventana`);
> - líneas guía y clic para navegar.

### 4.3 Reconstrucción 3D

> ✏️ **Pendiente — Emanuel:**
> - `contour` y su método;
> - submuestreo;
> - iluminación (Phong, especular, SSAO);
> - suavizado Taubin;
> - plano de corte;
> - barra de umbral y presets.

### 4.4 Rangos de densidad

Detalle en [densidades.md](densidades.md). Los rangos se definieron en tres pasos:

1. **Literatura** en HU: pulpa de 184 a 420 HU; hueso trabecular de 150 a 850 HU;
   cortical por encima de 850 HU; dentina de 1323 a 1899 HU; esmalte de 2071 a
   2955 HU [4, 17, 18].
2. **Histograma** de cada estudio, con umbrales automáticos (Otsu) y percentiles
   altos.
3. **Validación visual** en el render, y con las etiquetas de ToothFairy3: percentiles
   5–95 de la densidad de cada estructura.

### 4.5 Medición de rendimiento

Se midió el tiempo de extracción de la superficie y el número de triángulos con
submuestreo 1, 2 y 4 y con los tres algoritmos de PyVista.

> ✏️ **Pendiente — Emanuel:** FPS en la ventana real.

### 4.6 Pruebas con usuarios

Tres participantes que no construyeron la aplicación, idealmente de odontología o
medicina, hacen cinco tareas (abrir el estudio, ubicar la raíz de un molar, ajustar el
contraste, aislar el esmalte, rotar el modelo). Se registran el éxito y el tiempo por
tarea y se aplica el cuestionario SUS [19]. Protocolo en
[pruebas-usuarios.md](pruebas-usuarios.md).

## 5. Resultados

### 5.1 Reconstrucción por umbral (muestra de 3D Slicer) — resultado preliminar

![Isosuperficies en cuatro umbrales](../../results/investigacion/umbrales_muestra_slicer.png)

| Umbral (unidades del equipo) | Estructuras visibles |
|---|---|
| ~400 | Piel y tejido blando (ruidoso) |
| 700 | Cráneo, maxilares y dientes |
| 1000 | Hueso denso y dientes con sus raíces |
| 1250 | Coronas, brackets y parte del hueso cortical |
| 2000 | Solo los brackets de metal |

El histograma ([figura](../../results/investigacion/histograma_muestra_slicer.png))
muestra valores de 0 a 3874, con el aire en 0. Es decir, el equipo **no** entrega
unidades Hounsfield.

### 5.2 Rendimiento — resultado preliminar

Medido con la muestra de 330×360×360 vóxeles, umbral 1000, en un Ryzen 7 5800H:

| Submuestreo | `contour` | `marching_cubes` | `flying_edges` | Triángulos |
|---|---|---|---|---|
| 1 | 0.408 s | 0.278 s | 0.086 s | ~423 000 |
| 2 | 0.053 s | 0.047 s | 0.013 s | ~96 000 |
| 4 | 0.007 s | 0.008 s | 0.002 s | ~19 500 |

- *Flying edges* fue 4–5 veces más rápido que el método por defecto.
- Con submuestreo 2, los triángulos bajaron 4.4 veces, lo esperado si la superficie
  crece con el área.

### 5.3 Suavizado — resultado preliminar

En los dientes de la muestra, el suavizado Laplaciano (300 iteraciones) redujo el
volumen encerrado por la malla un 10.4 %; el de Taubin, un 1.3 %
([figura](../../results/investigacion/sombreado_y_suavizado.png)).

> ✏️ **Pendiente:**
> - **Nicolás + Emanuel:** densidad medida por estructura en ToothFairy3 (tabla de
>   [densidades.md §5](densidades.md#5-cómo-validar-los-rangos-en-hu-con-toothfairy3-fase-2))
>   y capturas de cada preset.
> - **Juan:** capturas del visor 2D.
> - **Nicolás:** resultados de las pruebas con usuarios.

## 6. Discusión y limitaciones

1. **El CBCT no está calibrado.** La muestra de Slicer confirmó lo que reporta la
   literatura [6, 7]: sus valores no son HU, y un umbral pensado en HU para el
   esmalte (≈ 2000) ahí solo muestra el metal. Los presets en HU solo valen para
   datos normalizados como ToothFairy3; para otros equipos deben ser relativos al
   estudio (percentiles del histograma).
2. **Densidades solapadas.** El hueso cortical denso se parece a la dentina, y el
   esmalte se parece a las restauraciones y al metal [23]. En la muestra, el umbral de
   las coronas también dejó parte del hueso del cráneo. La umbralización sola no
   separa estas estructuras; haría falta segmentación por forma o aprendizaje
   automático.
3. **Artefactos de metal y volumen parcial.** El metal genera rayas y superficies
   falsas. En los bordes, un vóxel mezcla tejidos y queda con valores intermedios.
4. **Umbrales automáticos.** Otsu separó bien aire, piel y tejido blando, pero no los
   dientes, que son menos del 1 % de los vóxeles. Los percentiles altos funcionaron
   mejor.
5. **Rendimiento frente a detalle.** El submuestreo hace la interacción fluida, pero
   pierde detalle fino (raíces delgadas, conductos).
6. **Muestra pequeña** de estudios y de usuarios.

## 7. Conclusión

> ✏️ **Pendiente — Nicolás:** redactar con los resultados finales. Debe **responder
> la pregunta directamente**. Borrador:

Es posible construir una interfaz que transforme un CBCT dental en un modelo 3D
interactivo y aísle estructuras por densidad combinando cuatro elementos:

1. un visor multicorte con control de contraste;
2. una isosuperficie (marching cubes / flying edges) con un umbral ajustable;
3. iluminación Phong y suavizado Taubin, para que la forma se perciba bien;
4. presets de densidad justificados con la literatura y medidos en los datos.

La principal condición es que los umbrales deben adaptarse al equipo, porque los
grises del CBCT no son unidades Hounsfield. Con datos normalizados (ToothFairy3),
los presets fijos son válidos.

**Trabajo futuro:**

- segmentación con aprendizaje automático usando las etiquetas de ToothFairy;
- renderizado volumétrico directo;
- medición de distancias en mm;
- exportación a STL para impresión 3D.

## Referencias

1. Scarfe W.C., Farman A.G. (2008). What is cone-beam CT and how does it work? *Dental Clinics of North America*, 52(4), 707–730. https://doi.org/10.1016/j.cden.2008.05.005
2. Feldkamp L.A., Davis L.C., Kress J.W. (1984). Practical cone-beam algorithm. *J. Optical Society of America A*, 1(6), 612–619.
3. NEMA. *DICOM Standard*. https://www.dicomstandard.org/
4. Reshetnikov A., Shaikhattarova N., Mazurok M., Kasatkina N. (2024). Dental tissue density in healthy children based on radiological data. *JMIRx Med*, 5, e56759. https://doi.org/10.2196/56759
5. Lumetti L., Tan Z.Q., Borghi L., et al. (2026). ToothFairy3: Scaling CBCT Maxillofacial Segmentation to 77 Classes with U-Mamba2. *MICCAI 2026*. (Citar también [20] y [21], que el dataset exige.)
6. Pauwels R., Jacobs R., Singer S.R., Mupparapu M. (2015). CBCT-based bone quality assessment: are Hounsfield units applicable? *Dentomaxillofacial Radiology*, 44(1), 20140238. https://doi.org/10.1259/dmfr.20140238
7. Pauwels R., Nackaerts O., Bellaiche N., et al. (2013). Variability of dental cone beam CT grey values for density estimations. *British Journal of Radiology*, 86(1021), 20120135. https://doi.org/10.1259/bjr.20120135
8. Mah P., Reeves T.E., McDavid W.D. (2010). Deriving Hounsfield units using grey levels in cone beam computed tomography. *Dentomaxillofacial Radiology*, 39(6), 323–335. https://doi.org/10.1259/dmfr/19603304
9. Ruiz-Imbert A.C., Cascante-Sequeira D. (2021). Valores de densidad en la escala de grises en tomografía computarizada de haz cónico: alcances y limitaciones. *Odovtos*, 23(2). https://doi.org/10.15517/ijds.2021.45106
10. Otsu N. (1979). A threshold selection method from gray-level histograms. *IEEE Trans. Systems, Man, and Cybernetics*, 9(1), 62–66.
11. Lorensen W.E., Cline H.E. (1987). Marching cubes: a high resolution 3D surface construction algorithm. *ACM SIGGRAPH Computer Graphics*, 21(4), 163–169. https://doi.org/10.1145/37402.37422
12. Phong B.T. (1975). Illumination for computer generated pictures. *Communications of the ACM*, 18(6), 311–317.
13. Gouraud H. (1971). Continuous shading of curved surfaces. *IEEE Trans. Computers*, C-20(6), 623–629.
14. Schroeder W., Maynard R., Geveci B. (2015). Flying edges: a high-performance scalable isocontouring algorithm. *IEEE LDAV 2015*.
15. Taubin G. (1995). A signal processing approach to fair surface design. *SIGGRAPH '95*, 351–358.
16. Garland M., Heckbert P.S. (1997). Surface simplification using quadric error metrics. *SIGGRAPH '97*, 209–216.
17. Misch C.E. (2008). *Contemporary Implant Dentistry* (3.ª ed.). Mosby.
18. Hiasa K., Abe Y., Okazaki Y., et al. (2011). Preoperative computed tomography-derived bone densities in Hounsfield units at implant sites acquired primary stability. *ISRN Dentistry*, 678729. https://doi.org/10.5402/2011/678729
19. Brooke J. (1996). SUS: a "quick and dirty" usability scale. En *Usability Evaluation in Industry*, 189–194. Taylor & Francis.
20. Bolelli F., Marchesini K., van Nistelrooij N., et al. (2025). Segmenting Maxillofacial Structures in CBCT Volumes. *CVPR 2025*. https://doi.org/10.1109/CVPR52734.2025.00494
21. Lumetti L., Pipoli V., Bolelli F., Ficarra E., Grana C. (2024). Enhancing Patch-Based Learning for the Segmentation of the Mandibular Canal. *IEEE Access*. https://doi.org/10.1109/ACCESS.2024.3408629
22. Fedorov A., et al. (2012). 3D Slicer as an image computing platform for the Quantitative Imaging Network. *Magnetic Resonance Imaging*, 30(9), 1323–1341. https://doi.org/10.1016/j.mri.2012.05.001 (fuente de la muestra CBCT).
23. Sakuma A., Saitoh H., Makino Y., et al. (2012). Three-dimensional visualization of composite fillings for dental identification using CT images. *Dentomaxillofacial Radiology*, 41(6), 515–519. https://doi.org/10.1259/dmfr/13441277
