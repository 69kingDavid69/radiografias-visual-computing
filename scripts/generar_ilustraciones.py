"""Ilustraciones calculadas con datos reales para la página (web/img).

Uso (desde la raíz, con la muestra en data/raw/):
    python scripts/generar_ilustraciones.py [results/calibracion_sts.csv]

Genera: radiografía simulada y corte sagital (PNG), suavizado 2D Laplaciano vs. Taubin,
recta de normalización de los estudios Pre y Post y, si existe el CSV de calibración
(scripts/calibrar_presets.py, PR #19), la gráfica del umbral óptimo de dientes.
"""
import os, sys, csv
from pathlib import Path
root = str(Path(__file__).resolve().parent.parent)
salida = os.path.join(root, "web", "img")
csv_cal = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "results", "calibracion_sts.csv")
os.chdir(root); sys.path.insert(0, root)
import numpy as np
from PIL import Image
from src.carga import cargar_estudio

TINTA, TINTA2, TINTA3, LINEA, ACENTO = "#e6edf3", "#a3b0bf", "#6f7d8c", "#2a3340", "#38bdf8"
FUENTE = 'font-family="Segoe UI, system-ui, sans-serif"'

e = cargar_estudio("data/raw/PreDentalSurgery.gipl.gz")
v = e.volumen

