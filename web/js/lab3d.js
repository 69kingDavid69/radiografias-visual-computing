// Visores 3D (portada y laboratorio). Las mallas salen de src/render_3d.superficie_por_banda.
import * as THREE from "three";
import { OrbitControls } from "../vendor/three/OrbitControls.js";
import { PLYLoader } from "../vendor/three/PLYLoader.js";

const COLOR = { hueso: 0xe8dcc4, dientes: 0xf1ece0, esmalte: 0xdcecff, metal: 0xff6347, dientes_detalle: 0xf1ece0 };
const INTERIOR = 0xd94a3d;
// Factores clásicos de Taubin (1995): un paso que encoge (λ) y otro que infla (μ, con |μ| > λ).
const LAMBDA = 0.33, MU = -0.34;
const cache = new Map();
const cargador = new PLYLoader();

function cargarMalla(nombre) {
  if (!cache.has(nombre)) {
    cache.set(nombre, new Promise((ok, mal) => {
      cargador.load(`modelos/${nombre}.ply`, (g) => {
        g.deleteAttribute("normal");
        g.computeVertexNormals();
        g.computeBoundingBox();
        g.computeBoundingSphere();
        ok(g);
      }, undefined, mal);
    }));
  }
  return cache.get(nombre);
}

function crearEscena(contenedor, { controles = true } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.localClippingEnabled = true;
  contenedor.appendChild(renderer.domElement);
  const escena = new THREE.Scene();
  const camara = new THREE.PerspectiveCamera(32, 1, 1, 5000);
  camara.up.set(0, 0, 1);
  escena.add(camara);
  escena.add(new THREE.HemisphereLight(0xffffff, 0x1b2430, 0.55));
  const clave = new THREE.DirectionalLight(0xffffff, 1.35);
  clave.position.set(-0.6, 0.4, 1);            // luz que sigue a la cámara (como una lámpara de cabeza)
  camara.add(clave);
  const relleno = new THREE.DirectionalLight(0xbfd9ff, 0.45);
  relleno.position.set(1, -0.3, -0.4);
  camara.add(relleno);
  const grupo = new THREE.Group();
  escena.add(grupo);
  let orbit = null;
  if (controles) {
    orbit = new OrbitControls(camara, renderer.domElement);
    orbit.enableDamping = true;
    orbit.dampingFactor = 0.08;
  }
  const ajustar = () => {
    const w = contenedor.clientWidth, h = contenedor.clientHeight;
    renderer.setSize(w, h, false);
    camara.aspect = w / h;
    camara.updateProjectionMatrix();
  };
  new ResizeObserver(ajustar).observe(contenedor);
  ajustar();
  return { renderer, escena, camara, grupo, orbit, contenedor };
}

// Encuadre frontal: la cara de la muestra mira hacia −y; z es arriba.
// `margen` > 1 deja aire alrededor del modelo; < 1 acerca la cámara.
function encuadrar(e, esfera, margen = 1.1) {
  const r = esfera.radius;
  const vertical = THREE.MathUtils.degToRad(e.camara.fov) / 2;
  const horizontal = Math.atan(Math.tan(vertical) * e.camara.aspect);
  const distancia = (margen * r) / Math.sin(Math.min(vertical, horizontal));
  e.camara.position.set(esfera.center.x, esfera.center.y - distancia, esfera.center.z + r * 0.15);
  e.camara.near = r / 50;
  e.camara.far = r * 20;
  e.camara.updateProjectionMatrix();
  if (e.orbit) { e.orbit.target.copy(esfera.center); e.orbit.update(); }
  else e.camara.lookAt(esfera.center);
}

function material(color, extra = {}) {
  return new THREE.MeshPhongMaterial({ color, specular: 0x3a3a3a, shininess: 40, ...extra });
}

