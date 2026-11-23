// Synthetic-only local beta registration and admin approval. No real mail/AI.
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

let input = '';
for await (const part of process.stdin) input += part;
const {base,screens} = JSON.parse(input);
const origin = new URL(base);
if (origin.protocol !== 'http:' || origin.hostname !== '127.0.0.1' || !origin.port) throw new Error('Loopback only');
const browser = await chromium.launch({headless: true, executablePath: '/opt/google/chrome/chrome', args: ['--no-sandbox']});
const contexts = [];
let debugPage;
let step = 'start';
try {
  async function context(viewport) {
    const ctx = await browser.newContext({viewport});
    contexts.push(ctx);
    await restrictBrowserNetwork(ctx, base);
    return ctx;
  }
  async function open(page, path) {
    await page.goto(base + path, {waitUntil:'domcontentloaded'});
    await page.waitForSelector('flutter-view');
    await page.locator('flt-semantics-placeholder').evaluateAll(nodes => nodes.forEach(n => n.click()));
    await page.waitForTimeout(500);
  }
  async function reveal(page, locator) {
    for (let i=0; i<35; i++) {
      const box = await locator.count() ? await locator.first().boundingBox().catch(() => null) : null;
      if (box && box.y >= 0 && box.y + box.height <= page.viewportSize().height) return locator.first();
      await page.mouse.move(page.viewportSize().width-25, page.viewportSize().height-80);
      await page.mouse.wheel(0, box && box.y < 0 ? -400 : 400);
      await page.waitForTimeout(120);
    }
    throw new Error('control not visible: ' + locator.toString());
  }
  async function tap(page, locator) {
    const node=await reveal(page, locator);
    const box=await node.boundingBox();
    await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
    await page.waitForTimeout(250);
  }
  async function type(page, label, value) {
    const field=await reveal(page,page.getByLabel(label,{exact:true}));
    await field.click(); await page.waitForTimeout(300);
    await page.keyboard.insertText(value); await page.waitForTimeout(400);
    assert.equal(await field.inputValue(),value);
  }
  const button=(page,name)=>page.getByRole('button',{name,exact:true});
  const parent=await context({width:390,height:844});
  const page=await parent.newPage();
  step='landing'; await open(page,'/');
  await tap(page,button(page,'Für die Beta anmelden'));
  step='register';
  await type(page,'E-Mail-Adresse','beta-browser@example.org');
  await type(page,'Dein Anzeigename','Künstlicher Elternteil');
  await type(page,'Name deiner Familie','Künstliche Familie');
  await type(page,'Neues Passwort','Synthetic-Parent-Password-123!');
  await tap(page,page.getByRole('checkbox').first());
  assert.equal(await page.getByRole('checkbox').first().getAttribute('aria-checked'), 'true', 'adult consent must be selected');
  const registered=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/register' && r.request().method()==='POST');
  registered.catch(()=>{});
  await tap(page,button(page,'Beta-Anmeldung absenden'));
  try { assert.equal((await registered).status(),201); } catch (e) {
    await page.screenshot({path:screens+'/registration-failure.png'});
    const issues = await page.locator('flt-semantics').allTextContents();
    throw new Error('registration did not send: '+JSON.stringify(issues.filter(x=>x.includes('prüf')||x.includes('Bestätige')||x.includes('Bitte')).slice(0,8)));
  }
  const mail=await parent.request.get(base+'/__fixture/beta-mail');
  const item=await mail.json(); assert.equal(item.ready,true);
  step='verify';
  await open(page,'/verify#token='+encodeURIComponent(item.token));
  const verify=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/verify' && r.request().method()==='POST');
  verify.catch(()=>{});
  await tap(page,button(page,'E-Mail bestätigen'));
  assert.equal((await verify).status(),200);
  const admin=await context({width:1280,height:900});
  const operator=await admin.newPage(); debugPage=operator;
  step='admin-login'; await open(operator,'/login');
  await type(operator,'E-Mail oder Benutzername','synthetic-beta-operator');
  await type(operator,'Passwort','Synthetic-Admin-Password-123!');
  const login=operator.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login' && r.request().method()==='POST');
  login.catch(()=>{});
  await tap(operator,button(operator,'Anmelden')); assert.equal((await login).status(),200);
  step='admin-beta'; await open(operator,'/admin/users');
  await tap(operator,operator.getByRole('button',{name:/Beta-Anmeldungen/}));
  await operator.getByRole('button',{name:'Freigeben',exact:true}).first().waitFor();
  await tap(operator,operator.getByRole('button',{name:'Freigeben',exact:true}).first());
  const decision=operator.waitForResponse(r=>r.url().includes('/beta-applications/') && r.url().endsWith('/decision') && r.request().method()==='POST');
  decision.catch(()=>{});
  await tap(operator,button(operator,'Freigeben').last());
  assert.equal((await decision).status(),200);
  step='parent-login'; await open(page,'/login');
  await type(page,'E-Mail oder Benutzername','beta-browser@example.org');
  await type(page,'Passwort','Synthetic-Parent-Password-123!');
  const parentLogin=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login' && r.request().method()==='POST');
  parentLogin.catch(()=>{});
  await tap(page,button(page,'Anmelden'));
  const loggedIn=await parentLogin; assert.equal(loggedIn.status(),200);
  const parentData=await loggedIn.json();
  const family=parentData.user.families[0].id;
  const appStatus=await parent.request.get(base+'/api/families/'+family+'/beta-application');
  assert.equal(appStatus.status(),200);
  assert.equal((await appStatus.json()).status,'approved');
  const child=await parent.request.post(base+'/api/families/'+family+'/children',{
    headers:{'X-Schulpilot-Request':'1'},
    data:{display_name:'Künstliches Testkind',username:'synthetic-beta-child',password:'Synthetic-Child-Password-123!',grade:6,subjects:['Mathematik']},
  });
  assert.equal(child.status(),201);
  const childData=await child.json();
  step='child-login';
  const childContext=await context({width:390,height:844});
  const childPage=await childContext.newPage(); debugPage=childPage;
  await open(childPage,'/login');
  await type(childPage,'E-Mail oder Benutzername','synthetic-beta-child');
  await type(childPage,'Passwort','Synthetic-Child-Password-123!');
  const childLogin=childPage.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login' && r.request().method()==='POST');
  childLogin.catch(()=>{});
  await tap(childPage,button(childPage,'Anmelden')); assert.equal((await childLogin).status(),200);
  await open(childPage,'/learn/'+childData.id);
  assert.equal(new URL(childPage.url()).pathname,'/learn/'+childData.id);
  const seeded=await childContext.request.post(base+'/__fixture/beta-unit?child_id='+encodeURIComponent(childData.id), {headers:{'X-Schulpilot-Request':'1'}});
  assert.equal(seeded.status(),200);
  const unit=(await seeded.json()).id;
  step='learning'; await open(childPage,'/unit/'+unit);
  const started=childPage.waitForResponse(r=>new URL(r.url()).pathname==='/api/units/'+unit+'/start' && r.request().method()==='POST');
  started.catch(()=>{});
  await tap(childPage,button(childPage,'Einheit starten')); assert.equal((await started).status(),200);
  const introduction=childPage.waitForResponse(r=>new URL(r.url()).pathname==='/api/units/'+unit+'/learning-session/action' && r.request().method()==='POST');
  introduction.catch(()=>{});
  await tap(childPage,button(childPage,'Erst selbst probieren')); assert.equal((await introduction).status(),200);
  await tap(childPage,childPage.getByRole('radio').first());
  const answer=childPage.waitForResponse(r=>new URL(r.url()).pathname==='/api/units/'+unit+'/questions/sum/answer' && r.request().method()==='POST');
  answer.catch(()=>{});
  await tap(childPage,button(childPage,'Antwort prüfen')); assert.equal((await answer).status(),200);
  await childPage.getByText('Richtig!',{exact:true}).last().waitFor();
  step='done'; console.log(JSON.stringify({approved:true}));
} catch(e) {
  if (debugPage) { await debugPage.screenshot({path:screens+'/browser-failure.png'}); console.error('route '+new URL(debugPage.url()).pathname+' '+(await debugPage.locator('flt-semantics').allTextContents()).slice(-8).join(' | ').slice(0,1500)); }
  console.error(`beta synthetic browser failed at ${step}: ${e.message}`); process.exitCode=1;
} finally {
  for (const ctx of contexts.reverse()) {
    try { await closeRestrictedBrowserContext(ctx); } catch(e) { console.error('browser cleanup failed'); process.exitCode=1; }
  }
  await browser.close();
}
