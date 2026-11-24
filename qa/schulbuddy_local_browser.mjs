// Local synthetic browser journey; the provider is replaced in the test process.
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

let input = '';
for await (const part of process.stdin) input += part;
const {base, token, material, screens} = JSON.parse(input);
const origin = new URL(base);
if (origin.protocol !== 'http:' || origin.hostname !== '127.0.0.1' || !origin.port || !/^[a-f0-9]{32}$/.test(material)) throw new Error('Invalid fixture');
const browser = await chromium.launch({headless:true, executablePath:'/opt/google/chrome/chrome', args:['--no-sandbox']});
const ctx = await browser.newContext({viewport:{width:390,height:844}, serviceWorkers:'block'});
let phase = 'setup', page;
try {
  await restrictBrowserNetwork(ctx, base);
  page = await ctx.newPage();
  let submittedQuestions=0;
  page.on('request',request=>{
    if (new URL(request.url()).pathname==='/api/schulbuddy/questions' && request.method()==='POST') submittedQuestions++;
  });
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
  phase='source';
  await open('/material/'+material);
  await page.getByText('Sachunterricht · Sonnensystem',{exact:true}).first().waitFor({timeout:15000});
  await tap(page.getByRole('button',{name:'Schulbuddy öffnen'}));
  await page.getByLabel('Deine Frage an Schulbuddy',{exact:true}).waitFor({timeout:15000});
  phase='ask';
  await type('Deine Frage an Schulbuddy','Was ist die Sonne?');
  const submitted=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/schulbuddy/questions' && r.request().method()==='POST');
  await tap(page.getByRole('button',{name:'Frage senden',exact:true}));
  const response=await submitted;
  assert.equal(response.status(),202);
  const body=response.request().postDataJSON();
  assert.equal(body.material_id,material);
  assert.equal(body.question,'Was ist die Sonne?');
  const work=await ctx.request.post(base+'/__buddy_test__/work',{headers:{'X-QA-Token':token,'X-Schulpilot-Request':'1'}});
  assert.equal(work.status(),200);
  assert.equal((await work.json()).status,'completed');
  phase='reply';
  await page.getByText('Die Sonne ist ein Stern.',{exact:true}).first().waitFor({timeout:30000});
  await page.getByText('Aus deinem Lernstoff: „Die Sonne ist ein Stern.“',{exact:true}).waitFor({timeout:15000});
  await page.screenshot({path:screens+'/buddy-source-390.png'});
  phase='reload';
  await open('/material/'+material);
  await tap(page.getByRole('button',{name:'Schulbuddy öffnen'}));
  await page.getByText('Die Sonne ist ein Stern.',{exact:true}).first().waitFor({timeout:15000});
  await page.getByText('Aus deinem Lernstoff: „Die Sonne ist ein Stern.“',{exact:true}).waitFor({timeout:15000});
  assert.equal(submittedQuestions,1);
  console.log(JSON.stringify({passed:true}));
} catch (error) {
  if (page) await page.screenshot({path:screens+'/failure-'+phase+'.png'}).catch(()=>{});
  console.error('Failed at '+phase+': '+error.message);
  process.exitCode=1;
} finally {
  await closeRestrictedBrowserContext(ctx);
  await browser.close();
}
