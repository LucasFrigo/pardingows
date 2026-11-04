// Draws the debt letter's texture, the one piece of text inside the 3D world:
//   node src/feliz/letter_tex.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'Fredoka-SemiBold.ttf'), 'Fredoka');

const W = 1024, H = 720;
const c = createCanvas(W, H);
const x = c.getContext('2d');
x.fillStyle = '#fbf6e6';
x.fillRect(0, 0, W, H);
x.fillStyle = '#d62f33';
x.fillRect(0, 0, W, 120);
x.fillStyle = '#ffffff';
x.font = '74px Fredoka';
x.textAlign = 'center';
x.fillText('COBRANÇA', W / 2, 86);
x.fillStyle = '#3a3026';
x.font = '92px Fredoka';
x.fillText('VOCÊ DEVE', W / 2, 270);
x.fillStyle = '#d62f33';
x.font = '178px Fredoka';
x.fillText('98.000', W / 2, 460);
x.strokeStyle = 'rgba(58,48,38,.35)';
x.lineWidth = 8;
for (let i = 0; i < 2; i++) {
  x.beginPath();
  x.moveTo(170, 540 + i * 60);
  x.lineTo(W - 170, 540 + i * 60);
  x.stroke();
}
const out = path.join(ROOT, 'blender/feliz/textures/carta.png');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, c.toBuffer('image/png'));
console.log('wrote', out);
