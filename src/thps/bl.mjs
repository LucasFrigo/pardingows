// Talks to the Blender addon socket (127.0.0.1:9876):
//   node src/thps/bl.mjs run script.py [--arg value]   runs a Python file in the open session
//   node src/thps/bl.mjs cmd get_sketchfab_status [jsonParams]
// Anything the script prints comes back on stdout.
import net from 'net';
import fs from 'fs';

export function send(type, params = {}, timeoutMs = 600000) {
  return new Promise((res, rej) => {
    const c = net.connect(9876, '127.0.0.1', () => c.write(JSON.stringify({ type, params })));
    let buf = '';
    const timer = setTimeout(() => { c.destroy(); rej(new Error(`no reply to ${type} after ${timeoutMs} ms`)); }, timeoutMs);
    c.on('data', d => {
      buf += d.toString('utf8');
      try {
        const j = JSON.parse(buf);
        clearTimeout(timer);
        c.end();
        res(j);
      } catch { /* partial reply, keep reading */ }
    });
    c.on('error', e => { clearTimeout(timer); rej(e); });
  });
}

if (process.argv[1]?.endsWith('bl.mjs')) {
  const [mode, what, extra] = process.argv.slice(2);
  const r = mode === 'run'
    ? await send('execute_code', { code: fs.readFileSync(what, 'utf8') })
    : await send(what, extra ? JSON.parse(extra) : {});
  if (r.status !== 'success') {
    console.error(r.message || JSON.stringify(r));
    process.exit(1);
  }
  const out = r.result?.result ?? r.result;
  console.log(typeof out === 'string' ? out : JSON.stringify(out, null, 1));
}
