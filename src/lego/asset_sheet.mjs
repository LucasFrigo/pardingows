// Builds numbered thumbnail sheets of the Sketchfab candidates and checks their licence on the public API. No account needed.
//   node src/lego/asset_sheet.mjs
// Out: blender/lego/review/00-assets-{1-figuras,2-pecas,3-cenarios}.png and 00-assets.json. Red text is a licence problem.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'Fredoka-SemiBold.ttf'), 'Fredoka');

const PAGES = {
  '1-figuras': [
    ['BASE RIG', '7e457f008932400d879504a8924fa3cf'], ['BASE RIG', '826da5c89c0e43b3ae31b3e4bb9e989c'], ['BASE RIG', '42612b64a3004d3c97872c4c444f9544'],
    ['BASE RIG', '3ac263e0f3104e46a392245ab56eec9f'], ['BASE', 'ce3274a82ee74249901010d93fce3853'], ['BASE', 'ba578425afcc4dc2b4879c92885ad92f'],
    ['BASE', '5ba6a5759315437a85fac54749c46c82'], ['BASE', 'c93e5655b94343afa12c6b3a1a81823a'], ['BASE', 'ea25f6a5c9f9491bb624ee731406b0e4'],
    ['CROWD', 'd98f8361b4314af286e6ae3742401570'], ['CROWD', '65f5df1e7c9a4cfe8e6bbe63ef880922'], ['CROWD', '9c8fa7f144d747dab1a1602b13431f05'],
    ['CROWD', '0393881e3e3a4883b6f572fff5149ecb'], ['CROWD', 'cbd0649a27664f17bf88d125fded129a'], ['CROWD', 'fcf25fb9770144e59d5f13d72db2d732'],
    ['CROWD', 'ab23809108d5469883d1ae0e8ff29caf'], ['CROWD', 'f54e5da4640c47ae861cdf1f742ced6f'], ['CROWD', '32a249e14f27436780aff34f4b00b499'],
    ['FAR CROWD', 'e7bdf43f03d4412dbc6e98852f5b371a'], ['FAR CROWD', 'b6457d9fdf4345a19381749169a56f93'], ['ROBBER', 'd1827a5a2f4548e48bb4b11e6522dc49'],
    ['DALI REF', '8badb112834946c2b3e044b67586954c'], ['SUIT', 'bcd5bfec376f486abdf1aa94efaa1f92'], ['SUIT', '3470c3aec04d4262b7e11994c3f31a8e'],
    ['CHILD', 'de0d79eb1cfa44ce895b8284dd336f73'], ['CHILD', 'cbd0649a27664f17bf88d125fded129a'],
  ],
  '2-pecas': [
    ['DALI MASK', '85beed593d2c49259c15b56be68e1d5c'], ['DALI MASK', 'd6c9f3b5dfa248c1830fe21fc4173482'], ['DALI MASK', '1f14f87ff10b4416bf181522cc4eb0f4'],
    ['HAIR', '42aa4810ed45460984183273c217654d'], ['HAIR', '03dbff0a4f4e4eafa116b8ff47770645'], ['BUBBLE', '1d24ea0a33cf435aaaca26153258bb3d'],
    ['BUBBLE', '431e655d024a4904b67c216ad256a177'], ['STUD', 'd0023a15d1ed4c25be357309da26afa4'], ['BRICKS', 'e04a66da0b4e4b6a86a7da18d8de4d75'],
    ['BRICK', 'fe10ac44c033412bbd43afb86cca6254'], ['BRICK', '34ccee53c6ee4e54a596a6386ebff4c2'], ['CASH', 'c9a3b36cb53b48cbbb017e551840d724'],
    ['CASH', '12ee4bb4ab814de6931b6f2460c4f11b'], ['CASH', '3f9d74e92b584af890a41cff108d2b1a'], ['GOLD', '0d1ff6b3e6d045cba78889caf7f5bc6e'],
    ['BRIEFCASE', '0f5b865144074c52b1ed04777de980d5'], ['BRIEFCASE', '9490e77925934d199235030b1a4d32c9'], ['DJ', 'b7bb537521bd4fa9be15926c24bb4656'],
    ['DJ', '89f366c3415641089e3192acffd0e89c'], ['DJ', '495a62d8f03f48788ae31e9d50648b9c'], ['JOINT', '5b7dcea4012d4843a4c2baac027c7e78'],
    ['JOINT', '00b86fecb88f4e5aa9a3f492dfae8448'], ['CLOCK', '19f68e57f79c40658b1c6bbe434a0386'], ['MUG BOARD', '61a20aade5fc49e78736cc8fd188a8eb'],
  ],
  '3-cenarios': [
    ['VAULT', 'af389a721faa4ec49eaec7ec2a215371'], ['INTERROG.', 'e3865c02170e43aba21d0c9d26904677'], ['INTERROG.', 'a4680b6c051c448e9fa3efe46c8975a7'],
    ['HOUSE', 'cc0ac9132a3646da9ba884bf78060c73'], ['HOUSE', '2f1fbbffe4f74330a0456b6434520bca'], ['HOUSE PROPS', '23a962a910604f4a86e7f13a4aea6b39'],
    ['BUS', '9fef772cf9a74aeab238828b82d05b29'], ['CAR', 'f55e4d6ed9354e3e933a28879153716b'], ['CARS', '6b94e5aef92c484d8e55516457325c26'],
    ['BIKE', 'b535a5a2173c49d592259dac7fc8b516'], ['TRAIN', '9c470dc0669c4eae8fbbdcdf00ac670d'], ['TRAIN', 'dde6a3f234554942ba9b65767e864e9b'],
    ['BENCH', '71f7a1b7b6ec44e7a3714cf3eb43d964'], ['TREE', '842efd6c8eb04449aca12cd599a27af3'], ['TREE', '6df6061f989747e1b334276f66c71576'],
    ['PLANTS', '78c18640757f4f16a316c76bc9ea8544'], ['BUSH', 'f3e20f36aa0d4483a960e39cb33e0727'], ['FLOWERS', '17e93f929b7d417a9ede9c55d56cb9da'],
    ['FLOWERS', 'd9c5c3c9366f4de0adba13d3ed80de93'], ['LAMP', '35e80fe8959049e3b7eaf4dcf8da6df8'], ['COUCH', '82160a5daf5343cb9dfaa280543a8bb5'],
    ['COUCH', '14381f3ceed94355b20ee516c8fad8b5'], ['TABLE', 'ce218d8147444a3c830e406e4bfb56b3'], ['CAGE', '999e12dcf6b54789bb4b5412c9218456'],
  ],
};

