// Opt-in against a fresh loopback SQLite app and a copied old web build only.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

const input = JSON.parse(readFileSync(0, 'utf8'));
const base = new URL(input.base);
assert.equal(base.protocol, 'http:');
assert.equal(base.hostname, '127.0.0.1');
assert(Number(base.port) >= 1024);
const browser = await chromium.launch({headless: true, executablePath: '/opt/google/chrome/chrome',
  args: ['--no-sandbox', '--disable-background-networking', '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1']});
const context = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
await restrictBrowserNetwork(context, input.base);
const page = await context.newPage();
const errors = [];
page.on('pageerror', e => errors.push(e.message));

async function open(path) {
  await page.goto(input.base + path, {waitUntil: 'domcontentloaded', timeout: 90000});
  await page.waitForSelector('flutter-view', {timeout: 90000});
  await page.locator('flt-semantics-placeholder').evaluateAll(nodes => nodes.forEach(n => n.click()));
  await page.waitForTimeout(250);
}
async function tap(locator) {
  const target = locator.first();
  for (let i = 0; i < 50; i++) {
    const box = await target.count() ? await target.boundingBox().catch(() => null) : null;
    if (box && box.width && box.height && box.y >= 0 && box.y + box.height < 820) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(150);
      return;
    }
    await page.mouse.move(195, 450);
    await page.mouse.wheel(0, i === 0 && !box ? -4000 : box && box.y < 0 ? -280 : 280);
    await page.waitForTimeout(150);
  }
  throw new Error('Synthetic old-client control not visible');
}
async function fill(locator, value) {
  await tap(locator);
  await page.keyboard.press('Control+A');
  await page.keyboard.insertText(value);
  await page.keyboard.press('Tab');
}

try {
  await open('/login');
  await page.evaluate(async () => {
    await navigator.serviceWorker.register('/site-cas-cache-sw.js');
    await navigator.serviceWorker.ready;
    const cache = await caches.open('synthetic-legacy-v1');
    await cache.add('/main.dart.js');
  });
  await page.waitForFunction(() => !!navigator.serviceWorker.controller, null, {timeout: 10000});
  const oldJs = page.waitForResponse(r => new URL(r.url()).pathname === '/main.dart.js');
  await page.reload({waitUntil: 'domcontentloaded', timeout: 90000});
  assert.equal((await oldJs).fromServiceWorker(), true, 'The old client must actually come from the local service-worker cache');
  await page.waitForSelector('flutter-view', {timeout: 90000});
  await page.locator('flt-semantics-placeholder').evaluateAll(nodes => nodes.forEach(n => n.click()));
  await fill(page.getByLabel('E-Mail oder Benutzername', {exact: true}), 'synthetic-cached-admin');
  await fill(page.getByLabel('Passwort', {exact: true}), 'synthetic-admin-password-123');
  await tap(page.getByRole('button', {name: 'Anmelden', exact: true}));
  await page.waitForURL('**/admin', {timeout: 30000});
  await open('/admin/settings');
  const before = await (await context.request.get(input.base + '/api/admin/installation')).json();
  await fill(page.getByLabel('Betreiber', {exact: true}), 'Synthetic cached stale change');
  const attempt = page.waitForResponse(r => new URL(r.url()).pathname === '/api/admin/installation/site' && r.request().method() === 'PUT');
  await tap(page.getByRole('button', {name: 'Einstellungen speichern', exact: true}));
  const response = await attempt;
  assert.equal(response.status(), 409);
  const sent = response.request().postDataJSON();
  assert.equal(sent.operator_name, 'Synthetic cached stale change');
  assert.equal(Object.hasOwn(sent, 'expected_revision'), false);
  const after = await (await context.request.get(input.base + '/api/admin/installation')).json();
  assert.equal(after.site_revision, before.site_revision);
  assert.equal(after.site.operator_name, before.site.operator_name);
  await page.screenshot({path: `${input.screens}/synthetic-cached-admin-conflict.png`});
  // The separate stop endpoint must still accept the same browser session.
  // Its visible button is exercised by installation_site_cas_test.dart.
  const stop = await context.request.post(input.base + '/api/admin/emergency-stop',
    {headers: {'X-Schulpilot-Request': '1'}, data: {}});
  assert.equal(stop.status(), 200);
  assert.deepEqual(errors, []);
} finally {
  await closeRestrictedBrowserContext(context);
  await browser.close();
}
