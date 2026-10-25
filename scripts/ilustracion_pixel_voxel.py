"""Ilustración de la portada: píxel (radiografía 2D) frente a vóxel (tomografía 3D).

Uso (desde la raíz, con la muestra en data/raw/):
    python scripts/ilustracion_pixel_voxel.py

Genera web/img/radiografia_pixeles.png y web/img/tomografia_voxeles.png con el estudio Pre:
la radiografía simulada con una ampliación donde se ven sus píxeles (cuadritos planos) y el
cubo de la tomografía con una esquina cortada (los tres cortes por dentro) y una ampliación donde se ven sus vóxeles (cubitos).
Solo cortes en gris y un bloque de diente: no se dibuja la superficie de la piel.
"""
import os, sys
from pathlib import Path
root = str(Path(__file__).resolve().parent.parent)
os.chdir(root); sys.path.insert(0, root)
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, ConnectionPatch
import pyvista as pv
from src.carga import cargar_estudio
from src.region import arcada_dental

salida = os.path.join(root, "web", "img")
ACENTO, TINTA, TINTA2 = "#38bdf8", "#e6edf3", "#a3b0bf"
GRIS_MAX = 2200                       # mismo recorte de grises que el resto de las figuras
LADO_PX = 720                         # 2× el tamaño de la tarjeta (360 px)

e = cargar_estudio("data/raw/PreDentalSurgery.gipl.gz")
v = e.volumen
dz, dy, dx = e.espaciado
nz, ny, nx = v.shape
z0, z1 = arcada_dental(v, e.espaciado, 1250)
zc = (z0 + z1) // 2                   # altura de los dientes

# Punto de la ampliación de la radiografía: esmalte en el frente de la arcada, a la altura de los dientes.
ys, xs = np.nonzero(v[zc] >= 1250)
i = np.argmin(ys)                     # el más adelante (y pequeño = frente en esta muestra)
yc, xc = int(ys[i]), int(xs[i])


def lienzo():
    fig = plt.figure(figsize=(LADO_PX / 100, LADO_PX / 100), dpi=100, facecolor="black")
    return fig


def titulo(fig, texto):
    # La tarjeta muestra la imagen a ~330 px: textos grandes; la explicación va en el pie de foto.
    fig.text(0.04, 0.96, texto, color=TINTA, fontsize=30, fontweight="bold", va="top")


# ---------------------------------------------------------------------------------------
# 1) Radiografía: proyección lateral (suma en x) y sus píxeles
proy = np.clip(v, 0, GRIS_MAX).sum(axis=2)[::-1]       # (z, y), z hacia arriba
lo, hi = np.percentile(proy, [1, 99.7])
rx = np.clip((proy - lo) / (hi - lo), 0, 1) ** 0.8

