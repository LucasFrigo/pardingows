// Environments. Each scene draws a full frame for video time v (exact) / vt (animation "on twos").
// World coordinates match the 540x960 screen at zoom 1; scenes run their own camera.
import { W, H, rect, ellipse, roundRect, clamp, lerp, easeOut, easeIn, easeInOut, backOut, between, hash, vnoise } from './engine.mjs';
import * as P from './props.mjs';
import { drawText, measure, stamp } from './type.mjs';
import { at, bar, CUT, S16, BEAT, beatNum, beatPhase, s16Num, pulse, STOP1, STOP2, CA_CUT } from './timeline.mjs';

const { INK } = P;
const BG = (g, paint) => g.fill(rect(-400, -400, W + 800, H + 800), paint, { boil: 0 });

export function camera(g, x, y, z = 1, rot = 0) {
  g.translate(W / 2, H / 2); g.rotate(rot); g.scale(z); g.translate(-x, -y);
}
const punch = (v, t, k = 0.08, len = 0.18) => (v >= t && v < t + len ? k * (1 - (v - t) / len) : 0);

// ---------------------------------------------------------------- A. padaria (also the loop-in, v < 0)
const POUR_MILK = at('40.1.4'), WIDE = at('40.3.1'), MANHA = at('41.1.1'), GRAB = at('41.3.1');
export function padaria(g, v, vt) {
  const wide = easeInOut(between(v, WIDE, WIDE + 0.28));
  const z = lerp(1.34 + 0.06 * clamp(v / WIDE), 1, wide) + 0.06 * between(v, WIDE + 0.3, CUT.commute) + punch(v, POUR_MILK, 0.07);
  camera(g, 270, lerp(588, 560, wide), z);
  BG(g, { Y: 0.24 });
  // window: sky + rising sun, then the wall frame masks it
  const sunY = lerp(470, 300, easeOut(between(v, MANHA, MANHA + 0.6)));
  g.fill(rect(300, 160, 200, 250), { P: 0.12 }, { boil: 0.5 });
  P.sun(g, 400, sunY, 46, vt);
  g.fill(rect(300, 410, 200, 120), { Y: 0.24 }, { boil: 0 });
  g.stroke(rect(300, 160, 200, 250), 6, INK.dark, { closed: true, id: 3 });
  g.stroke([[400, 160], [400, 410]], 4, INK.dark, { id: 4 });
  g.stroke([[300, 285], [500, 285]], 4, INK.dark, { id: 5 });
  // bread shelves + clock
  for (const [sy, n] of [[300, 3], [430, 3]]) {
    for (let i = 0; i < n; i++) P.bread(g, 60 + i * 70, sy - 12, 0.95, 120 + sy + i);
    g.shape(rect(18, sy, 250, 12), INK.wood, INK.dark, 3, { id: sy });
  }
  P.clock(g, 445, 478, 34, 6 + v * 0.02);
  P.counter(g, 640);

  // the glass (it slides home during the loop-in, and leaves with the hand at the end)
  const grab = easeIn(between(v, GRAB + 0.3, CUT.commute));
  const gx = 270 + 340 * (1 - easeOut(between(v, -0.75, -0.3))), gy = 640 - grab * 700;
  const level = v < POUR_MILK ? lerp(0.2, 0.48, between(v, -0.1, POUR_MILK)) : lerp(0.48, 0.86, easeOut(between(v, POUR_MILK, POUR_MILK + 0.45)));
  const mix = between(v, POUR_MILK + 0.05, POUR_MILK + 0.35);
  const contents = { P: lerp(INK.coffee.P, INK.cafeLeite.P, mix), B: lerp(INK.coffee.B, INK.cafeLeite.B, mix), Y: lerp(INK.coffee.Y, INK.cafeLeite.Y, mix) };
  const surface = gy - 132 * 1.7 * 0.94 * level;

  // coffee pot: pours from the loop-in until "leite"; milk jug pours on "leite"
  const potIn = easeOut(between(v, -0.7, -0.25)), potOut = easeIn(between(v, WIDE, WIDE + 0.25));
  const px = lerp(-140, 196, potIn) - potOut * 300, py = lerp(260, 418, potIn) - potOut * 300;
  g.save(); g.translate(px, py); P.pot(g, 0.8); g.restore();
  const jugIn = easeOut(between(v, POUR_MILK - 0.25, POUR_MILK)), jugOut = easeIn(between(v, WIDE, WIDE + 0.25));
  if (jugIn > 0) {
    const jx = lerp(680, 344, jugIn) + jugOut * 300, jy = lerp(260, 418, jugIn) - jugOut * 300;
    g.save(); g.translate(jx, jy); g.scale(-1, 1); P.pot(g, 0.8, { milk: true }); g.restore();
  }
  g.save(); g.translate(gx, gy); g.scale(1.7);
  P.glass(g, level, contents, { foam: between(v, POUR_MILK + 0.2, POUR_MILK + 0.5) });
  g.restore();
  if (v > -0.15 && v < POUR_MILK + 0.05) P.stream(g, px, py, 258, surface, vt, false);
  if (jugIn > 0 && v >= POUR_MILK && v < POUR_MILK + 0.42) {
    const jx = lerp(680, 344, jugIn), jy = 418;
    P.stream(g, jx, jy, 284, surface, vt, true);
  }
  if (v > POUR_MILK + 0.3 && grab < 0.2) { g.save(); g.translate(gx, surface - 22); P.steam(g, vt, { h: 80, paint: { P: 1 } }); g.restore(); }
  // his arm comes in from the corner and takes it
  if (v >= GRAB) {
    const k = easeOut(between(v, GRAB, GRAB + 0.2));
    const hx = lerp(640, gx + 66, k), hy = lerp(980, gy - 92, k), sx = 700, sy = gy + 380;
    P.arm(g, [[sx, sy], [lerp(sx, hx, 0.5) + 50, lerp(sy, hy, 0.5) + 20], [hx, hy]], 1.5);
  }
}

