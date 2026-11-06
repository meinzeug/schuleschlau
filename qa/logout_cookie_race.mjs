// Opt-in local pytest only: actual browser cookies, no production account.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {chromium} from 'playwright';
const input=JSON.parse(readFileSync(0,'utf8'));
const base=new URL(input.base);
assert.equal(base.hostname,'127.0.0.1');assert.equal(base.protocol,'http:');assert(Number(base.port)>=1024);
const browser=await chromium.launch({headless:true,executablePath:'/opt/google/chrome/chrome',args:['--no-sandbox']});
const context=await browser.newContext();
const first=await context.newPage(),second=await context.newPage();
try {
  await first.goto(input.base+'/');await second.goto(input.base+'/');
  async function login(page, username) {
    return page.evaluate(async ({username})=>{
      const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json','X-Schulpilot-Request':'1'},
        body:JSON.stringify({username,password:'secure-parent-pass-123'})});
      return {status:r.status,body:await r.json()};
    },{username});
  }
  const old=await login(first,'parent@example.org');assert.equal(old.status,200);assert.equal(old.body.user.id,input.old_user);
  await first.evaluate(()=>{window.pendingLogout=fetch('/api/auth/logout',{method:'POST',headers:{'X-Schulpilot-Request':'1'}}).then(r=>r.status);});
  let waiting=false;
  for(let n=0;n<100&&!waiting;n++) {waiting=(await (await context.request.get(input.base+'/__race/status')).json()).pending;if(!waiting)await new Promise(r=>setTimeout(r,50));}
  assert(waiting,'real old logout must reach its held response');
  const current=await login(second,'synthetic-new-parent');assert.equal(current.status,200);assert.equal(current.body.user.id,input.new_user);
  const flow = await second.evaluate(async () => {
    const headers={'Content-Type':'application/json','X-Schulpilot-Request':'1'};
    const prepare=await fetch('/api/auth/google/prepare',{method:'POST',headers,body:'{}'});
    if (!prepare.ok) return {status:prepare.status};
    const body=await prepare.json();
    const start=await fetch('/api/auth/google/start',{method:'POST',headers,body:JSON.stringify({request:body.request})});
    return {status:start.status, id:body.flow_id};
  });
  assert.equal(flow.status,200,'new tab started its own local Google flow');
  await context.request.get(input.base+'/__race/release');
  assert.equal(await first.evaluate(()=>window.pendingLogout),200);
  const google=await second.evaluate(async id=>{
    const r=await fetch('/api/auth/google/result',{method:'POST',headers:{'Content-Type':'application/json','X-Schulpilot-Request':'1'},body:JSON.stringify({flow_id:id})});
    return {status:r.status,body:await r.json()};
  },flow.id);
  assert.equal(google.status,200,'old logout must not erase the new flow cookie');
  assert.equal(google.body.status,'pending');
  const me=await second.evaluate(async ()=>{const r=await fetch('/api/auth/me');return {status:r.status,body:await r.json()};});
  assert.equal(me.status,200,'old logout response must not erase the new login');assert.equal(me.body.id,input.new_user);
  const out=await second.evaluate(async ()=>{const r=await fetch('/api/auth/logout',{method:'POST',headers:{'X-Schulpilot-Request':'1'}});return r.status;});
  assert.equal(out,200);
  assert.equal(await second.evaluate(async ()=>(await fetch('/api/auth/me')).status),401,'logout must revoke the session');
  process.stdout.write('synthetic real-browser cookie race passed\n');
} finally {await context.close();await browser.close();}
