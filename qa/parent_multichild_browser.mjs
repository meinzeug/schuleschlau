// Controlled by the isolated pytest harness. Only a loopback origin is allowed.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chromium} from 'playwright';

const input = JSON.parse(readFileSync(0, 'utf8'));
const url = new URL(input.base);
assert.equal(url.hostname, '127.0.0.1');
assert.equal(url.protocol, 'http:');
const browser = await chromium.launch({headless: true, executablePath: '/opt/google/chrome/chrome', args:['--no-sandbox']});
const context = await browser.newContext({viewport:{width:390,height:844}});
const page = await context.newPage();
const errors = [], writes = [];
page.on('pageerror', () => errors.push('runtime'));
page.on('request', request => {
  if (new URL(request.url()).pathname.startsWith('/api/') && !['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
    writes.push(new URL(request.url()).pathname);
  }
});
async function open(route) {
  await page.goto(input.base + route, {waitUntil:'domcontentloaded', timeout:90000});
  await page.waitForSelector('flutter-view', {timeout:90000});
  await page.locator('flt-semantics-placeholder').evaluateAll(nodes => nodes.forEach(n => n.click()));
}
try {
  await open('/login');
  const name = page.getByRole('textbox',{name:'E-Mail oder Benutzername',exact:true});
  await name.click(); await page.keyboard.type(input.username, {delay:5}); await page.keyboard.press('Tab');
  const password = page.getByLabel('Passwort',{exact:true});
  await password.click(); await page.keyboard.type(input.password, {delay:5}); await page.keyboard.press('Tab');
  const login = page.waitForResponse(r => new URL(r.url()).pathname === '/api/auth/login' && r.request().method() === 'POST', {timeout:15000});
  await page.getByRole('button',{name:'Anmelden',exact:true}).click();
  assert.equal((await login).status(), 200, 'synthetic browser login failed');
  await page.waitForURL(input.base+'/app',{timeout:15000});
  assert.deepEqual(writes, ['/api/auth/login']);
  for (const width of [390,1440]) {
    await page.setViewportSize({width,height:900});
    for (const [index, child] of input.children.entries()) {
      const response = page.waitForResponse(r => new URL(r.url()).pathname === `/api/children/${child}/learning-progress` && r.request().method() === 'GET', {timeout:30000});
      await open('/progress/'+child);
      const result = await response; assert.equal(result.status(), 200);
      const totals = (await result.json()).totals;
      assert.equal(totals.attempts, index ? 1 : 3);
      await page.getByText(index ? '1 Aufgabe geübt' : '2 Aufgaben geübt',{exact:false}).first().waitFor({timeout:30000});
      const body=await page.locator('flt-semantics-host').innerText();
      assert(body.includes(index ? 'Biologie' : 'Mathematik'));
      assert(body.includes('1 alleine gelöst'));
      if (!index) assert(body.includes('1 mit Hilfe gelöst'));
      assert(!/RenderFlex overflowed|ErrorWidget|Null check operator/.test(body));
      await page.screenshot({path:`${input.screens}/parent-progress-${index}-${width}.png`});
      const gradeResponse = page.waitForResponse(r => new URL(r.url()).pathname === `/api/children/${child}/grades` && r.request().method() === 'GET', {timeout:30000});
      await open('/grades/'+child);
      assert.equal((await gradeResponse).status(), 200);
      await page.getByText(index ? 'Künstliche Pflanzen' : 'Künstliche Brüche',{exact:false}).first().waitFor({timeout:30000});
      const gradesBody = await page.locator('flt-semantics-host').innerText();
      assert(gradesBody.includes(index ? 'Biologie' : 'Mathematik'));
      assert(gradesBody.includes(index ? '3 Biologie Test' : '2 Mathematik Test'), 'stored_grade_not_visible');
      assert(!/RenderFlex overflowed|ErrorWidget|Null check operator/.test(gradesBody));
      await page.screenshot({path:`${input.screens}/parent-grades-${index}-${width}.png`});
      const planResponse = page.waitForResponse(r => new URL(r.url()).pathname === `/api/children/${child}/learning-plan` && r.request().method() === 'GET', {timeout:30000});
      await open('/parent-plan/'+child+'?ansicht=topics');
      const plan = await planResponse; assert.equal(plan.status(), 200);
      const assignment = (await plan.json()).topics[0]; assert.equal(assignment.mandatory, true);
      await page.getByText(index ? 'Künstliche Pflanzen' : 'Künstliche Brüche',{exact:false}).first().waitFor({timeout:30000});
      const planBody = await page.locator('flt-semantics-host').innerText();
      assert(planBody.includes('Verbindlicher Elternauftrag'));
      assert(planBody.includes('Termin: ' + assignment.due.split('-').reverse().join('.')));
      await page.screenshot({path:`${input.screens}/parent-plan-${index}-${width}.png`});
      const weekResponse = page.waitForResponse(r => new URL(r.url()).pathname === `/api/children/${child}/learning-plan` && r.request().method() === 'GET', {timeout:30000});
      await open('/parent-plan/'+child+'?ansicht=week');
      const week = await weekResponse; assert.equal(week.status(), 200);
      const day = (await week.json()).plan.week[0];
      assert.equal(day.available_minutes, 0);
      assert.equal(day.paused, !index);
      assert.equal(day.free_day, Boolean(index));
      // Flutter merges passive day details into a group's accessible label.
      const weekFacts = page.locator('flt-semantics[aria-label*="Ohne festes Tagesziel"]');
      await weekFacts.first().waitFor({state:'attached',timeout:10000});
      const facts = await weekFacts.first().getAttribute('aria-label');
      assert(facts.includes('Ohne festes Tagesziel · freiwilliges Lernen bleibt möglich'));
      assert(facts.includes('0 Minuten vorgeschlagen'));
      await page.mouse.move(width / 2, 600);
      await page.mouse.wheel(0, 480);
      await page.waitForTimeout(250);
      await page.screenshot({path:`${input.screens}/parent-week-${index}-${width}.png`});
      const weekBody = await page.locator('flt-semantics-host').innerText();
      assert(!/RenderFlex overflowed|ErrorWidget|Null check operator/.test(weekBody));
    }
  }
  assert.deepEqual(writes, ['/api/auth/login']);
  assert.deepEqual(errors, []);
  process.stdout.write('isolated browser checks passed\n');
} finally {
  await context.close();
  await browser.close();
}
