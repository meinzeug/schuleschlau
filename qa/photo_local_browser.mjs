// Local synthetic browser journey; no provider is called.
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

let input = '';
for await (const part of process.stdin) input += part;
const {base, child, photo, screens} = JSON.parse(input);
const origin = new URL(base);
if (origin.protocol !== 'http:' || origin.hostname !== '127.0.0.1' || !origin.port || !/^[a-f0-9]{32}$/.test(child)) throw new Error('Invalid fixture');
const browser = await chromium.launch({headless:true, executablePath:'/opt/google/chrome/chrome', args:['--no-sandbox']});
const ctx = await browser.newContext({viewport:{width:390,height:844}, serviceWorkers:'block'});
let phase = 'setup', page;
const buttonBoxes={};
try {
  await restrictBrowserNetwork(ctx, base);
  page = await ctx.newPage();
  async function open(path) {
    await page.goto(base+path, {waitUntil:'domcontentloaded'});
    await page.waitForSelector('flutter-view');
    await page.locator('flt-semantics-placeholder').evaluateAll(nodes=>nodes.forEach(n=>n.click()));
    await page.waitForTimeout(700);
  }
  async function reveal(locator) {
    for (let i=0;i<35;i++) {
      const item=locator.first();
      const box=await item.count()?await item.boundingBox().catch(()=>null):null;
      if (box && box.y>=0 && box.y+box.height<=844) return item;
      await page.mouse.move(360,730);
      await page.mouse.wheel(0,box && box.y<0?-350:350);
      await page.waitForTimeout(100);
    }
    throw new Error('Missing visible control: '+locator.toString());
  }
  async function tap(locator) {
    const item=await reveal(locator), box=await item.boundingBox();
    await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
    await page.waitForTimeout(350);
  }
  async function type(label,text) {
    const item=await reveal(page.getByLabel(label,{exact:true}));
    await item.click();
    await page.waitForTimeout(400);
    await page.keyboard.insertText(text);
    await page.waitForTimeout(350);
    assert.equal(await item.inputValue(),text);
  }
  phase='login';
  await open('/login');
  await type('E-Mail oder Benutzername','test-child');
  await type('Passwort','secure-child-pass-123');
  const logged=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth/login' && r.request().method()==='POST');
  await tap(page.getByRole('button',{name:'Anmelden',exact:true}));
  assert.equal((await logged).status(),200);
  phase='blob-xhr';
  const blobRead=await page.evaluate(()=>new Promise((resolve,reject)=>{
    const url=URL.createObjectURL(new Blob(['synthetic-photo-read']));
    const request=new XMLHttpRequest();
    request.open('GET',url);
    request.onload=()=>{ URL.revokeObjectURL(url); resolve(request.responseText); };
    request.onerror=()=>{ URL.revokeObjectURL(url); reject(new Error('blob XHR blocked')); };
    request.send();
  }));
  assert.equal(blobRead,'synthetic-photo-read');
  for (const width of [390,1280]) {
    await page.setViewportSize({width,height:844});
    phase='photo-picker-'+width;
    await open('/after-school/'+child+'?capture=1');
    const picker=page.waitForEvent('filechooser',{timeout:30000});
    picker.catch(()=>{});
    await tap(page.getByRole('button',{name:'Fotos auswählen',exact:true}));
    await (await picker).setFiles(photo);
    phase='crop-'+width;
    await page.getByRole('button',{name:'Foto übernehmen',exact:true}).waitFor({timeout:30000});
    await tap(page.getByRole('button',{name:'Foto übernehmen',exact:true}));
    await page.getByRole('button',{name:'Fotos abgeben',exact:true}).waitFor({timeout:30000});
    const buttonBox=await page.getByRole('button',{name:'Fotos abgeben',exact:true}).boundingBox();
    assert.ok(buttonBox && buttonBox.width >= 260 && buttonBox.width <= 640);
    buttonBoxes[String(width)]=buttonBox;
    await page.screenshot({path:screens+'/photo-cropped-'+width+'.png'});
  }
  console.log(JSON.stringify({passed:true,buttonBoxes}));
} catch (error) {
  if (page) await page.screenshot({path:screens+'/failure-'+phase+'.png'}).catch(()=>{});
  console.error('Failed at '+phase+': '+error.message);
  process.exitCode=1;
} finally {
  await closeRestrictedBrowserContext(ctx);
  await browser.close();
}
