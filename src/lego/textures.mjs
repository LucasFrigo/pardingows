// Draws the minifig prints: faces and torso fronts. PNGs go to blender/lego/textures/.
//   node src/lego/textures.mjs
// The rig's Face and Torso_Front UVs show the image upside down, so prints are drawn the right way up and flipped on save.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, GlobalFonts } from '@napi-rs/canvas';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT = path.join(ROOT, 'blender/lego/textures');
fs.mkdirSync(OUT, { recursive: true });

const INK = '#1a1410';

function save(name, c, { flip = false } = {}) {
  let src = c;
  if (flip) {
    const f = createCanvas(c.width, c.height);
    const x = f.getContext('2d');
    x.translate(0, c.height);
    x.scale(1, -1);
    x.drawImage(c, 0, 0);
    src = f;
  }
  fs.writeFileSync(path.join(OUT, name + '.png'), src.toBuffer('image/png'));
}

// ---- Faces: 1024x512, transparent, drawn on the head's front. Eyes sit around y=235, mouth y=340, as in the rig's own face.
function face(name, draw) {
  const c = createCanvas(1024, 512);
  const x = c.getContext('2d');
  x.lineCap = 'round';
  x.lineJoin = 'round';
  draw(x);
  save(name, c, { flip: true });
}
const eyes = (x, { y = 238, rx = 44, ry = 38, gap = 134 } = {}) => {
  x.fillStyle = INK;
  for (const s of [-1, 1]) {
    x.beginPath();
    x.ellipse(512 + s * gap, y, rx, ry, 0, 0, Math.PI * 2);
    x.fill();
    x.fillStyle = '#ffffff';
    x.beginPath();
    x.ellipse(512 + s * gap - 12, y - 12, 11, 10, 0, 0, Math.PI * 2);
    x.fill();
    x.fillStyle = INK;
  }
};
const brows = (x, tilt, y = 160, len = 62, w = 20, colour = INK) => {
  x.strokeStyle = colour;
  x.lineWidth = w;
  for (const s of [-1, 1]) {
    x.beginPath();
    x.moveTo(512 + s * (134 - len), y + tilt);
    x.lineTo(512 + s * (134 + len), y - tilt);
    x.stroke();
  }
};
const smile = (x, w = 134, drop = 50, y = 336) => {
  x.strokeStyle = INK;
  x.lineWidth = 20;
  x.beginPath();
  x.moveTo(512 - w, y);
  x.quadraticCurveTo(512, y + drop * 2, 512 + w, y);
  x.stroke();
};
const openMouth = (x, w = 110, h = 92, y = 336, teeth = true) => {
  x.fillStyle = '#3b0d10';
  x.beginPath();
  x.moveTo(512 - w, y);
  x.quadraticCurveTo(512, y - 12, 512 + w, y);
  x.quadraticCurveTo(512, y + h * 2, 512 - w, y);
  x.fill();
  if (teeth) {
    x.fillStyle = '#ffffff';
    x.beginPath();
    x.moveTo(512 - w * 0.78, y + 3);
    x.quadraticCurveTo(512, y - 8, 512 + w * 0.78, y + 3);
    x.lineTo(512 + w * 0.62, y + 26);
    x.quadraticCurveTo(512, y + 16, 512 - w * 0.62, y + 26);
    x.fill();
  }
  x.strokeStyle = INK;
  x.lineWidth = 12;
  x.beginPath();
  x.moveTo(512 - w, y);
  x.quadraticCurveTo(512, y - 12, 512 + w, y);
  x.quadraticCurveTo(512, y + h * 2, 512 - w, y);
  x.stroke();
};

