// Bitmap fonts. BIG is 5x7 (captions, neon signs); MINI is 3x5 (badge).
const g = rows => rows.split(' ');

const BIG_GLYPHS = {
  A: g('.###. #...# #...# ##### #...# #...# #...#'),
  B: g('####. #...# #...# ####. #...# #...# ####.'),
  C: g('.###. #...# #.... #.... #.... #...# .###.'),
  D: g('####. #...# #...# #...# #...# #...# ####.'),
  E: g('##### #.... #.... ####. #.... #.... #####'),
  F: g('##### #.... #.... ####. #.... #.... #....'),
  G: g('.###. #...# #.... #.### #...# #...# .####'),
  H: g('#...# #...# #...# ##### #...# #...# #...#'),
  I: g('.###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.'),
  J: g('..### ...#. ...#. ...#. ...#. #..#. .##..'),
  K: g('#...# #..#. #.#.. ##... #.#.. #..#. #...#'),
  L: g('#.... #.... #.... #.... #.... #.... #####'),
  M: g('#...# ##.## #.#.# #.#.# #...# #...# #...#'),
  N: g('#...# ##..# #.#.# #..## #...# #...# #...#'),
  O: g('.###. #...# #...# #...# #...# #...# .###.'),
  P: g('####. #...# #...# ####. #.... #.... #....'),
  Q: g('.###. #...# #...# #...# #.#.# #..#. .##.#'),
  R: g('####. #...# #...# ####. #.#.. #..#. #...#'),
  S: g('.#### #.... #.... .###. ....# ....# ####.'),
  T: g('##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..'),
  U: g('#...# #...# #...# #...# #...# #...# .###.'),
  V: g('#...# #...# #...# #...# #...# .#.#. ..#..'),
  W: g('#...# #...# #...# #.#.# #.#.# #.#.# .#.#.'),
  X: g('#...# #...# .#.#. ..#.. .#.#. #...# #...#'),
  Y: g('#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..'),
  Z: g('##### ....# ...#. ..#.. .#... #.... #####'),
  0: g('.###. #...# #..## #.#.# ##..# #...# .###.'),
  1: g('..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.'),
  2: g('.###. #...# ....# ...#. ..#.. .#... #####'),
  3: g('####. ....# ....# .###. ....# ....# ####.'),
  4: g('...#. ..##. .#.#. #..#. ##### ...#. ...#.'),
  5: g('##### #.... ####. ....# ....# #...# .###.'),
  6: g('.###. #.... #.... ####. #...# #...# .###.'),
  7: g('##### ....# ...#. ..#.. .#... .#... .#...'),
  8: g('.###. #...# #...# .###. #...# #...# .###.'),
  9: g('.###. #...# #...# .#### ....# ....# .###.'),
  ',': g('... ... ... ... ... .#. #..'),
  '.': g('. . . . . . #'),
  '!': g('# # # # # . #'),
  '?': g('.###. #...# ....# ...#. ..#.. ..... ..#..'),
  '-': g('.... .... .... #### .... .... ....'),
  'Ç': g('.###. #...# #.... #.... #.... #...# .###. ..#.. .##..'),
  '+': g('..... ..#.. ..#.. ##### ..#.. ..#.. .....'),
  $: g('..#.. .#### #.#.. .###. ..#.# ####. ..#..'),
  "'": g('# # . . . . .'),
  ':': g('. . # . # . .'),
  '(': g('.# #. #. #. #. #. .#'),
  ')': g('#. .# .# .# .# .# #.'),
  '♥': g('.#.#. ##### ##### ##### .###. ..#.. .....'),
  '★': g('..#.. ..#.. ##### .###. .#.#. #...# .....'),
  '♪': g('..##. ..#.# ..#.. ..#.. .##.. ###.. .#...'),
};

// Accents sit in the two rows above the cap height.
const ACCENTS = {
  acute: ['...#.', '..#..'],
  tilde: ['.#..#', '#.##.'],
  circ: ['..#..', '.#.#.'],
};
const ACCENTED = {
  'Á': ['A', 'acute'], 'É': ['E', 'acute'], 'Í': ['I', 'acute'], 'Ó': ['O', 'acute'], 'Ú': ['U', 'acute'],
  'Ã': ['A', 'tilde'], 'Õ': ['O', 'tilde'], 'Â': ['A', 'circ'], 'Ê': ['E', 'circ'], 'Ô': ['O', 'circ'],
};

const MINI_GLYPHS = {
  A: g('.#. #.# ### #.# #.#'), D: g('##. #.# #.# #.# ##.'), G: g('.## #.. #.# #.# .##'),
  I: g('### .#. .#. .#. ###'), N: g('##. #.# #.# #.# #.#'), O: g('.#. #.# #.# #.# .#.'),
  P: g('##. #.# ##. #.. #..'), R: g('##. #.# ##. #.# #.#'), S: g('.## #.. .#. ..# ##.'),
  U: g('#.# #.# #.# #.# ###'), W: g('#.# #.# #.# ### #.#'), '-': g('.. .. ## .. ..'),
  '·': g('. . # . .'),
};

export const BIG = { glyphs: BIG_GLYPHS, h: 7, space: 4, gap: 1 };
export const MINI = { glyphs: MINI_GLYPHS, h: 5, space: 2, gap: 1 };

function glyphOf(font, ch) {
  if (font === BIG && ACCENTED[ch]) {
    const [base, acc] = ACCENTED[ch];
    return { rows: font.glyphs[base], accent: ACCENTS[acc] };
  }
  return { rows: font.glyphs[ch] || null, accent: null };
}

export function charWidth(font, ch) {
  if (ch === ' ') return font.space;
  const { rows } = glyphOf(font, ch);
  return rows ? rows[0].length + font.gap : font.space;
}

export function textWidth(font, str, scale = 1) {
  let w = 0;
  for (const ch of str) w += charWidth(font, ch);
  return (w - font.gap) * scale;
}

// Calls plot(x, y) for every lit pixel of str starting at (x, y) top-left of cap height.
export function eachPixel(font, str, x, y, scale, plot) {
  let cx = x;
  for (const ch of str) {
    const { rows, accent } = glyphOf(font, ch);
    if (rows) {
      const all = accent ? [[accent, -2], [rows, 0]] : [[rows, 0]];
      for (const [rr, off] of all)
        rr.forEach((row, ry) => {
          for (let rx = 0; rx < row.length; rx++)
            if (row[rx] === '#')
              for (let oy = 0; oy < scale; oy++)
                for (let ox = 0; ox < scale; ox++) plot(cx + rx * scale + ox, y + (ry + off) * scale + oy);
        });
    }
    cx += charWidth(font, ch) * scale;
  }
  return cx;
}

// Text with optional outline and drop shadow, the TikTok-caption look.
export function drawText(s, str, x, y, color, { font = BIG, scale = 1, outline = 0, shadow = 0, alpha = 1 } = {}) {
  if (shadow) eachPixel(font, str, x, y, scale, (px, py) => {
    for (let oy = -1; oy <= 2; oy++) for (let ox = -1; ox <= 2; ox++) s.blend(px + ox, py + oy + 1, shadow, alpha);
  });
  if (outline) eachPixel(font, str, x, y, scale, (px, py) => {
    for (let oy = -1; oy <= 1; oy++) for (let ox = -1; ox <= 1; ox++) s.blend(px + ox, py + oy, outline, alpha);
  });
  return eachPixel(font, str, x, y, scale, (px, py) => s.blend(px, py, color, alpha));
}
