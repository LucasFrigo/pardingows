// 15-bit colour with ordered dither, as the console's framebuffer did it. Works in place on RGBA pixels.
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => v / 16 - 0.47);
const STEP = 255 / 31;

export function ps1Colour(px, W, H) {
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
