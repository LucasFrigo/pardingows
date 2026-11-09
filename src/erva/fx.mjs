// The 2D cartoon gags, drawn onto the picture before the film pass. Times come from the timeline's syllables; positions
// from the shot's anchors (frames.json pts: x, y as 0..1 of the frame), so the effects stick to the characters.
import { TL } from './ui.mjs';
import { W, H, rng } from './film.mjs';

const S = (c, r, w, k = 0) => TL.cards[c].rows[r][w][2][k];
const AD = c => (TL.cards[c].adlib || []).flatMap(w => w[2]);
const INK = '#120d08', PAPER = '#f4efe2';
const at = (pts, name) => (pts && pts[name] ? [pts[name][0] * W, pts[name][1] * H] : null);
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));

function word(ctx, text, x, y, px, { rot = 0, alpha = 1, font = 'Limelight', fill = PAPER } = {}) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.font = `${px}px ${font}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.lineWidth = px * 0.16;
  ctx.strokeStyle = INK;
  ctx.strokeText(text, 0, 0);
  ctx.fillStyle = fill;
  ctx.fillText(text, 0, 0);
  ctx.restore();
}

function star(ctx, x, y, r, rot = 0, alpha = 1) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.beginPath();
  for (let k = 0; k < 10; k++) {
    const a = (k / 10) * Math.PI * 2, rr = k % 2 ? r * 0.42 : r;
    ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
  }
  ctx.closePath();
  ctx.fillStyle = PAPER;
  ctx.fill();
  ctx.lineWidth = Math.max(3, r * 0.14);
  ctx.strokeStyle = INK;
  ctx.stroke();
  ctx.restore();
}

function burst(ctx, x, y, r0, r1, n, alpha = 1, width = 7) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = INK;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  for (let k = 0; k < n; k++) {
    const a = (k / n) * Math.PI * 2 + 0.3;
    ctx.beginPath();
    ctx.moveTo(x + Math.cos(a) * r0, y + Math.sin(a) * r0);
    ctx.lineTo(x + Math.cos(a) * r1, y + Math.sin(a) * r1);
    ctx.stroke();
  }
  ctx.restore();
}

function note(ctx, x, y, s, alpha) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.fillStyle = INK;
  ctx.beginPath();
  ctx.ellipse(0, 0, 14, 10, -0.4, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillRect(10, -56, 5, 56);
  ctx.beginPath();
  ctx.moveTo(15, -56);
  ctx.quadraticCurveTo(38, -40, 28, -18);
  ctx.lineWidth = 6;
  ctx.strokeStyle = INK;
  ctx.stroke();
  ctx.restore();
}

function drop(ctx, x, y, s, alpha) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.beginPath();
  ctx.moveTo(0, -22);
  ctx.quadraticCurveTo(14, 2, 0, 12);
  ctx.quadraticCurveTo(-14, 2, 0, -22);
  ctx.fillStyle = PAPER;
  ctx.fill();
  ctx.lineWidth = 4;
  ctx.strokeStyle = INK;
  ctx.stroke();
  ctx.restore();
}

function bolt(ctx, x0, seed, alpha) {
  const r = rng(seed);
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = PAPER;
  ctx.lineWidth = 14;
  ctx.lineJoin = 'miter';
  ctx.beginPath();
  let x = x0, y = -20;
  ctx.moveTo(x, y);
  while (y < H * 0.55) {
    x += (r() - 0.5) * 160;
    y += 70 + r() * 90;
    ctx.lineTo(x, y);
  }
  ctx.shadowColor = PAPER;
  ctx.shadowBlur = 30;
  ctx.stroke();
  ctx.restore();
}

export function drawFX(ctx, song, pts, frame) {
  const t = song;
  // musical notes drifting out of the gramophone, one a beat, in the storyteller's room
  const g = at(pts, 'gramophone');
  if (g && t < 54.4) {
    const beat = 0.4;
    for (let b = Math.floor((t - 1.2) / beat); b <= Math.floor(t / beat); b++) {
      const age = t - b * beat;
      if (age < 0 || age > 1.2) continue;
      const r = rng(b * 97);
      note(ctx, g[0] - age * 140 * (0.6 + r()), g[1] - age * 260, 0.9 + r() * 0.5, Math.min(1, (1.2 - age) * 2.5));
    }
  }
  // NHAM: the three puffs on the pipe, and the flowers' three sniffs
  for (const [card, anchor] of [[1, 'eva_mouth'], [5, 'p1_head']]) {
    const p = at(pts, anchor);
    if (!p) continue;
    AD(card).forEach((s, k) => {
      const a = t - s;
      if (a >= 0 && a < 0.5) word(ctx, 'NHAM', p[0] + (k - 1) * 120, p[1] - 90 - a * 160, 64 + a * 40, { rot: (k - 1) * 0.2, alpha: 1 - a / 0.5 });
    });
  }
  // the two giant steps hit the ground
  const feet = at(pts, 'p1_feet');
  for (const s of [S(3, 0, 2), S(3, 0, 4)]) {
    const a = t - s;
    if (feet && a >= 0 && a < 0.25) burst(ctx, feet[0], feet[1], 60 + a * 300, 110 + a * 400, 10, 1 - a / 0.25);
  }
  // POP: the jungle springs up
  const popT = S(3, 0, 4) + 0.05;
  if (t >= popT && t < popT + 0.35) {
    const a = (t - popT) / 0.35;
    burst(ctx, W / 2, H * 0.55, 200 + a * 600, 320 + a * 900, 18, 1 - a, 10);
    word(ctx, 'POP!', W / 2, H * 0.3, 150 + a * 80, { alpha: 1 - a, rot: -0.1 });
  }
  // a question mark in the smoke over his head
  const head = at(pts, 'p1_head');
  const qT = S(6, 1, 0);
  if (head && t >= qT && t < qT + 1.4) {
    const a = (t - qT) / 1.4;
    word(ctx, '?', head[0] + 70, head[1] - 120 - a * 120, 170, { alpha: Math.min(1, (1 - a) * 3), rot: Math.sin(t * 6) * 0.15 });
  }
  // KA-CHING! the register says it doesn't pay
  const reg = at(pts, 'register');
  const kT = S(8, 1, 3);
  if (reg && t >= kT && t < kT + 0.7) {
    const a = (t - kT) / 0.7;
    word(ctx, 'KA-CHING!', reg[0], reg[1] - 200 - a * 60, 100, { alpha: 1 - a * a, rot: -0.08 });
    for (let k = 0; k < 5; k++) {
      const ang = (k / 5) * Math.PI * 2 + a * 2;
      star(ctx, reg[0] + Math.cos(ang) * (120 + a * 80), reg[1] - 60 + Math.sin(ang) * (90 + a * 60), 26, a * 4, 1 - a);
    }
  }
  // whoosh lines as the soul is pulled out
  const sT = S(9, 1, 1);
  if (head && t >= sT && t < sT + 0.7) {
    const a = (t - sT) / 0.7;
    ctx.save();
    ctx.globalAlpha = 1 - a;
    ctx.strokeStyle = PAPER;
    ctx.lineWidth = 8;
    for (let k = -1; k <= 1; k++) {
      ctx.beginPath();
      ctx.moveTo(head[0] + k * 50, head[1] + 60);
      ctx.quadraticCurveTo(head[0] + k * 80 + 40, head[1] - 80, head[0] + k * 30 + 90, head[1] - 220 - a * 100);
      ctx.stroke();
    }
    ctx.restore();
  }
  // the laugh: lightning on each group, HA and HO flying out of the mouth on every syllable
  const groups = [[11, 0, 0], [11, 0, 1], [11, 1, 0], [11, 1, 1]];
  groups.forEach(([c, r, w], gi) => {
    const g0 = S(c, r, w, 0);
    const a = t - g0;
    if (a >= 0 && a < 2 / 24) {
      ctx.fillStyle = 'rgba(255,252,240,0.55)';
      ctx.fillRect(0, 0, W, H);
    }
    if (a >= 0 && a < 3 / 24) bolt(ctx, W * (0.2 + 0.6 * rng(gi * 13)()), gi * 71 + 5, 1 - a * 6);
  });
  const mouthP = at(pts, 'cobra_mouth');
  if (mouthP) {
    groups.forEach(([c, r, w], gi) => {
      TL.cards[c].rows[r][w][2].forEach((s, k) => {
        const a = t - s;
        if (a < 0 || a > 0.6) return;
        const rr = rng(gi * 10 + k);
        const ang = -Math.PI / 2 + (rr() - 0.5) * 1.8;
        const dist = 120 + a * 700;
        word(ctx, gi === 0 || gi === 3 ? 'HA' : 'HO', mouthP[0] + Math.cos(ang) * dist, mouthP[1] + Math.sin(ang) * dist,
          90 + a * 120, { alpha: 1 - a / 0.6, rot: (rr() - 0.5) * 0.6 });
      });
    });
  }
  // BOING: the soul snaps back into him
  const bT = S(12, 0, 0);
  if (head && t >= bT && t < bT + 0.35) {
    const a = (t - bT) / 0.35;
    burst(ctx, head[0], head[1] + 120, 90 + a * 200, 160 + a * 260, 12, 1 - a);
    word(ctx, 'BOING!', head[0], head[1] - 140, 110, { alpha: 1 - a, rot: 0.1 });
  }
  // the cobra sweats while he raps at it
  const ch = at(pts, 'cobra_head');
  const rapT = S(14, 1, 0);
  if (ch && t >= rapT && t < 96.0) {
    for (let k = 0; k < 8; k++) {
      const born = rapT + k * 0.25;
      const a = t - born;
      if (a < 0 || a > 0.5) continue;
      const side = k % 2 ? 1 : -1;
      drop(ctx, ch[0] + side * (50 + a * 220), ch[1] - 40 - a * 120 + a * a * 600, 1.2, 1 - a / 0.5);
    }
  }
  // dizzy stars round its head as it goes for the bait
  const dz0 = S(15, 1, 0);
  if (ch && t >= dz0 && t < S(15, 1, 4, 3)) {
    for (let k = 0; k < 3; k++) {
      const ang = t * 7 + (k / 3) * Math.PI * 2;
      star(ctx, ch[0] + Math.cos(ang) * 90, ch[1] - 70 + Math.sin(ang) * 26, 22, ang);
    }
  }
  // SNAP! the box comes down
  const tr = at(pts, 'trap');
  const dT = S(15, 1, 4, 3);
  if (tr && t >= dT && t < dT + 0.3) {
    const a = (t - dT) / 0.3;
    burst(ctx, tr[0], tr[1] + 40, 140 + a * 200, 220 + a * 260, 14, 1 - a, 9);
    word(ctx, 'SNAP!', tr[0], tr[1] - 230, 130, { alpha: 1 - a, rot: -0.12 });
  }
}