// ---------------------------------------------------------------- B. commute: smoke on the way
const FUMACA = at('42.1.2'), CAMINHO = at('42.3.1'), APAZ = at('42.4.4'), GLUB1 = at('43.3.1');
export function commute(g, v, vt) {
  const relax = easeInOut(between(v, APAZ, APAZ + 0.45));
  const tilt = easeOut(between(v, GLUB1, GLUB1 + 0.15)) * 0.06;
  camera(g, lerp(270, 245, relax), lerp(480, 430, relax), 1 + 0.3 * relax + punch(v, CAMINHO, 0.05), tilt);
  BG(g, { P: 0.16 });
  const walk = 1 - relax;
  // scroll distance: walking speed, stopping as he relaxes
  const d = (vt - CUT.commute) * 150 - relax * 30;
  for (let i = -1; i < 7; i++) {
    const x = ((i * 130 - d * 0.35) % 910 + 910) % 910 - 200;
    P.building(g, x, 630, 110, 230 + hash(i, 4) * 170, { P: 0.38 }, 400 + i);
  }
  for (let i = -1; i < 6; i++) {
    const x = ((i * 190 - d) % 1140 + 1140) % 1140 - 300;
    P.building(g, x, 640, 150, 300 + hash(i, 9) * 220, { B: 0.55 }, 500 + i, { Y: 1 });
  }
  g.fill(rect(-300, 640, W + 600, 90), { Y: 0.45 }, { id: 2 });
  g.stroke([[-300, 640], [W + 300, 640]], 4, INK.dark, { id: 3 });
  g.fill(rect(-300, 730, W + 600, 500), { B: 0.4 }, { id: 4 });
  for (let i = 0; i < 8; i++) {
    const x = ((i * 120 - d * 1.6) % 960 + 960) % 960 - 200;
    g.fill(rect(x, 820, 60, 10), {}, { mode: 'knock', id: 5 + i });
  }
  // the walk (step on every beat)
  const ph = (vt - CUT.commute) / (BEAT * 2) * Math.PI * 2;
  const sw = Math.sin(ph) * 0.55 * walk;
  const pose = {
    lean: 0.06 * walk, bob: -Math.abs(Math.cos(ph)) * 6 * walk, head: -0.25 * relax,
    legs: [[sw, -Math.max(0, -Math.sin(ph)) * 0.8 * walk], [-sw, -Math.max(0, Math.sin(ph)) * 0.8 * walk]],
    // smoking arm: elbow down, forearm up toward the mouth, cigarette tipped up
    arms: [[-sw * 0.8 - 0.1, -0.3], [lerp(0.35, 0.2, relax) + sw * 0.1, lerp(2.5, 2.75, relax)]],
    prop: (gg, front) => { gg.save(); gg.translate(front[0], front[1]); gg.rotate(-1.0); P.cigarette(gg); gg.restore(); },
  };
  // smoke trail first, so it drifts behind him instead of across his face
  const rig = P.smurfRig(pose);
  const hx = 205 + (rig.hands[1][0] + 15) * 1.3, hy = 640 + (rig.hands[1][1] - 24) * 1.3;
  const headX = 205 + rig.head[0] * 1.3, headY = 640 + rig.head[1] * 1.3;
  for (let k = 0; k < 7; k++) {
    const age = ((vt - CUT.commute) * 2.2 + k / 7) % 1;
    P.cloud(g, hx - 30 - age * 230 * (0.4 + walk * 0.6) + Math.sin(age * 6 + k) * 10, hy - 40 - age * 170, 0.25 + age * 0.55, vt, 30 + k, { P: 0.3 }, { P: 1 });
  }
  g.save(); g.translate(205, 640); g.scale(1.3);
  const body = P.smurf(g, pose, 100);
  g.restore();
  // "fumaça": the big exhale; "apaziguar": the zen cloud
  const puff = easeOut(between(v, FUMACA, FUMACA + 0.35)) * (1 - between(v, CAMINHO + 0.2, CAMINHO + 0.5));
  if (puff > 0) P.cloud(g, headX + 70 + puff * 50, headY - 20 - puff * 40, 0.4 + puff * 1.1, vt, 41);
  if (relax > 0) {
    P.cloud(g, headX + 30, headY - 140 * relax, 0.6 + relax * 1.6, vt, 52, { P: 0.25, Y: 0.2 });
    P.cloud(g, headX - 90, headY - 60 - 60 * relax, 0.4 + relax * 0.9, vt, 63, { P: 0.25 });
    P.cloud(g, headX + 140, headY - 40 - 40 * relax, 0.3 + relax * 0.8, vt, 74, { P: 0.25 });
  }
  // first warning from the belly
  if (v >= GLUB1) {
    const bx = 205 + body.belly[0] * 1.3, by = 640 + body.belly[1] * 1.3;
    P.rumble(g, bx, by, 0.55, vt);
    P.sweat(g, headX - 34, headY - 20 + (v - GLUB1) * 40, -0.3, 1.2);
    drawText(g, 'GLUB', bx + 64, by - 96, 20, { paint: INK.red, weight: 1.5, seed: 5, jitter: 1 });
  }
  // the bus cuts across the foreground on "caminho"
  if (v >= CAMINHO - 0.05 && v < CAMINHO + 0.6) {
    const k = between(v, CAMINHO - 0.05, CAMINHO + 0.6);
    g.save(); g.translate(lerp(900, -500, k), 790); g.scale(1.35); P.bus(g); g.restore();
    g.save(); g.translate(270, 700); P.speedLines(g, 10, 160, vt, INK.dark); g.restore();
  }
}

