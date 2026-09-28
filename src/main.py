"""Punto de entrada: python -m src.main <carpeta_dicom> [--modo cortes|3d]"""
import argparse

from src.carga import cargar_serie_dicom
from src.render_3d import explorar_3d
from src.visor_cortes import explorar_cortes


def main():
    parser = argparse.ArgumentParser(description="Explorador de tomografías dentales (CBCT)")
    parser.add_argument("carpeta", help="Carpeta con los cortes DICOM del estudio")
    parser.add_argument("--modo", choices=["cortes", "3d"], default="cortes")
    parser.add_argument("--reduccion", type=int, default=2,
                        help="Submuestreo para el 3D (1 = resolución completa)")
    args = parser.parse_args()

    volumen, espaciado = cargar_serie_dicom(args.carpeta)
    print(f"Volumen {volumen.shape} (z, y, x), vóxel {espaciado} mm, "
          f"densidad de {volumen.min():.0f} a {volumen.max():.0f}")

    if args.modo == "cortes":
        explorar_cortes(volumen, espaciado)
    else:
        explorar_3d(volumen, espaciado, reduccion=args.reduccion)


if __name__ == "__main__":
    main()
