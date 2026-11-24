// Isolated opt-in synthetic browser fixture only. No real child, provider or server clock.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

const input = JSON.parse(readFileSync(0, 'utf8'));
const base = new URL(input.base);
assert.equal(base.protocol, 'http:');
assert.equal(base.hostname, '127.0.0.1');
assert(Number(base.port) >= 1024);
const headers = {'X-QA-Token': input.token, 'X-Schulpilot-Request': '1'};
const browser = await chromium.launch({headless:true, executablePath:'/opt/google/chrome/chrome', args:['--no-sandbox']});
let context, page, phase = 'setup';
const pageErrors = [], serverErrors = [];
async function tap(locator) {
  const target=locator.first();
  for(let n=0;n<45;n++) {
    const box=await target.count()?await target.boundingBox().catch(()=>null):null;
    if(box && box.width && box.height && box.y>=0 && box.y+box.height<page.viewportSize().height-2) {
      await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
      await page.waitForTimeout(180); return;
    }
    await page.mouse.move(195,400);
    await page.mouse.wheel(0,n===0&&!box?-4000:box&&box.y<0?-300:300);
    await page.waitForTimeout(130);
  }
  throw new Error('Control unreachable during '+phase+': '+String(locator)+' box='+JSON.stringify(await target.boundingBox().catch(()=>null)));
}
async function type(locator, value) {
  await tap(locator);
  await page.keyboard.press('Control+A');
  await page.keyboard.type(value,{delay:2});
  await page.keyboard.press('Tab');
  await page.waitForTimeout(200);
}
async function open(path) {
  await page.goto(input.base+path,{waitUntil:'domcontentloaded',timeout:90000});
  await page.waitForSelector('flutter-view',{timeout:90000});
  await page.locator('flt-semantics-placeholder').evaluateAll(nodes=>nodes.forEach(node=>node.click()));
  await page.waitForTimeout(350);
}
async function control(path,method='POST') {
  const response=await context.request.fetch(input.base+'/__recall_test__/'+path,{method,headers});
  assert.equal(response.status(),200,`${path}: ${response.status()} ${await response.text()}`);
  return response.json();
}
async function login(width, keepCurrent=false) {
  if(context && !keepCurrent) {await closeRestrictedBrowserContext(context); context=undefined;}
  const mobile=width<720;
  context=await browser.newContext({viewport:{width,height:844},isMobile:mobile,hasTouch:mobile,serviceWorkers:'block'});
  await restrictBrowserNetwork(context, input.base);
  page=await context.newPage();
  page.on('pageerror',()=>pageErrors.push(phase));
  page.on('response',r=>{const u=new URL(r.url());if(u.origin===input.base&&u.pathname.startsWith('/api/')&&r.status()>=500)serverErrors.push(u.pathname.replace(/[a-f0-9]{32}/g,':id'));});
  await open('/login');
  await type(page.getByRole('textbox',{name:'E-Mail oder Benutzername',exact:true}),'test-child');
  await type(page.getByLabel('Passwort',{exact:true}),'secure-child-pass-123');
  await tap(page.getByRole('button',{name:'Anmelden',exact:true}));
  await page.waitForURL(input.base+'/app',{timeout:30000});
}
async function shot(name) {await page.screenshot({path:`${input.screens}/${name}.png`});}
try {
  // First context exists only so the loopback controller can move the test clock.
  context=await browser.newContext({viewport:{width:390,height:844},serviceWorkers:'block'});
  await restrictBrowserNetwork(context, input.base);
  let done=false, rounds=0;
  const startedFromSubject=new Set(), startedFromToday=new Set();
  for(let day=0;day<12;day++) {
    const advance=await control('advance');
    if(advance.done) {done=true;break;}
    if(day<6 && day%2===1) await control('meet-goal');
    const width=[320,390,1280][day%3];
    phase='day-'+day+'-login'; await login(width);
    if(day<6) {
      phase='day-'+day+'-subject-navigation';
      if(width>=1100) {
        // Flutter's collapsed rail does not expose its destination as a
        // Playwright role on this web renderer; click the visible rail icon.
        await page.mouse.click(48,180);
      } else {
        const learn=page.getByRole('button',{name:'Lernen',exact:true})
          .or(page.getByRole('tab',{name:/^Lernen/})).first();
        await tap(learn);
      }
      await page.waitForURL(input.base+'/learn/'+input.child,{timeout:30000});
      const subject=page.getByRole('button',{name:/Mathematik.*Thema/}).first();
      await subject.waitFor({timeout:30000});
      await tap(subject);
      await page.waitForURL(new RegExp('/learn/'+input.child+'/subject/'),{timeout:30000});
      await page.getByRole('button',{name:/Brüche/}).first().waitFor({timeout:30000});
      if(day<3) await shot(`recall-subject-${width}`);
      if(day%2===1) await open('/app');
    }
    const start=day<6 && day%2===0
      ? page.getByRole('button',{name:/Brüche/}).first()
      : page.getByRole('button',{name:day<6?'Freiwillig weiterlernen':/^(Weiterlernen|Jetzt lernen|Freiwillig weiterlernen)$/,exact:day<6}).first();
    await start.waitFor({timeout:30000});
    if(day%2===1 && day<3) await shot(`recall-day-${day+1}-home-${width}`);
    const request=page.waitForResponse(r=>new URL(r.url()).pathname===`/api/children/${input.child}/units`&&r.request().method()==='POST');
    phase='day-'+day+'-start';
    await tap(start);
    const queued=await request;
    assert.equal(queued.status(),202);
    assert((await queued.request().postDataJSON()).review_of);
    (day<6 && day%2===0 ? startedFromSubject : startedFromToday).add(width);
    await page.waitForURL(new RegExp('/learning-preparation/'+input.child+'/'),{timeout:30000});
    const prepared=await control('work');
    assert.equal(prepared.status,'completed',prepared.error);
    assert.equal(prepared.kind,'unit');
    const id=prepared.result.unit_id;
    phase='day-'+day+'-preparation';
    await page.getByRole('button',{name:'Los geht’s',exact:true}).waitFor({timeout:30000});
    if(day<3) await shot(`recall-preparation-${width}`);
    await tap(page.getByRole('button',{name:'Los geht’s',exact:true}));
    await page.waitForURL(input.base+'/unit/'+id,{timeout:30000});
    if(day<3) {
      phase='day-'+day+'-learning-path';
      if(width<1100) {
        await tap(page.getByRole('button',{name:'Dein Lernweg',exact:true}));
        await page.getByText('Hier bist du',{exact:true}).first().waitFor({timeout:30000});
        await tap(page.getByRole('button',{name:'Lernweg schließen',exact:true}));
      } else {
        await page.getByText('Hier bist du',{exact:true}).first().waitFor({timeout:30000});
      }
    }
    const {questions}=await control('answers/'+id);
    for(let index=0;index<questions.length;index++) {
      const question=questions[index];phase='day-'+day+'-question-'+index;
      const fraction=question.answer.match(/^(-?\d+)\/(\d+)$/);
      if(fraction) {
        await page.getByRole('textbox',{name:'Zähler',exact:true}).waitFor({timeout:30000});
        await type(page.getByRole('textbox',{name:'Zähler',exact:true}),fraction[1]);
        await type(page.getByRole('textbox',{name:'Nenner',exact:true}),fraction[2]);
      } else {
        await type(page.getByRole('textbox',{name:'Deine Antwort',exact:true}),question.answer);
      }
      if(day<3 && index===0) await shot(`recall-task-${width}`);
      const answered=page.waitForResponse(r=>new URL(r.url()).pathname===`/api/units/${id}/questions/${question.id}/answer`&&r.request().method()==='POST');
      await tap(page.getByRole('button',{name:'Antwort prüfen',exact:true}));
      const response=await answered;assert.equal(response.status(),200);
      const saved=(await control('answers/'+id)).questions.find(q=>q.id===question.id);
      assert.equal(saved.attempts.length,1);assert.equal(saved.attempts[0].outcome,'correct');
      assert.equal(saved.attempts[0].assisted,false);
      await page.getByText('Richtig!',{exact:true}).last().waitFor({timeout:30000});
      if(day<3 && index===0) {
        await shot(`recall-feedback-${width}`);
        if(day===0) {
          // A separately authenticated device resumes the same saved feedback.
          const firstContext=context, firstPage=page;
          try {
            await login(390,true);
            await open('/unit/'+id);
            await page.getByText('Richtig!',{exact:true}).last().waitFor({timeout:30000});
            const secondDevice=(await control('answers/'+id)).questions.find(q=>q.id===question.id);
            assert.equal(secondDevice.attempts.length,1);
          } finally {
            if(context!==firstContext) await closeRestrictedBrowserContext(context);
            context=firstContext; page=firstPage;
          }
        }
        // An unacknowledged response survives a real page reload and must not
        // create another attempt or advance before the child chooses to.
        await open('/unit/'+id);
        await page.getByText('Richtig!',{exact:true}).last().waitFor({timeout:30000});
        const resumed=(await control('answers/'+id)).questions.find(q=>q.id===question.id);
        assert.equal(resumed.attempts.length,1);
        assert.equal(resumed.attempts[0].outcome,'correct');
        assert.equal(resumed.attempts[0].assisted,false);
      }
      await tap(page.getByRole('button',{name:index===questions.length-1?'Ergebnis ansehen':'Weiter',exact:true}));
    }
    phase='day-'+day+'-coaching';
    const report=await control('work');assert.equal(report.kind,'coach');assert.equal(report.status,'completed',report.error);
    if(day<3) await shot(`recall-day-${day+1}-result-${width}`);
    process.stdout.write(`Simulated day ${day+1}: ${advance.date}, round completed\n`);
    rounds++;
  }
  assert(done,'goals were not secure within twelve simulated rounds');
  assert(rounds>=3);
  assert.deepEqual([...startedFromSubject].sort((a,b)=>a-b),[320,390,1280]);
  assert.deepEqual([...startedFromToday].sort((a,b)=>a-b),[320,390,1280]);
  assert.deepEqual(pageErrors,[]);assert.deepEqual(serverErrors,[]);
  process.stdout.write(`Synthetic browser: ${rounds} rounds completed at 320, 390 and 1280 pixels\n`);
} catch(error) {
  process.stderr.write('phase='+phase+'\n');
  if(page) {
    process.stderr.write('url='+page.url()+'\n');
    process.stderr.write('semantics='+(await page.locator('flt-semantics-host').innerText().catch(()=>''))+'\n');
    await page.screenshot({path:`${input.screens}/recall-error.png`}).catch(()=>{});
  }
  throw error;
} finally {try {await closeRestrictedBrowserContext(context);} finally {await browser.close();}}
