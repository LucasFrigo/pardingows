// Builds a thumbnail sheet of the Sketchfab picks and checks their licence on the public API. No account needed.
//   node src/missao/asset_sheet.mjs [out.png]
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import ffmpeg from 'ffmpeg-static';
import { Surface, hex } from '../shared/engine.mjs';
import { drawText } from '../shared/font.mjs';
import { encodePNG } from '../shared/png.mjs';

const PICKS = [
  ['CASAS 1', 'b9797c38e4e645b39f0cda8c05bebd5f'],
  ['CASAS 2', 'c87942d7d3ba43648920c7f7cd451afc'],
  ['CASAS ALT', 'be4a54f622a14f8b8bb8df70046f1dc1'],
  ['CASAS ALT', '789cd0b9c4644a01adc3ace61573baf1'],
  ['CASAS ALT', 'e2b6f532e1fe4f7280890971d78183f4'],
  ['RUA PROPS', '381b65d98a5b4e3886ac2acace7e5c74'],
  ['CERCA', '57d3e84f276d46c6b4bab1e502d9a4d5'],
  ['RUA ALT', '12cb749961974f94a4063e67dafb2d76'],
  ['VAN', '1cac40905d494bae8108a556d870e23e'],
  ['PARAGUAIO', 'f9acca1dc1ec411699ffd6337889e058'],
  ['PARAGUAIO ALT', '67368ece5a8d47e7aeffbe2253f6bdd5'],
  ['DINGOW 1', 'dc42fa861cd645f489be5c9b3d2076fb'],
  ['DINGOW 2', '391f58976d4c484e85909d38561005af'],
  ['COLCHAO', 'e914df64a021484a91613b38c28ee538'],
  ['CAMA ALT', '4bc7357e5d494d8e9b70f58fc960003e'],
  ['RELOGIO', '23b2d0e81d414836877c555e5b5fc18d'],
  ['CRIADO', 'df9eb305734b412693c715f94e8878a0'],
  ['ABAJUR', '17aab30248a34734ae3c64137444aeae'],
  ['DINHEIRO', '632cf7dbc59a496283d1a6092dc6f9b0'],
  ['DINHEIRO 2', '4abdbd60b1cb41a88233d38f878798e3'],
  ['DINHEIRO ALT', 'be499af5e7294a1d97f34e808bf0474b'],
  ['LIXEIRA', 'aa73886e4a754f37bd7128d77c3aff6c'],
  ['LIXEIRA ALT', '7d149495e5004301b518ce3bd4895484'],
  ['SACOS', '9e769751ac3a4b6a893a5719349b78ca'],
  ['LATA LIXO', '6b691a9cb47249809e52aab5346aa430'],
  ['BOSTA', '5b80e6a023fc4ca591f4a9f73eb09a93'],
  ['POCA', '1b6132426e154eec994e3b59c65a2a07'],
  ['RATO', '896e654c7fdc41a78cf554005e3bdfcd'],
  ['LANCHONETE', '0d509e6f9e9f436092b80e918bada322'],
  ['LANCH ALT', '1a322d0c3eb543c3a5f9cea0937684d5'],
  ['CAIXA', '87562962d47e48b28cc1b874fa46a47f'],
  ['GELADEIRA', 'da718d715d3e4ec0a3b043946d2b3142'],
];

const out = process.argv[2] || 'blender/missao/review/00-assets.png';
fs.mkdirSync(path.dirname(out), { recursive: true });

const COLS = 6, TW = 300, TH = 169, CAP = 34, GAP = 4;
const rows = Math.ceil(PICKS.length / COLS);
const sheet = new Surface(COLS * (TW + GAP) + GAP, rows * (TH + CAP + GAP) + GAP).clear(hex('#14151c'));
const WHITE = hex('#ffffff'), YEL = hex('#ffd23f'), RED = hex('#ff5040');

for (const [i, [role, uid]] of PICKS.entries()) {
  const x = GAP + (i % COLS) * (TW + GAP), y = GAP + Math.floor(i / COLS) * (TH + CAP + GAP);
  const r = await fetch(`https://api.sketchfab.com/v3/models/${uid}`);
  if (!r.ok) {
    console.log(`${role} | ${uid} | HTTP ${r.status}`);
    drawText(sheet, `${role}: HTTP ${r.status}`, x, y + TH + 3, RED);
    continue;
  }
  const m = await r.json();
  const url = m.thumbnails?.images?.filter(im => im.width >= TW).sort((a, b) => a.width - b.width)[0]?.url;
  if (url) {
    const bytes = Buffer.from(await (await fetch(url)).arrayBuffer());
    // ffmpeg alone touches the downloaded image, which is decoded straight to raw pixels and never saved
    const d = spawnSync(ffmpeg, ['-v', 'error', '-i', 'pipe:0',
      '-vf', `scale=${TW}:${TH}:force_original_aspect_ratio=decrease,pad=${TW}:${TH}:(ow-iw)/2:(oh-ih)/2`,
      '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], { input: bytes, maxBuffer: 1 << 24 });
    if (d.stdout?.length === TW * TH * 4) {
      const px = new Uint32Array(d.stdout.buffer.slice(d.stdout.byteOffset, d.stdout.byteOffset + d.stdout.length));
      for (let row = 0; row < TH; row++) sheet.px.set(px.subarray(row * TW, (row + 1) * TW), (y + row) * sheet.w + x);
    }
  }
  const licence = m.license?.slug || m.license?.label || '?';
  const fine = m.isDownloadable && /^(by|cc0)$/.test(m.license?.slug || '');
  drawText(sheet, `${i + 1} ${role}`, x, y + TH + 3, YEL);
  drawText(sheet, m.name.toUpperCase().slice(0, 46), x, y + TH + 13, WHITE);
  drawText(sheet, `${m.faceCount}F ANIM ${m.animationCount} ${licence.toUpperCase()}`, x, y + TH + 23, fine ? WHITE : RED);
  console.log([i + 1, role, uid, m.name, m.user?.username, licence, `${m.faceCount}f`, `anim:${m.animationCount}`, m.isDownloadable ? 'dl' : 'NO-DL'].join(' | '));
}

fs.writeFileSync(out, encodePNG(sheet.w, sheet.h, Buffer.from(sheet.px.buffer)));
console.log('wrote', out, `${sheet.w}x${sheet.h}`);
