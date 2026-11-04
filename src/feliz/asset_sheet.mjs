// Builds a thumbnail sheet of the Sketchfab candidates and checks their licence on the public API. No account needed.
//   node src/feliz/asset_sheet.mjs [out.png]
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'Fredoka-SemiBold.ttf'), 'Fredoka');

const PICKS = [
  ['TREE', '2ed2a55eebbb4b4fb60484390f611d20'], ['TREE', 'b2321d4b5c084a9096e2e073bfe51618'], ['TREE', '886d00adb27f42b18a78004081a1f73c'],
  ['TREE', 'dde49eebec874267b52e53404655f9ca'], ['COCONUT', 'd141941578044b0f861ca83b36d4c411'], ['PALM', '55690379305145488e20afb05fc687e6'],
  ['HOUSE', '68fd7b3b59d8441e82e64960620ac0e2'], ['HOUSE', '45a28a49e57e496e8b91d6de5c0ac88a'], ['HOUSE', '6198d1e97a2340bf92748fc4fdca0a71'],
  ['HOUSE', '745f09c22e8943b3bcc5fa47e0aea6ec'], ['BANK', '643a7dbe74694e4d838bb761a19d92ba'],
  ['PLANTS', '442904f26b87407d98871b50b49c4169'], ['NATURE', 'cb45d4926fcb4807bc93126b59325cf8'], ['FLOWER', '58ce34c65642408cb92eab784af2bd6c'],
  ['BAMBOO', 'd0d5eb345ff7420bb7f5c5239fcec637'], ['LILY', '04dd636204cd4b0db45a4fc82efa4385'], ['LOTUS', '12768caa111f446b8796e70f9cc53a23'],
  ['FOUNTAIN', 'd6d9e82784ae466c9b568e968f60d2e2'], ['FENCE', '9d8ce953d9414a07b974af8629dda93a'], ['LAMP', '6f257cdc33e6470a836892cb7fa6a47f'],
  ['BENCH', 'e53ad46c604c44e59a98bad27041cb19'], ['PICNIC', 'fe35acda3a5245da8459d1a062e28190'], ['MAILBOX', '52cd14f6b8f54bb6bb26d728c02fd9e2'],
  ['APPLE', '0176be079c2449e7aaebfb652910a854'], ['FRUITS', '7032a06ecb9b4370bdae87f656012356'],
  ['BERG', 'e45e5e07a86d4e159acf3007da95d614'], ['BERG', '53532e62af0c483e82ecfc5694f8c2a9'], ['BERG', '8d067b5049c349c5af727b00e8f9dda6'],
  ['BERG', '546e180a3f5e420a9d7c0969194f5a9d'], ['BERG', '2f3c7ea09f3944c6ac561389ceb52145'], ['BERG', '22697eb04fd746b39eced08ef957bc84'], ['BERG', '4a36fcde390f42b1957b79fd8c35146f'],
  ['VILLAGER', 'b2bd1ee7858444bda366110a2d960386'], ['VILLAGER', '01674a892f414c0681afdeb563cc8e13'], ['VILLAGER', '613776d688764d0aaa615d1c84379733'],
  ['VILLAGER', '5be9012283c340de8d48a59bcfa0a39b'], ['VILLAGER', '2b3b6a5abe784dfe816fec5bf62542c2'], ['VILLAGER', '063f5f668fc14df0b095c0060b376882'], ['VILLAGER', '0a2f57a889d54e44974d2fc58ece8477'],
  ['HIVE', 'ef6d00cb87684d60ae47a5c1d4e50f20'], ['BEE', '76801d3aea024063bc5d91e4ee355508'], ['ENVELOPE', '196ab6a55cbd4b999beccbce3c7b92a0'],
  ['CLIPBOARD', '4a47897c83b94a988acfe271de27343d'], ['PHONE', '4ff99cf17b164e7b9790638c5d2ef4ce'], ['BOOMBOX', 'd9f19a9ddce04dac8586b34869d0c1ba'],
  ['AERO', 'e303396edee34b64af752cc1cba8e0f7'], ['AERO', '23ad9c70727c4edeabbf7208b7c3511c'], ['KOI', '236859b809984f52b70c94fd040b9c59'],
  ['DOLPHIN', 'f4abb460956240f98b7a6f19cc3037a1'], ['DOLPHIN', '3a7112396c7642df9201094a9b3634b0'], ['CLOWNFISH', '1bc61f9dc8e7483fab5b114f15231030'],
  ['BUTTERFLY', '0f24b085e8654e4db09c2fe681a79e3f'], ['CLOUDS', 'd9c1ff67f80841c6b1d8229dca5495a5'], ['AURORA', 'd66b8ca6f9b541beb54df5f115dce4fe'],
  ['ISLAND', 'b9a708aa70424f0699e9c4e3b5b5700a'], ['BALLOON', 'a420e9196b744919806ae532b3a11bf7'], ['BUBBLE', '893be3cf512848ba842912b7c61566b1'], ['DROPS', 'f8f24228aebf41f297c878ad82ea7db0'],
];

const out = path.resolve(process.argv[2] || path.join(ROOT, 'blender/feliz/review/00-assets.png'));
fs.mkdirSync(path.dirname(out), { recursive: true });

const COLS = 8, TW = 240, TH = 135, CAP = 62, GAP = 6;
const rows = Math.ceil(PICKS.length / COLS);
const canvas = createCanvas(COLS * (TW + GAP) + GAP, rows * (TH + CAP + GAP) + GAP);
const ctx = canvas.getContext('2d');
ctx.fillStyle = '#14151c';
ctx.fillRect(0, 0, canvas.width, canvas.height);

const report = [];
for (const [i, [role, uid]] of PICKS.entries()) {
  const x = GAP + (i % COLS) * (TW + GAP), y = GAP + Math.floor(i / COLS) * (TH + CAP + GAP);
  ctx.font = '15px Fredoka';
  const r = await fetch(`https://api.sketchfab.com/v3/models/${uid}`);
  if (!r.ok) {
    ctx.fillStyle = '#ff5040';
    ctx.fillText(`${i + 1} ${role}: HTTP ${r.status}`, x + 2, y + TH + 16);
    console.log(`${i + 1} | ${role} | ${uid} | HTTP ${r.status}`);
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
  ctx.fillText(`${i + 1} ${role}`, x + 2, y + TH + 16);
  ctx.fillStyle = '#ffffff';
  ctx.fillText(m.name.slice(0, 30), x + 2, y + TH + 34);
  ctx.fillStyle = fine ? '#ffffff' : '#ff5040';
  ctx.fillText(`${m.faceCount}f anim:${m.animationCount} ${licence}${m.isDownloadable ? '' : ' NO-DL'}`, x + 2, y + TH + 52);
  report.push({ n: i + 1, role, uid, name: m.name, author: m.user?.username, licence, faces: m.faceCount, anim: m.animationCount, dl: m.isDownloadable, url: m.viewerUrl });
  console.log([i + 1, role, uid, m.name, m.user?.username, licence, `${m.faceCount}f`, `anim:${m.animationCount}`, m.isDownloadable ? 'dl' : 'NO-DL'].join(' | '));
}

fs.writeFileSync(out, canvas.toBuffer('image/png'));
fs.writeFileSync(out.replace(/\.png$/, '.json'), JSON.stringify(report, null, 1));
console.log('wrote', out, `${canvas.width}x${canvas.height}`);
