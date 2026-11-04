// The director: picks the scene for each moment, runs the camera, and draws captions + badge.
import { Surface, W, H, hex, clamp, lerp, easeOut, easeIn, easeInOut, hash } from '../shared/engine.mjs';
import { BIG, MINI, drawText, textWidth } from '../shared/font.mjs';
import { C, heart, sparkle } from './art.mjs';
import { exterior, bar, hotTub, danceFloor, DOOR, BAR_TOP, BARTENDER_X, SEAT, GUY } from './scenes.mjs';
import { LINES, CUT, DROP, DURATION, BAR, beatPos, beatNum, beatPhase, kick } from './timeline.mjs';

const scene = new Surface(W, H);
const frame = new Surface(W, H);
const BLACK = hex('#000000');

const between = (v, a, b) => clamp((v - a) / (b - a));
const downbeat = n => DROP + n * BAR;            // 1.17, 2.89, 4.61, 6.32, 8.04, 9.75, 11.47, 13.19
const cutFlash = (v, at, len = 0.12, peak = 0.5) => (v >= at && v < at + len ? (1 - (v - at) / len) * peak : 0);
const ARMS = [['down', 'down'], ['up', 'down'], ['out', 'out'], ['down', 'up'], ['up', 'up'], ['head', 'out']];

// "TIPO MINECRAFT": the square guy is placed block by block on these beats.
const BUILD = [CUT[4], 7.181, 7.610];
// Where "QUADRADO" is sung: punch in on him.
const QUADRADO = LINES[5].rows[1][0].v;

export function renderFrame(v) {
  scene.clear(BLACK);
  const cam = { x: W / 2, y: H / 2, z: 1 };
  let shake = 0, flash = 0, dark = 0;

  if (v < DROP) {
    // A. Exterior hook: the sign flickers on, he struts to the door, we dive in.
    exterior(scene, v, Math.round(lerp(-24, DOOR.x, clamp(v / 1.0))));
    const dive = easeIn(between(v, 0.82, DROP));
    cam.z = 1 + dive * 6;
    cam.x = lerp(W / 2, DOOR.x, dive);
    cam.y = lerp(H / 2, DOOR.y, dive);
  } else if (v < CUT[1]) {
    // B. The drop: inside the club, crowd jumping.
    bar(scene, v, {
      smurf: { bob: beatPhase(v) < 0.35 ? 1 : 0, glint: beatNum(v) % 2 === 0, hand: [9, -12] },
      crowd: 1.4, beams: 1.6,
    });
    flash = cutFlash(v, DROP, 0.25, 0.85);
    shake = kick(v);
  } else if (v < CUT[2]) {
    // C. "lá só tem pardo pelado": the VIP hot tub.
    hotTub(scene, v);
    flash = cutFlash(v, CUT[1]);
  } else if (v < CUT[4]) {
    // D + E. "tira sua roupa, parda / esquece seu namorado"
    barSequence(v);
    flash = cutFlash(v, CUT[2]);
  } else if (v < CUT[6]) {
    // F. "tipo minecraft / esse branco é quadrado"
    const built = v < BUILD[1] ? 1 : v < BUILD[2] ? 2 : 3;
    const lastBuild = BUILD[built - 1];
    const dancing = v >= BUILD[2] + 0.2;
    const bn = beatNum(v);
    const guy = {
      x: GUY.x + (dancing ? [0, 1, 0, -1][bn % 4] : 0), y: GUY.y,
      bob: dancing && beatPhase(v) < 0.5 ? -1 : 0,
      arms: dancing ? ARMS[bn % ARMS.length] : ['down', 'down'],
      built, pop: v - lastBuild < 0.15 ? { y: GUY.y - [10, 36, 64][built - 1], a: 1 - (v - lastBuild) / 0.15 } : null,
    };
    danceFloor(scene, v, { guy, frame: v >= CUT[5] ? 1 : 0 });
    if (v >= QUADRADO) { cam.z = 2; cam.x = guy.x; cam.y = guy.y - 42; }
    flash = cutFlash(v, CUT[4]) + cutFlash(v, QUADRADO, 0.1, 0.4);
  } else if (v < CUT[7]) {
    // G. "não emplaca cos pardingow": she walks right past him.
    const snub = downbeat(6);
    const sx = lerp(160, -30, between(v, CUT[6] + 0.05, CUT[7] - 0.05));
    danceFloor(scene, v, {
      guy: {
        ...GUY, arms: ['down', 'offer'], sad: v >= snub, wilt: v >= snub ? 1 : 0,
        bob: v < snub && beatPhase(v) < 0.5 ? -1 : 0,
      },
      smurfette: {
        x: Math.round(sx), y: 182, walk: true, step: beatPos(v) / 2, bob: beatPhase(v) < 0.5 ? 0 : 1,
        wink: Math.abs(sx - GUY.x) < 40, hairFlip: Math.abs(sx - GUY.x) < 20 ? 1 : 0,
      },
      cloud: v >= snub ? Math.min(1, (v - snub) / 0.15) : 0,
      xMark: v >= snub ? Math.min(1, (v - snub) / 0.12) : 0,
    });
    if (v >= snub) shake = kick(v) * 0.6;
    flash = cutFlash(v, CUT[6], 0.1, 0.4);
  } else {
    // H. "aqui é aura todo mundo é safado"
    ({ shake, dark } = finale(v));
    flash = cutFlash(v, CUT[7]) + cutFlash(v, downbeat(7), 0.2, 0.7);
  }

  // camera: integer punch-ins and beat shake
  if (shake > 0.3) {
    const n = beatNum(v);
    cam.x += Math.round((hash(n) - 0.5) * 3 * shake);
    cam.y += Math.round((hash(n + 9) - 0.5) * 3 * shake);
  }
  if (cam.z === 1 && cam.x === W / 2 && cam.y === H / 2) frame.px.set(scene.px);
  else scene.zoomInto(frame, cam.x, cam.y, cam.z);

  if (flash > 0) frame.rect(0, 0, W, H, C.white, Math.min(1, flash));
  if (dark > 0) frame.rect(0, 0, W, H, BLACK, dark);
  captions(frame, v);
  badge(frame, v);
  return frame;
}

