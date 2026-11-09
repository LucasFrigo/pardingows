// Builds numbered thumbnail sheets of the Sketchfab candidates and checks their licence on the public API. No account needed.
//   node src/pardao/asset_sheet.mjs
// Out: blender/pardao/review/00-assets-{1-personagens,2-cenarios,3-objetos}.png and 00-assets.json. Red text is a problem or a rights flag.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'VT323-Regular.ttf'), 'VT323');

// Roles starting with ! are flagged red: a rights or fit question to settle before picking
const PAGES = {
  '1-personagens': [
    ['HOBO PACK', 'f1c8018af59643e0b009a6f018ed9fd9'], ['HOBO BEGGAR', 'f9182eda717247a7abcba196194678b4'], ['HOBO THUG', 'dbef859c56b94f29ba8f0f04ea0b69e7'],
    ['HOBO THUG', '6410256c1c41417bbc1de043983b3107'], ['HOBO THUG', 'a87ea950da3046fca42556f6e4d97978'], ['HOBO ANIM', 'b7fc02917e0348f49f5290aaa34cafdb'],
    ['HOBO ANIM', 'ccce1abd9086451da3bed9ec30c82c37'], ['HOBO BASE', '16522107ad84410dad419e2e3977e721'], ['HOBO BASE', 'ee1720e435104fcb9c146c7323b33cf3'],
    ['CROWD', '4fe76fdec12d456f9b0db06b45cc53d6'], ['CROWD', '18d109a76d714dc4a15b0e06794c1895'], ['!BANDIDO', 'd82140c46741468bbc5e9648b7e301d8'],
    ['DONKEY', 'e46951f1f62b44f79657400d75e8fc8d'], ['HORSE', '5b1bbcb42f4544c892381acdcb57c0de'],
  ],
  '2-favela': [
    ['FAVELA', 'e2b6f532e1fe4f7280890971d78183f4'], ['FAVELA', 'b9797c38e4e645b39f0cda8c05bebd5f'], ['FAVELA', 'c87942d7d3ba43648920c7f7cd451afc'],
    ['FAVELA', 'be4a54f622a14f8b8bb8df70046f1dc1'], ['FAVELA', '789cd0b9c4644a01adc3ace61573baf1'], ['FAVELA', 'f6548caa15d04a3d987540ac2de486a1'],
    ['FAVELA', '9631e0bae22343db82c44fe243af7c15'], ['FAVELA', '545c2cb0b12b4f5db74d014b4ebd620b'], ['FAVELA', '7164cfffd09743899278ab52f688e566'],
    ['FAVELA', '03a03568eb0d4c9cbae9b1ce4091b059'], ['FAVELA', '2473e58947004b3fadc5daa6fad6afeb'], ['FAR HILL', '2e238fa40a9844cb85374ea2d9715617'],
    ['STAIRS', 'b552862f1bff4a968fa65da90c6a9e6b'], ['STAIRS', '8bc4ce5657e548bbacada83f04e7f50d'], ['WALL', '51c6567b2d524f179254667176f60a3a'],
    ['GRAFFITI', '2fdfb7253c4044aab30c933cce951bc2'], ['GRAFFITI', '1cf3690327bd449881ba6857d8fe7caf'], ['METAL', 'ea06568a9e304ecc806cb7cb0552e269'],
    ['METAL', '990d00952f024be2abdfd8597cd577ea'], ['WATER TANK', 'aff4e9fd3f7042d5855fade7411df4df'], ['POWER LINE', '55261fa6535e4d5ea8c7af390c478110'],
    ['POWER POLE', '13b1a28037914b439da6dd4b0e97c19e'], ['LAMPPOST', 'e127bb7b1a154529b7d4fc4a1be4bc99'], ['FLAGS', '64a08e45f72640659a590cc1ea805301'],
    ['KOMBI', 'f6a7b54ec6d24d8e95992f68be6c930c'], ['MOTORBIKE', '9c486accf04f41389b8d5ca01968ec06'], ['!SUGARLOAF', '3056799d946547f9ae4641ec0535f735'],
  ],
  '3-objetos': [
    ['CHAIR', '68089dce5fa1461981d690f1cfd657fa'], ['CHAIRS', '0a6eafb63018479b98d29456dc3f6fc8'], ['BEER CRATE', '24329e92a51b41f690fe4bfbd510c9f3'],
    ['TABLE', 'c0f6e92135be4206a0b5de58c9d5f336'], ['TRASH BAG', '9ef36ddf03bb4db99bc32a369cc2c871'], ['TRASH BAGS', '51cb07645ffa494e9bb67b292f4df86e'],
    ['TRASH CAN', '269cc79ce7ca4dcf88030e7b7151dc36'], ['DUMPSTER', '7dca2f86161346a894f113cafb473e72'], ['FIRE BARREL', '166e9eb26fd9406b961fa08722648093'],
    ['FIRE BARREL', '597b2634c423409e9ad6ca36901dba9c'], ['CART', '96534b56f0d9487db08f00f1f9301fa1'], ['CART', 'b96f896453b240ae804d0399f1faf027'],
    ['BOXES', '5d3d508061e544739e37c685af235684'], ['BOXES', '72a4804f8a4d4de18e59abb60b81c54f'], ['BOOMBOX', 'd9f19a9ddce04dac8586b34869d0c1ba'],
    ['BASS BIN', '7c0d85ad0df04153a864a49e575b6416'], ['PA SPEAKER', 'b6d18dc5a9ae49aa872b5d2af72da659'], ['DJ', '00615da2444f437da7efa342c05be7ff'],
    ['MIC STAND', '16cfa90113ee43f4812d062d37d26462'], ['JOINT', 'fc5daec8fc7f4fbf9424736fd4bcbdf0'], ['CALENDAR', '592f4833145442d2871b8f7c23a113b0'],
    ['BAT', '2669cf86386747449611396c0409db47'], ['MELEE PSX', '79cae670d515469a947617d18e5a6c89'], ['GOLD CHAIN', 'c17a4e4ce9ed4a61adcad52016b8becf'],
  ],
};

