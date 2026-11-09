// 2D effects drawn onto the native 540x960 frame before the PS2 pass, so they get the same bloom and dither as the 3D.
// They track the 3D action through the anchors render_frames.py exports for the frame on screen (frames.json).
// Timing comes from cues.json, the same table Blender's shots.py uses.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const CUE = JSON.parse(fs.readFileSync(path.join(HERE, 'cues.json'), 'utf8'));
const W = 540, H = 960;
export const momentAt = t => { let i = 0; CUE.cuts.forEach((c, k) => { if (t >= c - 1e-6) i = k; }); return i; };
const since = (t, c) => t - c;
const ease = x => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };
// Deterministic noise so a re-render draws the same sparks
const hash = n => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
const BEAT = CUE.beat;
const beatsBetween = (a, b) => { const out = []; for (let k = 0; k < 400; k++) { const x = CUE.beat0 + k * BEAT; if (x >= a && x < b) out.push(x); } return out; };

function P(pts, name) {
  const p = pts?.[name];
  return p ? { x: p[0] * W, y: p[1] * H, z: p[2] } : null;
}

function star(ctx, x, y, r, n, fill, rot = 0, inner = 0.45) {
  ctx.beginPath();
  for (let i = 0; i < n * 2; i++) {
    const a = rot + (i * Math.PI) / n, rr = i % 2 ? r * inner : r;
    ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
  }
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
}

function glow(ctx, x, y, r, rgb, a) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, `rgba(${rgb},${a})`);
  g.addColorStop(1, `rgba(${rgb},0)`);
  ctx.fillStyle = g;
  ctx.fillRect(x - r, y - r, r * 2, r * 2);
}

function hitSpark(ctx, p, age, seed, big = 1) {
  if (!p || age < 0 || age > 0.18) return;
  const k = age / 0.18;
  glow(ctx, p.x, p.y, 50 * big * (1 - k * 0.5), '255,240,170', 0.9 * (1 - k));
  star(ctx, p.x, p.y, 34 * big * (1 - k * 0.4), 8, `rgba(255,255,255,${1 - k})`, hash(seed) * 3);
  star(ctx, p.x, p.y, 20 * big, 6, `rgba(255,210,60,${1 - k})`, hash(seed + 1) * 3);
}

function confetti(ctx, t, colors, n = 70, speed = 160) {
  for (let i = 0; i < n; i++) {
    const x = (hash(i) * W + Math.sin(t * 2 + i) * 18) % W;
    const y = ((hash(i + 99) * H + t * speed * (0.6 + hash(i + 7))) % (H + 40)) - 20;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(t * 5 + i);
    ctx.fillStyle = colors[i % colors.length];
    ctx.fillRect(-4, -2.5, 8, 5);
    ctx.restore();
  }
}

/** Whole-frame treatment for the moment: sway and double vision when stoned, black and white while dead. */
export function frameTransform(t) {
  const m = momentAt(t);
  if (m === 3 && t >= CUE.recoil) {
    const k = Math.min(1, (t - CUE.recoil) / 0.3);
    return { rot: 0.035 * k * Math.sin(t * 6), dx: 10 * k * Math.sin(t * 4.3), double: 0.35 * k, desat: 0 };
  }
  if (m === 7 && t >= CUE.gameover) return { rot: 0, dx: 0, double: 0, desat: 1, tint: [120, 0, 0, 0.25] };
  if (m === 8 && t < CUE.press) return { rot: 0, dx: 0, double: 0, desat: 0.9 };
  return null;
}