// ---------------------------------------------------------------- C. office: punch the clock
const KACHUNK = bar(44), TRAMPO = at('44.2.2');
export function office(g, v, vt) {
  camera(g, 270, 500, 1.05 + punch(v, KACHUNK, 0.12) + 0.05 * between(v, CUT.office, CUT.meeting), Math.sin(vt * 3) * 0.01);
  BG(g, { B: 0.2 });
  for (let i = 0; i < 12; i++) g.stroke([[-100 + i * 70, -200], [-100 + i * 70, 1200]], 2, { B: 0.45 }, { id: 20 + i });
  if (v >= KACHUNK && v < KACHUNK + 0.25) P.burst(g, 270, 470, 260 * easeOut((v - KACHUNK) / 0.12), INK.yellow, 701);
  g.save(); g.translate(270, 520); g.scale(1.45); P.timeClock(g); g.restore();
  // the card goes in, gets punched, pops out stamped
  let cy;
  if (v < KACHUNK) cy = lerp(160, 520, easeIn(between(v, CUT.office, KACHUNK)));
  else if (v < TRAMPO) cy = 560;
  else cy = lerp(560, 400, backOut(between(v, TRAMPO, TRAMPO + 0.2)));
  g.save(); g.translate(v >= TRAMPO ? lerp(270, 360, easeOut(between(v, TRAMPO, TRAMPO + 0.2))) : 270, cy);
  g.rotate(v >= TRAMPO ? 0.12 : 0); g.scale(v >= TRAMPO ? lerp(1.2, 1.55, easeOut(between(v, TRAMPO, TRAMPO + 0.2))) : 1.2);
  P.punchCard(g, v >= TRAMPO);
  g.restore();
}

