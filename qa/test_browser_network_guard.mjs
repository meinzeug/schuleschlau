// Real Chrome, two local-only servers: no public network or private data.
import assert from 'node:assert/strict';
import http from 'node:http';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

const listen = server => new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const close = server => new Promise(resolve => server.close(resolve));
let foreignRequests = 0, foreignUpgrades = 0;
let slowStarted;
const slowSeen = new Promise(resolve => { slowStarted = resolve; });
let closeTimeoutStarted;
const closeTimeoutSeen = new Promise(resolve => { closeTimeoutStarted = resolve; });
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
  } else if (req.url === '/slow') {
    slowStarted();
    setTimeout(() => res.end('slow fixture'), 200);
  } else if (req.url === '/fail') {
    req.socket.destroy();
  } else if (req.url === '/timeout') {
    // The test guard's short timeout must abort the page and fail cleanup.
  } else if (req.url === '/timeout-during-close') {
    closeTimeoutStarted();
  } else res.end('<html>synthetic fixture</html>');
});
await listen(originServer);
const base = `http://127.0.0.1:${originServer.address().port}`;
const browser = await chromium.launch({headless: true, executablePath: '/opt/google/chrome/chrome', args: ['--no-sandbox']});
try {
  process.stdout.write('Checking normal browser guard\n');
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
  // Close while a guarded response is still in flight. Disabling routing
  // alone must not create a window for foreign requests during teardown.
  const slowPage = await context.newPage();
  process.stdout.write('Checking in-flight browser guard teardown\n');
  await slowPage.goto(base);
  const pending = slowPage.evaluate(() => fetch('/slow').catch(() => null)).catch(() => null);
  await Promise.race([slowSeen, new Promise((_, reject) => setTimeout(() => reject(new Error('slow fetch did not reach local server')), 10000))]);
  const closing = closeRestrictedBrowserContext(context);
  await slowPage.evaluate(async url => { try { await fetch(url); } catch {} }, foreignOrigin).catch(() => {});
  await closing;
  await pending;
  assert.equal(foreignRequests, 0, 'teardown must not allow foreign HTTP');
  assert.equal(foreignUpgrades, 0, 'teardown must not allow foreign WebSockets');
  // Request failures must be reported, not leak an unhandled rejection or let
  // a journey pass merely because its visible assertions happened to pass.
  for (const requestPath of ['/fail', '/timeout']) {
    process.stdout.write(`Checking local ${requestPath} failure\n`);
    const failedContext = await browser.newContext({serviceWorkers: 'block'});
    await restrictBrowserNetwork(failedContext, base, {fetchTimeoutMs: 2000});
    const failedPage = await failedContext.newPage();
    await failedPage.goto(base);
    const success = await failedPage.evaluate(async path => {
      try { await fetch(path); return true; } catch { return false; }
    }, requestPath);
    assert.equal(success, false, `${requestPath} must fail in the page`);
    await assert.rejects(closeRestrictedBrowserContext(failedContext), /Synthetic browser network guard failed/);
  }
  process.stdout.write('Checking bounded in-flight timeout during teardown\n');
  const timeoutContext = await browser.newContext({serviceWorkers: 'block'});
  await restrictBrowserNetwork(timeoutContext, base, {fetchTimeoutMs: 2000});
  const timeoutPage = await timeoutContext.newPage();
  await timeoutPage.goto(base);
  const pendingTimeout = timeoutPage.evaluate(() => fetch('/timeout-during-close').catch(() => null)).catch(() => null);
  await Promise.race([closeTimeoutSeen, new Promise((_, reject) => setTimeout(() => reject(new Error('timeout fetch did not reach local server')), 10000))]);
  await assert.rejects(closeRestrictedBrowserContext(timeoutContext), /Synthetic browser network guard failed/);
  await pendingTimeout;
  assert.equal(foreignRequests, 0);
  assert.equal(foreignUpgrades, 0);
  process.stdout.write('Synthetic browser direct HTTP, redirect, WebSocket and in-flight teardown guards passed\n');
} finally {
  await browser.close();
  await close(originServer);
  await close(foreign);
}
