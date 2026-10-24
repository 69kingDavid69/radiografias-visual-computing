// Secciones 1–3: cortes 2D, barra de umbral con histograma y marching squares.
// El volumen llega como Uint8Array (z, y, x); densidad = byte × factor.

const ESCALA_VISTA = 3;                       // cada vóxel se dibuja de 3×3 píxeles de lienzo
const COLORES = { axial: "#e74c3c", coronal: "#2ecc71", sagital: "#3498db" };
const NOMBRES_PRESET = { hueso: "Hueso", dientes: "Dientes", esmalte: "Esmalte", metal: "Metal" };

// Ventanas de contraste del visor 2D del programa (src/densidades.py, escala "slicer").
const VENTANAS = { completo: [1250, 2500], dientes_hueso: [788, 1183], tejido_blando: [410, 158] };

export function crearVolumen(meta, bytes) {
  const [nz, ny, nx] = meta.forma;
  const f = meta.atlas.factor;
  return {
    nz, ny, nx, f,
    datos: bytes,
    valor(x, y, z) { return bytes[(z * ny + y) * nx + x] * f; },
  };
}

function queEs(v) {
  if (v < 200) return "aire";
  if (v < 700) return "piel / tejido blando";
  if (v < 1000) return "hueso";
  if (v < 1250) return "hueso denso o diente";
  if (v < 2000) return "esmalte (o hueso cortical)";
  return "metal";
}

// Pinta un corte en un lienzo: gris por ventana/nivel y, si se pide, máscara del umbral.
function pintarCorte(ctx, ancho, alto, leer, centro, anchoVentana, umbral) {
  const img = ctx.createImageData(ancho, alto);
  const lo = centro - anchoVentana / 2;
  const k = 255 / anchoVentana;
  for (let j = 0; j < alto; j++) {
    for (let i = 0; i < ancho; i++) {
      const v = leer(i, j);
      let g = (v - lo) * k;
      g = g < 0 ? 0 : g > 255 ? 255 : g;
      const p = (j * ancho + i) * 4;
      if (umbral !== undefined && v >= umbral) {
        img.data[p] = g * 0.35 + 56 * 0.65;
        img.data[p + 1] = g * 0.35 + 189 * 0.65;
        img.data[p + 2] = g * 0.35 + 248 * 0.65;
      } else {
        img.data[p] = img.data[p + 1] = img.data[p + 2] = g;
      }
      img.data[p + 3] = 255;
    }
  }
  return img;
}

// Interpolación lineal sobre una arista: dónde cruza el umbral entre a y b (0..1).
const t = (a, b, u) => (a === b ? 0.5 : Math.min(1, Math.max(0, (u - a) / (b - a))));

// Marching squares sobre una rejilla de valores; devuelve segmentos [x1, y1, x2, y2] en coordenadas de muestra.
export function marchingSquares(ancho, alto, leer, u) {
  const seg = [];
  for (let j = 0; j < alto - 1; j++) {
    for (let i = 0; i < ancho - 1; i++) {
      const a = leer(i, j), b = leer(i + 1, j), c = leer(i + 1, j + 1), d = leer(i, j + 1);
      const caso = (a >= u ? 8 : 0) | (b >= u ? 4 : 0) | (c >= u ? 2 : 0) | (d >= u ? 1 : 0);
      if (caso === 0 || caso === 15) continue;
      const arriba = [i + t(a, b, u), j];
      const derecha = [i + 1, j + t(b, c, u)];
      const abajo = [i + t(d, c, u), j + 1];
      const izquierda = [i, j + t(a, d, u)];
      const centroDentro = (a + b + c + d) / 4 >= u;
      for (const [p, q] of segmentosDeCaso(caso, centroDentro, arriba, derecha, abajo, izquierda)) {
        seg.push(p[0], p[1], q[0], q[1]);
      }
    }
  }
  return seg;
}