// ---------------------------------------------------------------- C2. the meeting
const UM = at('45.1.1'), REUNIAO = at('45.2.2');
export function meeting(g, v, vt) {
  const push = easeInOut(between(v, CUT.meeting + 0.3, CUT.panic1));
  camera(g, lerp(270, 270, push), lerp(480, 470, push), 1 + 0.32 * push + punch(v, UM, 0.08), 0);
  BG(g, { Y: 0.26 });
  g.save(); g.translate(270, 290); g.scale(0.9); P.whiteboard(g, vt); g.restore();
  // second hand ticks on every beat
  P.clock(g, 460, 330, 36, beatNum(v) / 60 * 12);
  const bob = i => (beatPhase(v) < 0.3 && (beatNum(v) + i) % 2 === 0 ? -4 : 0);
  g.save(); g.translate(92, 610 + bob(0)); P.bust(g, { B: 1 }, 300); g.restore();
  g.save(); g.translate(448, 610 + bob(1)); P.bust(g, { P: 0.8, B: 0.55 }, 310); g.restore();
  const nerves = between(v, UM, CUT.panic1);
  g.save(); g.translate(270 + Math.sin(vt * 40) * 2 * nerves, 700); g.scale(1.25);
  const body = P.smurf(g, { arms: [[0.9, -1.0 - nerves * 0.6], [-0.9, 1.0 + nerves * 0.6]], head: Math.sin(vt * 30) * 0.05 * nerves, mouth: v >= UM ? 'wavy' : 'smile' });
  g.restore();
  g.save(); g.translate(270, 645); P.table(g); g.restore();
  g.fill(rect(-100, 669, 740, 400), INK.wood, { id: 9 });
  g.stroke([[-100, 669], [640, 669]], 4, INK.dark, { id: 10 });
  const bx = 270 + body.belly[0] * 1.25, by = 700 + body.belly[1] * 1.25;
  if (v >= UM) P.rumble(g, bx, by + 6, 0.5 + nerves * 0.5, vt);
  if (v >= REUNIAO) {
    drawText(g, 'GLUB', bx + 70, by - 150, 24, { paint: INK.red, weight: 1.6, seed: 6, jitter: 1 });
    const hx = 270 + body.head[0] * 1.25, hy = 700 + body.head[1] * 1.25;
    for (let i = 0; i < 3; i++) {
      const a = ((vt - REUNIAO) * 1.6 + i / 3) % 1;
      P.sweat(g, hx + (i - 1) * 40 + (i - 1) * a * 40, hy - 30 + a * 60, (i - 1) * 0.5, 1.1, 50 + i);
    }
  }
}

