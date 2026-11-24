// Synthetic one-time links enter via stdin; never log URLs, values or exceptions.
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

let raw='';
for await (const part of process.stdin) raw+=part;
const {base,tokens,screens}=JSON.parse(raw);
const origin=new URL(base);
if(origin.protocol!=='http:' || origin.hostname!=='127.0.0.1' || !origin.port) throw new Error('Loopback required');
const browser=await chromium.launch({headless:true,executablePath:'/opt/google/chrome/chrome',args:['--no-sandbox']});
let ctx, page, phase='setup';
try {
  async function open(path) {
    await page.goto(base+path,{waitUntil:'domcontentloaded'});
    await page.waitForSelector('flutter-view');
    await page.locator('flt-semantics-placeholder').evaluateAll(nodes=>nodes.forEach(n=>n.click()));
    await page.waitForTimeout(500);
  }
  async function reveal(locator) {
    for(let i=0;i<40;i++) {
      const item=locator.first(), box=await item.count()?await item.boundingBox().catch(()=>null):null;
      if(box && box.y>=0 && box.y+box.height<=page.viewportSize().height) return item;
      await page.mouse.move(page.viewportSize().width-25,page.viewportSize().height-100);
      await page.mouse.wheel(0,box && box.y<0?-350:350);
      await page.waitForTimeout(120);
    }
    throw new Error('control unavailable');
  }
  async function tap(locator) {
    const item=await reveal(locator), box=await item.boundingBox();
    await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
    await page.waitForTimeout(300);
  }
  async function type(label,text) {
    const item=await reveal(page.getByLabel(label,{exact:false}));
    await tap(item); await page.waitForTimeout(350);
    await page.keyboard.insertText(text); await page.waitForTimeout(250);
    if(await item.inputValue()!==text) throw new Error('input mismatch');
  }
  async function code(expected) {
    const item=await reveal(page.getByLabel('Sicherer Link-Code',{exact:false}));
    await item.click(); await page.waitForTimeout(250);
    if(await item.inputValue()!==expected) throw new Error('link mismatch');
    assert.equal(await item.evaluate(el=>document.activeElement===el),true);
  }
  for(const width of [390,1280]) {
    phase='login-'+width;
    ctx=await browser.newContext({viewport:{width,height:844},serviceWorkers:'block'});
    await restrictBrowserNetwork(ctx,base);
    page=await ctx.newPage();
    await open('/login');
    await type('E-Mail oder Benutzername','test-child');
    await type('Passwort','secure-child-pass-123');
    const login=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login' && r.request().method()==='POST');
    await tap(page.getByRole('button',{name:'Anmelden',exact:true}));
    assert.equal((await login).status(),200);
    await page.waitForURL(url=>url.pathname==='/app',{timeout:15000});
    phase='logout-'+width;
    await open('/settings');
    const logout=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/logout' && r.request().method()==='POST');
    await tap(page.getByRole('button',{name:'Abmelden',exact:true}));
    assert.equal((await logout).status(),200);
    assert.equal((await ctx.request.get(base+'/api/auth/me')).status(),401);
    for(const route of ['verify','reset','invite']) {
      const pair=tokens[String(width)][route];
      phase=route+'-cold-'+width;
      await open('/'+route+'#token='+encodeURIComponent(pair.first));
      await code(pair.first);
      phase=route+'-reload-'+width;
      await page.reload({waitUntil:'domcontentloaded'});
      await page.waitForSelector('flutter-view');
      await page.locator('flt-semantics-placeholder').evaluateAll(nodes=>nodes.forEach(n=>n.click()));
      await code(pair.first);
      phase=route+'-replacement-'+width;
      await open('/'+route+'#token='+encodeURIComponent(pair.second));
      await code(pair.second);
      phase=route+'-fields-'+width;
      if(route==='reset') await type('Neues Passwort','synthetic-new-password-123');
      if(route==='invite') {
        phase=route+'-name-'+width;
        await type('Dein Anzeigename','Synthetischer Elternteil');
        phase=route+'-password-'+width;
        await type('Elternpasswort','synthetic-new-password-123');
      }
      const path=route==='invite'?'/api/invitations/accept':'/api/auth/'+route;
      const submitted=page.waitForResponse(r=>new URL(r.url()).pathname===path && r.request().method()==='POST');
      phase=route+'-submit-'+width;
      await tap(page.getByRole('button',{name:{verify:'E-Mail bestätigen',reset:'Passwort erneuern',invite:'Einladung annehmen'}[route],exact:true}));
      assert.equal((await submitted).status(),200);
    }
    await closeRestrictedBrowserContext(ctx); ctx=null;
  }
  console.log(JSON.stringify({passed:true}));
} catch (error) {
  console.error('Synthetic auth browser failed at '+phase);
  console.error('Error type: '+error.name);
  if(error.name==='TimeoutError') console.error('Timed out during '+String(error.message).split(':')[0]);
  if(['input mismatch','link mismatch','control unavailable'].includes(error.message)) console.error(error.message);
  if(page) await page.screenshot({path:screens+'/auth-failure.png'}).catch(()=>{});
  process.exitCode=1;
} finally {
  if(ctx) await closeRestrictedBrowserContext(ctx);
  await browser.close();
}
