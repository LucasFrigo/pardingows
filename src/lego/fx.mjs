// Comic overlays drawn on the picture, in both the captioned and caption-free videos: Israel's speech bubble, the pause symbol,
// the remix record, the 67,9 counter, pops, sparkles and Zzz. Positions follow the figures through src/lego/track.json.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { TL, W, H, FPS } from './ui.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TRACK = fs.existsSync(path.join(HERE, 'track.json')) ? JSON.parse(fs.readFileSync(path.join(HERE, 'track.json'), 'utf8')).frames : {};
const KEYS = Object.keys(TRACK).map(Number).sort((a, b) => a - b);
const word = (line, i) => TL.lines[line].words[i][1];
const shotT = name => TL.shots.find(s => s.sketch === name).t;
const shotEnd = name => {
  const i = TL.shots.findIndex(s => s.sketch === name);
  return i + 1 < TL.shots.length ? TL.shots[i + 1].t : TL.start + TL.frames / FPS;
};
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));

// The tracked point on the latest keyed frame at or before this one, in pixels
function at(f, key) {
  let k = null;
  for (const x of KEYS) { if (x <= f) k = x; else break; }
  const p = k && TRACK[k][key];
  return p ? [p[0] * W, p[1] * H] : null;
}

function star(ctx, x, y, r1, r2, n, rot = 0) {
  ctx.beginPath();
  for (let i = 0; i < n * 2; i++) {
    const r = i % 2 ? r2 : r1;
    const a = rot + (Math.PI * i) / n;
    ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
  }
  ctx.closePath();
}

function outlinedText(ctx, text, x, y, px, fill, stroke = '#1a1410', lw = 10) {
  ctx.font = `${px}px Fredoka`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.lineWidth = lw;
  ctx.strokeStyle = stroke;
  ctx.strokeText(text, x, y);
  ctx.fillStyle = fill;
  ctx.fillText(text, x, y);
}

function pop(ctx, x, y, s, label, fill = '#ffd23f') {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.fillStyle = fill;
  ctx.strokeStyle = '#1a1410';
  ctx.lineWidth = 8;
  star(ctx, 0, 0, 150, 92, 11, 0.2);
  ctx.fill();
  ctx.stroke();
  outlinedText(ctx, label, 0, 4, 78, '#ffffff', '#c8202a', 12);
  ctx.restore();
}

// ---- Street: Israel's rant bubble grows with every beat until "fodase" pops it
function rant(ctx, t, f) {
  const a = shotT('rua'), fod = word(0, 5);
  const p = at(f, 'israel');
  if (t < a || t > fod + 0.2 || !p) return;
  const [hx, hy] = p;
  if (t < fod) {
    const g = 0.55 + 0.75 * seg(t, a, fod);
    const shake = 6 * Math.sin(f * 2.1);
    const bx = clamp(hx + 120 * g, 260 * g, W - 230 * g), by = Math.max(hy - 190 * g, 170 * g);
    ctx.save();
    ctx.translate(bx + shake, by);
    ctx.scale(g, g);
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#1a1410';
    ctx.lineWidth = 9;
    ctx.beginPath();
    ctx.ellipse(0, 0, 230, 135, 0, 0, Math.PI * 2);
    ctx.moveTo(-90, 110);
    ctx.lineTo((hx - bx) / g * 0.75, (hy - by) / g * 0.75);
    ctx.lineTo(-20, 125);
    ctx.fill();
    ctx.stroke();
    ctx.beginPath();
    ctx.ellipse(0, 0, 226, 131, 0, 0, Math.PI * 2);
    ctx.fill();
    // A grawlix that reshuffles on every half beat
    const sets = ['#@$%&!', '%&!#@$', '$#!@%&', '!@&%$#'];
    const beat = Math.floor((t - TL.beat0) / (30 / TL.bpm));
    outlinedText(ctx, sets[beat % sets.length], 0, 6, 92, '#c8202a', '#1a1410', 8);
    ctx.restore();
  } else {
    pop(ctx, clamp(hx + 120, 200, W - 200), Math.max(hy - 190, 170), [0.6, 1.15, 1, 0.8, 0.5, 0.2][Math.min(Math.floor((t - fod) * FPS), 5)], 'POP!');
  }
}

// ---- Heist: the giant pause symbol, then a small one held in the corner
function pause(ctx, t) {
  const a = shotT('cofre'), z = shotEnd('cofre');
  if (t < a || t >= z) return;
  const age = t - a;
  const bar = (x, y, w, h) => {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, w * 0.25);
    ctx.fill();
    ctx.stroke();
  };
  ctx.save();
  if (age < 0.62) {
    const s = [0.6, 1.12, 1.04, 1][Math.min(Math.floor(age * FPS), 3)];
    ctx.globalAlpha = age > 0.45 ? 1 - (age - 0.45) / 0.17 : 0.92;
    ctx.translate(W / 2, 640);
    ctx.scale(s, s);
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = 'rgba(0,0,0,.55)';
    ctx.lineWidth = 10;
    bar(-150, -190, 105, 380);
    bar(45, -190, 105, 380);
  } else {
    ctx.translate(96, 210);
    ctx.fillStyle = '#c8202a';
    ctx.beginPath();
    ctx.roundRect(-46, -50, 330, 100, 20);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = 'rgba(0,0,0,0)';
    bar(-22, -30, 20, 60);
    bar(10, -30, 20, 60);
    outlinedText(ctx, 'PAUSADO', 160, 4, 56, '#ffffff', '#7f0b12', 6);
  }
  ctx.restore();
}