// ---------------------------------------------------------------------------
// Portada: hueso + metal girando solos.
// ---------------------------------------------------------------------------
export async function iniciarPortada(contenedor) {
  const e = crearEscena(contenedor, { controles: false });
  const [hueso, metal] = await Promise.all([cargarMalla("hueso"), cargarMalla("metal")]);
  e.grupo.add(new THREE.Mesh(hueso, material(COLOR.hueso)));
  e.grupo.add(new THREE.Mesh(metal, material(COLOR.metal, { shininess: 80 })));
  encuadrar(e, hueso.boundingSphere, 0.95);
  document.getElementById("cargando-portada").remove();
  const reducirMov = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let visible = true;
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(contenedor);
  const centro = hueso.boundingSphere.center;
  e.grupo.position.copy(centro);
  e.grupo.children.forEach((m) => m.position.sub(centro));
  const bucle = () => {
    requestAnimationFrame(bucle);
    if (!visible) return;
    if (!reducirMov) e.grupo.rotation.z += 0.004;
    e.renderer.render(e.escena, e.camara);
  };
  bucle();
}

// ---------------------------------------------------------------------------
// Suavizado de mallas (Laplaciano y Taubin), igual que vtkSmoothPolyData / WindowedSinc en concepto.
// ---------------------------------------------------------------------------
function vecindad(geometria) {
  const n = geometria.attributes.position.count;
  const idx = geometria.index.array;
  const sets = Array.from({ length: n }, () => new Set());
  for (let k = 0; k < idx.length; k += 3) {
    const a = idx[k], b = idx[k + 1], c = idx[k + 2];
    sets[a].add(b); sets[a].add(c); sets[b].add(a); sets[b].add(c); sets[c].add(a); sets[c].add(b);
  }
  const inicio = new Uint32Array(n + 1);
  for (let i = 0; i < n; i++) inicio[i + 1] = inicio[i] + sets[i].size;
  const vec = new Uint32Array(inicio[n]);
  for (let i = 0; i < n; i++) { let p = inicio[i]; for (const v of sets[i]) vec[p++] = v; }
  return { inicio, vec };
}

function pasoSuavizado(pos, aux, { inicio, vec }, factor) {
  const n = pos.length / 3;
  for (let i = 0; i < n; i++) {
    const a = inicio[i], b = inicio[i + 1];
    if (b === a) { aux[3 * i] = pos[3 * i]; aux[3 * i + 1] = pos[3 * i + 1]; aux[3 * i + 2] = pos[3 * i + 2]; continue; }
    let sx = 0, sy = 0, sz = 0;
    for (let k = a; k < b; k++) { const v = 3 * vec[k]; sx += pos[v]; sy += pos[v + 1]; sz += pos[v + 2]; }
    const m = b - a;
    aux[3 * i] = pos[3 * i] + factor * (sx / m - pos[3 * i]);
    aux[3 * i + 1] = pos[3 * i + 1] + factor * (sy / m - pos[3 * i + 1]);
    aux[3 * i + 2] = pos[3 * i + 2] + factor * (sz / m - pos[3 * i + 2]);
  }
  pos.set(aux);
}

function volumenMalla(pos, idx) {
  let v = 0;
  for (let k = 0; k < idx.length; k += 3) {
    const a = 3 * idx[k], b = 3 * idx[k + 1], c = 3 * idx[k + 2];
    v += pos[a] * (pos[b + 1] * pos[c + 2] - pos[b + 2] * pos[c + 1])
       - pos[a + 1] * (pos[b] * pos[c + 2] - pos[b + 2] * pos[c])
       + pos[a + 2] * (pos[b] * pos[c + 1] - pos[b + 1] * pos[c]);
  }
  return Math.abs(v / 6);
}

