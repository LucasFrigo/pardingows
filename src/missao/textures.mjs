// Pixel textures with text on them, drawn with the video's own font so they match the HUD.
//   node src/missao/textures.mjs
import fs from 'fs';
import path from 'path';
import { Surface, hex } from '../shared/engine.mjs';
import { BIG, MINI, drawText, textWidth } from '../shared/font.mjs';
import { encodePNG } from '../shared/png.mjs';

const OUT = 'blender/missao/textures';
fs.mkdirSync(OUT, { recursive: true });

function make(name, w, h, bg, draw) {
  const s = new Surface(w, h).clear(hex(bg));
  const center = (str, y, color, opt = {}) => {
    const x = Math.round((w - textWidth(opt.font || BIG, str, opt.scale || 1)) / 2);
    drawText(s, str, x, y, hex(color), opt.outline ? { ...opt, outline: hex(opt.outline) } : opt);
  };
  draw(s, center);
  fs.writeFileSync(path.join(OUT, name + '.png'), encodePNG(w, h, Buffer.from(s.px.buffer)));
}

const disc = (s, cx, cy, r, c) => {
  for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r) s.set(cx + x, cy + y, hex(c));
};

make('sign_lanchonete', 128, 24, '#c81e1e', (s, center) => {
  s.rect(0, 0, 128, 2, hex('#ffd23f'));
  s.rect(0, 22, 128, 2, hex('#ffd23f'));
  center('LANCHONETE', 5, '#ffffff', { scale: 2, outline: '#3a0808' });
});
make('sign_salgado', 96, 48, '#ffd23f', (s, center) => {
  s.rect(0, 0, 96, 3, hex('#c81e1e'));
  s.rect(0, 45, 96, 3, hex('#c81e1e'));
  center('SALGADO', 8, '#c81e1e', { scale: 2 });
  center('BOM', 27, '#1a1a20', { scale: 2 });
});
make('menu', 64, 48, '#1c2a22', (s, center) => {
  center('COXINHA', 5, '#ffd23f');
  center('R$ 5,00', 16, '#ffffff');
  center('PASTEL', 28, '#ffd23f');
  center('R$ 6,00', 38, '#ffffff');
});
// A made-up note, deliberately not a copy of any real banknote
make('nota', 64, 32, '#3f6fc4', (s) => {
  s.rect(2, 2, 60, 28, hex('#5a8ad8'));
  s.rect(4, 4, 56, 24, hex('#3f6fc4'));
  disc(s, 46, 16, 9, '#9dc0f0');
  drawText(s, 'R$', 7, 7, hex('#ffffff'), { scale: 2 });
  drawText(s, '100', 7, 22, hex('#ffffff'), { font: MINI });
});
make('clock', 64, 20, '#0c0404', (s, center) => {
  center('02:00', 3, '#ff2a1a', { scale: 2 });
});
make('coin', 16, 16, '#d89a1c', (s, center) => {
  disc(s, 8, 8, 7, '#ffd23f');
  disc(s, 8, 8, 5, '#f0b828');
  center('1', 5, '#8a5a08');
});
make('poster', 64, 96, '#101018', (s, center) => {
  s.rect(3, 3, 58, 90, hex('#7a1414'));
  s.rect(5, 5, 54, 86, hex('#101018'));
  center('PARDIN', 16, '#ffd23f', { scale: 1 });
  center('GOWS', 27, '#ffd23f', { scale: 2 });
  disc(s, 32, 62, 13, '#a0623a');
  s.rect(21, 58, 22, 5, hex('#050508'));
  s.rect(19, 44, 26, 8, hex('#f0f0f0'));
});
console.log('wrote textures to', OUT);