// ---------------------------------------------------------------- D/I. panic close-up and the stop
// The band stops: the page goes blank and still, only he trembles.
export function panic(g, v, vt, stop) {
  const frozen = v >= stop[0] && v < stop[1];   // the band comes back for "eu vou me..."
  const tz = frozen ? easeInOut(between(v, stop[0], stop[1])) : 0;
  camera(g, 270, lerp(480, 430, tz), 1 + 0.16 * tz, 0);
  if (!frozen) {
    BG(g, { Y: 1 });
    for (let i = 0; i < 16; i++) {
      const a = i / 16 * Math.PI * 2 + vt * 0.8;
      g.fill([[270, 280], [270 + Math.cos(a) * 900, 280 + Math.sin(a) * 900], [270 + Math.cos(a + 0.16) * 900, 280 + Math.sin(a + 0.16) * 900]], { P: 0.55 }, { id: 30 + i, boil: 0.3 });
    }
  } else BG(g, {});
  const tremble = frozen ? 2.2 : 5;
  const jx = (hash(Math.floor(v * 30), 1) - 0.5) * 2 * tremble, jy = (hash(Math.floor(v * 30), 2) - 0.5) * tremble;
  g.save(); g.translate(270 + jx, 990 + jy); g.scale(2.85);
  const body = P.smurf(g, { arms: [[0.2, 1.3], [-0.2, -1.3]], head: Math.sin(vt * 25) * 0.04, legs: [[0, 0], [0, 0]], mouth: frozen ? 'o' : 'wavy' }, 100);
  g.restore();
  const bx = 270 + body.belly[0] * 2.85 + jx, by = 990 + body.belly[1] * 2.85;
  P.rumble(g, bx, by - 10, frozen ? 0.9 : 1.2, frozen ? v : vt);
  const hx = 270 + body.head[0] * 2.85 + jx, hy = 990 + body.head[1] * 2.85 + jy;
  const n = frozen ? 3 : 6;
  for (let i = 0; i < n; i++) {
    const a = ((frozen ? v * 0.45 : vt * 1.8) + i / n) % 1;
    const side = i % 2 ? 1 : -1, ang = -1.2 + (i / n) * 0.9;
    P.sweat(g, hx + side * (70 + a * 90), hy - 40 + Math.sin(ang) * 30 + a * a * 160, side * 0.4, 1.7, 50 + i);
  }
}

// ---------------------------------------------------------------- E. the calendar: "já tem muitos anos"
const YEAR0 = 2017, Y2026 = at('48.2.3'), FLIP = (Y2026 - CUT.calendar) / 9;   // 9 pages land on "anos"
export function calendarScene(g, v, vt) {
  const flips = Math.min(9, Math.floor((v - CUT.calendar) / FLIP) + 1);
  const slam = punch(v, Y2026, 0.1, 0.22);
  camera(g, 270, 470, 1.04 + 0.1 * between(v, CUT.calendar, CUT.lactose) + slam, Math.sin(vt * 2) * 0.03);
  BG(g, { B: 0.78 });
  for (let i = 0; i < 9; i++) g.fill(ellipse(60 + (i % 3) * 210, 120 + Math.floor(i / 3) * 330, 70, 70), { B: 0.78, P: 0.3 }, { id: 50 + i, mode: 'over' });
  if (v >= Y2026 && v < Y2026 + 0.3) P.burst(g, 270, 400, 330, INK.yellow, 702, 18);
  g.save(); g.translate(270, 430); g.scale(1.3 + slam); P.calendar(g, YEAR0 + flips); g.restore();
  for (let k = 0; k < flips; k++) {
    const tk = CUT.calendar + k * FLIP, a = v - tk;
    if (a < 0 || a > 0.45) continue;
    const dir = hash(k, 3) > 0.5 ? 1 : -1;
    g.save(); g.translate(270 + dir * (40 + a * 900), 400 - a * 500 + a * a * 1400); g.scale(0.95 - a);
    P.page(g, dir * a * 7, 330 + k);
    g.restore();
  }
}

