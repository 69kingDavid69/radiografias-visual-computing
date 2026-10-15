# Pruebas con usuarios

> **Para qué sirve en el proyecto.** La pregunta de investigación habla de una
> *interfaz gráfica*. Este protocolo comprueba si una persona que **no construyó la
> aplicación** puede explorar un CBCT en 2D y 3D y aislar estructuras por densidad.
> Sus resultados van a la sección "Resultados" del [informe](informe.md), y los
> problemas encontrados se vuelven issues para el visor 2D y la vista 3D. Se aplica
> en la Fase 3 del [ROADMAP](../ROADMAP.md), cuando exista la ventana unificada.

## Participantes

- **3 personas** que no hayan construido la aplicación: idealmente dos estudiantes
  de odontología o medicina y una de otra carrera, para comparar.
- Registrar solo: código (P1, P2, P3), carrera y semestre, y si han visto
  tomografías antes. **No guardar nombres** en el repositorio.

## Preparación

- [ ] Computador con la app de la Fase 3 y **un estudio ya en `data/raw/`**
      (ToothFairy3, con molares completos y sin implantes, para que las tareas
      tengan solución).
- [ ] Cronómetro, este guion impreso y la plantilla de registro.
- [ ] Antes de cada sesión: cerrar la app y reiniciar la cámara 3D.
- [ ] Hacer una **sesión piloto** con alguien del equipo para ajustar los tiempos.

## Consentimiento (leer en voz alta)

> "Estamos probando una aplicación, no a ti. Si algo no te sale, es un problema de
> la aplicación y nos sirve mucho saberlo. Te pediremos hacer cinco tareas y que
> pienses en voz alta mientras las haces. La imagen es una tomografía anónima de un
> dataset público. No grabamos video ni guardamos tu nombre. Puedes parar cuando
> quieras. ¿Estás de acuerdo?"

## Tareas

Se leen una por una. No se explica cómo hacerlas. **Tiempo máximo: 3 minutos** por
tarea. Si se pasa del tiempo, se marca como no completada y se sigue.

| # | Tarea (lo que se le dice) | Se completa cuando… | Qué evalúa |
|---|---|---|---|
| 1 | "Abre el estudio que está en la carpeta `data/raw/…`." | Se ven los cortes 2D y el modelo 3D | Selector de estudio |
| 2 | "Encuentra el corte donde se ve la **raíz de un molar** inferior." | Señala una raíz de molar en el visor 2D | Deslizador de cortes, vistas ortogonales |
| 3 | "Ajusta el contraste para que se distinga el **esmalte** de la **dentina**." | El esmalte se ve claramente más brillante que la dentina | Ventana/nivel |
| 4 | "Deja visible **solo el esmalte** en el modelo 3D." | Solo se ven las coronas | Barra de umbral / presets |
| 5 | "Rota el modelo para ver la **mandíbula desde abajo**." | La vista muestra la base de la mandíbula | Cámara 3D |

## Qué registrar por tarea

- **Éxito:** sí / con ayuda / no.
- **Tiempo** en segundos.
- **Errores o confusiones:** dónde hizo clic primero, qué buscó y no encontró, qué dijo en voz alta.
- **Cita textual** útil para el informe (opcional).

## Cuestionario final: SUS (System Usability Scale)

Escala estándar de usabilidad de 10 preguntas (Brooke, 1996). Respuesta del 1
(totalmente en desacuerdo) al 5 (totalmente de acuerdo).

1. Creo que me gustaría usar esta aplicación con frecuencia.
2. Encontré la aplicación innecesariamente compleja.
3. Pensé que la aplicación era fácil de usar.
4. Creo que necesitaría ayuda de una persona técnica para poder usar esta aplicación.
5. Encontré que las funciones de la aplicación estaban bien integradas.
6. Pensé que había demasiada inconsistencia en la aplicación.
7. Imagino que la mayoría de las personas aprendería a usar esta aplicación muy rápido.
8. Encontré la aplicación muy engorrosa de usar.
9. Me sentí muy seguro(a) usando la aplicación.
10. Necesité aprender muchas cosas antes de poder empezar con esta aplicación.

**Cálculo:** a las preguntas impares se les resta 1; a las pares se les resta su
valor de 5. Se suman los 10 resultados y se multiplica por 2.5, lo que da un
puntaje de 0 a 100. Como referencia habitual, un puntaje **≥ 68** se considera
por encima del promedio.

**Preguntas abiertas:**

- ¿Qué fue lo más difícil?
- ¿Para qué te serviría esto en tu carrera?
- ¿Qué le agregarías?

## Plantilla de registro

| Participante | Perfil | T1 | T2 | T3 | T4 | T5 | SUS | Observaciones principales |
|---|---|---|---|---|---|---|---|---|
| P1 | | ✔/~/✘ · s | | | | | | |
| P2 | | | | | | | | |
| P3 | | | | | | | | |

## Después de las pruebas

1. Resumir por tarea: tasa de éxito, tiempo promedio y principales confusiones.
2. **Crear un issue en GitHub por cada problema**, con la etiqueta `usabilidad`, y
   asignarlo según el módulo: interfaz y visor 2D (Juan) o vista 3D y presets
   (Emanuel).
3. Llevar la tabla y el puntaje SUS promedio a la sección de resultados del
   [informe](informe.md).

## Referencia

- Brooke J. (1996). SUS: a "quick and dirty" usability scale. En P.W. Jordan et al.
  (eds.), *Usability Evaluation in Industry*, 189–194. Taylor & Francis.