// D + E: Smurfette arrives behind the bar, flirts, slides him the drink, flips the boyfriend's photo.
function barSequence(v) {
  const enter = easeOut(between(v, CUT[2], CUT[2] + 0.55));
  let sfx = lerp(165, BARTENDER_X, enter);
  const slideA = CUT[3] + 0.3, slideB = slideA + 0.45;
  const flick = downbeat(3);
  if (v > slideB + 0.1) sfx = lerp(BARTENDER_X, BARTENDER_X - 6, easeInOut(between(v, slideB + 0.1, flick - 0.15)));
  const winking = v >= 4.78 && v < 5.12;
  const smitten = v >= 4.85 && v < 5.6;

  const sf = {
    x: Math.round(sfx), walk: enter < 1, step: beatPos(v) / 2, bob: beatPhase(v) < 0.5 ? 0 : 1,
    hairFlip: v >= downbeat(2) && v < downbeat(2) + 0.3 ? 1 : 0, wink: winking,
  };
  if (v >= CUT[3] && v < slideA) { sf.hand = [10, -16]; sf.drink = true; }
  else if (v >= slideA && v < slideA + 0.2) sf.hand = [12, -14];
  else if (v >= flick - 0.12 && v < flick + 0.2) sf.hand = [14, -16];

  const st = { smurfette: sf, photoDown: v >= flick, smurf: { glint: beatNum(v) % 2 === 0, bob: beatPhase(v) < 0.35 ? 1 : 0 } };
  if (smitten) Object.assign(st.smurf, { shadesDown: 1, mouth: 'o' });

  // the drink: sliding down the counter, then caught
  const catchX = SEAT[0] + 28;
  if (v >= slideA && v < slideB) {
    st.drinkX = lerp(sfx - 22, catchX, easeOut(between(v, slideA, slideB)));
    st.drinkSpeed = true;
  }
  if (v >= slideB - 0.12) st.smurf.hand = [13, -19];
  if (v >= slideB) {
    st.smurf.drink = true;
    if (v >= flick + 0.1) st.smurf.hand = [11, -23];  // cheers!
  }
  bar(scene, v, st);

  if (winking) sparkle(scene, sfx - 16, 88, 3, C.white);
  if (smitten) for (let i = 0; i < 3; i++) {
    const ph = (v - 4.85) * 1.6 + i * 0.3;
    heart(scene, 26 + i * 8 + Math.round(Math.sin(ph * 8) * 2), 92 - ph * 30, i % 2 ? C.pink : C.pinkL);
  }
  if (v >= flick && v < flick + 0.25) {
    const k = (v - flick) / 0.25;
    for (let i = 0; i < 6; i++) sparkle(scene, 69 + Math.cos(i * 1.1) * k * 12, BAR_TOP - 4 - Math.sin(i * 1.1) * k * 8, 1, C.white);
  }
}

