// Builds numbered thumbnail sheets of the Sketchfab candidates and checks their licence on the public API. No account needed.
// Thumbnails are toned to sepia, which is how they'll read in the video.
//   node src/erva/asset_sheet.mjs
// Out: blender/erva/review/00-assets-{1-sala,2-selva,3-objetos}.png and 00-assets.json. Red text is a problem.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'AlfaSlabOne-Regular.ttf'), 'Alfa');

const PAGES = {
  '1-sala': [
    ['ROCKING CHAIR', 'd5e784aa92464572af37264c3b3d2fa6'], ['ROCKING CHAIR', 'bcd3f4e05ec44902af3b5668b2b831ca'],
    ['WING CHAIR', '49e21ea4c0bf469387471934dd8bf0fa'], ['ARMCHAIR', 'c20f084f29bd440197a18b4c750f69eb'],
    ['ARMCHAIR', '3a27e309342248da97dd058f8ca27caa'], ['CLOCK', '5dfff9d9c87f44cba61fb83179b0e3e2'],
    ['CLOCK', '6ede129be11e43cea5c279e34a7eddaa'], ['GRAMOPHONE', '5e892fc786db4ca1b36738ab5e40e64d'],
    ['GRAMOPHONE', 'a7508a4233a344008029d21a2f0024bd'], ['RADIO', 'c744a35e88ae4f0f9d71483623412808'],
    ['RADIO', 'e2b64f5031fa45e8be661a89baeae3f0'], ['ROOM', 'f98bbad839d94faea529d82fc5f28017'],
    ['BOOK', 'cc887c88fe954dc2a4be11fcfb83fec6'], ['BOOK OPEN', 'bcc69dacd1bc4eadaf4b9fc0d6e2430b'],
    ['BOOK OPEN', 'b30b6a9018f842e7b12622387979b0fa'], ['BOOKS', 'd845597f22d8454cb9775dc8018bc5a8'],
    ['POP-UP BOOK', '01fce127f039463d8466f086529e458f'], ['LONG PIPE', 'f8a626bec4984fd083758dc07bcf057a'],
    ['PIPE', '01ae21fd01614dc39f8d1a720a7804dd'], ['PIPE', 'd995ebacdc304433b39cc9a1b9e2b13b'],
    ['LONG PIPE', '6c3c666b903e4fd5a3f0adc9f88ac289'],
  ],
  '2-selva': [
    ['PALM', '95cd1a77789241ee82a960bad5dfe809'], ['BANANA', '85695b82c7ba4b3497a663616cc3bf25'],
    ['BANANA', '3856533f350b4d33b47d5d434b9ac911'], ['MONSTERA', '28bb9cca91e6479cadcd9c55242f43c1'],
    ['MONSTERA', '5ca0f61ec2a94ba8b9ecdb72e713bec6'], ['TARO', '3c9390ddb8c04387afa22241ada26a7b'],
    ['ALOCASIA', '09127a0699ea4d1c9246227e19ab452b'], ['ELEPHANT EAR', '75882b72d1374270aeac76c96db2aa4e'],
    ['BUSH', '9d9ce79d3ae040619e96d5b22c7de1a6'], ['TREES', '6cfabc6732bf40fea7090cb6557ee0d8'],
    ['TOON TREE', 'd631da94d5c14b85b44d9a737fef883f'], ['TREE', 'e319ba8a4572485087b779db7b8bdb20'],
    ['APPLE TREE', '0fa93c551d8449808cc1f85c4238bf93'], ['APPLE TREE', '956713eaab454decb4081fa38dfdb84b'],
    ['FALLEN TREE', '85be5e12759d460cb5f1f0d7a4c109b6'], ['STUMP', '04d51f5c2fb643aab3b93b451d1b77c9'],
    ['MUSHROOMS', '9d22e02ce2a548959b1c4c4c1d546842'], ['MUSHROOMS', '52e5a7373b454b1bbd789ab8ea13c0fb'],
    ['ROCKS', '480403c4689a425db3748baa88ad52c4'], ['TERRAIN', '6ee7945b00dc4b3db1d204a48de7677f'],
    ['VINE', 'e4665bcbc81a43cb90bf998242a75b6a'], ['FLOWER', '7d8acfb0b38d4e4b9ef2c6e336473049'],
    ['DAISY', '54045596253e478993ca96572cb1bf6b'], ['FLOWERS', 'bffdeb9b066c43ac9456d9899e37d509'],
    ['LOTUS', '12768caa111f446b8796e70f9cc53a23'], ['CLOUD', 'f31be54812a348df86d94171098dae19'],
    ['CLOUDS', 'd9c1ff67f80841c6b1d8229dca5495a5'], ['SPOOKY TREE', '134a1f03b97d453d8ba63752f9c3b28d'],
    ['SPOOKY TREE', 'f879f1e82b4e4ae8a392d00ac0c9dd1f'], ['SPOOKY TREE', '29afefd67e6648e0a9275bc15937e6bf'],
    ['SPOOKY TREE', 'e4ffba856d8e4c2aa905a32634a5ae65'], ['DEAD TREE', 'addc2aef9e534a93a8798320fea440ef'],
    ['GNARLED TREE', '7bdf7f23455e4298b77d3982461888a7'], ['SKELETONS', 'f07fa9b47c8c4d468b3f5a2124d53a15'],
    ['SKULL CANDLE', '05b7d3d9b9584858a425bc2716fb726b'],
  ],
  '3-objetos': [
    ['CIGARETTE', '08ec2ff5d829436c955f4b5e8e0e47a7'], ['CIGARETTES LIT', '52ecf4556be14ffc9226b48eac330feb'],
    ['JOINTS', '00b86fecb88f4e5aa9a3f492dfae8448'], ['JOINT', 'c91b6896fa41446c96feb09ed0002a3a'],
    ['ERVA PLANT', '79fe78fd6c6a426b8584115e772a5818'], ['ERVA PLANT', '73637ede37884a56bcb0f7e5d75b2ff8'],
    ['ERVA LEAF', '333f1d0c9f224e70b46782323b881ffe'], ['BOWLER HAT', '3c3f5bfb98284924a70cf410ab532bc9'],
    ['CASH REGISTER', '119e19154a6e40429c47449b7b1e2717'], ['CASH REGISTER', '87562962d47e48b28cc1b874fa46a47f'],
    ['SIGN', '0d2fbde1a0a446a1b3bb808664a7e08a'], ['SIGN', '5f0565ea4c5c46048e299cabe3768812'],
    ['JAR', 'a9709a4cae864de4a1738519376621f6'], ['PEARLS', 'badddc19523f4dc08344e8da5b143dae'],
    ['MICROPHONE', 'a5986b39102f47c5b32b212365dd7276'], ['GLOVE', '537b54ae49be4c32a00512cf13149578'],
  ],
};

