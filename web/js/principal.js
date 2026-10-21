// Punto de entrada de la página: carga los datos y arranca cada sección.
import { crearVolumen, iniciarPlanos, iniciarUmbral, iniciarMarching } from "./cortes.js";
import { iniciarPortada, iniciarLaboratorio } from "./lab3d.js";

const tooltip = document.getElementById("tooltip");

async function cargarAtlas(meta) {
  const img = new Image();
  img.src = `datos/${meta.atlas.archivo}`;
  await img.decode();
  const lienzo = document.createElement("canvas");
  lienzo.width = img.width;
  lienzo.height = img.height;
  const ctx = lienzo.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0);
  const rgba = ctx.getImageData(0, 0, img.width, img.height).data;
  const [nz, ny, nx] = meta.forma;
  const bytes = new Uint8Array(nz * ny * nx);
  const cols = meta.atlas.columnas;
  for (let z = 0; z < nz; z++) {
    const fx = (z % cols) * nx, fy = Math.floor(z / cols) * ny;
    for (let y = 0; y < ny; y++) {
      const fila = ((fy + y) * img.width + fx) * 4;
      const destino = (z * ny + y) * nx;
      for (let x = 0; x < nx; x++) bytes[destino + x] = rgba[fila + x * 4];
    }
  }
  return bytes;
}

function resaltarNavegacion() {
  const enlaces = [...document.querySelectorAll(".nav ul a")];
  const secciones = enlaces.map((a) => document.querySelector(a.getAttribute("href")));
  const obs = new IntersectionObserver((entradas) => {
    for (const en of entradas) {
      if (!en.isIntersecting) continue;
      enlaces.forEach((a) => a.classList.toggle("activo", a.getAttribute("href") === `#${en.target.id}`));
    }
  }, { rootMargin: "-45% 0px -50% 0px" });
  secciones.forEach((s) => s && obs.observe(s));
}

async function arrancar() {
  resaltarNavegacion();
  const meta = await (await fetch("datos/meta.json")).json();
  iniciarPortada(document.getElementById("visor-portada")).catch((e) => console.error("portada", e));
  iniciarLaboratorio(meta);
  const vol = crearVolumen(meta, await cargarAtlas(meta));
  iniciarPlanos(vol, meta, tooltip);
  iniciarUmbral(vol, meta, tooltip);
  iniciarMarching(vol, meta);
}

arrancar().catch((e) => {
  console.error(e);
  document.body.insertAdjacentHTML("afterbegin",
    `<div style="background:#5c1d1d;color:#fff;padding:10px 16px">No se pudieron cargar los datos de la página (${e.message}). Si la abriste como archivo, sírvela con <code>python -m http.server</code> dentro de la carpeta web/.</div>`);
});