// ---------------------------------------------------------------- F. lactose: the carton, then the gut
const NAO_CAI = bar(49), CAI = at('49.2.1'), BEM = at('49.2.3');
export function lactoseScene(g, v, vt) {
  if (v < NAO_CAI) {
    camera(g, 270, 470, 1.08 + 0.08 * between(v, CUT.lactose, NAO_CAI), Math.sin(vt * 4) * 0.04);
    BG(g, { P: 0.85, B: 0.3 });
    for (let i = -6; i < 10; i++) g.fill([[i * 80, 300], [i * 80 + 40, 300], [i * 80 + 140, 200], [i * 80 + 100, 200]].map(([x, y]) => [x, y + 230]), INK.yellow, { id: 60 + i });
    g.fill(rect(-200, 398, 940, 8), INK.dark, { id: 59 }); g.fill(rect(-200, 494, 940, 8), INK.dark, { id: 58 });
    g.save(); g.translate(270, 585 + Math.sin(vt * 9) * 4); g.rotate(Math.sin(vt * 5) * 0.06); g.scale(1.55);
    P.milkCarton(g, { label: 'LEITE' });
    g.restore();
    g.save(); g.translate(410, 250); P.sparkle(g, 0, 0, 30 + pulse(v) * 10, INK.yellow); g.restore();
    return;
  }
  const anger = v < CAI ? 0.25 : v < BEM ? 0.65 : 1;
  camera(g, 270, 470, 1.05 + punch(v, CAI, 0.08) + punch(v, BEM, 0.12), 0);
  BG(g, { Y: 0.9 });
  g.save(); g.translate(270, 500); g.scale(1.2); P.bellyXray(g, vt, anger); g.restore();
  // the drop of milk falling into the stomach
  const d = between(v, NAO_CAI, NAO_CAI + 0.3);
  if (d < 1) {
    const dy = lerp(110, 330, easeIn(d));
    g.fill([[300, dy - 26], ...ellipse(300, dy, 16, 16).slice(2, 15)], {}, { mode: 'knock', id: 70 });
    g.stroke([[300, dy - 26], ...ellipse(300, dy, 16, 16).slice(2, 15)], 3, INK.dark, { id: 70, closed: true });
  }
}

// ---------------------------------------------------------------- G. "eu não ligo, me dá logo..."
const NAO = bar(50), MEDA = at('50.2.3'), DA = at('50.3.1'), LOGO = at('50.3.4');
export function shrugScene(g, v, vt) {
  if (v < MEDA) {
    const s = easeOut(between(v, NAO, NAO + 0.12));
    camera(g, 270, 480, 1.0 + 0.06 * s + punch(v, NAO, 0.06), 0);
    BG(g, { Y: 0.9 });
    for (let r = 0; r < 14; r++)
      for (let c = 0; c < 9; c++) if ((r + c) % 2 === 0) g.dot(c * 70 + (r % 2) * 35, r * 75, 9, { P: 0.6 }, { id: r * 9 + c, boil: 0.3 });
    g.save(); g.translate(270, 690 - s * 10); g.scale(1.45);
    const body = P.smurf(g, {
      arms: [[lerp(0.15, -1.25, s), lerp(-0.2, -1.35, s)], [lerp(-0.15, 1.25, s), lerp(0.2, 1.35, s)]],
      head: s * -0.12, lean: Math.sin(vt * 6) * 0.03 * s, mouth: s > 0 ? 'grin' : 'smile',
    }, 100);
    g.restore();
    if (s > 0) for (let i = 0; i < 3; i++) P.sparkle(g, 270 + (i - 1) * 150, 330 - (i % 2) * 60, 14 + 8 * pulse(v), INK.yellow, 510 + i);
    return;
  }
  // diner counter: the hand slaps the counter, then beckons "logo"
  camera(g, 270, 500, 1.1 + punch(v, DA, 0.12), 0);
  BG(g, { P: 0.2 });
  if (v >= DA && v < DA + 0.25) P.burst(g, 270, 540, 250 * easeOut((v - DA) / 0.1), INK.yellow, 703);
  g.fill(rect(-200, 540, 940, 30), { B: 0.25 }, { id: 2 }); g.stroke([[-200, 540], [740, 540]], 4, INK.dark, { id: 3 });
  for (let i = 0; i < 12; i++) g.fill(rect(-200 + i * 90, 570, 45, 500), { P: 1 }, { id: 4 + i });
  g.stroke([[-200, 570], [740, 570]], 4, INK.dark, { id: 20 });
  const slap = v < DA ? lerp(330, 548, easeIn(between(v, MEDA, DA))) : 548;
  const beck = v >= LOGO ? Math.abs(Math.sin((v - LOGO) / (S16 * 2) * Math.PI)) : 0;
  const hx = 270, hy = slap - 30 - beck * 34;
  P.arm(g, [[470, -140], [400, lerp(-140, hy, 0.5)], [hx, hy]], 2.2);
}

