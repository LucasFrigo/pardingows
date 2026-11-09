// Small hard-edged textures drawn with the video's pixel font, written to blender/zombies/textures/.
//   node src/zombies/textures.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', '..', 'blender/zombies/textures');
fs.mkdirSync(OUT, { recursive: true });
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'VT323-Regular.ttf'), 'VT323');

function tex(name, w, h, draw) {
  const c = createCanvas(w, h);
  draw(c.getContext('2d'), w, h);
  fs.writeFileSync(path.join(OUT, name), c.toBuffer('image/png'));
  console.log('wrote', name);
}

// Chest patch: a parody squad badge, deliberately not the S.T.A.R.S. star
tex('patch.png', 128, 64, (g, w, h) => {
  g.fillStyle = '#c9a227';
  g.fillRect(0, 0, w, h);
  g.fillStyle = '#10151c';
  g.fillRect(4, 4, w - 8, h - 8);
  g.fillStyle = '#f2f2ea';
  g.font = '32px VT323';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText('P.A.R.D.O.S.', w / 2, h / 2 + 1);
});

// Lettering across the back of the vest
tex('back.png', 128, 48, (g, w, h) => {
  g.fillStyle = '#1b2420';
  g.fillRect(0, 0, w, h);
  g.fillStyle = '#d8d6c8';
  g.font = '48px VT323';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText('PARDOS', w / 2, h / 2 + 1);
});

// A repeatable scatter, so re-running gives the same pixels
function rng(seed) {
  let x = seed;
  return () => (x = (x * 1664525 + 1013904223) >>> 0) / 4294967296;
}

function speckle(g, w, h, base, spread, seed) {
  const r = rng(seed);
  for (let y = 0; y < h; y += 2) {
    for (let x = 0; x < w; x += 2) {
      const k = 1 + (r() - 0.5) * spread;
      g.fillStyle = `rgb(${base.map(c => Math.min(255, c * k) | 0).join(',')})`;
      g.fillRect(x, y, 2, 2);
    }
  }
}

// Cracked asphalt
tex('asfalto.png', 128, 128, (g, w, h) => {
  speckle(g, w, h, [52, 52, 56], 0.45, 7);
  const r = rng(99);
  g.strokeStyle = '#17171a';
  g.lineWidth = 2;
  for (let i = 0; i < 7; i++) {
    let x = r() * w, y = r() * h;
    g.beginPath();
    g.moveTo(x, y);
    for (let k = 0; k < 5; k++) {
      x += (r() - 0.5) * 34;
      y += (r() - 0.5) * 34;
      g.lineTo(x, y);
    }
    g.stroke();
  }
});

// Lane marking, tiled along the road
tex('faixa.png', 64, 64, (g, w, h) => {
  speckle(g, w, h, [52, 52, 56], 0.4, 11);
  g.fillStyle = '#a89a58';
  g.fillRect(26, 0, 12, 40);
});

// Dungeon floor: big worn flagstones
tex('lajes.png', 128, 128, (g, w, h) => {
  speckle(g, w, h, [78, 72, 66], 0.4, 21);
  g.fillStyle = '#26221e';
  for (const y of [0, 64]) g.fillRect(0, y, w, 3);
  for (const [x, y] of [[0, 0], [64, 0], [32, 64], [96, 64]]) g.fillRect(x, y, 3, 64);
});

// A dark city block with a few lit windows
tex('predio.png', 64, 128, (g, w, h) => {
  g.fillStyle = '#14161c';
  g.fillRect(0, 0, w, h);
  const r = rng(5);
  for (let y = 6; y < h - 6; y += 12) {
    for (let x = 6; x < w - 6; x += 12) {
      const on = r();
      g.fillStyle = on > 0.9 ? '#d8a040' : on > 0.8 ? '#7a4a20' : '#0a0b0e';
      g.fillRect(x, y, 6, 8);
    }
  }
});

// A blood pool on a transparent ground: chunky pixels, cartoonish by choice
tex('sangue.png', 64, 64, (g, w, h) => {
  g.clearRect(0, 0, w, h);
  const r = rng(13);
  g.fillStyle = '#5a0a0a';
  for (let i = 0; i < 26; i++) {
    const a = r() * Math.PI * 2, d = r() * r() * 26;
    const s = 4 + (r() * 10 | 0);
    g.fillRect((32 + Math.cos(a) * d - s / 2) | 0, (32 + Math.sin(a) * d * 0.7 - s / 2) | 0, s, s);
  }
});
