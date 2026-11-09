// The title card, the FIM card and the iris, drawn in Node (greys: the film pass tones them sepia).
//   titleCard(ctx, s)   s = seconds since the card came up    PARDINGOWS apresenta · PARDÃO e a ERVA on sunburst rays
//   fimCard(ctx, s)     FIM and PARDINGOWS on sunburst rays, fading to black over the last half second
//   iris(ctx, r, cx, cy) everything outside a circle goes black (r in pixels)
import { W, H } from './film.mjs';

function rays(ctx, s, cx, cy, light = '#d9d4c8', dark = '#a49e90', n = 28) {
  ctx.save();
  ctx.fillStyle = dark;
  ctx.fillRect(0, 0, W, H);
  ctx.translate(cx, cy);
  ctx.rotate(s * 0.25);
  ctx.fillStyle = light;
  const R = Math.hypot(W, H);
  for (let k = 0; k < n; k++) {
    const a = (k / n) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(Math.cos(a) * R, Math.sin(a) * R);
    ctx.lineTo(Math.cos(a + Math.PI / n) * R, Math.sin(a + Math.PI / n) * R);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}

function plaque(ctx, x, y, w, h, r) {
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.45)';
  ctx.shadowBlur = 30;
  ctx.shadowOffsetY = 14;
  ctx.fillStyle = '#f3efe4';
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fill();
  ctx.restore();
  ctx.strokeStyle = '#141008';
  ctx.lineWidth = 12;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.stroke();
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.roundRect(x + 22, y + 22, w - 44, h - 44, Math.max(0, r - 18));
  ctx.stroke();
}

function lettering(ctx, text, x, y, px, font, { fill = '#141008', stroke = null, sw = 0, shadow = true } = {}) {
  ctx.save();
  ctx.font = `${px}px ${font}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'alphabetic';
  if (shadow) {
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.fillText(text, x + px * 0.04, y + px * 0.05);
  }
  if (stroke) {
    ctx.lineJoin = 'round';
    ctx.lineWidth = sw;
    ctx.strokeStyle = stroke;
    ctx.strokeText(text, x, y);
  }
  ctx.fillStyle = fill;
  ctx.fillText(text, x, y);
  ctx.restore();
}

export function titleCard(ctx, s) {
  rays(ctx, s, W / 2, H * 0.47);
  const pop = Math.min(1, s / 0.25);
  const k = 1 + 0.12 * Math.sin(pop * Math.PI) * (1 - pop);
  ctx.save();
  ctx.translate(W / 2, H * 0.47);
  ctx.scale(k * pop + 0.0001, k * pop + 0.0001);
  ctx.translate(-W / 2, -H * 0.47);
  plaque(ctx, 90, H * 0.47 - 520, W - 180, 1040, 80);
  lettering(ctx, 'PARDINGOWS', W / 2, H * 0.47 - 360, 78, 'Limelight', { shadow: false });
  lettering(ctx, 'apresenta', W / 2, H * 0.47 - 280, 52, 'Abril', { shadow: false });
  lettering(ctx, 'PARDÃO', W / 2, H * 0.47 - 60, 160, 'Limelight', { fill: '#f3efe4', stroke: '#141008', sw: 24 });
  lettering(ctx, 'e a', W / 2, H * 0.47 + 70, 86, 'Abril', { shadow: false });
  lettering(ctx, 'ERVA', W / 2, H * 0.47 + 290, 210, 'Limelight', { fill: '#f3efe4', stroke: '#141008', sw: 28 });
  ctx.restore();
}

export function fimCard(ctx, s, total) {
  rays(ctx, s, W / 2, H * 0.45, '#cfc9bc', '#8f897c', 32);
  const pop = Math.min(1, s / 0.3);
  const k = pop + 0.15 * Math.sin(pop * Math.PI) * (1 - pop);
  ctx.save();
  ctx.translate(W / 2, H * 0.45);
  ctx.scale(k + 0.0001, k + 0.0001);
  ctx.fillStyle = '#141008';
  ctx.beginPath();
  ctx.arc(0, 0, 330, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#f3efe4';
  ctx.lineWidth = 10;
  ctx.beginPath();
  ctx.arc(0, 0, 300, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
  lettering(ctx, 'FIM', W / 2, H * 0.45 + 120 * k, 330 * k, 'Limelight', { fill: '#f3efe4', shadow: false });
  if (s > 0.35) lettering(ctx, 'PARDINGOWS', W / 2, H * 0.45 + 520, 96, 'Limelight', { fill: '#f3efe4', stroke: '#141008', sw: 18 });
  const out = Math.min(1, Math.max(0, (s - (total - 0.5)) / 0.5));
  if (out > 0) {
    ctx.fillStyle = `rgba(0,0,0,${out})`;
    ctx.fillRect(0, 0, W, H);
  }
}

export function iris(ctx, r, cx = W / 2, cy = H / 2) {
  ctx.save();
  ctx.fillStyle = '#000';
  ctx.beginPath();
  ctx.rect(-50, -50, W + 100, H + 100);
  ctx.arc(cx, cy, Math.max(0, r), 0, Math.PI * 2, true);
  ctx.fill('evenodd');
  // the iris's own soft edge ring, like a lens closing
  if (r > 2) {
    ctx.strokeStyle = 'rgba(0,0,0,0.6)';
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.restore();
}
