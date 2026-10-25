"""Molar ilustrativo para la portada de la página (web/modelos/molar.ply).

Uso (desde la raíz):
    python scripts/generar_molar.py

Un primer molar inferior definido como superficie implícita con proporciones anatómicas
(corona más ancha que el cuello, cinco cúspides, dos raíces aplanadas), con irregularidades
suaves para que no sea simétrico. Se convierte en malla con marching cubes (flying edges,
el mismo algoritmo del programa), se suaviza con Taubin y se colorea por vértice:
esmalte en la corona y raíz más amarilla, separadas por la línea cervical.
No usa datos de pacientes: en la página se presenta como modelo ilustrativo.
"""
import pathlib

import numpy as np
import pyvista as pv

h = 0.13
X, Y, Z = np.arange(-7.5, 7.5, h, dtype=np.float32), np.arange(-7, 7, h, dtype=np.float32), np.arange(-16, 9, h, dtype=np.float32)

def smin(a, b, k):
    t = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - t) + a * t - k * t * (1 - t)

def smax(a, b, k):
    return -smin(-a, -b, k)

rng = np.random.default_rng(7)
ONDAS = [(tuple(rng.normal(0, 1, 3) / 1.0 * f), rng.uniform(0, 6.3), a) for f, a in [(0.8, 0.10), (0.9, 0.09), (1.3, 0.06), (1.6, 0.05), (2.2, 0.03), (2.6, 0.025)]]

def campo(x, y, z):
    # Corona: secciones superelípticas cuyo ancho crece desde el cuello y cae hacia la cara oclusal.
    s = np.clip(z / 7.0, -0.35, 1)
    u = np.clip((z + 1.8) / 5.0, 0, 1)
    a = 3.6 + 1.85 * u * u * (3 - 2 * u) - 0.9 * np.clip((z - 3.6) / 3.0, 0, 1) ** 2         # mesiodistal
    b = 0.93 * a                                              # vestibulolingual
    n = 2.4
    d2 = ((np.abs(x) / a) ** n + (np.abs(y) / b) ** n) ** (1 / n) - 1
    d2 *= np.minimum(a, b)
    # Cara oclusal: cinco cúspides (tres vestibulares, dos linguales) y los surcos entre ellas.
    techo = np.full_like(x, 5.0)
    for cx, cy, alto in [(-3.0, -2.3, 1.35), (0.1, -2.7, 1.25), (3.1, -2.0, 1.05), (-2.4, 2.4, 1.6), (2.5, 2.5, 1.5)]:
        techo += alto * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 1.75 ** 2))
    techo -= 0.7 * np.exp(-(y + 0.25 * np.sin(x * 0.9)) ** 2 / (2 * 0.65 ** 2)) * np.exp(-(x / 4.2) ** 6)
    for gx in (-1.3, 1.4):
        techo -= 0.4 * np.exp(-(x - gx) ** 2 / (2 * 0.5 ** 2)) * np.exp(-(y / 3.2) ** 6)
    corona = smax(smax(d2, z - techo, 1.7), -(z + 0.6), 1.6)

    # Raíces mesial y distal: aplanadas, separadas desde el tronco y curvadas hacia distal.
    def raiz(signo, largo):
        t = np.clip(-z / largo, 0, 1)
        cx = signo * (1.45 + (2.2 if signo < 0 else 1.6) * t ** 0.9) + (1.3 if signo < 0 else 0.5) * t ** 2
        perfil = np.sqrt(np.clip(1 - t ** 3, 0, 1))
        wmd = 2.1 * perfil * (1 - 0.45 * t) + 0.03
        wbl = 3.5 * perfil * (1 - 0.55 * t) + 0.03
        d = np.sqrt(((x - cx) / wmd) ** 2 + (y / wbl) ** 2) - 1
        return smax(d * np.minimum(wmd, 1.0), -z - largo, 0.2)
    raices = smin(raiz(-1, 14.0), raiz(1, 12.6), 1.2)
    raices = smax(raices, z - 1.0, 0.8)
    forma = smin(corona, raices, 1.3)
    # Irregularidades suaves (ningún diente real es simétrico): suma de ondas de baja frecuencia.
    for (kx, ky, kz), fase, amp in ONDAS:
        forma += amp * np.sin(kx * x + ky * y + kz * z + fase)
    return forma

forma = np.empty((len(X), len(Y), len(Z)), np.float32)
for k0 in range(0, len(Z), 24):
    x, y, z = np.meshgrid(X, Y, Z[k0:k0 + 24], indexing='ij')
    forma[:, :, k0:k0 + 24] = campo(x, y, z)   # por bloques: menos memoria

img = pv.ImageData(dimensions=forma.shape, spacing=(h, h, h), origin=(-7.5, -7, -16))
img.point_data["d"] = forma.ravel(order="F")
malla = img.contour([0.0], scalars="d", method="flying_edges").clean().connectivity("largest")
malla = malla.smooth_taubin(n_iter=120, pass_band=0.02).decimate(0.5).smooth_taubin(n_iter=30, pass_band=0.05).compute_normals(auto_orient_normals=True)
print("triangulos", malla.n_cells, malla.bounds)

WEB = pathlib.Path(__file__).resolve().parents[1] / "web" / "modelos"
malla.point_data.clear(); malla.cell_data.clear()
p = malla.points
cervical = -0.3 + 0.9 * np.cos(2 * np.arctan2(p[:, 1], p[:, 0])) ** 2      # sube hacia las caras proximales
w = np.clip((p[:, 2] - cervical) / 1.4 + 0.5, 0, 1)[:, None]
w = w * w * (3 - 2 * w)               # 1 = corona, 0 = raíz
esmalte = np.array([232, 227, 214]) + np.clip(p[:, 2:3] - 4, 0, 3) * 2      # más claro hacia las cúspides
raiz = np.array([224, 210, 182]) - np.clip(-p[:, 2:3] - 6, 0, 8) * 2.5     # más amarilla hacia la punta
malla.point_data["colores"] = np.clip(w * esmalte + (1 - w) * raiz, 0, 255).astype(np.uint8)
malla.save(WEB / "molar.ply", binary=True, texture="colores")
print("ok", (WEB / "molar.ply").stat().st_size)