const REVIEW = path.join(ROOT, 'blender/erva/review');
fs.mkdirSync(REVIEW, { recursive: true });
const COLS = 6, TW = 320, TH = 200, CAP = 80, GAP = 8, HEAD = 56;

async function api(uid) {
  for (let tries = 0; tries < 5; tries++) {
    const r = await fetch(`https://api.sketchfab.com/v3/models/${uid}`);
    if (r.status !== 429) return r;
    await new Promise(res => setTimeout(res, 4000 * (tries + 1)));
  }
  return { ok: false, status: 429 };
}

// Luminance to a sepia ramp (dark umber to warm paper), in place
function sepia(ctx, x, y, w, h) {
  const im = ctx.getImageData(x, y, w, h);
  const d = im.data;
  for (let i = 0; i < d.length; i += 4) {
    const l = (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]) / 255;
    d[i] = 26 + l * 225; d[i + 1] = 20 + l * 215; d[i + 2] = 14 + l * 186;
  }
  ctx.putImageData(im, x, y);
}

const report = [];
let num = 0;
for (const [page, picks] of Object.entries(PAGES)) {
  const rows = Math.ceil(picks.length / COLS);
  const canvas = createCanvas(COLS * (TW + GAP) + GAP, HEAD + rows * (TH + CAP + GAP) + GAP);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1c1812';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#f2e6c9';
  ctx.font = '34px Alfa';
  ctx.fillText(`PARDÃO E A ERVA · ${page.toUpperCase()} · thumbnails in sepia, as they'll read in the video`, GAP + 4, 40);
  for (const [i, [role, uid]] of picks.entries()) {
    num++;
    const x = GAP + (i % COLS) * (TW + GAP), y = HEAD + GAP + Math.floor(i / COLS) * (TH + CAP + GAP);
    ctx.font = '21px Alfa';
    const r = await api(uid);
    if (!r.ok) {
      ctx.fillStyle = '#ff5040';
      ctx.fillText(`${num} ${role}: HTTP ${r.status}`, x + 2, y + TH + 24);
      console.log(`${num} | ${role} | ${uid} | HTTP ${r.status}`);
      continue;
    }
    const m = await r.json();
    const url = m.thumbnails?.images?.filter(im => im.width >= TW).sort((a, b) => a.width - b.width)[0]?.url;
    ctx.fillStyle = '#2a241b';
    ctx.fillRect(x, y, TW, TH);
    if (url) {
      try {
        // The thumbnail is only decoded in memory, never saved
        const img = await loadImage(Buffer.from(await (await fetch(url)).arrayBuffer()));
        const k = Math.min(TW / img.width, TH / img.height);
        ctx.drawImage(img, x + (TW - img.width * k) / 2, y + (TH - img.height * k) / 2, img.width * k, img.height * k);
        sepia(ctx, x, y, TW, TH);
      } catch { /* leave the slot blank */ }
    }
    const licence = m.license?.slug || '?';
    const fine = m.isDownloadable && /^(by|cc0)$/.test(licence);
    ctx.fillStyle = '#f5c95a';
    ctx.fillText(`${num} ${role}`, x + 2, y + TH + 24);
    ctx.fillStyle = '#f2e6c9';
    ctx.font = '17px Alfa';
    ctx.fillText(m.name.slice(0, 34), x + 2, y + TH + 48);
    ctx.fillStyle = fine ? '#bfb39a' : '#ff5040';
    ctx.fillText(`${m.faceCount}f · anim ${m.animationCount} · ${licence}${m.isDownloadable ? '' : ' · NO-DL'}`, x + 2, y + TH + 71);
    report.push({ n: num, page, role, uid, name: m.name, author: m.user?.username, licence, faces: m.faceCount, anim: m.animationCount, dl: m.isDownloadable, url: m.viewerUrl });
    console.log([num, role, uid, m.name, m.user?.username, licence, `${m.faceCount}f`, m.isDownloadable ? 'dl' : 'NO-DL'].join(' | '));
  }
  const out = path.join(REVIEW, `00-assets-${page}.png`);
  fs.writeFileSync(out, canvas.toBuffer('image/png'));
  console.log('wrote', out, `${canvas.width}x${canvas.height}`);
}
fs.writeFileSync(path.join(REVIEW, '00-assets.json'), JSON.stringify(report, null, 1));
