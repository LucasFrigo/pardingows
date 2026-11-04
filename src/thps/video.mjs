// renderFrame(rgba, v): takes one raw Blender frame, applies the PS1 colour pass, then the HUD.
import { Surface } from '../shared/engine.mjs';
import { ps1Colour } from '../shared/ps1.mjs';
import { drawHud, W, H } from './hud.mjs';

export { W, H };
export const FRAME_BYTES = W * H * 4;

const surface = new Surface(W, H);
const view = new Uint8Array(surface.px.buffer);

export function renderFrame(rgba, v, { hud = true } = {}) {
  view.set(rgba);
  ps1Colour(view, W, H);
  if (hud) drawHud(surface, v);
  return view;
}
