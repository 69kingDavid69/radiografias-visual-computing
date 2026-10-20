"""Punto de entrada: python -m src.main <estudio> [--modo cortes|3d]"""
import argparse

from src.carga import cargar_estudio
from src.render_3d import explorar_3d
from src.visor_cortes import explorar_cortes


def main():
    parser = argparse.ArgumentParser(description="Explorador de tomografías dentales (CBCT)")
    parser.add_argument("estudio", help="Carpeta DICOM o archivo .gipl.gz / .nii.gz / .mha / .nrrd")
    parser.add_argument("--modo", choices=["cortes", "3d"], default="cortes")
    parser.add_argument("--reduccion", type=int, default=2,
                        help="Submuestreo para el 3D (1 = resolución completa)")
    parser.add_argument("--sin-cache", action="store_true",
                        help="Releer el estudio original aunque exista data/processed/<id>.npz")
    args = parser.parse_args()

    estudio = cargar_estudio(args.estudio, usar_cache=not args.sin_cache)
    volumen, espaciado = estudio.volumen, estudio.espaciado
    minimo, maximo = estudio.metadatos["rango"]
    print(f"{estudio.id} ({estudio.metadatos['formato']}): volumen {volumen.shape} (z, y, x), "
          f"vóxel {espaciado} mm, densidad de {minimo:.0f} a {maximo:.0f}, "
          f"escala: {estudio.metadatos.get('escala') or 'desconocida (solo barra libre)'}")

    if args.modo == "cortes":
        explorar_cortes(volumen, espaciado)
    else:
        explorar_3d(volumen, espaciado, reduccion=args.reduccion)


if __name__ == "__main__":
    main()
