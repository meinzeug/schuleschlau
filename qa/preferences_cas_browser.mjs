// Real local backend, artificial accounts and data only; launched by opt-in pytest.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chromium} from 'playwright';

const input = JSON.parse(readFileSync(0, 'utf8'));
const url = new URL(input.base);
assert.equal(url.protocol, 'http:');
assert.equal(url.hostname, '127.0.0.1');
assert(Number(url.port) >= 1024);
assert.equal(input.first, 'parent@example.org');
assert.equal(input.second, 'synthetic-cas-parent');
assert.equal(input.password, 'secure-parent-pass-123');
const browser = await chromium.launch({headless:true, executablePath:'/opt/google/chrome/chrome', args:['--no-sandbox']});
const contexts = [];
let phase = 'setup';
const errors = [], writes = [];
async function open(page, path) {
  await page.goto(input.base+path, {waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForSelector('flutter-view',{timeout:90000});
  await page.locator('flt-semantics-placeholder').evaluateAll(nodes=>nodes.forEach(n=>n.click()));
  await page.waitForTimeout(300);
}
async function tap(page, locator) {
  const target=locator.first();
  for(let n=0;n<45;n++) {
    const box=await target.count() ? await target.boundingBox().catch(()=>null) : null;
    const bottom = await page.getByText('Lernziele & Plan',{exact:true}).count() ? 15 : 95;
    if(box && box.width && box.height && box.y>=0 && box.y+box.height<page.viewportSize().height-bottom) {
      await page.mouse.click(box.x+box.width/2,box.y+box.height/2); await page.waitForTimeout(180); return;
    }
    await page.mouse.move(195,450);
    await page.mouse.wheel(0,n===0&&!box?-4000:box&&box.y<0?-260:260); await page.waitForTimeout(160);
  }
  await page.screenshot({path:`${input.screens}/synthetic-cas-unreachable.png`});
  throw new Error(`synthetic control unreachable in ${phase}: ${locator}`);
}
async function type(page, locator, value) {
  await tap(page,locator); await page.keyboard.press('Control+A');
  await page.keyboard.type(value,{delay:3}); await page.keyboard.press('Tab'); await page.waitForTimeout(150);
}
async function login(user) {
  const context=await browser.newContext({viewport:{width:390,height:900},isMobile:true,hasTouch:true});
  contexts.push(context);
  const page=await context.newPage();
  page.on('pageerror',()=>errors.push(phase));
  page.on('request',r=>{const path=new URL(r.url()).pathname;if(path.startsWith('/api/')&&r.method()!=='GET')writes.push({path,method:r.method()});});
  await open(page,'/login');
  await type(page,page.getByRole('textbox',{name:'E-Mail oder Benutzername',exact:true}),user);
  await type(page,page.getByLabel('Passwort',{exact:true}),input.password);
  await tap(page,page.getByRole('button',{name:'Anmelden',exact:true}));
  await page.waitForURL(input.base+'/app',{timeout:30000});
  return {page,context};
}
async function preferences(page) {
  const read=page.waitForResponse(r=>new URL(r.url()).pathname===`/api/children/${input.child}/learning-plan`&&r.request().method()==='GET');
  await open(page,`/parent-plan/${input.child}?ansicht=week`);
  const response=await read; assert.equal(response.status(),200);
  assert.equal((await response.json()).child.preferences_revision,1);
  await tap(page,page.getByRole('button',{name:'Seitenoptionen',exact:true}));
  await tap(page,page.getByText('Vorgaben & Kalender',{exact:true}));
  await tap(page,page.getByRole('button',{name:'Lernvorgaben anpassen',exact:true}));
  await page.getByText('Lernziele & Plan',{exact:true}).waitFor();
}
try {
  phase='first-login'; const first=await login(input.first);
  phase='second-login'; const second=await login(input.second);
  phase='first-open'; await preferences(first.page);
  phase='second-open'; await preferences(second.page);
  phase='first-edit';
  await type(first.page,first.page.getByRole('textbox',{name:'Mindestziel pro Tag',exact:true}),'37');
  await type(first.page,first.page.getByRole('textbox',{name:'Themen zum Wiederholen',exact:true}),'Mathematik: Künstliches Ziel');
  await tap(first.page,first.page.getByRole('switch',{name:/Push am Kindergerät erlauben/}));
  const saved=first.page.waitForResponse(r=>new URL(r.url()).pathname===`/api/children/${input.child}/preferences`&&r.request().method()==='PUT');
  saved.catch(()=>{});
  await tap(first.page,first.page.getByRole('button',{name:'Speichern',exact:true}));
  const firstResult=await saved; assert.equal(firstResult.status(),200); assert.equal(firstResult.request().headers()['if-match'],'1');
  phase='second-conflict';
  await type(second.page,second.page.getByRole('textbox',{name:'Mindestziel pro Woche',exact:true}),'200');
  const conflict=second.page.waitForResponse(r=>new URL(r.url()).pathname===`/api/children/${input.child}/preferences`&&r.request().method()==='PUT');
  conflict.catch(()=>{});
  await tap(second.page,second.page.getByRole('button',{name:'Speichern',exact:true}));
  const stale=await conflict; assert.equal(stale.status(),409); assert.equal(stale.request().headers()['if-match'],'1');
  assert.equal((await stale.json()).code,'preferences_revision_conflict');
  await second.page.getByText('Aktuellen Stand laden',{exact:true}).waitFor({timeout:10000});
  await second.page.screenshot({path:`${input.screens}/synthetic-cas-conflict.png`});
  await second.page.getByText('Die Lernvorgaben wurden zwischenzeitlich geändert.',{exact:false}).first().waitFor({state:'attached',timeout:10000});
  const draft=second.page.getByRole('textbox',{name:'Mindestziel pro Woche',exact:true});
  await tap(second.page,draft);
  assert.equal(await draft.inputValue(),'200');
  await tap(second.page,second.page.getByRole('button',{name:'Aktuellen Stand laden',exact:true}));
  await tap(second.page,second.page.getByRole('button',{name:'Entwurf behalten',exact:true}));
  await tap(second.page,draft);
  assert.equal(await draft.inputValue(),'200');
  assert.equal(writes.filter(x=>x.path.endsWith('/preferences')).length,2);
  // Exercise the old API contract, without pretending to run an old APK.
  const family=await second.context.request.get(input.base+`/api/families/${input.family}`);
  assert.equal(family.status(),200);
  const snapshot=(await family.json()).children.find(row=>row.id===input.child).preferences;
  const oldClient=await second.context.request.put(input.base+`/api/children/${input.child}/preferences`, {
    headers:{'X-Schulpilot-Request':'1'}, data:snapshot,
  });
  assert.equal(oldClient.status(),428);
  const oldError=await oldClient.json();
  assert.equal(oldError.code,'preferences_revision_required');
  assert(oldError.detail.includes('App aktualisieren'));
  assert.deepEqual(errors,[]);
  process.stdout.write('synthetic two-parent CAS browser passed\n');
} finally {for(const ctx of contexts)await ctx.close();await browser.close();}