# 1) Radiografía simulada (proyección lateral) y un corte sagital del mismo lado.
proy = np.clip(v, 0, 2200).sum(axis=2)                 # suma a lo largo de x → vista lateral
proy = proy[::-1]                                       # z hacia arriba
p_lo, p_hi = np.percentile(proy, [1, 99.7])
img = np.clip((proy - p_lo) / (p_hi - p_lo), 0, 1) ** 0.8
Image.fromarray((img * 255).astype(np.uint8)).save(os.path.join(salida, "radiografia_simulada.png"), optimize=True)
corte = v[:, :, v.shape[2] // 2][::-1]
c = np.clip(corte / 2200, 0, 1)
Image.fromarray((c * 255).astype(np.uint8)).save(os.path.join(salida, "corte_sagital.png"), optimize=True)
print("radiografía y corte:", proy.shape)

# 2) Suavizado de un contorno ruidoso: Laplaciano vs. Taubin (2D, mismos factores que la página).
rng = np.random.default_rng(3)
n = 90
ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
r = 1 + 0.10 * np.sin(5 * ang) + rng.normal(0, 0.045, n)
pts = np.c_[r * np.cos(ang), r * np.sin(ang)]
def paso(p, f):
    vec = (np.roll(p, 1, 0) + np.roll(p, -1, 0)) / 2
    return p + f * (vec - p)
def area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
lap, tau = pts.copy(), pts.copy()
for _ in range(40):
    lap = paso(lap, 0.33)
    tau = paso(paso(tau, 0.33), -0.34)
a0 = area(pts)
def poligono(p, cx, cy, s, color, ancho, guion=""):
    d = " ".join(f"{cx + s * x:.1f},{cy - s * y:.1f}" for x, y in p)
    extra = f' stroke-dasharray="{guion}"' if guion else ""
    return f'<polygon points="{d}" fill="none" stroke="{color}" stroke-width="{ancho}" stroke-linejoin="round"{extra}/>'
W, H, s = 720, 260, 88
paneles = [("Original (con ruido)", pts, None), (f"Laplaciano: área {100*area(lap)/a0:.0f} %", lap, pts), (f"Taubin: área {100*area(tau)/a0:.0f} %", tau, pts)]
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Un contorno ruidoso suavizado con Laplaciano encoge; con Taubin conserva el tamaño">']
for k, (titulo, p, ref) in enumerate(paneles):
    cx = 120 + k * 240
    if ref is not None:
        svg.append(poligono(ref, cx, 125, s, TINTA3, 1.2, "4 4"))
    svg.append(poligono(p, cx, 125, s, ACENTO if k else TINTA, 2.4))
    svg.append(f'<text x="{cx}" y="{H - 14}" text-anchor="middle" fill="{TINTA2}" font-size="17" {FUENTE}>{titulo}</text>')
svg.append("</svg>")
open(os.path.join(salida, "suavizado_2d.svg"), "w", encoding="utf-8").write("\n".join(svg))
print("suavizado:", round(100 * area(lap) / a0), round(100 * area(tau) / a0))

# 3) Normalización: dos estudios, dos puntos (aire y tejido blando) → una recta.
pre = (0.6, 399.0)                 # metadatos del estudio Pre (aire, blando) en crudo
post = (-2239.5, -153.5)           # estudio Post en crudo (bitácora / carga real)
W, H = 720, 300
M = dict(i=70, d=30, a=26, b=50)
xmin, xmax, ymin, ymax = -2600, 700, -150, 650
X = lambda x: M["i"] + (x - xmin) / (xmax - xmin) * (W - M["i"] - M["d"])
Y = lambda y: H - M["b"] - (y - ymin) / (ymax - ymin) * (H - M["a"] - M["b"])
g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Recta de normalización de dos estudios CBCT">']
for yv in (0, 200, 410, 600):
    g.append(f'<line x1="{M["i"]}" x2="{W-M["d"]}" y1="{Y(yv):.1f}" y2="{Y(yv):.1f}" stroke="{LINEA}"/>')
    g.append(f'<text x="{M["i"]-8}" y="{Y(yv)+4:.1f}" text-anchor="end" fill="{TINTA3}" font-size="15" {FUENTE}>{yv}</text>')
for xv in (-2500, -2000, -1500, -1000, -500, 0, 500):
    g.append(f'<text x="{X(xv):.1f}" y="{H-M["b"]+18}" text-anchor="middle" fill="{TINTA3}" font-size="15" {FUENTE}>{str(xv).replace("-", "−")}</text>')
g.append(f'<text x="{(M["i"]+W-M["d"])/2}" y="{H-8}" text-anchor="middle" fill="{TINTA2}" font-size="16" {FUENTE}>valor en crudo del equipo</text>')
g.append(f'<text x="16" y="{(H-M["b"]+M["a"])/2}" text-anchor="middle" fill="{TINTA2}" font-size="16" {FUENTE} transform="rotate(-90 16 {(H-M["b"]+M["a"])/2})">escala común</text>')
for (aire, blando), color, nombre in ((pre, "#e8d393", "Estudio Pre"), (post, ACENTO, "Estudio Post")):
    a = 410 / (blando - aire); b = -a * aire
    x1, x2 = max(xmin, (ymin - b) / a), min(xmax, (ymax - b) / a)
    g.append(f'<line x1="{X(x1):.1f}" y1="{Y(a*x1+b):.1f}" x2="{X(x2):.1f}" y2="{Y(a*x2+b):.1f}" stroke="{color}" stroke-width="2.5"/>')
    for xv, yv, etiqueta in ((aire, 0, "aire"), (blando, 410, "tejido blando")):
        g.append(f'<circle cx="{X(xv):.1f}" cy="{Y(yv):.1f}" r="6" fill="{color}" stroke="#0e1116" stroke-width="2"/>')
    g.append(f'<text x="{X(blando)-12:.1f}" y="{Y(410)-12:.1f}" text-anchor="end" fill="{color}" font-size="16" font-weight="600" {FUENTE}>{nombre}</text>')
g.append(f'<text x="{X(-1300):.1f}" y="{Y(0)-10:.1f}" text-anchor="middle" fill="{TINTA2}" font-size="15" {FUENTE}>aire → 0</text>')
g.append(f'<text x="{X(-1300):.1f}" y="{Y(410)-10:.1f}" text-anchor="middle" fill="{TINTA2}" font-size="15" {FUENTE}>tejido blando → 410</text>')
g.append("</svg>")
open(os.path.join(salida, "normalizacion.svg"), "w", encoding="utf-8").write("\n".join(g))

# 4) Calibración: umbral óptimo de "dientes" en 11 pacientes (STS-3D-Tooth), en HU.
if not os.path.exists(csv_cal):
    print("sin", csv_cal, "→ no se regenera calibracion.svg")
    sys.exit(0)
filas = list(csv.DictReader(open(csv_cal, encoding="utf-8")))
hu = sorted((float(f["umbral_optimo"]) - float(f["b"])) / float(f["a"]) for f in filas)
med = float(np.median(hu))
W, H = 720, 180
M = dict(i=40, d=40)
xmin, xmax = 400, 1500
X = lambda x: M["i"] + (x - xmin) / (xmax - xmin) * (W - M["i"] - M["d"])
c = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Umbral óptimo de dientes en 11 pacientes: mediana {med:.0f} HU frente a 1300 HU de la literatura">']
c.append(f'<line x1="{M["i"]}" x2="{W-M["d"]}" y1="110" y2="110" stroke="{LINEA}" stroke-width="2"/>')
for xv in range(400, 1501, 200):
    c.append(f'<line x1="{X(xv):.1f}" x2="{X(xv):.1f}" y1="110" y2="116" stroke="{TINTA3}"/>')
    c.append(f'<text x="{X(xv):.1f}" y="134" text-anchor="middle" fill="{TINTA3}" font-size="15" {FUENTE}>{xv}</text>')
c.append(f'<text x="{W/2}" y="164" text-anchor="middle" fill="{TINTA2}" font-size="16" {FUENTE}>umbral óptimo de "dientes" (HU) — un punto por paciente</text>')
contador = {}
for h in hu:
    k = round(h / 25)
    contador[k] = contador.get(k, 0) + 1
    c.append(f'<circle cx="{X(h):.1f}" cy="{110 - 12 * contador[k]:.1f}" r="7" fill="{ACENTO}" stroke="#0e1116" stroke-width="2"><title>{h:.0f} HU</title></circle>')
for xv, color, texto, dy in ((med, ACENTO, f"medido: {med:.0f} HU", 30), (1300, "#e8d393", "literatura: 1300 HU", 30)):
    c.append(f'<line x1="{X(xv):.1f}" x2="{X(xv):.1f}" y1="{dy}" y2="110" stroke="{color}" stroke-dasharray="4 4" stroke-width="2"/>')
    c.append(f'<text x="{X(xv):.1f}" y="{dy-8}" text-anchor="middle" fill="{color}" font-size="16" font-weight="600" {FUENTE}>{texto}</text>')
c.append("</svg>")
open(os.path.join(salida, "calibracion.svg"), "w", encoding="utf-8").write("\n".join(c))
print("calibración HU:", [round(h) for h in hu], "mediana", round(med))
