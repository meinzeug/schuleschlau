// Two independent synthetic browser sessions on one isolated loopback app.
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

let input = '';
for await (const part of process.stdin) input += part;
const {base, unit, child, day, screens} = JSON.parse(input);
const origin = new URL(base);
if (origin.protocol !== 'http:' || origin.hostname !== '127.0.0.1' || !origin.port || ![unit,child,day].every(id=>/^[a-f0-9]{32}$/.test(id))) throw new Error('Invalid isolated fixture');
const browser = await chromium.launch({headless:true, executablePath:'/opt/google/chrome/chrome', args:['--no-sandbox']});
const contexts = [];
let debugPage, step = 'start';
try {
  async function context() {
    const ctx = await browser.newContext({viewport:{width:390,height:844}, serviceWorkers:'block'});
    contexts.push(ctx);
    await restrictBrowserNetwork(ctx, base);
    return ctx;
  }
  async function open(page, path) {
    await page.goto(base + path, {waitUntil:'domcontentloaded'});
    await page.waitForSelector('flutter-view');
    await page.locator('flt-semantics-placeholder').evaluateAll(nodes => nodes.forEach(n => n.click()));
    await page.waitForTimeout(600);
  }
  async function reveal(page, locator) {
    for (let i=0; i<35; i++) {
      const target = locator.first();
      const box = await target.count() ? await target.boundingBox().catch(() => null) : null;
      if (box && box.y >= 0 && box.y + box.height <= page.viewportSize().height) return target;
      await page.mouse.move(365,740);
      await page.mouse.wheel(0, box && box.y < 0 ? -380 : 380);
      await page.waitForTimeout(120);
    }
    throw new Error('Control not visible: ' + locator.toString());
  }
  async function tap(page, locator) {
    const node = await reveal(page, locator);
    const box = await node.boundingBox();
    await page.mouse.click(box.x+box.width/2, box.y+box.height/2);
    await page.waitForTimeout(350);
  }
  async function type(page,label,value) {
    const input = await reveal(page,page.getByLabel(label,{exact:true}));
    await input.click();
    await page.waitForTimeout(300);
    await page.keyboard.insertText(value);
    await page.waitForTimeout(400);
    assert.equal(await input.inputValue(),value);
  }
  async function login(ctx, username, password='secure-parent-pass-123') {
    const page = await ctx.newPage();
    debugPage = page;
    await open(page,'/login');
    await type(page,'E-Mail oder Benutzername',username);
    await type(page,'Passwort',password);
    const response = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login' && r.request().method()==='POST');
    await tap(page,page.getByRole('button',{name:'Anmelden',exact:true}));
    assert.equal((await response).status(),200);
    await page.waitForTimeout(800);
    return page;
  }
  async function inbox(ctx, cursor) {
    const url = base+'/api/notifications/inbox?paginate=1'+(cursor?'&cursor='+encodeURIComponent(cursor):'');
    const response = await ctx.request.get(url, {headers:{'X-Client-Platform':'web'}});
    assert.equal(response.status(),200);
    return response.json();
  }
  async function poll(fn, predicate) {
    for (let i=0;i<50;i++) {
      const value=await fn();
      if (predicate(value)) return value;
      await new Promise(resolve=>setTimeout(resolve,150));
    }
    throw new Error('Timed out: '+step);
  }
  const one = await context();
  step='login-first';
  const page = await login(one,'parent@example.org');
  const baseline = await inbox(one);
  assert.equal(baseline.items.length,50);
  assert.ok(baseline.next_cursor);
  assert.ok(baseline.items.every(item=>!item.read));
  const oldBefore = await inbox(one,baseline.next_cursor);
  assert.ok(oldBefore.items.length > 0 && oldBefore.items.every(item=>!item.read));
  step='open-bell';
  await tap(page,page.getByRole('button',{name:/Benachrichtigungen/}));
  await page.getByText('Deine Neuigkeiten',{exact:true}).waitFor({timeout:15000});
  const opened = await poll(()=>inbox(one), data=>data.items.some(item=>item.read));
  const readFirst = new Set(opened.items.filter(item=>item.read).map(item=>item.id));
  assert.ok(readFirst.size < baseline.items.length);
  const oldAfter = await inbox(one,baseline.next_cursor);
  assert.ok(oldAfter.items.every(item=>!item.read));
  await page.screenshot({path:screens+'/bell-first-390.png'});
  step='load-older-in-bell';
  const nextPage = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/notifications/inbox' && new URL(r.url()).searchParams.has('cursor') && r.request().method()==='GET');
  await tap(page,page.getByRole('button',{name:'Weitere laden',exact:true}));
  assert.equal((await nextPage).status(),200);
  assert.ok((await inbox(one,baseline.next_cursor)).items.every(item=>!item.read));
  step='round-link';
  await tap(page,page.getByRole('button',{name:/Deine Lernrunde ist bereit/}));
  await page.waitForURL(url=>url.pathname==='/unit/'+unit,{timeout:15000});
  step='scroll-bell';
  await open(page,'/app');
  await tap(page,page.getByRole('button',{name:/Benachrichtigungen/}));
  await page.getByText('Deine Neuigkeiten',{exact:true}).waitFor({timeout:15000});
  const beforeBellScroll = await inbox(one);
  for (let i=0;i<4;i++) {
    await page.mouse.move(330,300);
    await page.mouse.wheel(0,260);
    await page.waitForTimeout(300);
  }
  await poll(()=>inbox(one), data=>data.items.filter(item=>item.read).length > beforeBellScroll.items.filter(item=>item.read).length);
  assert.ok((await inbox(one,baseline.next_cursor)).items.some(item=>!item.read));
  step='login-second';
  const two = await context();
  const pageTwo = await login(two,'parent@example.org');
  const other = await context();
  await login(other,'other-notice-parent@example.org');
  step='cross-session-status';
  const second = await inbox(two);
  const secondStates = new Map(second.items.map(item=>[item.id,item.read]));
  for (const id of readFirst) assert.equal(secondStates.get(id),true);
  const otherStates = await inbox(other);
  assert.ok(otherStates.items.every(item=>!item.read));
  step='all-notices-scroll';
  debugPage = pageTwo;
  await open(pageTwo,'/notifications');
  await pageTwo.waitForURL(url=>url.pathname==='/notifications',{timeout:15000});
  await pageTwo.getByText('Deine Neuigkeiten',{exact:true}).filter({visible:true}).first().waitFor({timeout:15000});
  await poll(()=>inbox(two), data=>data.items.some(item=>item.read));
  const beforeScroll = await inbox(two);
  let scrolled = beforeScroll;
  const initialReadCount = beforeScroll.items.filter(item=>item.read).length;
  for (let i=0;i<30 && scrolled.items.filter(item=>item.read).length<=initialReadCount;i++) {
    await pageTwo.mouse.move(300,650);
    await pageTwo.mouse.wheel(0,350);
    await pageTwo.waitForTimeout(350);
    scrolled = await inbox(two);
  }
  assert.ok(scrolled.items.filter(item=>item.read).length > initialReadCount);
  assert.ok(scrolled.items.some(item=>!item.read));
  assert.ok((await inbox(two,baseline.next_cursor)).items.some(item=>!item.read));
  await pageTwo.screenshot({path:screens+'/all-notices-scrolled-390.png'});
  step='child-ready-notices';
  const parentBeforeChild = await inbox(one);
  const childContext = await context();
  const childPage = await login(childContext,'test-child','secure-child-pass-123');
  const childInbox = await inbox(childContext);
  const roundNotice=childInbox.items.find(item=>item.kind==='round_ready' && item.route==='/unit/'+unit);
  const pageNotice=childInbox.items.find(item=>item.kind==='preparation' && item.route===`/after-school/${child}?day=${day}`);
  assert(roundNotice && pageNotice);
  assert.equal(roundNotice.read,false);
  assert.equal(pageNotice.read,false);
  await tap(childPage,childPage.getByRole('button',{name:/Benachrichtigungen/}));
  await childPage.screenshot({path:screens+'/child-bell-390.png'});
  await tap(childPage,childPage.getByRole('button',{name:/Heftseite.*Bitte prüfen/}));
  await childPage.waitForURL(url=>url.pathname===`/after-school/${child}` && url.searchParams.get('day')===day,{timeout:15000});
  await open(childPage,'/app');
  await tap(childPage,childPage.getByRole('button',{name:/Benachrichtigungen/}));
  await tap(childPage,childPage.getByRole('button',{name:/Deine Lernrunde ist bereit/}));
  await childPage.waitForURL(url=>url.pathname==='/unit/'+unit,{timeout:15000});
  const childAfter=await poll(()=>inbox(childContext), data=>[roundNotice.id,pageNotice.id].every(id=>data.items.some(item=>item.id===id && item.read)));
  assert([roundNotice.id,pageNotice.id].every(id=>childAfter.items.some(item=>item.id===id && item.read)));
  const parentAfterChild=await inbox(one);
  for (const id of [roundNotice.id,pageNotice.id]) {
    const before=parentBeforeChild.items.find(item=>item.id===id);
    const after=parentAfterChild.items.find(item=>item.id===id);
    assert(before && after);
    assert.equal(after.read,before.read);
  }
  console.log(JSON.stringify({passed:true, contexts:4, firstVisible:readFirst.size, afterScroll:scrolled.items.filter(item=>item.read).length, roundLink:true, childPreparation:true, childRound:true}));
} catch (error) {
  if (debugPage) await debugPage.screenshot({path:screens+'/failure-'+step+'.png'}).catch(()=>{});
  console.error('Failed at '+step+': '+error.message);
  process.exitCode=1;
} finally {
  for (const ctx of contexts.reverse()) await closeRestrictedBrowserContext(ctx);
  await browser.close();
}
