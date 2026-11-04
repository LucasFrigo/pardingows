// Searches Sketchfab's public API for downloadable CC0 / CC-BY models. No account needed to search.
//   node src/thps/sketchfab_search.mjs "low poly police car" "another query"
const queries = process.argv.slice(2);
const seen = new Map();

for (const q of queries) {
  for (const license of ['cc0', 'by']) {
    const u = new URL('https://api.sketchfab.com/v3/search');
    u.search = new URLSearchParams({ type: 'models', downloadable: 'true', q, license, count: '24', sort_by: '-likeCount' });
    const r = await fetch(u);
    if (!r.ok) { console.error(`${q} [${license}]: HTTP ${r.status}`); continue; }
    for (const m of (await r.json()).results) {
      if (!seen.has(m.uid)) seen.set(m.uid, { q, ...m });
    }
  }
}

const rows = [...seen.values()]
  .filter(m => m.faceCount && m.faceCount < 40000)
  .sort((a, b) => a.q.localeCompare(b.q) || b.likeCount - a.likeCount);
for (const m of rows) {
  const thumb = m.thumbnails?.images?.find(i => i.width >= 400 && i.width <= 800)?.url || '';
  console.log([m.q, m.uid, m.name, m.user?.displayName, m.license?.label, `${m.faceCount}f`, `anim:${m.animationCount}`, `likes:${m.likeCount}`, thumb].join(' | '));
}
console.log(`${rows.length} models under 40k faces`);