// ---------------------------------------------------------------- G2. the milkshake hero shot
const SHAKE_IN = bar(51);
export function milkshakeScene(g, v, vt) {
  const rise = backOut(between(v, SHAKE_IN, SHAKE_IN + 0.3), 1.6);
  camera(g, 270, 480, 1 + 0.08 * between(v, SHAKE_IN, CUT.vegetal), Math.sin(vt * 2.5) * 0.02);
  if (v < SHAKE_IN) {
    BG(g, { P: 1 });
    P.burst(g, 270, 450, 120 + 600 * easeIn(between(v, CUT.milkshake, SHAKE_IN)), INK.yellow, 704, 16);
    return;
  }
  BG(g, { P: 0.2 });
  P.sunburst(g, 270, 380, 900, vt * 0.9, 22);
  g.save(); g.translate(270, lerp(1250, 690, rise)); g.scale(1.42); P.milkshake(g, vt); g.restore();
  for (let i = 0; i < 6; i++) {
    const tw = pulse(v - i * S16 * 2, 6);
    P.sparkle(g, 270 + Math.cos(i * 1.05 + 0.4) * 190, 380 + Math.sin(i * 1.05 + 0.4) * 200, 10 + tw * 22, i % 2 ? INK.paper : INK.yellow, 520 + i);
  }
}

// ---------------------------------------------------------------- H. plant milks get rejected
const STAMPS = [at('52.2.1'), at('52.3.3'), at('53.1.2')], SWIPE = at('53.2.2');
export function vegetalScene(g, v, vt) {
  const panicK = between(v, SWIPE, CUT.panic2);
  camera(g, 270, 480, 1 + 0.05 * panicK + STAMPS.reduce((a, t) => a + punch(v, t, 0.06), 0), Math.sin(vt * 20) * 0.015 * panicK);
  BG(g, { B: 0.22 });
  for (let i = 0; i < 8; i++) g.stroke([[-50, 140 + i * 70], [600, 140 + i * 70]], 3, { B: 0.5 }, { id: 30 + i });
  P.counter(g, 540);
  // the arm sweeps the counter; each carton launches the moment the mitt reaches it
  const sw = between(v, SWIPE, SWIPE + 0.35), reach = easeOut(sw);
  const hx = lerp(-60, 700, reach) + Math.max(0, v - SWIPE - 0.35) * 2200;   // then it slides out of frame
  if (v >= SWIPE) P.arm(g, [[hx - 460, 520], [hx - 220, 490], [hx, 470]], 1.8);
  for (let k = 0; k < 3; k++) {
    const x0 = 125 + k * 145;
    const hitAt = 1 - Math.cbrt(1 - (x0 - 40 + 60) / 760);   // sw where the mitt touches this carton
    const fly = v >= SWIPE ? easeOut(clamp((sw - hitAt) / 0.5)) : 0;
    g.save();
    g.translate(x0 + fly * 520, 540 - fly * 260 + fly * fly * 300); g.rotate(fly * (2 + k)); g.scale(0.92);
    P.plantCarton(g, k, 380 + k * 40);
    if (v >= STAMPS[k]) {
      const st = v - STAMPS[k];
      g.save(); g.translate(0, -100); g.scale(1 + 1.4 * (1 - easeOut(clamp(st / 0.08))));
      stamp(g, 'NÃO', 0, 0, k === 2 ? 40 : 32, { paint: INK.red, rot: -0.3 + k * 0.15, seed: 30 + k, weight: 1.7 });
      g.restore();
    }
    g.restore();
  }
  if (v >= SWIPE + 0.1) {
    for (let i = 0; i < 5; i++) {
      const a = ((vt - SWIPE) * 1.5 + i / 5) % 1;
      P.sweat(g, 60 + i * 105, 200 + a * 300, 0, 1.4, 60 + i);
    }
  }
}