const REVIEW = path.join(ROOT, 'blender/pardao/review');
fs.mkdirSync(REVIEW, { recursive: true });

const COLS = 6, TW = 320, TH = 180, CAP = 76, GAP = 8;

async function api(uid) {
  for (let tries = 0; tries < 5; tries++) {
    const r = await fetch(`https://api.sketchfab.com/v3/models/${uid}`);
    if (r.status !== 429) return r;
    await new Promise(res => setTimeout(res, 4000 * (tries + 1)));
  }
  return { ok: false, status: 429 };
}

const report = [];
let num = 0;
for (const [page, picks] of Object.entries(PAGES)) {
  const rows = Math.ceil(picks.length / COLS);
  const canvas = createCanvas(COLS * (TW + GAP) + GAP, rows * (TH + CAP + GAP) + GAP);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#14151c';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (const [i, [role, uid]] of picks.entries()) {
    num++;
    const x = GAP + (i % COLS) * (TW + GAP), y = GAP + Math.floor(i / COLS) * (TH + CAP + GAP);
    ctx.font = '24px VT323';
    const r = await api(uid);
    if (!r.ok) {
      ctx.fillStyle = '#ff5040';
      ctx.fillText(`${num} ${role}: HTTP ${r.status}`, x + 2, y + TH + 22);
      console.log(`${num} | ${role} | ${uid} | HTTP ${r.status}`);
      continue;
    }
    const m = await r.json();
    const url = m.thumbnails?.images?.filter(im => im.width >= TW).sort((a, b) => a.width - b.width)[0]?.url;
    if (url) {
      try {
        // The downloaded thumbnail is only decoded in memory, never saved
        const img = await loadImage(Buffer.from(await (await fetch(url)).arrayBuffer()));
        const k = Math.min(TW / img.width, TH / img.height);
        ctx.drawImage(img, x + (TW - img.width * k) / 2, y + (TH - img.height * k) / 2, img.width * k, img.height * k);
      } catch { /* leave the slot blank */ }
    }
    const licence = m.license?.slug || m.license?.label || '?';
    const fine = m.isDownloadable && /^(by|cc0)$/.test(m.license?.slug || '');
    ctx.fillStyle = role.startsWith('!') ? '#ff5040' : '#ffd23f';
    ctx.fillText(`${num} ${role}`, x + 2, y + TH + 22);
    ctx.fillStyle = '#ffffff';
    ctx.fillText(m.name.slice(0, 36), x + 2, y + TH + 45);
    ctx.fillStyle = fine ? '#ffffff' : '#ff5040';
    ctx.fillText(`${m.faceCount}f anim:${m.animationCount} ${licence}${m.isDownloadable ? '' : ' NO-DL'}`, x + 2, y + TH + 68);
    report.push({ n: num, page, role, uid, name: m.name, author: m.user?.username, licence, faces: m.faceCount, anim: m.animationCount, dl: m.isDownloadable, url: m.viewerUrl });
    console.log([num, role, uid, m.name, m.user?.username, licence, `${m.faceCount}f`, `anim:${m.animationCount}`, m.isDownloadable ? 'dl' : 'NO-DL'].join(' | '));
  }
  const out = path.join(REVIEW, `00-assets-${page}.png`);
  fs.writeFileSync(out, canvas.toBuffer('image/png'));
  console.log('wrote', out, `${canvas.width}x${canvas.height}`);
}
fs.writeFileSync(path.join(REVIEW, '00-assets.json'), JSON.stringify(report, null, 1));
