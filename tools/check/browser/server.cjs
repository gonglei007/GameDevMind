// Read-only static fixture server; never bind the test checkout to public interfaces.
const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
const publicRoots = ['nav','mds','code','images','overview','exports'];
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8',
  '.css':'text/css; charset=utf-8','.md':'text/plain; charset=utf-8',
  '.png':'image/png','.svg':'image/svg+xml','.jpg':'image/jpeg','.json':'application/json'};
const server = http.createServer(async (req,res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (pathname === '/healthz') { res.end('gamedevmind-browser-regression'); return; }
    if (pathname === '/favicon.ico') { res.writeHead(204); res.end(); return; }
    if (!['GET','HEAD'].includes(req.method) ||
        !/^\/(nav|mds|code|images|overview|exports)\//.test(pathname)) {
      res.writeHead(404); res.end(); return;
    }
    let file = path.resolve(root, '.' + pathname);
    if (!file.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
    if ((await fs.stat(file)).isDirectory()) {
      // Directory destinations expose their real README, not an invented GitHub tree UI.
      const index = path.join(file, 'index.html');
      file = await fs.stat(index).then(()=>index,()=>path.join(file,'README.md'));
    }
    const real = await fs.realpath(file);
    if (!real.startsWith(root + path.sep) || !publicRoots.includes(path.relative(root,real).split(path.sep)[0])) {
      res.writeHead(403); res.end(); return;
    }
    res.setHeader('Content-Type', types[path.extname(real)] || 'application/octet-stream');
    res.setHeader('Cache-Control','no-store');
    res.end(req.method === 'HEAD' ? undefined : await fs.readFile(real));
  } catch {
    res.writeHead(404); res.end('Not found');
  }
});
server.listen(Number(process.env.BROWSER_TEST_PORT || 4173), '127.0.0.1');
for (const signal of ['SIGINT','SIGTERM']) process.on(signal,()=>server.close(()=>process.exit(0)));
