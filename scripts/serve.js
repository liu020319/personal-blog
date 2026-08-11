const http = require('http');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const port = Number(process.env.PORT || 4173);
const resumeApiPort = Number(process.env.RESUME_API_PORT || 8091);
const mime = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.pdf': 'application/pdf',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8'
};

http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, `http://${request.headers.host}`).pathname);
  if (pathname.startsWith('/blog-api/')) {
    const proxyRequest = http.request({
      hostname: '127.0.0.1',
      port: resumeApiPort,
      path: pathname.replace('/blog-api', '') || '/',
      method: request.method,
      headers: { ...request.headers, host: `127.0.0.1:${resumeApiPort}` }
    }, (proxyResponse) => {
      response.writeHead(proxyResponse.statusCode || 502, proxyResponse.headers);
      proxyResponse.pipe(response);
    });
    proxyRequest.on('error', () => {
      response.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
      response.end(JSON.stringify({ ok: false, message: '本地简历服务尚未启动' }));
    });
    request.pipe(proxyRequest);
    return;
  }
  const requested = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
  const file = path.resolve(root, requested);

  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    response.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
    response.end(fs.readFileSync(path.join(root, '404.html')));
    return;
  }

  response.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(response);
}).listen(port, '127.0.0.1', () => {
  console.log(`Personal blog preview: http://127.0.0.1:${port}`);
});
