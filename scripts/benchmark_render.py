"""Script de benchmark para medir el rendimiento de render_3d con diferentes reducciones."""
import argparse
import csv
from pathlib import Path
import time

import numpy as np

from src.carga import cargar_serie_dicom
from src.render_3d import a_pyvista

def medir_reduccion(volumen, espaciado, reduccion, umbral):
    """Mide el tiempo que tarda en generar la malla y cuenta los triángulos."""
    
    # 1. Medir el tiempo de preparación de la malla PyVista con time.perf_counter()
    # que es el reloj de mayor precisión que tiene python

    t0 = time.perf_counter()
    #registra el valor del contador antes de comenzar la tarea pesada
    malla = a_pyvista(volumen, espaciado, reduccion=reduccion)
    tiempo_malla = time.perf_counter() - t0

    # 2. Medir el tiempo de Marching Cubes (contour)
    
    #Registra el valor del contador en el instante en que terminó la tarea.
    t1 = time.perf_counter()
    superficie = malla.contour([umbral], scalars="densidad")
    tiempo_contour = time.perf_counter() - t1

    return {
        # Factor de submuestreo evaluado (1, 2 o 4)
        "reduccion": reduccion,

        # Tamaño de la cuadrícula tridimensional en orden (Z x Y x X)
        "dimensiones": f"{malla.dimensions[2]}x{malla.dimensions[1]}x{malla.dimensions[0]}",

        # Cantidad total de vóxeles que quedaron en la cuadrícula
        "voxeles": malla.n_points,

        # Tiempo (s) en preparar la estructura volumétrica en PyVista
        "tiempo_malla_s": round(tiempo_malla, 4),

        # Tiempo (s) del algoritmo Marching Cubes para calcular la superficie
        "tiempo_contour_s": round(tiempo_contour, 4),

        # Tiempo total acumulado de procesamiento (malla + Marching Cubes)
        "tiempo_total_s": round(tiempo_malla + tiempo_contour, 4),

        # Número de triángulos en la malla 3D (carga geométrica para la GPU)
        "triangulos": superficie.n_cells,

        # Número de vértices 3D que componen esos triángulos
        "puntos": superficie.n_points,
    }


def main():
    # 1. Configurar argumentos de consola (nargs='?' permite ejecutar sin pasar ruta obligatoria)
    parser = argparse.ArgumentParser(description="Benchmark de render 3D con reducciones 1, 2 y 4")
    parser.add_argument("carpeta", nargs="?", default="data/raw/muestra_sintetica",
                        help="Ruta a la carpeta DICOM (por defecto: data/raw/muestra_sintetica)")
    parser.add_argument("--salida", default="results/tiempos.csv",
                        help="Ruta del CSV de salida (por defecto: results/tiempos.csv)")
    args = parser.parse_args()

    # 2. Cargar el volumen médico y su espaciado en milímetros
    print(f"\n Cargando estudio desde: {args.carpeta}")
    volumen, espaciado = cargar_serie_dicom(args.carpeta)
    print(f"   Volumen {volumen.shape} (z, y, x), vóxel {espaciado} mm")

    # 3. Umbral de prueba: tomamos el 60% del rango de densidad para simular estructura ósea
    minimo, maximo = float(np.min(volumen)), float(np.max(volumen))
    umbral = minimo + 0.6 * (maximo - minimo)
    print(f"   Umbral de densidad seleccionado: {umbral:.1f}\n")

    # 4. Medir sistemáticamente los tres niveles de reducción exigidos en el plan
    resultados = []
    print("Ejecutando benchmark...")
    for r in [1, 2, 4]:
        print(f"   -> Evaluando reducción = {r} ...")
        res = medir_reduccion(volumen, espaciado, reduccion=r, umbral=umbral)
        resultados.append(res)

    # 5. Asegurar que la carpeta 'results/' exista para evitar errores al guardar
    ruta_salida = Path(args.salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # 6. Escribir los resultados en CSV usando las claves del diccionario como encabezados
    with open(ruta_salida, mode="w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=resultados[0].keys())
        escritor.writeheader()
        escritor.writerows(resultados)

    print(f"\n Resultados guardados exitosamente en: {ruta_salida}")

    # 7. Imprimir tabla formateada en consola para visualización inmediata
    print("\n" + "=" * 75)
    print(f"{'Reducción':<10} | {'Dimensiones':<15} | {'Vóxeles':<10} | {'Tiempo Total (s)':<18} | {'Triángulos':<12}")
    print("=" * 75)
    for r in resultados:
        print(f"{r['reduccion']:<10} | {r['dimensiones']:<15} | {r['voxeles']:<10} | {r['tiempo_total_s']:<18.4f} | {r['triangulos']:<12}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