export function drawFX(ctx, t, pts) {
  const m = momentAt(t);
  ctx.save();
  if (m === 1 && t >= CUE.escuro) {
    // "!" over every Mildingow who can still see him
    for (const n of ['M1', 'M2', 'M3']) {
      const p = P(pts, n + '_head');
      if (!p) continue;
      const a = since(t, CUE.escuro), hop = a < 0.15 ? (1 - a / 0.15) * 14 : Math.sin(t * 12) * 2;
      ctx.font = 'bold 44px Bungee';
      ctx.textAlign = 'center';
      ctx.lineWidth = 6;
      ctx.strokeStyle = '#000';
      ctx.strokeText('!', p.x, p.y - 22 - hop);
      ctx.fillStyle = '#ffd400';
      ctx.fillText('!', p.x, p.y - 22 - hop);
    }
  }
  if (m === 3) {
    const item = P(pts, 'ITEM_baseado');
    if (item && t < CUE.grab) {
      glow(ctx, item.x, item.y, 40 + 6 * Math.sin(t * 14), '140,255,120', 0.7);
      for (let i = 0; i < 4; i++) star(ctx, item.x + Math.cos(t * 6 + i * 1.6) * 30, item.y + Math.sin(t * 6 + i * 1.6) * 30, 6, 4, 'rgba(255,255,220,.9)', t * 4);
    }
    const head = P(pts, 'P1_head');
    if (head && t >= CUE.grab) {
      // Smoke puffs drifting up from the mouth
      for (let i = 0; i < 9; i++) {
        const born = CUE.grab + i * 0.14, a = t - born;
        if (a < 0 || a > 1.2) continue;
        const r = 10 + a * 38;
        ctx.fillStyle = `rgba(215,225,215,${0.55 * (1 - a / 1.2)})`;
        ctx.beginPath();
        ctx.arc(head.x - 20 + Math.sin(i * 2 + t * 3) * 14, head.y + 30 - a * 90, r, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    if (t >= CUE.jab) hitSpark(ctx, P(pts, 'P1_hand'), t - CUE.jab - 0.06, 3, 1.3);
    if (head && t >= CUE.recoil) {
      for (let i = 0; i < 4; i++) {
        const a = t * 7 + (i * Math.PI) / 2;
        star(ctx, head.x + Math.cos(a) * 46, head.y - 30 + Math.sin(a) * 12, 11, 5, '#ffe14a', t * 3);
      }
    }
  }
  if (m === 4) {
    const r = P(pts, 'ITEM_radio');
    if (r && t >= CUE.radio_land) {
      for (const b of [CUE.radio_land, ...beatsBetween(CUE.radio_land + 0.1, CUE.cuts[5])]) {
        const a = t - b;
        if (a < 0 || a > 0.45) continue;
        const k = a / 0.45;
        ctx.strokeStyle = `rgba(120,240,255,${1 - k})`;
        ctx.lineWidth = 10 * (1 - k) + 2;
        ctx.beginPath();
        ctx.ellipse(r.x, r.y, 30 + k * 260, (30 + k * 260) * 0.38, 0, 0, Math.PI * 2);
        ctx.stroke();
      }
      for (let i = 0; i < 5; i++) {
        // Music notes rising off the boombox (drawn: the fonts have no note glyph)
        const a = (t * 0.9 + i * 0.2) % 1, x = r.x - 50 + i * 25, y = r.y - 40 - a * 130;
        ctx.fillStyle = ctx.strokeStyle = `rgba(255,230,90,${1 - a})`;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.ellipse(x, y, 7, 5, -0.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.moveTo(x + 6, y);
        ctx.lineTo(x + 6, y - 22);
        ctx.lineTo(x + 14, y - 16);
        ctx.stroke();
      }
    }
  }
  if (m === 5) {
    const hits = [167.80, 168.04, 168.27, 168.51, CUE.absurdo, ...[1, 2, 3, 4, 5, 6].map(k => CUE.absurdo + 0.118 * k)];
    hits.forEach((h, i) => hitSpark(ctx, P(pts, 'M1_chest') || P(pts, 'M1_head'), t - h, i, i >= 4 ? 1.4 : 1));
  }
  if (m === 7) {
    const fires = [0, 1, 2, 3, 4].map(i => CUE['fire' + i]);
    for (const n of ['M1', 'M2', 'M3']) {
      const p = P(pts, n + '_muzzle');
      if (!p) continue;
      fires.forEach((f, i) => {
        const a = t - f;
        if (a < 0 || a > 0.07) return;
        glow(ctx, p.x, p.y, 60, '255,200,90', 0.95);
        star(ctx, p.x, p.y, 26, 6, '#fff6c8', hash(i + n.length) * 3, 0.35);
      });
    }
  }
  if (m === 8 && t >= CUE.press && t < CUE.press + 0.12) {
    ctx.fillStyle = `rgba(255,255,255,${1 - (t - CUE.press) / 0.12})`;
    ctx.fillRect(0, 0, W, H);
  }
  if (m === 9 && t >= CUE.dance - 0.4) {
    const k = ease((t - CUE.dance + 0.4) / 0.5);
    for (const n of ['P1', 'P2', 'P3', 'P4']) {
      const c = P(pts, n + '_chest');
      if (!c) continue;
      glow(ctx, c.x, c.y + 10, 80 * k, '255,120,20', 0.55 * k);
      for (let i = 0; i < 6; i++) {
        const a = (t * 2.2 + i / 6) % 1;
        ctx.fillStyle = `rgba(255,${160 - a * 120},30,${(1 - a) * 0.8 * k})`;
        ctx.beginPath();
        const x = c.x - 30 + i * 12 + Math.sin(t * 9 + i) * 4, y = c.y + 70 - a * 120;
        ctx.moveTo(x - 7, y);
        ctx.lineTo(x + 7, y);
        ctx.lineTo(x, y - 26 * (1 - a));
        ctx.fill();
      }
    }
  }
  if (m === 11) confetti(ctx, t, ['#8a8a8a', '#6e6e6e', '#a29c8e'], 40, 60);
  if (m === 13) {
    if (t >= CUE.qte_press && t < CUE.impact + 0.2) {
      // Bullet-time speed lines
      ctx.strokeStyle = 'rgba(255,255,255,.35)';
      ctx.lineWidth = 2;
      for (let i = 0; i < 26; i++) {
        const a = hash(i) * Math.PI * 2, r0 = 200 + hash(i + 5) * 120;
        ctx.beginPath();
        ctx.moveTo(W / 2 + Math.cos(a) * r0, H * 0.45 + Math.sin(a) * r0);
        ctx.lineTo(W / 2 + Math.cos(a) * (r0 + 260), H * 0.45 + Math.sin(a) * (r0 + 260));
        ctx.stroke();
      }
    }
    hitSpark(ctx, P(pts, 'M1_chest'), t - CUE.impact, 9, 2.2);
    if (t >= CUE.impact && t < CUE.impact + 0.08) {
      ctx.fillStyle = 'rgba(255,255,255,.75)';
      ctx.fillRect(0, 0, W, H);
    }
  }
  if (m === 15) {
    const b = P(pts, 'JUMENTO_body');
    if (b && t >= CUE.charge && t < CUE.crash) {
      for (let i = 0; i < 10; i++) {
        // Dust kicked up around its hooves, drifting outwards whatever way it runs
        const a = (t * 3 + i / 10) % 1, ang = hash(i) * Math.PI * 2;
        ctx.fillStyle = `rgba(190,170,140,${0.5 * (1 - a)})`;
        ctx.beginPath();
        ctx.arc(b.x + Math.cos(ang) * (20 + a * 70), b.y + 45 + Math.sin(ang) * (8 + a * 20) - a * 18, 10 + a * 24, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    const h = P(pts, 'JUMENTO_head');
    hitSpark(ctx, h, t - CUE.crash, 21, 2.4);
    if (h && t >= CUE.crash + 0.1) {
      for (let i = 0; i < 5; i++) {
        const a = t * 6 + (i * Math.PI * 2) / 5;
        star(ctx, h.x + Math.cos(a) * 50, h.y - 40 + Math.sin(a) * 14, 12, 5, '#ffe14a', t * 3);
      }
    }
  }
  if (m === 16) confetti(ctx, t, ['#ff3b3b', '#ffd23f', '#3bd16f', '#3b7bff', '#ff6ad5'], 90, 200);
  ctx.restore();
}