// Pardo's nose sits low on his face, so his mouth goes below it
face('face_pardo', x => { eyes(x); smile(x, 128, 34, 398); });
face('face_pardo_open', x => { eyes(x); openMouth(x, 96, 42, 398); });
face('face_pardo_sleep', x => {
  x.strokeStyle = INK;
  x.lineWidth = 20;
  for (const s of [-1, 1]) {
    x.beginPath();
    x.moveTo(512 + s * 88, 238);
    x.quadraticCurveTo(512 + s * 134, 276, 512 + s * 180, 238);
    x.stroke();
  }
  smile(x, 70, 26);
});
face('face_israel', x => { eyes(x, { rx: 38, ry: 42 }); brows(x, -6, 158, 62, 20, '#8a6a1c'); smile(x, 96, 26, 346); });
face('face_israel_rant', x => { eyes(x, { rx: 38, ry: 42 }); brows(x, 24, 156, 66, 24, '#8a6a1c'); openMouth(x, 112, 104, 330); });
face('face_israel_shock', x => {
  eyes(x, { rx: 34, ry: 48 });
  brows(x, -16, 138, 60, 20, '#8a6a1c');
  x.fillStyle = INK;
  x.beginPath();
  x.ellipse(512, 362, 34, 40, 0, 0, Math.PI * 2);
  x.fill();
});
face('face_father', x => { eyes(x); brows(x, -4); smile(x, 118, 40); });
face('face_father_run', x => { eyes(x); brows(x, 12); openMouth(x, 90, 66, 338); });
face('face_child', x => { eyes(x, { rx: 48, ry: 50, gap: 126 }); smile(x, 96, 46, 340); });
face('face_child_open', x => { eyes(x, { rx: 48, ry: 50, gap: 126 }); openMouth(x, 84, 72, 338); });

// ---- Torso fronts: 512x512, opaque, filling the whole front panel, top of the image at the neck.
function torso(name, base, draw) {
  const c = createCanvas(512, 512);
  const x = c.getContext('2d');
  x.fillStyle = base;
  x.fillRect(0, 0, 512, 512);
  x.lineCap = 'round';
  x.lineJoin = 'round';
  draw(x);
  save(name, c, { flip: true });
}
// Pardo is bare-chested: a light drawn chest and belly button
torso('torso_pardo', '#a8754a', x => {
  x.strokeStyle = '#7f5532';
  x.lineWidth = 7;
  for (const s of [-1, 1]) {
    x.beginPath();
    x.moveTo(256 + s * 18, 190);
    x.quadraticCurveTo(256 + s * 90, 232, 256 + s * 138, 186);
    x.stroke();
  }
  x.beginPath();
  x.arc(256, 400, 9, 0, Math.PI * 2);
  x.stroke();
});
// Israel: blue-and-white striped shirt, open collar
torso('torso_israel', '#f4f6f8', x => {
  x.fillStyle = '#1f62c4';
  for (let i = 0; i < 6; i++) x.fillRect(0, 92 + i * 76, 512, 34);
  x.fillStyle = '#f4f6f8';
  x.beginPath();
  x.moveTo(150, 0);
  x.lineTo(256, 118);
  x.lineTo(362, 0);
  x.fill();
  x.fillStyle = '#e6c4a0';
  x.beginPath();
  x.moveTo(186, 0);
  x.lineTo(256, 84);
  x.lineTo(326, 0);
  x.fill();
  x.strokeStyle = '#1f62c4';
  x.lineWidth = 10;
  x.beginPath();
  x.moveTo(150, 0);
  x.lineTo(256, 118);
  x.lineTo(362, 0);
  x.stroke();
});
// Red jumpsuit: collar, long zip, belt, chest pocket
torso('torso_robber', '#b5121b', x => {
  x.strokeStyle = '#7f0b12';
  x.lineWidth = 10;
  x.beginPath();
  x.moveTo(150, 0);
  x.lineTo(256, 80);
  x.lineTo(362, 0);
  x.stroke();
  x.strokeStyle = '#d9d9d9';
  x.lineWidth = 11;
  x.beginPath();
  x.moveTo(256, 80);
  x.lineTo(256, 512);
  x.stroke();
  x.fillStyle = '#d9d9d9';
  x.fillRect(244, 118, 24, 34);
  x.fillStyle = '#26211f';
  x.fillRect(0, 438, 512, 44);
  x.fillStyle = '#b8b8b8';
  x.fillRect(226, 430, 60, 60);
  x.strokeStyle = '#7f0b12';
  x.lineWidth = 8;
  x.strokeRect(330, 170, 104, 98);
});
// Father: grey suit, white shirt, tie
torso('torso_father', '#7c8691', x => {
  x.fillStyle = '#f4f4f0';
  x.beginPath();
  x.moveTo(166, 0);
  x.lineTo(256, 300);
  x.lineTo(346, 0);
  x.fill();
  x.fillStyle = '#7d1c22';
  x.beginPath();
  x.moveTo(234, 36);
  x.lineTo(278, 36);
  x.lineTo(268, 76);
  x.lineTo(286, 240);
  x.lineTo(256, 282);
  x.lineTo(226, 240);
  x.lineTo(244, 76);
  x.fill();
  x.strokeStyle = '#566069';
  x.lineWidth = 10;
  x.beginPath();
  x.moveTo(166, 0);
  x.lineTo(256, 300);
  x.lineTo(256, 512);
  x.moveTo(346, 0);
  x.lineTo(256, 300);
  x.stroke();
  x.fillStyle = '#566069';
  x.fillRect(84, 360, 104, 10);
  x.fillRect(324, 360, 104, 10);
  x.fillStyle = '#d5d5d0';
  x.beginPath();
  x.arc(276, 350, 9, 0, Math.PI * 2);
  x.fill();
  x.beginPath();
  x.arc(276, 420, 9, 0, Math.PI * 2);
  x.fill();
});
// Child: red jacket over a white tee, zip open
torso('torso_child', '#c23a2a', x => {
  x.fillStyle = '#f2f2ee';
  x.beginPath();
  x.moveTo(190, 0);
  x.lineTo(226, 512);
  x.lineTo(286, 512);
  x.lineTo(322, 0);
  x.fill();
  x.strokeStyle = '#8c2519';
  x.lineWidth = 9;
  x.beginPath();
  x.moveTo(190, 0);
  x.lineTo(226, 512);
  x.moveTo(322, 0);
  x.lineTo(286, 512);
  x.stroke();
  x.strokeRect(70, 340, 98, 92);
  x.strokeRect(344, 340, 98, 92);
});