function segmentosDeCaso(caso, centroDentro, A, R, B, L) {
  switch (caso) {
    case 1: case 14: return [[L, B]];
    case 2: case 13: return [[B, R]];
    case 3: case 12: return [[L, R]];
    case 4: case 11: return [[A, R]];
    case 6: case 9: return [[A, B]];
    case 7: case 8: return [[L, A]];
    case 5: return centroDentro ? [[L, A], [B, R]] : [[L, B], [A, R]];
    case 10: return centroDentro ? [[A, R], [L, B]] : [[L, A], [B, R]];
    default: return [];
  }
}

const DESCRIPCION_CASO = (caso) => {
  if (caso === 0) return "todas las esquinas fuera: no hay borde";
  if (caso === 15) return "todas las esquinas dentro: no hay borde";
  if (caso === 5 || caso === 10) return "caso ambiguo (silla): se decide con el promedio del centro de la celda";
  const n = [8, 4, 2, 1].filter((b) => caso & b).length;
  return n === 1 || n === 3 ? "una esquina distinta: el borde corta esa esquina" : "dos esquinas de un lado: el borde atraviesa la celda";
};

// ---------------------------------------------------------------------------
// Sección 1: tres planos con ventana/nivel.
// ---------------------------------------------------------------------------
export function iniciarPlanos(vol, meta, tooltip) {
  const estado = { z: meta.corte_dientes, y: Math.floor(vol.ny / 2), x: Math.floor(vol.nx / 2), centro: VENTANAS.completo[0], ancho: VENTANAS.completo[1], voxeles: true };
  const planos = {
    axial: { w: vol.nx, h: vol.ny, eje: "z", max: vol.nz, leer: (i, j) => vol.valor(i, j, estado.z) },
    coronal: { w: vol.nx, h: vol.nz, eje: "y", max: vol.ny, leer: (i, j) => vol.valor(i, estado.y, vol.nz - 1 - j) },
    sagital: { w: vol.ny, h: vol.nz, eje: "x", max: vol.nx, leer: (i, j) => vol.valor(estado.x, i, vol.nz - 1 - j) },
  };
  const offscreen = document.createElement("canvas");
  const octx = offscreen.getContext("2d");

  for (const [nombre, p] of Object.entries(planos)) {
    const nodo = document.querySelector(`.plano[data-plano="${nombre}"]`);
    p.lienzo = nodo.querySelector("canvas");
    p.lienzo.width = p.w * ESCALA_VISTA;
    p.lienzo.height = p.h * ESCALA_VISTA;
    p.lienzo.style.aspectRatio = `${p.w} / ${p.h}`;
    p.ctx = p.lienzo.getContext("2d");
    p.barra = nodo.querySelector("input");
    p.salida = nodo.querySelector("output");
    p.barra.min = 0;
    p.barra.max = p.max - 1;
    p.barra.value = estado[p.eje];
    p.barra.addEventListener("input", () => { estado[p.eje] = +p.barra.value; dibujarTodo(); });
    p.lienzo.addEventListener("mousemove", (e) => leerVoxel(nombre, e));
    p.lienzo.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
    p.lienzo.addEventListener("click", (e) => mover(nombre, e));
  }

  function aVoxel(nombre, e) {
    const p = planos[nombre];
    const r = p.lienzo.getBoundingClientRect();
    const i = Math.min(p.w - 1, Math.max(0, Math.floor(((e.clientX - r.left) / r.width) * p.w)));
    const j = Math.min(p.h - 1, Math.max(0, Math.floor(((e.clientY - r.top) / r.height) * p.h)));
    if (nombre === "axial") return { x: i, y: j, z: estado.z };
    if (nombre === "coronal") return { x: i, y: estado.y, z: vol.nz - 1 - j };
    return { x: estado.x, y: i, z: vol.nz - 1 - j };
  }

  function leerVoxel(nombre, e) {
    const { x, y, z } = aVoxel(nombre, e);
    const v = vol.valor(x, y, z);
    const texto = `Vóxel (x ${x}, y ${y}, z ${z}) · densidad <b>${v}</b> · probablemente <b>${queEs(v)}</b>`;
    document.getElementById("lectura-voxel").innerHTML = texto;
    tooltip.innerHTML = `densidad <b>${v}</b><br>${queEs(v)}`;
    tooltip.style.display = "block";
    tooltip.style.left = `${e.clientX + 14}px`;
    tooltip.style.top = `${e.clientY + 14}px`;
  }

  function mover(nombre, e) {
    const { x, y, z } = aVoxel(nombre, e);
    Object.assign(estado, { x, y, z });
    for (const p of Object.values(planos)) p.barra.value = estado[p.eje];
    dibujarTodo();
  }

  function dibujarTodo() {
    for (const [nombre, p] of Object.entries(planos)) {
      offscreen.width = p.w;
      offscreen.height = p.h;
      octx.putImageData(pintarCorte(octx, p.w, p.h, p.leer, estado.centro, estado.ancho), 0, 0);
      p.ctx.imageSmoothingEnabled = !estado.voxeles;
      p.ctx.drawImage(offscreen, 0, 0, p.lienzo.width, p.lienzo.height);
      // Líneas guía: dónde están los otros dos cortes.
      const s = ESCALA_VISTA;
      p.ctx.lineWidth = 2;
      p.ctx.setLineDash([6, 5]);
      const linea = (color, x1, y1, x2, y2) => { p.ctx.strokeStyle = color; p.ctx.beginPath(); p.ctx.moveTo(x1, y1); p.ctx.lineTo(x2, y2); p.ctx.stroke(); };
      if (nombre === "axial") {
        linea(COLORES.coronal, 0, (estado.y + 0.5) * s, p.lienzo.width, (estado.y + 0.5) * s);
        linea(COLORES.sagital, (estado.x + 0.5) * s, 0, (estado.x + 0.5) * s, p.lienzo.height);
      } else if (nombre === "coronal") {
        const yz = (vol.nz - 1 - estado.z + 0.5) * s;
        linea(COLORES.axial, 0, yz, p.lienzo.width, yz);
        linea(COLORES.sagital, (estado.x + 0.5) * s, 0, (estado.x + 0.5) * s, p.lienzo.height);
      } else {
        const yz = (vol.nz - 1 - estado.z + 0.5) * s;
        linea(COLORES.axial, 0, yz, p.lienzo.width, yz);
        linea(COLORES.coronal, (estado.y + 0.5) * s, 0, (estado.y + 0.5) * s, p.lienzo.height);
      }
      p.ctx.setLineDash([]);
      p.salida.textContent = `${estado[p.eje] + 1} / ${p.max}`;
    }
    document.getElementById("out-centro").textContent = estado.centro;
    document.getElementById("out-ancho").textContent = estado.ancho;
  }

  const centro = document.getElementById("centro");
  const ancho = document.getElementById("ancho");
  centro.value = estado.centro;
  ancho.value = estado.ancho;
  const alCambiarVentana = () => {
    estado.centro = +centro.value;
    estado.ancho = +ancho.value;
    document.querySelectorAll("[data-ventana]").forEach((b) => b.setAttribute("aria-pressed", "false"));
    dibujarTodo();
  };
  centro.addEventListener("input", alCambiarVentana);
  ancho.addEventListener("input", alCambiarVentana);
  document.querySelectorAll("[data-ventana]").forEach((boton) => {
    boton.addEventListener("click", () => {
      [estado.centro, estado.ancho] = VENTANAS[boton.dataset.ventana];
      centro.value = estado.centro;
      ancho.value = estado.ancho;
      document.querySelectorAll("[data-ventana]").forEach((b) => b.setAttribute("aria-pressed", String(b === boton)));
      dibujarTodo();
    });
  });
  const btnVox = document.getElementById("btn-voxeles");
  btnVox.addEventListener("click", () => {
    estado.voxeles = !estado.voxeles;
    btnVox.setAttribute("aria-pressed", String(estado.voxeles));
    document.querySelectorAll(".plano").forEach((n) => n.classList.toggle("suave", !estado.voxeles));
    dibujarTodo();
  });
  dibujarTodo();
}

