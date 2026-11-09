// The game's interface at 1080x1920, drawn after the PS2 pass so it stays crisp: the 4-player bar, enemy and boss bars,
// combo counter, banners and the full-screen game screens (game over, continue, week map, move list, results).
// Everything is a function of song time t, the cues and the anchors of the frame on screen.
// Safe area: x 40..910 (TikTok's buttons sit right of 918), y 200..1250 (captions below, TikTok's top bar above).
import { CUE, momentAt } from './fx.mjs';

const W = 1080, H = 1920;
const ease = x => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };
const back = x => { x = Math.max(0, Math.min(1, x)); const c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2; };
const blink = (t, hz = 3) => Math.floor(t * hz * 2) % 2 === 0;
const PLAYERS = [
  { id: 'P1', name: 'PARDO', cap: '#f4f4f4', join: -1 },
  { id: 'P2', name: 'PJHONSON', cap: '#d8262c', join: CUE.p2_land },
  { id: 'P3', name: 'AZUL', cap: '#2a62d8', join: CUE.p3_land },
  { id: 'P4', name: 'VERDE', cap: '#2fa84a', join: CUE.p4_land },
];
const HITS = [167.80, 168.04, 168.27, 168.51, CUE.absurdo, ...[1, 2, 3, 4, 5, 6].map(k => CUE.absurdo + 0.118 * k)];

function txt(ctx, s, x, y, size, fill, { font = 'Bungee', stroke = '#0a0a14', lw = size * 0.16, align = 'center', base = 'middle' } = {}) {
  ctx.font = `${size}px ${font}`;
  ctx.textAlign = align;
  ctx.textBaseline = base;
  ctx.lineJoin = 'round';
  if (lw) {
    ctx.lineWidth = lw;
    ctx.strokeStyle = stroke;
    ctx.strokeText(s, x, y);
  }
  ctx.fillStyle = fill;
  ctx.fillText(s, x, y);
}

function grad(ctx, y0, y1, a, b) {
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  g.addColorStop(0, a);
  g.addColorStop(1, b);
  return g;
}

function panel(ctx, x, y, w, h, alpha = 0.82, r = 16) {
  ctx.save();
  ctx.fillStyle = grad(ctx, y, y + h, `rgba(26,48,116,${alpha})`, `rgba(6,12,40,${alpha + 0.06})`);
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fill();
  ctx.lineWidth = 5;
  ctx.strokeStyle = grad(ctx, y, y + h, '#f4f8ff', '#8aa2c8');
  ctx.stroke();
  ctx.restore();
}

