// renderFrame(story, run, v): stacks the two panels, or takes the one full-screen frame after NÃO!, then applies the PS1 colour pass and the HUD.
import { Surface } from '../shared/engine.mjs';
import { ps1Colour } from '../shared/ps1.mjs';
import { drawHud, W, H, SEAM } from './hud.mjs';

export { W, H, SEAM };
export const PANEL_BYTES = W * SEAM * 4;
export const FULL_BYTES = W * H * 4;

const surface = new Surface(W, H);
const view = new Uint8Array(surface.px.buffer);

export function renderFrame(story, run, v, { hud = true } = {}) {
  if (run) {
    view.set(story, 0);
    view.set(run, PANEL_BYTES);
  } else {
    view.set(story);
  }
  ps1Colour(view, W, H);
  if (hud) drawHud(surface, v);
  return view;
}
