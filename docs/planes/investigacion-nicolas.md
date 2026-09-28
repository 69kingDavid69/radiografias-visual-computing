# Plan de construcción — Nicolás (investigación y datos)

**Soy dueño de:** los datasets, `docs/investigacion/`, los rangos de densidad
(junto con Emanuel), las pruebas con usuarios y el informe final.
**Entrego a:** David (datos para cargar) y Emanuel (rangos de densidad).
**Estoy en la ruta crítica:** sin dataset, el equipo no puede pasar de la fase 0.
La fase 0 es la tarea más urgente del proyecto.

---

## Fase 0 — Dataset candidato (lo antes posible)
Crear `docs/investigacion/datasets.md` con una tabla de 2–3 candidatos (por
ejemplo ToothFairy, ToothFairy2, CTooth u otros de repositorios académicos):

| Columna | Qué anotar |
|---|---|
| Nombre y enlace | Página oficial |
| Tipo | ¿Es CBCT **dental**? (no sirve un CT de cráneo genérico) |
| Formato | **DICOM, NIfTI o .npy**. Si no es DICOM, avisarle a David ese día. |
| Licencia | ¿Permite uso académico? ¿Pide citar? |
| Acceso | ¿Descarga libre o registro/aprobación? ¿Cuánto tarda? |
| Anonimizado | ¿Lo declaran? |
| Tamaño | GB totales y tamaño de un estudio |

Recomendar uno y pedir acceso de inmediato si requiere registro.

**Hecho cuando:** el equipo elige dataset en la reunión semanal.

## Fase 1 — Datos disponibles para el equipo
1. Descargar 3–5 estudios y compartirlos por Drive o OneDrive, **nunca por GitHub**.
2. Verificar la anonimización. David deja un script que lista las etiquetas
   `PatientName`, `PatientID` y `PatientBirthDate` de cada archivo; todas deben
   estar vacías o anonimizadas.
3. Anotar por estudio: equipo, número de cortes y tamaño del vóxel. Eso sirve
   para detectar casos raros.
4. Empezar el **marco teórico** en `docs/investigacion/marco-teorico.md`:
   - qué es un CBCT y en qué se diferencia de un CT médico;
   - el formato DICOM (qué es un corte, el reescalado y el espaciado);
   - la anatomía mínima: esmalte, dentina, pulpa, hueso cortical y trabecular.

**Hecho cuando:** los tres devs tienen los estudios en su `data/raw/`.

## Fase 2 — Rangos de densidad (con Emanuel)
1. Buscar en la literatura (PubMed, Google Scholar) los valores de densidad de
   hueso y esmalte en CBCT, y **por qué el CBCT no está calibrado en Hounsfield**.
   Guardar las citas.
2. Con Emanuel, leer el histograma de cada estudio y proponer los rangos de
   `RANGOS_DENSIDAD`.
3. Documentar en `docs/investigacion/densidades.md`: rango elegido → fuente o
   evidencia del histograma → captura de cómo se ve.
4. Agregar al marco teórico: umbralización y marching cubes, explicados en palabras.

**Hecho cuando:** cada preset tiene un rango justificado con fuente o con datos.

## Fase 3 — Pruebas con usuarios
1. Guion de prueba con 4–5 tareas, por ejemplo: "abre el estudio", "encuentra
   el corte donde se ve la raíz de un molar", "deja visible solo el esmalte",
   "rota el modelo para ver la mandíbula desde abajo".
2. Probar con 3 personas que no hayan construido la app (idealmente de salud:
   odontología o medicina).
3. Registrar tiempo por tarea, dónde se confundieron y comentarios, en
   `docs/investigacion/pruebas-usuarios.md`, y crear un issue en GitHub por cada
   problema encontrado.

**Hecho cuando:** los hallazgos están escritos y los issues asignados a Juan o Emanuel.

## Fase 4 — Informe y demo
- [ ] Estructura: pregunta de investigación → marco teórico → método → resultados
  (capturas, tiempos, pruebas con usuarios) → limitaciones → conclusión.
- [ ] Integrar las secciones técnicas que escriba cada dev.
- [ ] La conclusión debe **responder la pregunta de investigación**.
- [ ] Abrir y cerrar la demo: contexto clínico y conclusiones.
