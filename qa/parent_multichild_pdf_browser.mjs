// Opt-in pytest harness only: local SQLite and entirely synthetic PDF/accounts.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chromium} from 'playwright';

const input = JSON.parse(readFileSync(0, 'utf8'));
const url = new URL(input.base);
assert.equal(url.hostname, '127.0.0.1');
assert.equal(url.protocol, 'http:');
const browser = await chromium.launch({headless:true, executablePath:'/opt/google/chrome/chrome', args:['--no-sandbox']});
const context = await browser.newContext({viewport:{width:390,height:900}});
const page = await context.newPage();
const writes = [], errors = [];
page.on('pageerror', () => errors.push('runtime'));
page.on('request', request => {
  const path = new URL(request.url()).pathname;
  if (path.startsWith('/api/') && !['GET','HEAD','OPTIONS'].includes(request.method())) writes.push(path);
});
const button = name => page.getByRole('button',{name,exact:true});
async function open(route) {
  await page.goto(input.base+route, {waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForSelector('flutter-view',{timeout:90000});
  await page.locator('flt-semantics-placeholder').evaluateAll(nodes=>nodes.forEach(n=>n.click()));
}
async function tap(locator) {
  const target=locator.first();
  for(let i=0;i<40;i++) {
    if(!await target.count()) {await page.mouse.wheel(0,250); await page.waitForTimeout(150); continue;}
    const box=await target.boundingBox().catch(()=>null);
    if(box && box.width>0 && box.height>0 && box.y>=0 && box.y+box.height<page.viewportSize().height-8) {
      await page.mouse.click(box.x+box.width/2,box.y+box.height/2); await page.waitForTimeout(200); return;
    }
    await page.mouse.move(page.viewportSize().width/2,page.viewportSize().height/2);
    await page.mouse.wheel(0,box && box.y<0 ? -300 : 300); await page.waitForTimeout(150);
  }
  throw Error('synthetic_control_unreachable');
}
try {
  await open('/login');
  await page.getByRole('textbox',{name:'E-Mail oder Benutzername',exact:true}).click();
  await page.keyboard.type(input.username,{delay:5}); await page.keyboard.press('Tab');
  await page.getByLabel('Passwort',{exact:true}).click();
  await page.keyboard.type(input.password,{delay:5}); await page.keyboard.press('Tab');
  const login=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login' && r.request().method()==='POST');
  await tap(button('Anmelden')); assert.equal((await login).status(),200);
  await page.waitForURL(input.base+'/app',{timeout:30000});
  for(const width of [390,1280]) {
   await page.setViewportSize({width,height:900});
   for(const [childIndex,child] of input.children.entries()) {
    await open('/grades/'+child);
    for(let pass=0;pass<2;pass++) {
      const previouslyImported = width !== 390 || pass !== 0;
      await tap(button('PDF importieren'));
      const chooser=page.waitForEvent('filechooser',{timeout:20000});
      const uploaded=page.waitForResponse(r=>new URL(r.url()).pathname===`/api/children/${child}/grade-imports` && r.request().method()==='POST',{timeout:45000}).then(async r=>({status:r.status(),body:await r.json()}));
      await tap(button('PDF auswählen')); await (await chooser).setFiles(input.pdf);
      const upload=await uploaded; assert.equal(upload.status,201);
      const preview=upload.body;
      assert.equal(preview.items.length,3);
      assert.equal(new Set(preview.items.map(item=>item.slot_key)).size,3);
      assert.equal(preview.counts[previouslyImported ? 'existing' : 'new'],3);
      const beforeConfirm=await context.request.get(input.base+`/api/children/${child}/grades`);
      assert.equal(beforeConfirm.status(),200);
      assert.equal((await beforeConfirm.json()).pagination.total,previouslyImported ? 3 : 0);
      await button('Auswahl übernehmen').waitFor({state:'attached',timeout:15000});
      await page.screenshot({path:`${input.screens}/pdf-preview-${childIndex}-${width}-${pass}.png`});
      const confirmed=page.waitForResponse(r=>new URL(r.url()).pathname===`/api/children/${child}/grade-imports/${preview.id}/confirm` && r.request().method()==='POST',{timeout:30000}).then(async r=>({status:r.status(),body:await r.json()}));
      await tap(button('Auswahl übernehmen'));
      const response=await confirmed; assert.equal(response.status,200);
      const result=response.body; assert.equal(result.added,previouslyImported ? 0 : 3);
      if(previouslyImported) assert.equal(result.unchanged,3);
      await tap(button('Fertig'));
    }
   }
  }
  assert.equal(writes.filter(p=>p==='/api/auth/login').length,1);
  assert.equal(writes.length,17);
  assert(writes.every(p=>p==='/api/auth/login' || input.children.some(id=>p.startsWith(`/api/children/${id}/grade-imports`))));
  assert.deepEqual(errors,[]);
  process.stdout.write('synthetic PDF browser checks passed\n');
} finally {await context.close(); await browser.close();}