// ---- Bench: the thought bubble pops on "mal"
function bubblePop(ctx, t, f) {
  const mal = word(3, 6);
  const p = at(f, 'bubble');
  if (!p || t < mal || t > mal + 0.25) return;
  pop(ctx, p[0], p[1], [0.5, 0.95, 0.85, 0.6, 0.35, 0.15, 0.05, 0][Math.min(Math.floor((t - mal) * FPS), 7)], 'POP!', '#9fd4f5');
}

// ---- Chase: a record scratches in the corner on "remix"
function record(ctx, t) {
  const rmx = word(4, 6), dos = word(4, 7);
  if (t < rmx - 0.05 || t > dos + 0.45) return;
  const s = seg(t, rmx - 0.05, rmx + 0.05) * (1 - seg(t, dos + 0.3, dos + 0.45));
  const spin = t < dos ? 2.6 * Math.sin(((t - rmx) / 0.18) * Math.PI) : (t - dos) * 14;
  ctx.save();
  ctx.translate(W - 240, 330);
  ctx.scale(s, s);
  ctx.rotate(spin);
  ctx.fillStyle = '#16171b';
  ctx.beginPath();
  ctx.arc(0, 0, 170, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,.12)';
  ctx.lineWidth = 3;
  for (let r = 70; r < 165; r += 14) {
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.fillStyle = '#c8202a';
  ctx.beginPath();
  ctx.arc(0, 0, 58, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#f2c300';
  ctx.beginPath();
  ctx.arc(0, 0, 10, 0, Math.PI * 2);
  ctx.fill();
  ctx.rotate(-spin);
  outlinedText(ctx, 'REMIX', 0, 230, 70, '#f2c300', '#1a1410', 10);
  ctx.restore();
}

// ---- Plaza: the density counter rolls up as the camera cranes over the crowd
function counter(ctx, t) {
  const crane = word(5, 5), z = shotEnd('praca');
  if (t < crane || t >= z) return;
  const age = t - crane;
  const value = 67.9 * Math.min(1, age / 0.7) ** 0.6;
  const s = [0.7, 1.08, 1][Math.min(Math.floor(age * FPS), 2)];
  ctx.save();
  ctx.translate(W / 2, 360);
  ctx.scale(s, s);
  ctx.shadowColor = 'rgba(0,0,0,.45)';
  ctx.shadowBlur = 24;
  ctx.shadowOffsetY = 10;
  ctx.fillStyle = '#f2c300';
  ctx.beginPath();
  ctx.roundRect(-330, -150, 660, 300, 26);
  ctx.fill();
  ctx.shadowColor = 'rgba(0,0,0,0)';
  // Studs along the top, like the caption plates
  for (let i = 0; i < 8; i++) {
    const x = -280 + i * 80;
    ctx.fillStyle = '#b58f00';
    ctx.beginPath();
    ctx.ellipse(x, -150 + 4, 26, 11, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillRect(x - 26, -168, 52, 18);
    ctx.fillStyle = '#ffe65c';
    ctx.beginPath();
    ctx.ellipse(x, -168, 26, 11, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  outlinedText(ctx, value.toFixed(1).replace('.', ','), 0, -30, 170, '#ffffff', '#1a1410', 14);
  outlinedText(ctx, 'NOIA / M²', 0, 92, 72, '#25211a', '#f2c300', 2);
  ctx.restore();
}

// ---- Interrogation: the joint arrives with a sparkle
function sparkle(ctx, t, f) {
  const bas = word(6, 10);
  const p = at(f, 'joint');
  if (!p || t < bas || t > bas + 0.7) return;
  const age = t - bas;
  ctx.save();
  ctx.fillStyle = '#fff6c9';
  ctx.strokeStyle = 'rgba(0,0,0,.35)';
  ctx.lineWidth = 4;
  for (let i = 0; i < 5; i++) {
    const a = i * 1.26 + age * 3;
    const r = 70 + 90 * age;
    const s = (1 - age / 0.7) * (i % 2 ? 26 : 40);
    star(ctx, p[0] + Math.cos(a) * r, p[1] + Math.sin(a) * r, s, s * 0.35, 4, a);
    ctx.fill();
    ctx.stroke();
  }
  ctx.restore();
}

// ---- Bedroom: Zzz rises once he's down
function sleep(ctx, t, f) {
  const fall = word(7, 6), land = fall + 0.24;
  const p = at(f, 'pardo');
  if (!p || t < land) return;
  for (let i = 0; i < 3; i++) {
    const a = land + 0.12 + i * 0.3;
    if (t < a) continue;
    const u = (t - a) % 1.1;
    ctx.save();
    ctx.globalAlpha = 1 - u / 1.1;
    outlinedText(ctx, 'Z', p[0] + 60 + i * 50 + 18 * Math.sin(u * 5), p[1] - 70 - u * 260, 70 + i * 16, '#ffffff', '#2a3a7a', 9);
    ctx.restore();
  }
}

export function drawFx(ctx, v) {
  const t = v + TL.start;
  const f = Math.round(v * FPS) + 1;
  rant(ctx, t, f);
  pause(ctx, t);
  bubblePop(ctx, t, f);
  record(ctx, t);
  counter(ctx, t);
  sparkle(ctx, t, f);
  sleep(ctx, t, f);
}
