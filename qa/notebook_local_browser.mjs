// Invoked only by the opt-in isolated pytest harness. No provider or worker.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chromium} from 'playwright';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

const input = JSON.parse(readFileSync(0, 'utf8'));
const address = new URL(input.base);
assert.equal(address.protocol, 'http:');
assert.equal(address.hostname, '127.0.0.1');
assert(Number(address.port) >= 1024);
assert.equal(input.parent, 'parent@example.org');
assert.equal(input.parent_password, 'secure-parent-pass-123');
assert.equal(input.child_password, 'secure-child-pass-123');
const browser = await chromium.launch({headless:true, executablePath:'/opt/google/chrome/chrome', args:['--no-sandbox']});
let context, page, phase = 'setup';
const pageErrors = [], mutations = [], serverErrors = [];
async function open(path) {
  await page.goto(input.base + path, {waitUntil:'domcontentloaded', timeout:90000});
  await page.waitForSelector('flutter-view', {timeout:90000});
  await page.locator('flt-semantics-placeholder').evaluateAll(nodes => nodes.forEach(node => node.click()));
  await page.waitForTimeout(300);
}
async function tap(locator) {
  const target=locator.first();
  for (let n=0; n<40; n++) {
    const box=await target.count() ? await target.boundingBox().catch(()=>null) : null;
    const bottom = page.viewportSize().width>=720 || await page.getByRole('dialog').count() ? 20 : 95;
    if (box && box.width && box.height && box.y>=0 && box.y+box.height<page.viewportSize().height-bottom) {
      await page.mouse.click(box.x+box.width/2,box.y+box.height/2); await page.waitForTimeout(180); return;
    }
    await page.mouse.move(page.viewportSize().width/2,page.viewportSize().height/2);
    await page.mouse.wheel(0,n===0&&!box?-4000:box&&box.y<0?-300:300); await page.waitForTimeout(130);
  }
  throw new Error('Synthetic control not reachable in '+phase+': '+String(locator));
}
async function type(locator, value) {
  await tap(locator); await page.keyboard.press('Control+A');
  await page.keyboard.type(value,{delay:3}); await page.keyboard.press('Tab'); await page.waitForTimeout(200);
}
async function login(username, width) {
  context=await browser.newContext({viewport:{width,height:900}, isMobile:width===390, hasTouch:width===390, serviceWorkers:'block'});
  await restrictBrowserNetwork(context, input.base);
  page=await context.newPage(); page.on('pageerror',()=>pageErrors.push(phase));
  page.on('response',r=>{const u=new URL(r.url());if(u.origin===input.base&&u.pathname.startsWith('/api/')&&r.status()>=500)serverErrors.push(u.pathname.replace(/[a-f0-9]{32}/g,':id'));});
  await open('/login');
  await type(page.getByRole('textbox',{name:'E-Mail oder Benutzername',exact:true}),username);
  await type(page.getByLabel('Passwort',{exact:true}),username===input.parent?input.parent_password:input.child_password);
  await tap(page.getByRole('button',{name:'Anmelden',exact:true}));
  await page.waitForURL(input.base+'/app',{timeout:30000});
  page.on('request',r=>{const path=new URL(r.url()).pathname;if(path.startsWith('/api/')&&r.method()!=='GET') mutations.push({path,method:r.method()});});
}
async function api(path) {
  const response=await context.request.get(input.base+'/api'+path,{headers:{'X-Schulpilot-Request':'1'}});
  assert.equal(response.status(),200);return response.json();
}
async function album(child, subject) {
  await open(`/library/${child}`);
  await tap(page.getByRole('button',{name:/^Mathematik(?:,|\s)/s}));
  await page.getByRole('button',{name:/Seite auswählen\s+1 von/}).first().waitFor({timeout:30000});
  const result=await api(`/children/${child}/materials?subject_id=${subject}`);
  return result;
}
async function screenshot(name) { await page.screenshot({path:`${input.screens}/${name}.png`}); }
try {
  phase='parent-preview';await login(input.parent,390);
  const child=input.children[0], subject=input.subject_id;
  const list=await album(child,subject);assert.equal(list.total,5);
  const preview=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/delete-preview')&&r.request().method()==='POST');
  await tap(page.getByRole('button',{name:'Heftseite löschen',exact:true}));
  const response=await preview;assert.equal(response.status(),200);
  const data=await response.json();assert.equal(data.count,1);assert.equal(data.unit_count,1);assert.equal(data.answer_count,1);
  await page.getByText('Heftseite löschen?',{exact:true}).waitFor();
  const previewText=await page.locator('flt-semantics-host').innerText();
  assert(previewText.includes('1 verknüpfte Lernrunde'));
  assert(previewText.includes('1 gespeichertem Antwortversuch'));
  await screenshot('parent-delete-preview-390');
  await tap(page.getByRole('button',{name:'Abbrechen',exact:true}));
  assert.equal((await api(`/children/${child}/materials?subject_id=${subject}`)).total,5);
  const rereadBefore=mutations.length;
  await tap(page.getByRole('button',{name:'Mit KI neu lesen',exact:true}));
  await tap(page.getByRole('button',{name:'Abbrechen',exact:true}));
  assert.equal(mutations.length,rereadBefore,'cancelled reread must not create a job');
  await closeRestrictedBrowserContext(context); context=undefined;

  for (const [index,width,multiple] of [[0,390,false],[1,1280,true]]) {
    phase='child-'+width;
    await login(index?'notebook-browser-second':'test-child',width);
    const id=input.children[index], viewed=[];
    page.on('response',r=>{const path=new URL(r.url()).pathname;if(r.status()===200&&path.endsWith('/image'))viewed.push(path.split('/').at(-2));});
    const own=await album(id,subject);assert.equal(own.total,5);
    for(let n=0;n<4;n++) {
      await tap(page.getByRole('button',{name:'Nächste Seite',exact:true}));
      await page.getByRole('button',{name:new RegExp('Seite auswählen\\s+'+(n+2)+' von 5')}).first().waitFor();
    }
    for(let n=0;n<30&&!input.pages[index].every(p=>viewed.includes(p.id));n++) await page.waitForTimeout(200);
    assert(input.pages[index].every(p=>viewed.includes(p.id)),'each synthetic image must be fetched');
    await screenshot('child-album-'+width);
    const sibling=await context.request.get(input.base+'/api/materials/'+input.pages[1-index][0].id+'/image',{headers:{'X-Schulpilot-Request':'1'}});
    assert([403,404].includes(sibling.status()));
    // Confirmed pages must not offer child deletion; server checks it as well.
    assert.equal(await page.getByRole('button',{name:'Heftseite löschen',exact:true}).count(),0);
    const current=own.items[4];
    let requestBody;
    page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname.endsWith('/units'))requestBody=r.postDataJSON();});
    await tap(page.getByRole('button',{name:'Übungen zu dieser Heftseite erstellen',exact:true}));
    if(multiple){
      await tap(page.getByText('Weitere Heftseiten hinzufügen',{exact:true}));
      const extra=own.items.find(row=>row.id!==current.id);
      await tap(page.getByRole('checkbox',{name:new RegExp(extra.topic,'i')}));
    }
    await screenshot('child-sources-'+width);
    await tap(page.getByRole('button',{name:'Runde vorbereiten',exact:true}));
    await page.waitForURL(new RegExp('/learning-preparation/'+id+'/'),{timeout:30000});
    assert.equal(requestBody.material_id,current.id);
    assert.equal(requestBody.notebook_sources.length,multiple?2:1);
    for(const ref of requestBody.notebook_sources){const match=own.items.find(row=>row.id===ref.id);assert(match);assert.equal(ref.revision,match.revision);}
    await closeRestrictedBrowserContext(context); context=undefined;
  }
  phase='child-unconfirmed-delete';await login('notebook-browser-third',390);
  const third=input.children[2];
  assert.equal((await album(third,subject)).total,1);
  const thirdPreview=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/delete-preview')&&r.request().method()==='POST');
  await tap(page.getByRole('button',{name:'Heftseite löschen',exact:true}));
  const pr=await thirdPreview;assert.equal(pr.status(),200);assert.equal((await pr.json()).count,1);
  await page.getByText('Heftseite löschen?',{exact:true}).waitFor();
  const deletion=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/bulk-delete')&&r.request().method()==='POST');
  await tap(page.getByRole('button',{name:'Heftseite löschen',exact:true}));
  const dr=await deletion;assert.equal(dr.status(),200);assert.equal((await dr.json()).deleted_count,1);
  const missing=await context.request.get(input.base+'/api/materials/'+input.unconfirmed_id+'/image',{headers:{'X-Schulpilot-Request':'1'}});
  assert([403,404].includes(missing.status()));
  assert.deepEqual(pageErrors,[]);
  assert.deepEqual(serverErrors,[], 'Synthetic local API 5xx');
  assert.equal(mutations.filter(x=>x.path.endsWith('/units')).length,2);
  assert.equal(mutations.filter(x=>x.path.endsWith('/delete-preview')).length,2);
  assert.equal(mutations.filter(x=>x.path.endsWith('/bulk-delete')).length,1);
  assert(!mutations.some(x=>/\/reprocess$/.test(x.path)));
  process.stdout.write('Isolated notebook browser checks passed\n');
} finally {
  if(serverErrors.length)process.stderr.write('Synthetic API 5xx: '+JSON.stringify(serverErrors)+'\n');
  try { await closeRestrictedBrowserContext(context); } finally { await browser.close(); }
}
