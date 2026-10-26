// Tiny static server for previewing dist/ locally: npm run dev  →  http://localhost:3000
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const port = Number(process.env.PORT) || 3000;
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif', '.avif': 'image/avif' };

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  let rel = decodeURIComponent(url.pathname);
  let file = path.join(dist, rel);
  if (!file.startsWith(dist)) { res.writeHead(403).end(); return; }
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
    if (!rel.endsWith('/')) { res.writeHead(301, { Location: rel + '/' + url.search }).end(); return; }
    file = path.join(file, 'index.html');
  }
  if (!fs.existsSync(file)) {
    res.writeHead(404, { 'Content-Type': types['.html'] });
    res.end(fs.existsSync(path.join(dist, '404.html')) ? fs.readFileSync(path.join(dist, '404.html')) : 'Not found');
    return;
  }
  res.writeHead(200, { 'Content-Type': types[path.extname(file).toLowerCase()] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}).listen(port, () => console.log(`Preview: http://localhost:${port}`));