function portrait(ctx, x, y, s, cap, grey = false) {
  ctx.save();
  ctx.fillStyle = '#10152c';
  ctx.fillRect(x, y, s, s);
  ctx.beginPath();
  ctx.rect(x, y, s, s);
  ctx.clip();
  ctx.fillStyle = grey ? '#666' : '#8a4a22';
  ctx.beginPath();
  ctx.arc(x + s * 0.5, y + s * 0.68, s * 0.34, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(x + s * 0.17, y + s * 0.6, s * 0.12, 0, Math.PI * 2);
  ctx.arc(x + s * 0.83, y + s * 0.6, s * 0.12, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = grey ? '#999' : cap;
  ctx.beginPath();
  ctx.moveTo(x + s * 0.12, y + s * 0.52);
  ctx.quadraticCurveTo(x + s * 0.3, y + s * 0.02, x + s * 0.72, y + s * 0.1);
  ctx.quadraticCurveTo(x + s * 0.98, y + s * 0.3, x + s * 0.88, y + s * 0.52);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#05060c';
  ctx.fillRect(x + s * 0.2, y + s * 0.55, s * 0.6, s * 0.11);
  ctx.restore();
  ctx.lineWidth = 3;
  ctx.strokeStyle = '#e8eefc';
  ctx.strokeRect(x, y, s, s);
}

function bar(ctx, x, y, w, h, v, colA = '#7dff6a', colB = '#ffd23f', ghost = null) {
  ctx.fillStyle = '#05060c';
  ctx.fillRect(x - 3, y - 3, w + 6, h + 6);
  ctx.fillStyle = '#3a1010';
  ctx.fillRect(x, y, w, h);
  if (ghost !== null && ghost > v) {
    ctx.fillStyle = '#ff5a3c';
    ctx.fillRect(x, y, w * ghost, h);
  }
  ctx.fillStyle = grad(ctx, y, y + h, v > 0.3 ? colA : '#ff4a3c', v > 0.3 ? colB : '#b01818');
  ctx.fillRect(x, y, w * Math.max(0, v), h);
  ctx.fillStyle = 'rgba(255,255,255,.35)';
  ctx.fillRect(x, y, w * Math.max(0, v), h * 0.3);
}

// ---------------------------------------------------------------- game state over time
function health(id, t) {
  let h = 1.0;
  if (id === 'P1' && t >= CUE.recoil) h -= 0.12;   // punched a lamp post
  if (t >= CUE.cuts[6] && t < CUE.press) h -= 0.35 * ease((t - CUE.enquadram) / 0.4);
  if (t >= CUE.fire0 && t < CUE.press) h -= 0.6 * ease((t - CUE.fire0) / (CUE.gameover - CUE.fire0));
  if (t >= CUE.gameover && t < CUE.press) h = 0;
  if (t >= CUE.press) h = ease((t - CUE.press) / 0.5);
  if (id === 'P1' && t >= CUE.grab && t < CUE.cuts[6]) h = Math.min(1, h + 0.1);
  return Math.max(0, Math.min(1, h));
}

function score(t) {
  let s = 1200;
  s += HITS.filter(h => h <= t).length * 1500;
  if (t >= CUE.absurdo) s += 99900;
  if (t >= CUE.radio_land) s += 5000;
  if (t >= CUE.impact) s += 25000;
  if (t >= CUE.crash) s += 200000;
  if (t >= CUE.cuts[16]) s += Math.min(1, (t - CUE.cuts[16]) / 0.6) * 47000;
  return Math.floor(s);
}

function playerBar(ctx, t) {
  PLAYERS.forEach((p, i) => {
    const x = 40 + i * 218, y = 206;
    const joined = t >= p.join;
    panel(ctx, x, y, 206, 120, 0.7, 12);
    portrait(ctx, x + 10, y + 12, 62, p.cap, !joined);
    if (!joined) {
      if (blink(t, 2)) txt(ctx, 'PRESS', x + 140, y + 44, 26, '#ffe45a');
      if (blink(t, 2)) txt(ctx, 'START', x + 140, y + 78, 26, '#ffe45a');
      return;
    }
    const pop = p.join > 0 ? back((t - p.join) / 0.25) : 1;
    ctx.save();
    ctx.translate(x + 103, y + 60);
    ctx.scale(pop, pop);
    ctx.translate(-(x + 103), -(y + 60));
    txt(ctx, p.name, x + 82, y + 30, 22, p.cap === '#f4f4f4' ? '#ffffff' : p.cap, { align: 'left', lw: 5 });
    const h = health(p.id, t);
    bar(ctx, x + 82, y + 54, 112, 16, h, '#7dff6a', '#2fae2f', health(p.id, t - 0.25));
    txt(ctx, i === 0 ? String(score(t)).padStart(7, '0') : String(Math.floor(score(t) * (0.4 + i * 0.13))).padStart(7, '0'), x + 82, y + 94, 20, '#ffffff', { align: 'left', font: 'Russo', lw: 4 });
    ctx.restore();
  });
}

function enemyBar(ctx, t, name, v, y = 346, w = 520) {
  const x = 40;
  panel(ctx, x, y, w + 40, 76, 0.7, 10);
  txt(ctx, name, x + 20, y + 24, 24, '#ff8a8a', { align: 'left', lw: 5 });
  bar(ctx, x + 20, y + 44, w, 18, v, '#ff6a3c', '#c81e1e');
}

function banner(ctx, t, t0, lines, { y = 640, colors = ['#ffe45a', '#ff8a1e'], size = 96, stripes = false, shake = 0 } = {}) {
  const a = t - t0;
  if (a < 0) return;
  const k = back(a / 0.22);
  ctx.save();
  ctx.translate(W / 2 - 80 + (shake ? Math.sin(t * 60) * shake : 0), y);
  ctx.scale(k, k);
  if (stripes) {
    ctx.save();
    ctx.fillStyle = '#ffd400';
    ctx.fillRect(-470, -size * lines.length * 0.62, 940, size * lines.length * 1.24);
    ctx.beginPath();
    ctx.rect(-470, -size * lines.length * 0.62, 940, size * lines.length * 1.24);
    ctx.clip();
    ctx.fillStyle = '#111';
    for (let i = -20; i < 20; i++) {
      ctx.beginPath();
      ctx.moveTo(i * 70 + ((t * 200) % 70), -300);
      ctx.lineTo(i * 70 + 35 + ((t * 200) % 70), -300);
      ctx.lineTo(i * 70 - 165 + ((t * 200) % 70), 300);
      ctx.lineTo(i * 70 - 200 + ((t * 200) % 70), 300);
      ctx.fill();
    }
    ctx.restore();
  }
  lines.forEach((s, i) => {
    const yy = (i - (lines.length - 1) / 2) * size * 1.08;
    const g = grad(ctx, yy - size / 2, yy + size / 2, colors[0], colors[1]);
    txt(ctx, s, 0, yy, size, g, { lw: size * 0.18 });
  });
  ctx.restore();
}

function dim(ctx, a) {
  ctx.fillStyle = `rgba(4,6,16,${a})`;
  ctx.fillRect(0, 0, W, H);
}

const A2 = (pts, n) => (pts?.[n] ? { x: pts[n][0] * W, y: pts[n][1] * H } : null);

function bubble(ctx, p, s, t0, t) {
  if (!p || t < t0) return;
  const k = back((t - t0) / 0.18);
  const x = Math.max(260, Math.min(700, p.x)), y = Math.max(420, p.y - 170);
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  ctx.fillStyle = '#fff';
  ctx.strokeStyle = '#111';
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.roundRect(-230, -62, 460, 124, 40);
  ctx.moveTo(-30, 60);
  ctx.lineTo(10, 120);
  ctx.lineTo(40, 60);
  ctx.fill();
  ctx.stroke();
  ctx.fillRect(-28, 54, 64, 12);
  txt(ctx, s, 0, 4, 58, '#d01818', { lw: 0 });
  ctx.restore();
}

// ---------------------------------------------------------------- per-moment screens
const DAYS = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM'];
const LOST = ['PASSINHO DOS PARDOS', 'BANGER NOVO DE TERÇA', 'COMBO DE 999 HITS', 'PARDJHONSON NO MIC', 'O JUMENTO CAINDO',
  'AQUECIMENTO COMPLETO', 'BAILE ATÉ DE MANHÃ', 'O PARDO SE DESCOBRINDO', 'BASEADO DO POSTE', 'TERÇA DOS PARDOS'];
// Inputs as tokens: arrows by direction, buttons X O T(riangle) S(quare). The fonts have none of these glyphs, so they're drawn.
const MOVES = [['D DR R X', 'PASSINHO SINISTRO'], ['R R O', 'RASTEIRA DO MORRO'], ['D U T', 'VOADORA DE TERÇA'], ['L DL D X', 'BOLADÃO SUPREMO'],
  ['X X X', 'PAREDÃO SÔNICO'], ['D D S', 'CHINELADA FANTASMA'], ['R D DR T', 'MALANDRAGEM CARIOCA'], ['S T O', 'SOTAQUE DESTRUIDOR'],
  ['U U D D', 'FUGA DA BLITZ'], ['O O X', 'AQUECIMENTO INFINITO'], ['DL R S', 'PARDO INVISÍVEL'], ['T O X S', 'BANGER NA CARA']];
const ARROW = { R: 0, DR: 45, D: 90, DL: 135, L: 180, UL: 225, U: 270, UR: 315 };

function button(ctx, kind, x, y, s) {
  const col = { X: '#7fb6ff', O: '#ff6a6a', T: '#6aff9e', S: '#ff9ee8' }[kind];
  ctx.save();
  ctx.fillStyle = '#10152c';
  ctx.beginPath();
  ctx.arc(x, y, s, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = Math.max(2, s * 0.12);
  ctx.strokeStyle = '#e8eefc';
  ctx.stroke();
  ctx.strokeStyle = col;
  ctx.lineWidth = Math.max(3, s * 0.2);
  ctx.lineCap = 'round';
  const r = s * 0.5;
  ctx.beginPath();
  if (kind === 'X') { ctx.moveTo(x - r, y - r); ctx.lineTo(x + r, y + r); ctx.moveTo(x + r, y - r); ctx.lineTo(x - r, y + r); }
  if (kind === 'O') ctx.arc(x, y, r, 0, Math.PI * 2);
  if (kind === 'T') { ctx.moveTo(x, y - r); ctx.lineTo(x + r, y + r * 0.75); ctx.lineTo(x - r, y + r * 0.75); ctx.closePath(); }
  if (kind === 'S') ctx.rect(x - r * 0.8, y - r * 0.8, r * 1.6, r * 1.6);
  ctx.stroke();
  ctx.restore();
}

function arrow(ctx, dir, x, y, s) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate((ARROW[dir] * Math.PI) / 180);
  ctx.fillStyle = '#ffe45a';
  ctx.strokeStyle = '#0a0a14';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(s, 0);
  ctx.lineTo(0, -s * 0.8);
  ctx.lineTo(0, -s * 0.35);
  ctx.lineTo(-s, -s * 0.35);
  ctx.lineTo(-s, s * 0.35);
  ctx.lineTo(0, s * 0.35);
  ctx.lineTo(0, s * 0.8);
  ctx.closePath();
  ctx.stroke();
  ctx.fill();
  ctx.restore();
}

function inputs(ctx, seq, x, y, s = 13) {
  for (const tok of seq.split(' ')) {
    if (ARROW[tok] !== undefined) arrow(ctx, tok, x + s, y, s);
    else button(ctx, tok, x + s, y, s);
    x += s * 2.6;
  }
}

function starShape(ctx, x, y, r, fill) {
  ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / 5, rr = i % 2 ? r * 0.45 : r;
    ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
  }
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = '#0a0a14';
  ctx.stroke();
}

function check(ctx, x, y, s) {
  ctx.save();
  ctx.strokeStyle = '#7dff6a';
  ctx.lineWidth = 6;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(x - s * 0.5, y);
  ctx.lineTo(x - s * 0.1, y + s * 0.4);
  ctx.lineTo(x + s * 0.6, y - s * 0.5);
  ctx.stroke();
  ctx.restore();
}

export function drawHUD(ctx, t, pts) {
  const m = momentAt(t);
  const fullScreen = m === 10 || m === 12 || (m === 7 && t >= CUE.gameover) || (m === 8 && t < CUE.press);
  ctx.save();

  if (m === 14) {
    // Cutscene letterbox, clear of the captions
    const k = ease((t - CUE.cuts[14]) / 0.2);
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, 300 * k);
    ctx.fillRect(0, H - 360 * k, W, 360 * k);
  }
  if (m === 10 || m === 12) dim(ctx, 0.72);
  if (m === 7 && t >= CUE.gameover) dim(ctx, 0.45 * ease((t - CUE.gameover) / 0.15));

  if (!fullScreen && m !== 14) playerBar(ctx, t);

  // 1. Title, then the character card
  if (m === 0) {
    const a = 1 - ease((t - CUE.descobri + 0.3) / 0.3);
    if (a > 0) {
      ctx.globalAlpha = a;
      txt(ctx, 'PARDÃO', 470, 520, 150, grad(ctx, 450, 590, '#fff2a0', '#ff9a1e'), { lw: 26 });
      txt(ctx, '2000', 470, 660, 130, grad(ctx, 600, 720, '#7fe0ff', '#2a62d8'), { lw: 22 });
      txt(ctx, 'PRESS START', 470, 800, 44, '#ffffff', { lw: 8 });
      ctx.globalAlpha = 1;
    }
    if (t >= CUE.descobri) {
      const k = back((t - CUE.descobri) / 0.3);
      const x = 400 + (1 - k) * 600, y = 420;
      panel(ctx, x, y, 500, 430, 0.85);
      txt(ctx, 'NOVO PERSONAGEM', x + 250, y + 46, 30, '#ffe45a', { lw: 6 });
      portrait(ctx, x + 24, y + 86, 130, '#f4f4f4');
      txt(ctx, 'PARDO', x + 330, y + 128, 64, '#ffffff', { lw: 10 });
      txt(ctx, 'NEW!', x + 330, y + 190, 40, '#ff5a3c', { lw: 7 });
      [['MALANDRAGEM', 0.99], ['BAILE', 0.99], ['SONO', 0.0], ['ESCURO', 0.0]].forEach(([s, v], i) => {
        const yy = y + 260 + i * 42;
        txt(ctx, s, x + 30, yy, 24, '#ffffff', { align: 'left', font: 'Russo', lw: 4 });
        bar(ctx, x + 250, yy - 10, 220, 20, v * ease((t - CUE.descobri - 0.2 - i * 0.12) / 0.3), '#7fe0ff', '#2a62d8');
      });
    }
  }
  // 2. Stealth readout in the blackout
  if (m === 1 && t >= CUE.escuro) {
    const k = back((t - CUE.escuro) / 0.2);
    ctx.save();
    ctx.translate(470, 470);
    ctx.scale(k, k);
    panel(ctx, -230, -54, 460, 108, 0.85);
    txt(ctx, 'STEALTH  0%', 0, 0, 52, blink(t, 4) ? '#ff5a3c' : '#ffe45a', { lw: 9 });
    ctx.restore();
  }
  // 3. Joining players
  if (m === 2) {
    PLAYERS.slice(1).forEach((p, i) => {
      const a = t - p.join;
      if (a < 0 || a > 0.9) return;
      txt(ctx, `${p.id} ENTROU!`, 470, 560 + i * 90, 66, p.cap, { lw: 12 });
    });
  }
  // 4. The joint: +HP, INT -99, OUCH
  if (m === 3) {
    const head = A2(pts, 'P1_head');
    if (head && t >= CUE.grab) {
      const a = t - CUE.grab;
      txt(ctx, '+HP', head.x - 120, head.y - 60 - a * 80, 54, '#7dff6a', { lw: 9 });
      if (a > 0.3) txt(ctx, 'INT -99', head.x + 70, head.y - 30 - (a - 0.3) * 70, 54, '#ff4a3c', { lw: 9 });
    }
    if (t >= CUE.recoil) banner(ctx, t, CUE.recoil, ['BURRO!'], { y: 560, colors: ['#ffb0ff', '#b44aff'], size: 110, shake: 6 });
  }
  // 5. Tuesday stage card
  if (m === 4) {
    if (t < CUE.cuts[4] + 1.05) banner(ctx, t, CUE.cuts[4], ['TERÇA-FEIRA', 'NOVO BANGER!'], { y: 600, size: 92, stripes: true, colors: ['#ff3b3b', '#a00000'] });
    const knocked = t >= CUE.radio_land + 0.3;
    if (knocked) enemyBar(ctx, t, 'MILDINGOWS', 1 - 0.18 * Math.floor((t - CUE.radio_land) / CUE.beat));
  }
  // 6. Combo
  if (m === 5) {
    const n = HITS.filter(h => h <= t).length;
    if (n > 0) {
      const last = Math.max(...HITS.filter(h => h <= t));
      const shown = t >= CUE.absurdo ? 999 : n;
      const pop = 1 + 0.35 * Math.max(0, 1 - (t - last) / 0.12);
      ctx.save();
      ctx.translate(700, 700);
      ctx.scale(pop, pop);
      txt(ctx, String(shown), 0, 0, 150, grad(ctx, -70, 70, '#fff6a0', '#ff6a1e'), { lw: 22 });
      txt(ctx, 'HITS', 0, 100, 56, '#ffffff', { lw: 10 });
      ctx.restore();
      enemyBar(ctx, t, 'MILDINGOW', Math.max(0, 1 - n * 0.09));
    }
    if (t >= CUE.absurdo) banner(ctx, t, CUE.absurdo, ['ABSURDO!!'], { y: 980, size: 120, colors: ['#ffe45a', '#ff2a2a'], shake: 8 });
  }
  // 7. Horde warning
  if (m === 6 && t < CUE.enquadram) {
    if (blink(t, 4)) {
      ctx.fillStyle = 'rgba(200,0,0,.35)';
      ctx.fillRect(0, 0, W, H);
    }
    banner(ctx, t, CUE.cuts[6], ['WARNING!'], { y: 560, size: 120, colors: ['#ffffff', '#ff4a3c'] });
    banner(ctx, t, CUE.cuts[6] + 0.25, ['MILDINGOWS', 'x1000'], { y: 800, size: 84, colors: ['#ffe45a', '#ff8a1e'] });
  }
  if (m === 6 && t >= CUE.enquadram) banner(ctx, t, CUE.enquadram, ['ENQUADRADOS!'], { y: 560, size: 84, colors: ['#ffffff', '#ff8a8a'] });
  // 8. Game over
  if (m === 7 && t >= CUE.gameover) {
    const a = t - CUE.gameover;
    'GAME'.split('').forEach((c, i) => {
      const d = Math.max(0, Math.min(1, (a - i * 0.04) / 0.18));
      txt(ctx, c, 220 + i * 120, 560 - (1 - back(d)) * 500, 150, grad(ctx, 480, 640, '#ff8a8a', '#a00000'), { lw: 22 });
    });
    'OVER'.split('').forEach((c, i) => {
      const d = Math.max(0, Math.min(1, (a - 0.12 - i * 0.04) / 0.18));
      txt(ctx, c, 220 + i * 120, 740 - (1 - back(d)) * 600, 150, grad(ctx, 660, 820, '#ff8a8a', '#a00000'), { lw: 22 });
    });
    bubble(ctx, { x: 470, y: 1110 }, 'SÓ LAMENTO!', CUE.lamento, t);  // fixed under GAME OVER, clear of the letters
  }
  // 9. Continue
  if (m === 8) {
    if (t < CUE.press) {
      dim(ctx, 0.35);
      txt(ctx, 'CONTINUE?', 470, 520, 110, grad(ctx, 460, 580, '#ffffff', '#7fe0ff'), { lw: 18 });
      const n = t < CUE.cont8 ? 9 : 8;
      const since = t - (n === 9 ? CUE.cont9 : CUE.cont8);
      const pop = 1 + 0.4 * Math.max(0, 1 - since / 0.15);
      ctx.save();
      ctx.translate(470, 760);
      ctx.scale(pop, pop);
      txt(ctx, String(n), 0, 0, 260, grad(ctx, -120, 120, '#ffe45a', '#ff6a1e'), { lw: 30 });
      ctx.restore();
      if (blink(t, 3)) txt(ctx, 'INSERT COIN', 470, 980, 52, '#ffffff', { lw: 9 });
    } else {
      if (t < CUE.press + 0.45) txt(ctx, 'READY!', 470, 520, 100, '#7dff6a', { lw: 16 });
      banner(ctx, t, CUE.press + 0.05, ['ATENÇÃO!'], { y: 740, size: 120, stripes: true, colors: ['#ff2a2a', '#7a0000'], shake: blink(t, 6) ? 4 : 0 });
    }
  }
  // 10. Warm-up super meter
  if (m === 9) {
    const k = ease((t - CUE.cuts[9]) / (CUE.dance - CUE.cuts[9]));
    panel(ctx, 70, 380, 800, 120, 0.8);
    txt(ctx, 'AQUECIMENTO', 110, 418, 40, '#ffb04a', { align: 'left', lw: 7 });
    bar(ctx, 110, 448, 640, 30, k, '#ffd23f', '#ff4a1e');
    if (t >= CUE.dance) txt(ctx, 'MAX!', 812, 462, 48, blink(t, 5) ? '#ffffff' : '#ff4a1e', { lw: 8 });
  }
  // 11. The week map
  if (m === 10) {
    txt(ctx, 'SEMANA DOS PARDOS', 470, 300, 62, grad(ctx, 270, 330, '#fff2a0', '#ff9a1e'), { lw: 11 });
    const nodes = DAYS.map((d, i) => ({ d, x: 130 + (i % 2 ? 560 : 120) + (i % 2 ? 0 : 60 * Math.sin(i)), y: 390 + i * 92 }));
    ctx.lineWidth = 10;
    ctx.strokeStyle = '#c8b27a';
    ctx.setLineDash([22, 16]);
    ctx.beginPath();
    nodes.forEach((n, i) => (i ? ctx.lineTo(n.x, n.y) : ctx.moveTo(n.x, n.y)));
    ctx.stroke();
    ctx.setLineDash([]);
    const onTer = t >= CUE.terca;
    nodes.forEach((n, i) => {
      const hot = i === 1 && onTer;
      ctx.fillStyle = hot ? '#ffd23f' : i === 1 ? '#ff8a1e' : '#30406a';
      ctx.beginPath();
      ctx.arc(n.x, n.y, hot ? 54 + 6 * Math.sin(t * 12) : 40, 0, Math.PI * 2);
      ctx.fill();
      ctx.lineWidth = 6;
      ctx.strokeStyle = '#fff';
      ctx.stroke();
      txt(ctx, n.d, n.x, n.y, hot ? 34 : 28, '#ffffff', { lw: 6 });
    });
    const cursorFrom = nodes[0], cursorTo = nodes[1];
    const k = ease((t - (CUE.terca - 0.35)) / 0.3);
    const cx = cursorFrom.x + (cursorTo.x - cursorFrom.x) * k, cy = cursorFrom.y + (cursorTo.y - cursorFrom.y) * k;
    portrait(ctx, cx + 52, cy - 36 + Math.sin(t * 8) * 6, 72, '#f4f4f4');
    if (onTer) {
      panel(ctx, 300, 520 - 40, 560, 90, 0.9);
      txt(ctx, 'TERÇA DOS PARDOS', 580, 525, 38, '#ffe45a', { lw: 7 });
      starShape(ctx, 330, 525, 20, '#ffe45a');
      starShape(ctx, 830, 525, 20, '#ffe45a');
    }
    if (t >= CUE.cola) {
      const kk = back((t - CUE.cola) / 0.25);
      ctx.save();
      ctx.translate(560, 1080);
      ctx.scale(kk, kk);
      panel(ctx, -300, -70, 600, 140, 0.9);
      portrait(ctx, -280, -52, 104, '#666', true);
      txt(ctx, 'MILDINGOW 3', -150, -22, 34, '#bbbbbb', { align: 'left', lw: 6 });
      txt(ctx, 'DISCONNECTED', -150, 30, 38, '#ff5a3c', { align: 'left', lw: 7 });
      ctx.restore();
    }
  }
  // 12. Stage clear, and everything Mildingow 3 missed
  if (m === 11) {
    banner(ctx, t, CUE.cuts[11] + 0.15, ['STAGE CLEAR'], { y: 470, size: 96, colors: ['#fff2a0', '#d4a01e'] });
    if (t >= CUE.lista - 0.4) {
      const k = ease((t - CUE.lista + 0.4) / 0.25);
      panel(ctx, 90, 600, 780, 560 * k, 0.88);
      if (k > 0.9) {
        txt(ctx, 'VOCÊ PERDEU:', 480, 650, 46, '#ff8a8a', { lw: 8 });
        ctx.save();
        ctx.beginPath();
        ctx.rect(100, 690, 760, 380);
        ctx.clip();
        const scroll = (t - CUE.lista) * 260;
        LOST.concat(LOST).forEach((s, i) => {
          const y = 720 + i * 56 - scroll;
          check(ctx, 140, y, 22);
          txt(ctx, s, 175, y, 30, '#ffffff', { align: 'left', font: 'Russo', lw: 5 });
        });
        ctx.restore();
        const n = Math.max(0, Math.min(47, Math.floor((t - CUE.lista) * 60)));
        txt(ctx, `${n} ACONTECIMENTOS`, 480, 1110, 48, '#ffe45a', { lw: 8 });
      }
    }
  }
  // 13. Pause: the move list
  if (m === 12) {
    txt(ctx, 'PAUSE', 470, 280, 70, '#ffffff', { lw: 12 });
    panel(ctx, 60, 340, 820, 860, 0.9);
    txt(ctx, 'LISTA DE GOLPES', 470, 392, 48, '#ffe45a', { lw: 8 });
    ctx.save();
    ctx.beginPath();
    ctx.rect(70, 430, 800, 680);
    ctx.clip();
    const speed = t < CUE.ideias ? 120 : 900;
    const scroll = (t - CUE.cuts[12]) * speed + (t >= CUE.ideias ? -(CUE.ideias - CUE.cuts[12]) * (900 - 120) : 0);
    for (let i = 0; i < 80; i++) {
      const [inp, name] = MOVES[i % MOVES.length];
      const y = 470 + i * 64 - scroll;
      if (y < 400 || y > 1150) continue;
      txt(ctx, `${String(i + 1).padStart(3, '0')}`, 100, y, 26, '#8aa2c8', { align: 'left', font: 'Russo', lw: 4 });
      inputs(ctx, inp, 180, y, 13);
      txt(ctx, name, 400, y, 30, '#ffffff', { align: 'left', font: 'Russo', lw: 5 });
    }
    ctx.restore();
    const count = t < CUE.ideias ? 12 : Math.min(1000, 12 + Math.floor((t - CUE.ideias) * 900));
    txt(ctx, `${count} / 1000 GOLPES NOVOS`, 470, 1160, 40, '#ffe45a', { lw: 7 });
  }
  // 14. Quick-time event and the clash
  if (m === 13) {
    if (t >= CUE.qte && t < CUE.qte_press + 0.25) {
      const pressed = t >= CUE.qte_press;
      const r = pressed ? 110 + (t - CUE.qte_press) * 600 : 100 + 10 * Math.sin(t * 20);
      ctx.save();
      ctx.globalAlpha = pressed ? Math.max(0, 1 - (t - CUE.qte_press) / 0.25) : 1;
      ctx.fillStyle = 'rgba(10,14,40,.8)';
      ctx.beginPath();
      ctx.arc(470, 720, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.lineWidth = 10;
      ctx.strokeStyle = '#7fb6ff';
      ctx.stroke();
      button(ctx, 'X', 470, 720, r * 0.62);
      ctx.restore();
      if (!pressed) txt(ctx, 'APERTE AGORA!', 470, 880, 56, '#ffffff', { lw: 10 });
    }
    if (t >= CUE.qte_press && t < CUE.impact) txt(ctx, 'BULLET TIME', 470, 470, 60, '#7fe0ff', { lw: 10 });
    if (t >= CUE.impact) banner(ctx, t, CUE.impact, ['PERFEITO!'], { y: 560, size: 110, colors: ['#ffffff', '#7fe0ff'], shake: 6 });
  }
  // 15. Cutscene: accent bonus
  if (m === 14 && t >= CUE.sotaque) {
    const a = t - CUE.sotaque;
    txt(ctx, 'SOTAQUE +100', 470, 470 - a * 40, 66, '#7dff6a', { lw: 12 });
    txt(ctx, 'PULAR', 860, 260, 30, '#ffffff', { lw: 5, align: 'right' });
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.moveTo(712, 246); ctx.lineTo(736, 260); ctx.lineTo(712, 274); ctx.fill();
  }
  // 16. Boss
  if (m === 15) {
    if (t < CUE.charge + 0.35) banner(ctx, t, CUE.boss, ['!! CHEFE !!'], { y: 600, size: 110, colors: ['#ffffff', '#ff4a3c'], shake: 4 });
    const fill = ease((t - CUE.boss) / 0.4);
    const v = t >= CUE.crash ? Math.max(0, 1 - (t - CUE.crash) / 0.25) : fill;
    enemyBar(ctx, t, 'JUMENTO', v, 346, 760);
    if (t >= CUE.crash + 0.08) banner(ctx, t, CUE.crash + 0.08, ['K.O.!'], { y: 650, size: 170, colors: ['#ffe45a', '#ff2a2a'], shake: 5 });
  }
  // 17. Results
  if (m === 16) {
    const k = ease((t - CUE.cuts[16]) / 0.25);
    panel(ctx, 110, 380, 740, 470 * k, 0.88);
    if (k > 0.95) {
      txt(ctx, 'RESULTADO', 480, 430, 56, '#ffe45a', { lw: 9 });
      [['HITS', '999'], ['MILDINGOWS', 'x1000'], ['SCORE', String(score(t))]].forEach(([a, b], i) => {
        txt(ctx, a, 150, 510 + i * 62, 34, '#ffffff', { align: 'left', font: 'Russo', lw: 5 });
        txt(ctx, b, 810, 510 + i * 62, 34, '#7fe0ff', { align: 'right', font: 'Russo', lw: 5 });
      });
      txt(ctx, 'MALANDRAGEM', 150, 730, 40, '#ffffff', { align: 'left', lw: 7 });
      const s = Math.max(0, Math.min(1, (t - CUE.cuts[16] - 0.35) / 0.15));
      if (s > 0) {
        ctx.save();
        ctx.translate(730, 730);
        ctx.scale(3 - 2 * s, 3 - 2 * s);
        txt(ctx, 'S', 0, 0, 150, grad(ctx, -70, 70, '#fff2a0', '#ff9a1e'), { lw: 22 });
        ctx.restore();
      }
    }
    const p2 = A2(pts, 'P2_head');
    if (p2 && t >= CUE.tag) {
      const kk = back((t - CUE.tag) / 0.2);
      ctx.save();
      ctx.translate(Math.max(220, Math.min(720, p2.x)), Math.max(920, p2.y - 110));
      ctx.scale(kk, kk);
      panel(ctx, -200, -40, 400, 80, 0.9, 12);
      txt(ctx, 'PARDJHONSON', 0, 2, 40, '#ff6a6a', { lw: 7 });
      ctx.restore();
    }
  }
  ctx.restore();
}