// ---------------------------------------------------------------------------
// Laboratorio.
// ---------------------------------------------------------------------------
export function iniciarLaboratorio(meta) {
  const contenedor = document.getElementById("escena-lab");
  const e = crearEscena(contenedor);
  const hud = document.getElementById("hud-lab");
  const estado = { pestana: "estructuras", estructura: "dientes", sombreado: "phong", brillo: 40, triangulos: false,
                   suavizado: "ninguno", iteraciones: 40, eje: "x", corte: 500, girar: false, fps: 0, modelo: null };
  let mallas = [];                 // [{mesh, interior, alambre}]
  let detalle = null;              // datos del modelo de detalle para suavizar
  let token = 0;

  const ESTRUCTURAS = {
    hueso: { texto: "Hueso (≥ 700)", capas: [["hueso", 1]] },
    dientes: { texto: "Dientes (≥ 1000)", capas: [["dientes", 1]] },
    esmalte: { texto: "Esmalte (≥ 1250)", capas: [["esmalte", 1]] },
    metal: { texto: "Metal (≥ 2000)", capas: [["metal", 1]] },
    implante: { texto: "Hueso + metal", capas: [["hueso", 0.18], ["metal", 1]] },
  };
  const DESCRIPCION = {
    hueso: "Todo lo que supera 700: cráneo, maxilares y dientes. El programa le aplica un suavizado gaussiano de 0.5 mm antes de marching cubes para quitar pedacitos sueltos.",
    dientes: "Desde 1000 queda el hueso más denso y los dientes con sus raíces. Es el preset con el que mejor se ven las raíces.",
    esmalte: "Desde 1250 quedan las coronas (esmalte), pero también los brackets y algo de hueso cortical: sus densidades se cruzan.",
    metal: "Desde 2000 solo queda metal: aquí, los brackets de ortodoncia. El metal es más denso que cualquier tejido.",
    implante: "Vista de implante (idea del equipo): hueso casi transparente y metal sólido, para ver el metal dentro del hueso.",
  };

  const chips = document.getElementById("chips-estructura");
  for (const [clave, { texto }] of Object.entries(ESTRUCTURAS)) {
    const b = document.createElement("button");
    b.className = "chip";
    b.dataset.estructura = clave;
    const color = clave === "metal" || clave === "implante" ? "var(--metal)" : `#${COLOR[clave].toString(16)}`;
    b.innerHTML = `<span class="punto" style="background:${color}"></span>${texto}`;
    b.setAttribute("aria-pressed", String(clave === estado.estructura));
    b.addEventListener("click", () => { estado.estructura = clave; marcar(chips, "estructura", clave); mostrar(); });
    chips.appendChild(b);
  }

  function marcar(padre, dato, valor) {
    padre.querySelectorAll(`[data-${dato}]`).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset[dato] === valor)));
  }

  function planoCorte() {
    const caja = estado.modelo?.boundingBox;
    if (!caja) return null;
    const eje = estado.eje;
    const f = estado.corte / 1000;
    const pos = caja.min[eje] + f * (caja.max[eje] - caja.min[eje]);
    const normal = new THREE.Vector3(eje === "x" ? -1 : 0, eje === "y" ? -1 : 0, eje === "z" ? -1 : 0);
    document.getElementById("out-corte").textContent = `${Math.round(f * 100)} %`;
    return new THREE.Plane(normal, pos);
  }

  // Al cortar, la cámara mira la cara del corte (lo que queda está del lado negativo del eje).
  function vistaCorte() {
    const esfera = estado.modelo?.boundingSphere;
    if (!esfera) return;
    const vertical = THREE.MathUtils.degToRad(e.camara.fov) / 2;
    const d = (0.62 * esfera.radius) / Math.sin(Math.min(vertical, Math.atan(Math.tan(vertical) * e.camara.aspect)));
    const dir = { x: new THREE.Vector3(0.85, -0.45, 0.28), y: new THREE.Vector3(0.35, 0.85, 0.4), z: new THREE.Vector3(0.25, -0.55, 0.8) }[estado.eje].normalize();
    // Mirar al centro de la parte que queda (entre el borde del modelo y el plano).
    const caja = estado.modelo.boundingBox;
    const objetivo = esfera.center.clone();
    const pos = caja.min[estado.eje] + (estado.corte / 1000) * (caja.max[estado.eje] - caja.min[estado.eje]);
    objetivo[estado.eje] = (caja.min[estado.eje] + pos) / 2;
    e.orbit.target.copy(objetivo);
    e.camara.position.copy(objetivo).addScaledVector(dir, d);
    e.orbit.update();
  }

  function aplicarEstilo() {
    const corte = estado.pestana === "corte" ? planoCorte() : null;
    const planos = corte ? [corte] : [];
    for (const { mesh, interior, alambre } of mallas) {
      mesh.material.flatShading = estado.sombreado === "plano";
      mesh.material.shininess = estado.brillo;
      mesh.material.clippingPlanes = planos;
      mesh.material.needsUpdate = true;
      interior.visible = !!corte;
      interior.material.clippingPlanes = planos;
      alambre.visible = estado.triangulos && estado.pestana === "luz";
    }
  }

  async function mostrar() {
    const mio = ++token;
    const usarDetalle = ["luz", "suavizado", "corte"].includes(estado.pestana);
    const capas = usarDetalle ? [["dientes_detalle", 1]] : ESTRUCTURAS[estado.estructura].capas;
    document.getElementById("cargando-lab")?.removeAttribute("hidden");
    const geos = await Promise.all(capas.map(([n]) => cargarMalla(n)));
    if (mio !== token) return;
    document.getElementById("cargando-lab")?.setAttribute("hidden", "");
    for (const m of mallas) e.grupo.remove(m.mesh, m.interior, m.alambre);
    mallas = [];
    capas.forEach(([nombre, opacidad], k) => {
      let g = geos[k];
      if (nombre === "dientes_detalle") g = prepararDetalle(g);
      const transparente = opacidad < 1;
      const mesh = new THREE.Mesh(g, material(COLOR[nombre], transparente ? { transparent: true, opacity: opacidad, depthWrite: false } : {}));
      mesh.renderOrder = transparente ? 2 : 1;
      const interior = new THREE.Mesh(g, material(INTERIOR, { side: THREE.BackSide, shininess: 10 }));
      interior.visible = false;
      const alambre = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: 0x0b1620, wireframe: true, transparent: true, opacity: 0.35 }));
      alambre.visible = false;
      e.grupo.add(mesh, interior, alambre);
      mallas.push({ mesh, interior, alambre });
    });
    const nuevoModelo = geos[0];
    if (estado.modelo !== nuevoModelo) { estado.modelo = nuevoModelo; encuadrar(e, nuevoModelo.boundingSphere, usarDetalle ? 0.8 : 0.95); }
    document.getElementById("texto-estructura").textContent = DESCRIPCION[estado.estructura];
    aplicarEstilo();
  }

  function prepararDetalle(g) {
    if (!detalle) {
      detalle = { geo: g, original: Float32Array.from(g.attributes.position.array), aux: new Float32Array(g.attributes.position.count * 3), vec: vecindad(g) };
      detalle.vol0 = volumenMalla(detalle.original, g.index.array);
      document.getElementById("tri-suav").textContent = (g.index.count / 3).toLocaleString("es-CO");
    }
    return detalle.geo;
  }

  function suavizar() {
    if (!detalle) return;
    const pos = detalle.geo.attributes.position.array;
    pos.set(detalle.original);
    const n = estado.iteraciones;
    if (estado.suavizado === "laplaciano") {
      for (let k = 0; k < n; k++) pasoSuavizado(pos, detalle.aux, detalle.vec, LAMBDA);
    } else if (estado.suavizado === "taubin") {
      for (let k = 0; k < n; k++) { pasoSuavizado(pos, detalle.aux, detalle.vec, LAMBDA); pasoSuavizado(pos, detalle.aux, detalle.vec, MU); }
    }
    detalle.geo.attributes.position.needsUpdate = true;
    detalle.geo.computeVertexNormals();
    const pct = (100 * volumenMalla(pos, detalle.geo.index.array)) / detalle.vol0;
    document.getElementById("vol-cambio").textContent = `${pct.toFixed(1)} %`;
  }

  // Pestañas
  const botones = document.querySelectorAll(".pestanas [role=tab]");
  botones.forEach((b) => b.addEventListener("click", async () => {
    estado.pestana = b.dataset.pestana;
    botones.forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    document.querySelectorAll(".contenido-pestana").forEach((c) => { c.hidden = c.dataset.contenido !== estado.pestana; });
    await mostrar();
    if (estado.pestana === "suavizado") suavizar();
    if (estado.pestana === "corte") vistaCorte();
  }));

  // Luz
  document.querySelectorAll("[data-sombreado]").forEach((b) => b.addEventListener("click", () => {
    estado.sombreado = b.dataset.sombreado;
    document.querySelectorAll("[data-sombreado]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    aplicarEstilo();
  }));
  const brillo = document.getElementById("brillo");
  const outBrillo = document.getElementById("out-brillo");
  outBrillo.textContent = brillo.value;
  brillo.addEventListener("input", () => { estado.brillo = +brillo.value; outBrillo.textContent = brillo.value; aplicarEstilo(); });
  const btnTri = document.getElementById("btn-triangulos");
  btnTri.addEventListener("click", () => { estado.triangulos = !estado.triangulos; btnTri.setAttribute("aria-pressed", String(estado.triangulos)); aplicarEstilo(); });

  // Suavizado
  const chipsSuav = document.getElementById("chips-suavizado");
  chipsSuav.querySelectorAll("[data-suavizado]").forEach((b) => b.addEventListener("click", () => {
    estado.suavizado = b.dataset.suavizado;
    marcar(chipsSuav, "suavizado", estado.suavizado);
    suavizar();
  }));
  const iter = document.getElementById("iteraciones");
  const outIter = document.getElementById("out-iter");
  outIter.textContent = iter.value;
  let pendiente = 0;
  iter.addEventListener("input", () => {
    estado.iteraciones = +iter.value;
    outIter.textContent = iter.value;
    cancelAnimationFrame(pendiente);
    pendiente = requestAnimationFrame(suavizar);
  });

  // Corte
  document.querySelectorAll("[data-eje]").forEach((b) => b.addEventListener("click", () => {
    estado.eje = b.dataset.eje;
    document.querySelectorAll("[data-eje]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    aplicarEstilo();
    vistaCorte();
  }));
  document.getElementById("pos-corte").addEventListener("input", (ev) => { estado.corte = +ev.target.value; aplicarEstilo(); });

  // Rendimiento
  const btnGirar = document.getElementById("btn-girar");
  btnGirar.addEventListener("click", () => { estado.girar = !estado.girar; btnGirar.setAttribute("aria-pressed", String(estado.girar)); });
  if (e.orbit) e.orbit.autoRotateSpeed = 4;

  // Bucle de dibujo con medición de FPS (solo mientras la sección está visible).
  let visible = false;
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(contenedor);
  let cuadros = 0, t0 = performance.now();
  const bucle = () => {
    requestAnimationFrame(bucle);
    if (!visible) return;
    if (e.orbit) { e.orbit.autoRotate = estado.girar; e.orbit.update(); }
    e.renderer.render(e.escena, e.camara);
    cuadros++;
    const ahora = performance.now();
    if (ahora - t0 > 500) {
      estado.fps = Math.round((cuadros * 1000) / (ahora - t0));
      cuadros = 0; t0 = ahora;
      const tri = mallas.reduce((s, m) => s + (m.mesh.geometry.index ? m.mesh.geometry.index.count / 3 : 0), 0);
      document.getElementById("tri-vivo").textContent = tri.toLocaleString("es-CO");
      document.getElementById("fps-vivo").textContent = estado.fps;
      hud.innerHTML = `Triángulos <b>${tri.toLocaleString("es-CO")}</b> · FPS <b>${estado.fps}</b>`;
    }
  };
  bucle();

  // Carga diferida: el laboratorio se arma cuando la sección se acerca a la pantalla.
  const obs = new IntersectionObserver(([en]) => { if (en.isIntersecting) { obs.disconnect(); mostrar(); } }, { rootMargin: "400px" });
  obs.observe(contenedor);
}