// ---------------------------------------------------------------- I. CAGAR!!!: the sprint
export function sprint(g, v, vt) {
  const t = v - CUT.cagar;
  const shake = 9;
  camera(g, 270 + (hash(s16Num(v), 5) - 0.5) * shake, 480 + (hash(s16Num(v), 6) - 0.5) * shake, 1.06, (hash(s16Num(v), 7) - 0.5) * 0.06);
  const flash = [{ P: 1 }, { Y: 1 }, { B: 1 }, { P: 1, Y: 1 }][s16Num(v) % 4];
  BG(g, flash);
  for (let i = 0; i < 18; i++) {
    const a = i / 18 * Math.PI * 2 + t * 3;
    g.fill([[270, 480], [270 + Math.cos(a) * 900, 480 + Math.sin(a) * 900], [270 + Math.cos(a + 0.12) * 900, 480 + Math.sin(a + 0.12) * 900]], {}, { mode: 'knock', id: 40 + i, boil: 0.5 });
  }
  g.save(); g.translate(270, 760); P.speedLines(g, 16, 220, vt * 3, INK.dark, 720); g.restore();
  const x = lerp(-90, 620, between(v, CUT.cagar, CUT.door));
  const ph = v / (BEAT / 2) * Math.PI * 2, sw = Math.sin(ph);
  g.save(); g.translate(x, 800); g.scale(1.5);
  P.smurf(g, { lean: 0.45, legs: [[sw * 1.1, -0.4 - Math.max(0, -sw)], [-sw * 1.1, -0.4 - Math.max(0, sw)]], arms: [[-sw * 1.3, -1.2], [sw * 1.3, -1.2]], head: 0.15, mouth: 'o' }, 100);
  g.restore();
  for (let i = 0; i < 4; i++) P.cloud(g, x - 90 - i * 70, 780 - i * 8, 0.35 + i * 0.12, vt, 90 + i, { Y: 0.3 }, INK.dark);
}

// ---------------------------------------------------------------- J. the bathroom door
const SLAM = CUT.door;
export function doorScene(g, v, vt) {
  const t = v - SLAM;
  const sh = t < 0.25 ? (1 - t / 0.25) * 14 : pulse(v, 12) * 3;
  camera(g, 270 + (hash(Math.floor(v * 30), 3) - 0.5) * sh, 470 + (hash(Math.floor(v * 30), 4) - 0.5) * sh, 1.04 + punch(v, SLAM, 0.1, 0.2), 0);
  BG(g, { Y: 0.32, P: 0.14 });
  for (let i = 0; i < 10; i++) g.stroke([[-100 + i * 80, -200], [-100 + i * 80, 820]], 3, { Y: 0.6, P: 0.3 }, { id: 30 + i });
  g.fill(rect(-200, 820, 940, 400), { B: 0.4 }, { id: 2 });
  g.stroke([[-200, 820], [740, 820]], 5, INK.dark, { id: 3 });
  if (t < 0.22) P.burst(g, 270, 500, 300 + 200 * t, INK.yellow, 705, 16);
  g.save(); g.translate(270, 820); P.door(g, t < 0.3 ? 1 : pulse(v, 10), true); g.restore();
  // the toilet paper escapes under the door
  const un = easeOut(between(v, SLAM + 0.15, SLAM + 0.5));
  if (un > 0) { g.save(); g.translate(330 + un * 120, 800); P.toiletRoll(g, un, vt); g.restore(); }
  // impact text for the slam
  if (t < 0.3) {
    const k = 1 + 0.6 * (1 - easeOut(t / 0.1));
    g.save(); g.translate(140, 330); g.rotate(-0.25); g.scale(k);
    drawText(g, 'BAM!', -70, -28, 56, { paint: INK.red, weight: 1.9, seed: 9, jitter: 1 });
    g.restore();
  }
}