// ---- The giant calendar: a tear-off page, red header, the date, the day's name
GlobalFonts.registerFromPath(path.join(path.dirname(fileURLToPath(import.meta.url)), 'fonts', 'Fredoka-SemiBold.ttf'), 'Fredoka');
{
  const c = createCanvas(860, 1140);
  const x = c.getContext('2d');
  x.fillStyle = '#fbfaf3';
  x.fillRect(0, 0, 860, 1140);
  x.fillStyle = '#c8202a';
  x.fillRect(0, 0, 860, 230);
  x.fillStyle = '#ffffff';
  x.textAlign = 'center';
  x.textBaseline = 'middle';
  x.font = '132px Fredoka';
  x.fillText('TERÇA', 430, 122);
  x.fillStyle = '#25211a';
  x.font = '430px Fredoka';
  x.fillText('67', 430, 520);
  x.fillStyle = '#c8202a';
  x.font = '112px Fredoka';
  x.fillText('DOS PARDOS', 430, 870);
  x.fillStyle = '#25211a';
  x.font = '60px Fredoka';
  x.fillText('é a data', 430, 1000);
  x.fillStyle = '#25211a';
  for (const hx of [160, 330, 530, 700]) {
    x.beginPath();
    x.arc(hx, 28, 12, 0, Math.PI * 2);
    x.fill();
  }
  fs.writeFileSync(path.join(OUT, 'calendar.png'), c.toBuffer('image/png'));
}
console.log('textures in', OUT, fs.readdirSync(OUT).length);
