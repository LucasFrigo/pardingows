// Builds numbered thumbnail sheets of the Sketchfab candidates and checks their licence on the public API. No account needed.
//   node src/zombies/asset_sheet.mjs
// Out: blender/zombies/review/00-assets-{1-personagens,2-cenarios,3-objetos}.png and 00-assets.json. Red text is a problem or a rights flag.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
GlobalFonts.registerFromPath(path.join(HERE, 'fonts', 'VT323-Regular.ttf'), 'VT323');

// RE marks fan models of Capcom designs: CC-BY on Sketchfab doesn't clear those rights
const PAGES = {
  '1-personagens': [
    ['ZOMBIE ANIM', 'e5780c5c161c461783d978aee98a865b'], ['ZOMBIE ANIM', '9f8f0885b2f94c6890c4debaceac9421'], ['ZOMBIE ANIM', 'c5a77a38545543ce9c64eaa534afc23b'],
    ['ZOMBIE ANIM', '4bd337e88ffb46909dc3021c5b620aa2'], ['ZOMBIE ANIM', 'f37f43b23fd541df8a2926571acfce70'], ['ZOMBIE ANIM', '49b3b4307f6a4d2386fdb02354158d04'],
    ['ZOMBIE ANIM', '2457028ac0ca4214bd1f5dc3b9d11129'], ['ZOMBIE ANIM', '6c112bed707b4444864b606299f8b85a'], ['ZOMBIE ANIM', 'e550de538cf042fdb15bc71e78800863'],
    ['ZOMBIE ANIM', '4b99029f6ca5413aa4924b4724336ccd'], ['ZOMBIE ANIM', 'a972e941ea554773bf3b00b82c090f4f'], ['ZOMBIE RIG', 'a1db577d7e7b494b9a7f9a05a0de4895'],
    ['ZOMBIE', '71ae143c2468421b940d9bdeeaef7158'], ['ZOMBIE', 'ba0232355d5c4f86aab3edc3cd5d7331'], ['ZOMBIE', '0541416bd635486f95cb3d44f8f676c1'],
    ['ZOMBIE', '4ef24684d8234c5bb565e6aa2b6199bb'], ['ZOMBIE', '2bd10adbc3a24922bae826d45141e80b'], ['CRAWLER', '92e32f2303fa4a339590c243fd6c505a'],
    ['SHEETS', '98751f4c67074ff1a9d4213e5cfcdc43'], ['F. ZOMBIE', '5990107ff5da4d2ab8a7024f2664f564'], ['F. ZOMBIE', 'ab1210913a9545ada66690984029b285'],
    ['F. BASE', '8c88f6a41a4d4ac09a2e9c7cca61708b'], ['F. BASE', '02f1992aec88488291fdf35640bacb15'], ['F. BASE', 'd46828e60eb141c5866545f62fe662ce'],
    ['BODY', 'b04951e54a5746a78e825e2420e3cdac'], ['BODY', 'ec24eba25dc24093959e7ecf62024774'], ['BODY', '1e6ae13f6c2e46429eaca4d22d8bdbaa'],
    ['DOG', 'a0570f82ac974a6bb3214364b0e2b16d'], ['DOG', 'b06341d813b0422d900efb5fd07a7551'], ['ROACH', '4b19ed8851f74c278eef835250a82896'], ['SKELETON', '0559c4623da344df9755a2ded991e540'],
    ['RE TYRANT', '15f12782bb0a48a091de43c1dab4b435'], ['RE LICKER', '2fd160ff6aa14b81aac2afe0690c67be'], ['RE JILL', 'e9d9f1d73dc64653828c4a9412997ef2'], ['RE CHRIS', '9d719ad4b2a14301a33667deb537bb73'],
  ],
  '2-cenarios': [
    ['MANSION', 'f2835cf5ee06400da7ce3ca872c29f0b'], ['MANSION', '452c8783fd96456387f9f84fe8d05b94'], ['MANSION', '8e790a9b805a486fb7f8d46a462b14e8'], ['MANSION', '36873481ff5c4001aaafe2724bb1fc26'],
    ['CORRIDOR', '1e20facf9cf14dbf84fac4e33eba3b71'], ['CORRIDOR', '30f359fcea3d4b498b179cd8ba9201ea'], ['CORRIDOR', '8cd1f363993f4aa094da3c2dc8995772'], ['CORRIDOR', '10217a58dd9e45a494b41ebc0593f58a'], ['HALL', '9d57979efd8d43fc970388e50dc7adc0'],
    ['DUNGEON', '10838c04681e460183338685944a4bc0'], ['DUNGEON', '25e82c96b345415ebacddcae989601db'], ['DUNGEON', '7b5317e6f9874455a29b6185f85201a8'], ['DUNGEON', '8647cb0c1b5745479e3473c7f1fc5a67'], ['BARS', '410e6acfc4c448d3835929e1b6d6df3a'],
    ['CITY', '252280ef88fc48808c38e6ed0627271a'], ['CITY', '381b65d98a5b4e3886ac2acace7e5c74'], ['RUIN', '9fdc8d1f23a249768c377db0dfcaf42c'], ['RUIN', 'b6a7905251f54a419232ae44c5117517'],
    ['BURN CAR', '578b6d6bcdd444b894ba1889d71fb71e'], ['WRECK', '87cbb2ec7a994c2a9e7bd7a62f1f7ff3'], ['COP CAR', '3000906db39245ff8e519f85a50a8403'], ['LIGHTS', '1d7ac82702484f979b37bfa896983bbc'], ['LAMP', '81a8d1861bbd4cef8ab1aed2986bf873'],
    ['BARRICADE', '89a79068de614a478aeaea49371cfef8'], ['CHOPPER', '5bbed2de9baa4a13a7faa72653b78b64'], ['WALL', '0aaf61c5dc5d4008befa851e7971cdee'], ['TAPE', '83351a4cd72346ccad6792dfde46d22e'],
    ['DOORS', '16dd7631d2e145ffacfc374961d71cf1'], ['DOORS', '02e442c6d4a24df29624808d058f010a'], ['WINDOW', '318f9848bcb04a7c9974c949b4a3b10b'], ['WINDOW', 'b08907202ad54cc982cbc111da27f37c'],
    ['FIREPLACE', 'd1473f5f384a411f979b99214de9f2a9'], ['FIREPLACE', '7154a82dc7844075996c65aeb508bfd5'],
  ],
  '3-objetos': [
    ['RE HERB', '1b1d108aa999474794315030795b1f5a'], ['RE MEDBOX', '9cc0fb2e1bed40f386c80d7fb74164b2'], ['PISTOL', '6640a5fd40b4456c94578b015264e305'], ['SHOTGUN', '89afc8d893ba479b9dcf1ee39e049bcd'], ['SHOTGUN', '0e73b7d193154536b66f270899d4e2d8'], ['MELEE', '79cae670d515469a947617d18e5a6c89'],
    ['SYRINGE', '1de7893db91c4cf8822ff10ee999cd67'], ['SYRINGE', 'cdcc401bf48d42e3895965d52eb2f3d8'], ['HEAL PACK', '2c6fea8bd48944389ae6d1f22b391f3e'], ['GLUE', '39207e87ba90446fa0e3c40a93148efa'], ['GLUE', 'c07de0f37b5647a9bf8b7394263001e4'],
    ['DOVE', '797d27b68af3453e865149435df6aa30'], ['DOVE', '79de3c5b47f24376a5694029b1693088'], ['DOVE', '5884a0f5200c44ceaa7d0399bea577f9'],
    ['TYPEWRITER', '1d6009449fe84fd79454c4081eb743bf'], ['CANDLE', '9debe7915b8740bb83f4493c0d9a5f51'], ['CANDELABRA', '89f71a03a338491c92ada680e6f51749'], ['CHANDELIER', '7058eec02b434b9e8f3ffe3ec0f93083'], ['CHANDELIER', 'e7a99b9024904ce3ac60c8831acd0418'],
    ['CLOCK', '6ede129be11e43cea5c279e34a7eddaa'], ['COBWEBS', '2dd4798676d84bc7af5d2a8f5834563a'], ['COBWEBS', '7092699196a94b4b9953225caadc23ca'], ['CRATE', '2f0af73d6d734669b486b9d8a90cf23e'], ['CORK BOARD', '92c8eed11d404a01b0ca2237919c79c6'],
    ['BOOKSHELF', 'bf8be00f3d344ebdafd701fb90d65497'], ['BOOKSHELF', '740d1f30ffc140aa9a37a25bb604bc2c'], ['PAINTING', 'eb869f2272334150977ca9d9b89fc986'], ['PAINTING', 'b2895c1c3b42401a949deac049e0051d'], ['PAINTING', 'd794819d83594c4eb069ca31d4f214b4'],
    ['TORCH', '156b8eca745549ee951abd8aa58f2d3f'], ['TORCH', '951742f266b447e2b78ad7e8f5023f67'], ['GRAVES', '216711532d5a4078b9c0d5020af01eb1'],
  ],
};

const REVIEW = path.join(ROOT, 'blender/zombies/review');
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
    ctx.fillStyle = role.startsWith('RE ') ? '#ff5040' : '#ffd23f';
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