const REVIEW = path.join(ROOT, 'blender/lego/review');
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
    ctx.font = '20px Fredoka';
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
    ctx.fillStyle = '#ffd23f';
    ctx.fillText(`${num} ${role}`, x + 2, y + TH + 22);
    ctx.fillStyle = '#ffffff';
    ctx.font = '17px Fredoka';
    ctx.fillText(m.name.slice(0, 36), x + 2, y + TH + 45);
    ctx.fillStyle = fine ? '#ffffff' : '#ff5040';
    ctx.fillText(`${m.faceCount}f anim:${m.animationCount} ${licence}${m.isDownloadable ? '' : ' NO-DL'}`, x + 2, y + TH + 68);
    report.push({ n: num, page, role, uid, name: m.name, author: m.user?.username, licence, faces: m.faceCount, anim: m.animationCount, dl: m.isDownloadable, url: m.viewerUrl });
    console.log([num, role, uid, m.name.slice(0, 40), licence, `${m.faceCount}f`, `anim:${m.animationCount}`, m.isDownloadable ? 'dl' : 'NO-DL'].join(' | '));
  }
  const out = path.join(REVIEW, `00-assets-${page}.png`);
  fs.writeFileSync(out, canvas.toBuffer('image/png'));
  console.log('wrote', out, `${canvas.width}x${canvas.height}`);
}
fs.writeFileSync(path.join(REVIEW, '00-assets.json'), JSON.stringify(report, null, 1));