// ---------------------------------------------------------------------------
// Sección 2: barra de umbral + histograma.
// ---------------------------------------------------------------------------
export function iniciarUmbral(vol, meta, tooltip) {
  const estado = { umbral: 1000, z: meta.corte_dientes };
  const lienzo = document.getElementById("lienzo-umbral");
  lienzo.width = vol.nx * ESCALA_VISTA;
  lienzo.height = vol.ny * ESCALA_VISTA;
  const ctx = lienzo.getContext("2d");
  const off = document.createElement("canvas");
  off.width = vol.nx;
  off.height = vol.ny;
  const octx = off.getContext("2d");
  const barra = document.getElementById("umbral-barra");
  const barraCorte = document.getElementById("corte-umbral");
  barraCorte.min = 0;
  barraCorte.max = vol.nz - 1;
  barraCorte.value = estado.z;

  // Chips: los presets del programa + el tejido blando (solo como referencia).
  const chips = document.getElementById("chips-umbral");
  const opciones = [["blando", "Tejido blando (~400)", 400, "#c9a27e"]];
  for (const [nombre, [minimo]] of Object.entries(meta.presets)) {
    if (!NOMBRES_PRESET[nombre]) continue;
    const color = nombre === "metal" ? "var(--metal)" : nombre === "hueso" ? "var(--hueso)" : nombre === "esmalte" ? "var(--esmalte)" : "var(--dientes)";
    opciones.push([nombre, `${NOMBRES_PRESET[nombre]} (${minimo})`, minimo, color]);
  }
  for (const [nombre, texto, valor, color] of opciones) {
    const b = document.createElement("button");
    b.className = "chip";
    b.dataset.valor = valor;
    b.innerHTML = `<span class="punto" style="background:${color}"></span>${texto}`;
    b.setAttribute("aria-pressed", String(valor === estado.umbral));
    b.addEventListener("click", () => fijar(valor));
    chips.appendChild(b);
  }

  // Histograma (SVG). Eje y logarítmico.
  const h = meta.histograma;
  const W = 440, H = 250, M = { i: 40, d: 8, a: 40, b: 26 };
  const max = Math.max(...h.conteos);
  const xDe = (v) => M.i + ((v - h.inicio) / (h.paso * h.conteos.length)) * (W - M.i - M.d);
  const yDe = (c) => (c <= 0 ? H - M.b : H - M.b - (Math.log10(c) / Math.log10(max)) * (H - M.a - M.b));
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Histograma de densidades de la tomografía");
  const nuevo = (tag, attrs, padre = svg) => { const n = document.createElementNS(svgNS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); padre.appendChild(n); return n; };
  for (const e of [1, 10, 100, 1e3, 1e4, 1e5, 1e6, 1e7]) {
    if (e > max) break;
    const y = yDe(e);
    nuevo("line", { x1: M.i, x2: W - M.d, y1: y, y2: y, class: "eje", "stroke-opacity": 0.5 });
    nuevo("text", { x: M.i - 6, y: y + 4, "text-anchor": "end" }).textContent = e >= 1e6 ? `${e / 1e6}M` : e >= 1e3 ? `${e / 1e3}k` : e;
  }
  const barras = [];
  const anchoBarra = (W - M.i - M.d) / h.conteos.length;
  h.conteos.forEach((c, k) => {
    const v0 = h.inicio + k * h.paso;
    const y = yDe(c);
    const r = nuevo("rect", { x: xDe(v0) + 0.5, y, width: Math.max(1, anchoBarra - 1), height: H - M.b - y, rx: 1, class: "barra" });
    barras.push([r, v0]);
    const zona = nuevo("rect", { x: xDe(v0), y: M.a, width: anchoBarra, height: H - M.a - M.b, fill: "transparent" });
    zona.style.cursor = "pointer";
    zona.addEventListener("mousemove", (e) => {
      tooltip.innerHTML = `${v0}–${v0 + h.paso}: <b>${c.toLocaleString("es-CO")}</b> vóxeles<br><span style="color:#a3b0bf">${queEs(v0 + h.paso / 2)}</span>`;
      tooltip.style.display = "block";
      tooltip.style.left = `${e.clientX + 14}px`;
      tooltip.style.top = `${e.clientY + 14}px`;
    });
    zona.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
    zona.addEventListener("click", () => fijar(v0));
  });
  nuevo("line", { x1: M.i, x2: W - M.d, y1: H - M.b, y2: H - M.b, class: "eje" });
  for (let v = 0; v <= 4000; v += 500) nuevo("text", { x: xDe(v), y: H - 10, "text-anchor": v === 4000 ? "end" : "middle" }).textContent = v;
  let fila = 0;
  for (const [nombre, [minimo]] of Object.entries(meta.presets)) {
    if (!NOMBRES_PRESET[nombre]) continue;
    const yEtiqueta = M.a - 24 + (fila++ % 2) * 13;   // alternar alturas para que no se monten
    nuevo("line", { x1: xDe(minimo), x2: xDe(minimo), y1: yEtiqueta + 3, y2: H - M.b, class: "marca-preset" });
    nuevo("text", { x: xDe(minimo), y: yEtiqueta, "text-anchor": "middle" }).textContent = NOMBRES_PRESET[nombre].toLowerCase();
  }
  const lineaUmbral = nuevo("line", { y1: M.a - 2, y2: H - M.b, class: "linea-umbral" });
  document.getElementById("histograma").appendChild(svg);

  function fijar(v) {
    estado.umbral = v;
    barra.value = v;
    dibujar();
  }

  let pendiente = false;
  function dibujar() {
    if (pendiente) return;
    pendiente = true;
    requestAnimationFrame(() => {
      pendiente = false;
      const u = estado.umbral;
      const leer = (i, j) => vol.valor(i, j, estado.z);
      octx.putImageData(pintarCorte(octx, vol.nx, vol.ny, leer, 1250, 2500, u), 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(off, 0, 0, lienzo.width, lienzo.height);
      // Borde con marching squares (coordenadas de muestra = centro de cada vóxel).
      const s = ESCALA_VISTA;
      const seg = marchingSquares(vol.nx, vol.ny, leer, u);
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (let k = 0; k < seg.length; k += 4) {
        ctx.moveTo((seg[k] + 0.5) * s, (seg[k + 1] + 0.5) * s);
        ctx.lineTo((seg[k + 2] + 0.5) * s, (seg[k + 3] + 0.5) * s);
      }
      ctx.stroke();
      // Porcentajes
      let n = 0;
      const base = estado.z * vol.nx * vol.ny;
      const limite = Math.ceil(u / vol.f);
      for (let k = 0; k < vol.nx * vol.ny; k++) if (vol.datos[base + k] >= limite) n++;
      let total = 0;
      for (let k = 0; k < vol.datos.length; k++) if (vol.datos[k] >= limite) total++;
      document.getElementById("pct-corte").textContent = `${((100 * n) / (vol.nx * vol.ny)).toFixed(1)} %`;
      document.getElementById("pct-total").textContent = `${((100 * total) / vol.datos.length).toFixed(2)} %`;
      document.getElementById("out-umbral").textContent = u;
      document.getElementById("out-corte-umbral").textContent = `${estado.z + 1} / ${vol.nz}`;
      lineaUmbral.setAttribute("x1", xDe(u));
      lineaUmbral.setAttribute("x2", xDe(u));
      for (const [r, v0] of barras) r.classList.toggle("sobre", v0 + h.paso > u);
      chips.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.valor === u)));
    });
  }
  barra.addEventListener("input", () => { estado.umbral = +barra.value; dibujar(); });
  barraCorte.addEventListener("input", () => { estado.z = +barraCorte.value; dibujar(); });
  dibujar();
}