fig = lienzo()
titulo(fig, "2D · píxeles")
ax = fig.add_axes([0.0, 0.03, 0.60, 0.82])
ax.imshow(rx, cmap="gray", aspect=dz / dy, interpolation="bilinear")
ax.axis("off")
n = 8                                                   # ampliación de 8 × 8 píxeles
fila, col = nz - 1 - zc - n // 2, yc - n // 2
ax.add_patch(Rectangle((col - 0.5, fila - 0.5), n, n, fill=False, ec=ACENTO, lw=2))
zoom = fig.add_axes([0.57, 0.33, 0.41, 0.41])
bloque = rx[fila:fila + n, col:col + n]
zoom.imshow(bloque, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
for k in range(n + 1):
    zoom.axhline(k - 0.5, color="#000", lw=1.2); zoom.axvline(k - 0.5, color="#000", lw=1.2)
zoom.set_xticks([]); zoom.set_yticks([])
for s in zoom.spines.values():
    s.set_edgecolor(ACENTO); s.set_linewidth(2)
fig.add_artist(ConnectionPatch((col + n - 0.5, fila - 0.5), (-0.5, -0.5), "data", "data", axesA=ax, axesB=zoom, color=ACENTO, lw=1.2))
fig.add_artist(ConnectionPatch((col + n - 0.5, fila + n - 0.5), (-0.5, n - 0.5), "data", "data", axesA=ax, axesB=zoom, color=ACENTO, lw=1.2))
fig.text(0.775, 0.29, "1 píxel:\nun cuadrado plano", color=TINTA, fontsize=21, ha="center", va="top", linespacing=1.3)
fig.savefig(os.path.join(salida, "radiografia_pixeles.png"), facecolor="black")
plt.close(fig)

# ---------------------------------------------------------------------------------------
# 2) Tomografía: el cubo con una esquina cortada (se ven los tres cortes por dentro) y sus vóxeles
red = 2
sub = np.clip(v[::red, ::red, ::red], 0, GRIS_MAX)
cubo = pv.ImageData(dimensions=np.array(sub.shape[::-1]) + 1, spacing=(dx * red, dy * red, dz * red))
cubo.cell_data["densidad"] = sub.ravel(order="C")
X, Y, Z = nx * dx, ny * dy, nz * dz
xm, ym, zm = X / 2, Y / 2, zc * dz            # la esquina se corta hasta la altura de los dientes
cc = cubo.cell_centers().points
fuera = (cc[:, 0] > xm) & (cc[:, 1] < ym) & (cc[:, 2] > zm)   # derecha, adelante, arriba
solido = cubo.extract_cells(np.nonzero(~fuera)[0]).extract_surface(algorithm="dataset_surface")
aristas = solido.extract_feature_edges(feature_angle=45, boundary_edges=False, manifold_edges=False,
                                        non_manifold_edges=False)

# Vóxel ampliado: esmalte en el piso del corte (cara axial de los dientes, en la esquina abierta)
zs = zc - 1
cand = np.argwhere(v[zs, : ny // 2, nx // 2:] >= 1250)
yv, xv = cand[len(cand) // 2]; xv += nx // 2
punto = ((xv + 0.5) * dx, (yv + 0.5) * dy, zm)

def camara(pl):
    pl.camera.focal_point = (X / 2, Y / 2, Z / 2)
    pl.camera.position = (X * 2.2, -Y * 1.4, Z * 2.0)
    pl.camera.up = (0, 0, 1)
    pl.reset_camera()

pl = pv.Plotter(off_screen=True, window_size=(900, 900))
pl.set_background("black")
# El aire en gris oscuro (clim desde −800) para que el bloque se lea sólido; luz suave para las caras.
pl.add_mesh(solido, scalars="densidad", cmap="gray", clim=(-800, GRIS_MAX), show_scalar_bar=False,
            ambient=0.6, diffuse=0.5, specular=0)
pl.add_mesh(aristas, color=TINTA2, line_width=2)
pl.add_mesh(pv.Sphere(radius=2.2, center=punto), color=ACENTO)
camara(pl)
img_cubo = pl.screenshot(return_img=True)
ren = pl.renderer
ren.SetWorldPoint(*punto, 1.0); ren.WorldToDisplay()
px, py, _ = ren.GetDisplayPoint()
alto_img = img_cubo.shape[0]
punto_img = (px, alto_img - py)                 # coordenadas de imagen (y hacia abajo)
pl.close()

# Bloque de 6 × 6 × 6 vóxeles bajo ese punto, a resolución completa; sin un octante, para que
# se vea que son cubitos también por dentro.
m = 6
b = np.clip(v[zs - m + 1:zs + 1, yv - m // 2:yv + m // 2, xv - m // 2:xv + m // 2], 0, GRIS_MAX)
vox = pv.ImageData(dimensions=(m + 1, m + 1, m + 1), spacing=(dx, dy, dz))
vox.cell_data["densidad"] = b.ravel(order="C")
k, j_, i_ = np.meshgrid(range(m), range(m), range(m), indexing="ij")
quitar = ((k >= m // 2) & (j_ < m // 2) & (i_ >= m // 2)).ravel(order="C")
vox = vox.extract_cells(np.nonzero(~quitar)[0])
pl = pv.Plotter(off_screen=True, window_size=(600, 600))
pl.set_background("black")
pl.add_mesh(vox, scalars="densidad", cmap="gray", clim=(-800, GRIS_MAX), show_edges=True, edge_color="#0b0f14",
            line_width=2, show_scalar_bar=False, ambient=0.45, diffuse=0.6)
pl.camera.focal_point = (m * dx / 2, m * dy / 2, m * dz / 2)
pl.camera.position = (m * dx * 2.2, -m * dy * 1.4, m * dz * 2.0)
pl.camera.up = (0, 0, 1); pl.reset_camera(); pl.camera.zoom(1.1)
img_vox = pl.screenshot(return_img=True)
pl.close()

fig = lienzo()
titulo(fig, "3D · vóxeles")
ax = fig.add_axes([0.0, 0.02, 0.66, 0.82]); ax.imshow(img_cubo); ax.axis("off")
zoom = fig.add_axes([0.57, 0.33, 0.41, 0.41]); zoom.imshow(img_vox); zoom.set_xticks([]); zoom.set_yticks([])
for s in zoom.spines.values():
    s.set_edgecolor(ACENTO); s.set_linewidth(2)
n_img = img_vox.shape[0]
for esquina in ((0, 0), (0, n_img)):
    fig.add_artist(ConnectionPatch(punto_img, esquina, "data", "data", axesA=ax, axesB=zoom, color=ACENTO, lw=1.2))
fig.text(0.775, 0.29, f"1 vóxel:\nun cubo de {dx:.1f} mm".replace(".", ","), color=TINTA, fontsize=21, ha="center", va="top", linespacing=1.3)
fig.savefig(os.path.join(salida, "tomografia_voxeles.png"), facecolor="black")
plt.close(fig)
print("radiografía:", (zc, yc), "vóxel:", (zs, int(yv), int(xv)), "arcada:", (z0, z1))
