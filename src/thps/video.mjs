// renderFrame(rgba, v): takes one raw Blender frame, applies the PS1 colour pass, then the HUD.
import { Surface } from '../shared/engine.mjs';
import { drawHud, W, H } from './hud.mjs';

export { W, H };
export const FRAME_BYTES = W * H * 4;

const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => v / 16 - 0.47);
const STEP = 255 / 31;

// 15-bit colour with ordered dither, as the console's framebuffer did it
function ps1Colour(px) {
  for (let y = 0, i = 0; y < H; y++) {
    for (let x = 0; x < W; x++, i += 4) {
      const d = BAYER[((y & 3) << 2) | (x & 3)] * STEP;
      for (let c = 0; c < 3; c++) {
        const q = Math.round((px[i + c] + d) / STEP) * STEP;
        px[i + c] = q < 0 ? 0 : q > 255 ? 255 : q;
      }
      px[i + 3] = 255;
    }
  }
}

const surface = new Surface(W, H);
const view = new Uint8Array(surface.px.buffer);

export function renderFrame(rgba, v, { hud = true } = {}) {
  view.set(rgba);
  ps1Colour(view);
  if (hud) drawHud(surface, v);
  return view;
}