// ---------------------------------------------------------------------------
// Sección 3: marching squares sobre un recorte de un diente.
// ---------------------------------------------------------------------------
export function iniciarMarching(vol, meta) {
  const N = 16;                           // vóxeles por lado del recorte
  const z = meta.corte_dientes;
  // Elegir la ventana de N×N con más vóxeles de borde (donde el algoritmo trabaja).
  const borde = new Uint8Array(vol.nx * vol.ny);
  for (let y = 1; y < vol.ny - 1; y++) for (let x = 1; x < vol.nx - 1; x++) {
    const dentro = vol.valor(x, y, z) >= 1000;
    const vecinoFuera = vol.valor(x + 1, y, z) < 1000 || vol.valor(x - 1, y, z) < 1000 || vol.valor(x, y + 1, z) < 1000 || vol.valor(x, y - 1, z) < 1000;
    borde[y * vol.nx + x] = dentro && vecinoFuera ? 1 : 0;
  }
  let mejor = { n: -1, x: 0, y: 0 };
  for (let y0 = 0; y0 <= vol.ny - N; y0++) for (let x0 = 0; x0 <= vol.nx - N; x0++) {
    let n = 0;
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) n += borde[(y0 + j) * vol.nx + x0 + i];
    if (n > mejor.n) mejor = { n, x: x0, y: y0 };
  }
  const leer = (i, j) => vol.valor(mejor.x + i, mejor.y + j, z);

  const lienzo = document.getElementById("lienzo-ms");
  const ctx = lienzo.getContext("2d");
  const barra = document.getElementById("umbral-ms");
  const salidaCaso = document.getElementById("caso-ms");
  let u = +barra.value;
  let celda = null;
  const paso = lienzo.width / N;
  const c = (k) => (k + 0.5) * paso;     // centro de un vóxel en el lienzo

  function dibujar() {
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const g = Math.max(0, Math.min(255, (leer(i, j) / 2500) * 255));
      ctx.fillStyle = `rgb(${g},${g},${g})`;
      ctx.fillRect(i * paso, j * paso, paso, paso);
    }
    // Rejilla de celdas (entre centros de vóxel)
    ctx.strokeStyle = "rgba(56,189,248,0.18)";
    ctx.lineWidth = 1;
    for (let k = 0; k < N; k++) {
      ctx.beginPath(); ctx.moveTo(c(k), c(0)); ctx.lineTo(c(k), c(N - 1)); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(c(0), c(k)); ctx.lineTo(c(N - 1), c(k)); ctx.stroke();
    }
    if (celda) {
      ctx.fillStyle = "rgba(56,189,248,0.16)";
      ctx.fillRect(c(celda.i), c(celda.j), paso, paso);
      ctx.strokeStyle = "#38bdf8";
      ctx.strokeRect(c(celda.i), c(celda.j), paso, paso);
    }
    // Borde
    const seg = marchingSquares(N, N, leer, u);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.beginPath();
    for (let k = 0; k < seg.length; k += 4) { ctx.moveTo(c(seg[k]), c(seg[k + 1])); ctx.lineTo(c(seg[k + 2]), c(seg[k + 3])); }
    ctx.stroke();
    // Esquinas
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const dentro = leer(i, j) >= u;
      ctx.beginPath();
      ctx.arc(c(i), c(j), dentro ? 5 : 3.5, 0, Math.PI * 2);
      ctx.fillStyle = dentro ? "#38bdf8" : "#3d4855";
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#0e1116";
      ctx.stroke();
    }
    document.getElementById("out-umbral-ms").textContent = u;
    describir();
  }

  function describir() {
    if (!celda) return;
    const { i, j } = celda;
    const a = leer(i, j), b = leer(i + 1, j), cc = leer(i + 1, j + 1), d = leer(i, j + 1);
    const caso = (a >= u ? 8 : 0) | (b >= u ? 4 : 0) | (cc >= u ? 2 : 0) | (d >= u ? 1 : 0);
    salidaCaso.innerHTML = `Esquinas: ${a} · ${b} · ${cc} · ${d} &nbsp;→&nbsp; <b>caso ${caso}</b> (${caso.toString(2).padStart(4, "0")}): ${DESCRIPCION_CASO(caso)}`;
  }

  lienzo.addEventListener("mousemove", (e) => {
    const r = lienzo.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * lienzo.width;
    const py = ((e.clientY - r.top) / r.height) * lienzo.height;
    const i = Math.floor(px / paso - 0.5), j = Math.floor(py / paso - 0.5);
    if (i >= 0 && j >= 0 && i < N - 1 && j < N - 1) { celda = { i, j }; dibujar(); }
  });
  barra.addEventListener("input", () => { u = +barra.value; dibujar(); });
  dibujar();
}
