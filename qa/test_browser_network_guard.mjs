// Real Chrome, two local-only servers: no public network or private data.
import assert from 'node:assert/strict';
import http from 'node:http';
import {chromium} from 'playwright';
import {restrictBrowserNetwork} from './browser_network_guard.mjs';

const listen = server => new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const close = server => new Promise(resolve => server.close(resolve));
let foreignRequests = 0, foreignUpgrades = 0;
const foreign = http.createServer((_req, res) => { foreignRequests++; res.end('foreign'); });
foreign.on('upgrade', (_req, socket) => { foreignUpgrades++; socket.destroy(); });
await listen(foreign);
const foreignOrigin = `http://127.0.0.1:${foreign.address().port}`;
const originServer = http.createServer((req, res) => {
  if (req.url === '/redirect') {
    res.writeHead(302, {location: foreignOrigin}); res.end();
  } else if (req.url === '/cookie') {
    res.setHeader('Set-Cookie', 'fixture=yes; Path=/; HttpOnly'); res.end('set');
  } else if (req.url === '/cookie-check') {
    res.end(req.headers.cookie || 'missing');
  } else res.end('<html>synthetic fixture</html>');
});
await listen(originServer);
const base = `http://127.0.0.1:${originServer.address().port}`;
const browser = await chromium.launch({headless: true, executablePath: '/opt/google/chrome/chrome', args: ['--no-sandbox']});
try {
  const context = await browser.newContext({serviceWorkers: 'block'});
  await restrictBrowserNetwork(context, base);
  const page = await context.newPage();
  await page.goto(base);
  assert.equal(await page.evaluate(async () => (await fetch('/cookie')).text()), 'set');
  assert.equal(await page.evaluate(async () => (await fetch('/cookie-check')).text()), 'fixture=yes');
  const external = await page.evaluate(async url => { try { await fetch(url); return true; } catch { return false; } }, foreignOrigin);
  assert.equal(external, false);
  const wsFailed = await page.evaluate(url => new Promise(resolve => {
    const socket = new WebSocket(url.replace('http:', 'ws:'));
    socket.onopen = () => resolve(false);
    socket.onerror = () => resolve(true);
    socket.onclose = () => resolve(true);
    setTimeout(() => resolve(false), 3000);
  }), foreignOrigin);
  assert.equal(wsFailed, true);
  await assert.rejects(page.goto(base + '/redirect'));
  assert.equal(foreignRequests, 0, 'foreign HTTP must not reach the other server');
  assert.equal(foreignUpgrades, 0, 'WebSocket must not reach the other server');
  process.stdout.write('Synthetic browser direct HTTP, redirect and WebSocket guards passed\n');
} finally {
  await browser.close();
  await close(originServer);
  await close(foreign);
}