// H: he drinks, the aura explodes, the whole club goes off, then lights out for the loop.
function finale(v) {
  const auraT = downbeat(7);
  const sipA = CUT[7] + 0.3, sipB = auraT - 0.1;
  const st = {
    smurfette: { x: BARTENDER_X, bob: beatPhase(v) < 0.5 ? 0 : 1, hand: [8, -18] },
    photoDown: true,
    smurf: { glint: beatNum(v) % 2 === 0 },
  };
  let shake = 0;
  if (v < auraT) {
    const lift = easeOut(between(v, CUT[7], sipA));
    st.smurf.hand = [lerp(11, 7, lift), lerp(-23, -14, lift)];
    st.smurf.drink = true;
    st.smurf.drinkLevel = 1 - between(v, sipA, sipB);
    if (v >= sipA) { st.smurf.mouth = 'o'; st.smurf.bob = -1; }
  } else {
    st.aura = Math.min(1, (v - auraT) / 0.1);
    st.auraT = auraT;
    st.crowd = 1.6;
    st.beams = 2.2;
    st.smurf = { glint: true, mouth: 'open', hand: [13, -28], drink: true, drinkLevel: 0, bob: beatPhase(v) < 0.4 ? 1 : 0 };
    Object.assign(st.smurfette, { heartEyes: true, hand: [6, -30] });
    shake = kick(v);
  }
  const end = DURATION - 0.32;
  st.signOn = v < end ? 1 : (Math.floor((v - end) * 30) % 3 === 0 ? 1 : 0);
  bar(scene, v, st);

  if (v >= sipA && v < sipB) {
    const n = Math.floor((v - sipA) / 0.22);
    drawText(scene, 'GLUP', 56 + (n % 2) * 4, 92 - (n % 3) * 4, hex('#ffe14a'), { outline: C.out });
  }
  if (v >= auraT) for (let i = 0; i < 4; i++) {
    const ph = ((v - auraT) * 0.9 + i / 4) % 1;
    heart(scene, 92 + Math.sin(ph * 7 + i) * 8, 90 - ph * 50, i % 2 ? C.pink : C.pinkL);
  }
  return { shake, dark: easeIn(between(v, end, DURATION)) * 0.92 };
}

// ---------------------------------------------------------------- captions (karaoke)
const CAP_CX = 62, CAP_Y = 166, ROW_H = 12;
const SUNG = hex('#ff3fb4'), TODO = C.white, EDGE = hex('#12061c'), DROP_SHADOW = hex('#3a0d52');

function captions(f, v) {
  const line = LINES.find(l => v >= l.v - 0.05 && v < l.end - 0.03);
  if (!line) return;
  const rise = Math.round((1 - easeOut(between(v, line.v - 0.05, line.v + 0.07))) * 4);
  const words = line.rows.flat();
  const active = words.reduce((a, w, i) => (v >= w.v ? i : a), -1);
  const y0 = CAP_Y + (line.rows.length === 1 ? ROW_H / 2 : 0) + rise;
  const rowX = line.rows.map(row => Math.round(CAP_CX - textWidth(BIG, row.map(w => w.text).join(' ')) / 2));

  // translucent backing so the words read over any background
  line.rows.forEach((row, ri) => {
    const width = textWidth(BIG, row.map(w => w.text).join(' '));
    const bx = rowX[ri] - 4, by = y0 + ri * ROW_H - 4, bw = width + 8, bh = ROW_H + 2;
    f.rect(bx + 1, by, bw - 2, bh, EDGE, 0.55);
    f.rect(bx, by + 1, 1, bh - 2, EDGE, 0.55); f.rect(bx + bw - 1, by + 1, 1, bh - 2, EDGE, 0.55);
  });

  let wi = 0;
  line.rows.forEach((row, ri) => {
    let x = rowX[ri];
    for (const w of row) {
      const isActive = wi === active;
      const pop = isActive ? Math.round(2 * Math.exp(-(v - w.v) * 14)) : 0;
      const color = wi <= active ? SUNG : TODO;
      const tw = textWidth(BIG, w.text);
      if (isActive && v - w.v < 0.12) f.glow(x + tw / 2, y0 + ri * ROW_H + 3, 12, SUNG, 0.35);
      drawText(f, w.text, x, y0 + ri * ROW_H - pop, color, { outline: EDGE, shadow: DROP_SHADOW });
      x += tw + BIG.gap + BIG.space;
      wi++;
    }
  });
}

// ---------------------------------------------------------------- badge
const BADGE = 'PARDINGOWS - SURUPARDO';
function badge(f, v) {
  const x = 3, y = 20, w = textWidth(MINI, BADGE) + 16, h = 11;
  f.rect(x, y, w, h, hex('#12061c'), 0.82);
  f.rect(x, y, w, 1, C.pink); f.rect(x, y + h - 1, w, 1, C.pink);
  f.rect(x, y, 1, h, C.pink); f.rect(x + w - 1, y, 1, h, C.pink);
  drawText(f, '♪', x + 3, y + 2 - (kick(v) > 0.5 ? 1 : 0), C.pink);
  drawText(f, BADGE, x + 11, y + 3, C.white, { font: MINI });
}
