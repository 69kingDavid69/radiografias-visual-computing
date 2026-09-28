# Plan de construcción — David (Dev 1: datos y pipeline)

**Soy dueño de:** `src/carga.py`, `src/filtros.py`, `src/main.py`, `tests/`, la integración
final y la revisión de PRs.
**Entrego a:** Juan y Emanuel, que consumen el volumen que yo cargo.
**Dependo de:** Nicolás, que consigue el dataset.

## Contrato que expongo (fijarlo en la fase 1 y no cambiarlo sin avisar)

```python
@dataclass
class Estudio:
    id: str                      # nombre de la carpeta
    volumen: np.ndarray          # float32 (z, y, x)
    espaciado: tuple             # (dz, dy, dx) en mm
    metadatos: dict              # equipo, fecha, n_cortes… (sin datos del paciente)

def cargar_estudio(carpeta: str, usar_cache: bool = True) -> Estudio: ...
```

Juan y Emanuel solo usan `Estudio`, nunca `pydicom` directamente.

---

## Fase 0 — Vertical slice
- [x] Repo, `.gitignore`, esqueleto de los tres módulos.
- [x] Prueba con esfera sintética y `CT_small.dcm`.
- [ ] Mandar invitaciones del repo y acompañar a cada uno a correr el proyecto.
- [ ] Proteger `main` en GitHub: solo se entra por PR con una aprobación.

**Hecho cuando:** Juan y Emanuel ejecutan `--modo 3d` en sus computadores.

## Fase 1 — Datos reales · rama `feat/estudio`
1. Crear el dataclass `Estudio` y `cargar_estudio()` en `carga.py`, que envuelva a
   `cargar_serie_dicom()`.
2. **Espaciado en z:** calcularlo con *todas* las diferencias entre cortes
   consecutivos, no solo las dos primeras. Si no son uniformes (faltan cortes),
   lanzar una advertencia.
3. **Multiframe:** leer el espaciado desde
   `SharedFunctionalGroupsSequence[0].PixelMeasuresSequence[0]`
   (`SliceThickness` / `SpacingBetweenSlices`) cuando exista.
4. **Orientación:** revisar `ImageOrientationPatient`. Si el estudio no es axial
   puro, documentarlo como limitación. No reorientar todavía.
5. **Formato:** si Nicolás confirma que el dataset viene en NIfTI (`.nii.gz`) o
   `.npy` en vez de DICOM, agregar `cargar_nifti()` con `nibabel` y que
   `cargar_estudio()` decida por la extensión.
6. **Caché:** guardar `data/processed/<id>.npz` (volumen y espaciado) y leerlo si
   existe. El primer arranque es lento y los siguientes deben ser casi instantáneos.
7. **Tests** en `tests/test_carga.py` con `pytest`:
   - esfera sintética → forma y espaciado correctos;
   - `CT_small.dcm` → reescalado a densidad (mínimo ≈ −896);
   - carpeta vacía → `FileNotFoundError`.

**Hecho cuando:** un estudio real del dataset carga con espaciado correcto, la
segunda carga usa la caché y `pytest` pasa.

## Fase 2 — Filtro de ruido · rama `feat/filtros`
1. `src/filtros.py`: `suavizar(volumen, metodo="gauss"|"mediana", intensidad)`
   con `scipy.ndimage` o `skimage.filters`.
2. Medir con Emanuel cuántos "pedacitos sueltos" quita el filtro en el render
   (número de regiones conectadas de la superficie, antes y después).
3. Opción `--suavizar` en `main.py`.

**Hecho cuando:** el render del hueso con filtro se ve continuo y el tiempo
extra es menor a 2 s por estudio.

## Fase 3 — Integración · rama `feat/app`
1. Con Juan: el botón "Abrir estudio" llama a `cargar_estudio()` en un hilo
   (`QThread`) para no congelar la ventana, y muestra una barra de progreso.
2. `main.py` pasa a lanzar la app unificada. El modo CLI queda como
   `--modo cortes|3d` para depurar.
3. Revisar los PRs de fase 3 y resolver conflictos de integración.

**Hecho cuando:** `python -m src.main` abre la ventana sin argumentos.

## Fase 4 — Cierre
- [ ] README final con capturas y requisitos.
- [ ] Etiqueta `v1.0` en GitHub.
- [ ] Sección técnica del informe: carga DICOM, reescalado y espaciado.
