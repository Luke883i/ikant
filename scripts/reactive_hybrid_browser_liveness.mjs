import fs from 'node:fs';
import {spawn,spawnSync} from 'node:child_process';

const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const cdpTimeoutMs=Number(process.env.IKANT_CDP_TIMEOUT_MS||12000);
const startupTimeoutMs=Number(process.env.IKANT_BROWSER_STARTUP_TIMEOUT_MS||30000);
const conditionTimeoutMs=Number(process.env.IKANT_BROWSER_CONDITION_TIMEOUT_MS||10000);

function findBrowser(){
  if(process.env.IKANT_BROWSER)return process.env.IKANT_BROWSER;
  for(const name of ['google-chrome','chromium','chromium-browser']){
    const r=spawnSync('sh',['-c',`command -v ${name}`],{encoding:'utf8'});
    if(r.status===0&&r.stdout.trim())return r.stdout.trim();
  }
  throw new Error('Chromium-compatible browser not found');
}
function getJson(url){return new Promise((resolve,reject)=>{const req=fetch(url).then(async r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}).then(resolve,reject);void req;});}
async function waitForActivePort(profile,deadline=Date.now()+startupTimeoutMs){
  const path=`${profile}/DevToolsActivePort`;
  while(Date.now()<deadline){
    try{const lines=fs.readFileSync(path,'utf8').trim().split(/\r?\n/),port=Number(lines[0]);if(Number.isInteger(port)&&port>0)return port;}catch{}
    await sleep(50);
  }
  throw new Error('DevToolsActivePort unavailable');
}
async function waitJson(url,deadline=Date.now()+startupTimeoutMs){let last='';while(Date.now()<deadline){try{return await getJson(url);}catch(error){last=String(error?.message||error);}await sleep(80);}throw new Error(`DevTools endpoint unavailable: ${last}`);}
class CDP{
  constructor(ws){this.ws=ws;this.id=0;this.pending=new Map();ws.onmessage=e=>{const msg=JSON.parse(e.data);if(msg.id&&this.pending.has(msg.id)){const p=this.pending.get(msg.id);clearTimeout(p.timer);this.pending.delete(msg.id);msg.error?p.reject(new Error(msg.error.message)):p.resolve(msg.result);}};ws.onclose=()=>{for(const [id,p] of this.pending){clearTimeout(p.timer);p.reject(new Error('websocket closed'));this.pending.delete(id);}};}
  call(method,params={},ms=cdpTimeoutMs){return new Promise((resolve,reject)=>{const id=++this.id,timer=setTimeout(()=>{this.pending.delete(id);reject(new Error(`${method} timeout after ${ms}ms`));},ms);this.pending.set(id,{resolve,reject,timer});this.ws.send(JSON.stringify({id,method,params}));});}
}
async function evaluate(cdp,expression,{awaitPromise=false}={}){const out=await cdp.call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise});if(out.exceptionDetails)throw new Error(out.exceptionDetails.text||'Runtime.evaluate exception');return out.result.value;}
async function waitValue(cdp,expression,predicate,label,deadline=Date.now()+conditionTimeoutMs){let last;while(Date.now()<deadline){last=await evaluate(cdp,expression,{awaitPromise:true});if(predicate(last))return last;await sleep(40);}throw new Error(`${label} condition timeout; last=${JSON.stringify(last)}`);}
async function startFixture(){
  const child=spawn(process.env.PYTHON||'python',['scripts/reactive_hybrid_browser_fixture.py'],{stdio:['ignore','pipe','pipe']});
  let stderr='';child.stderr.on('data',d=>{stderr=(stderr+d.toString('utf8')).slice(-4096);});
  const line=await new Promise((resolve,reject)=>{let buf='';const timer=setTimeout(()=>reject(new Error(`reactive fixture startup timeout: ${stderr}`)),10000);child.stdout.on('data',chunk=>{buf+=chunk.toString('utf8');const i=buf.indexOf('\n');if(i>=0){clearTimeout(timer);resolve(buf.slice(0,i));}});child.on('exit',code=>{clearTimeout(timer);reject(new Error(`reactive fixture exited ${code}: ${stderr}`));});});
  const info=JSON.parse(line);return {child,info,getStderr:()=>stderr};
}

export async function runReactiveHybridBrowserLiveness(){
  const fixture=await startFixture();
  const {port,pairing_code:pairingCode}=fixture.info;
  const origin=`http://127.0.0.1:${port}`;
  const browser=findBrowser(),profile=`/tmp/ikant-reactive-browser-${process.pid}-${Date.now()}`;
  const child=spawn(browser,['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run',`--user-data-dir=${profile}`,'--remote-debugging-port=0','--remote-allow-origins=*','about:blank'],{stdio:['ignore','ignore','pipe']});
  let stderr='',ws;
  child.stderr?.on('data',chunk=>{stderr=(stderr+chunk.toString('utf8')).slice(-4096);});
  try{
    const cdpPort=await waitForActivePort(profile),targets=await waitJson(`http://127.0.0.1:${cdpPort}/json/list`),target=targets.find(x=>x.type==='page')||targets[0];
    if(!target?.webSocketDebuggerUrl)throw new Error('DevTools page target unavailable');
    ws=new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(new Error('websocket open timeout')),5000);ws.onopen=()=>{clearTimeout(t);resolve();};ws.onerror=()=>{clearTimeout(t);reject(new Error('websocket error'));};});
    const cdp=new CDP(ws);await cdp.call('Page.enable');await cdp.call('Runtime.enable');await cdp.call('Page.navigate',{url:origin+'/manifest.webmanifest'});
    await waitValue(cdp,'location.origin',v=>v===origin,'fixture origin');
    const pair=await evaluate(cdp,`(async()=>{const r=await fetch('/api/v1/pair',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify({code:${JSON.stringify(pairingCode)}})});return {status:r.status,body:await r.json()};})()`,{awaitPromise:true});
    if(pair?.status!==200||!pair?.body?.bearer_token)throw new Error(`pairing failed: ${JSON.stringify(pair)}`);
    const token=String(pair.body.bearer_token),auth=JSON.stringify('Bearer '+token);
    await evaluate(cdp,`window.__ikantSlowTurn=fetch('/api/v2/shell/command',{method:'POST',headers:{Authorization:${auth},'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify({op:'TURN',payload:{text:'slow reactive browser turn'}})}).then(async r=>({status:r.status,body:await r.json()}));'started'`);
    const running=await waitValue(cdp,`(async()=>{const r=await fetch('/api/v9/work/current',{headers:{Authorization:${auth},Accept:'application/json'},cache:'no-store'});return r.json();})()`,v=>v?.active===true&&v?.phase==='RUNNING','RUNNING work observable during synchronous TURN');
    const turn=await evaluate(cdp,'window.__ikantSlowTurn',{awaitPromise:true});
    if(turn?.status!==200||!turn?.body?.frame)throw new Error(`slow TURN failed: ${JSON.stringify(turn)}`);
    const sealed=await evaluate(cdp,`(async()=>{const r=await fetch('/api/v9/work/current',{headers:{Authorization:${auth},Accept:'application/json'},cache:'no-store'});return r.json();})()`,{awaitPromise:true});
    if(sealed?.phase!=='SEALED'||sealed?.active!==true)throw new Error(`work did not remain active through canonical frame sealing: ${JSON.stringify(sealed)}`);
    const ack=await evaluate(cdp,`(async()=>{const r=await fetch('/api/v2/shell/ack',{method:'POST',headers:{Authorization:${auth},'Content-Type':'application/json',Accept:'application/json'},body:'{}'});return {status:r.status,body:await r.json()};})()`,{awaitPromise:true});
    if(ack?.status!==200||ack?.body?.acknowledged!==true)throw new Error(`ACK failed: ${JSON.stringify(ack)}`);
    const delivered=await evaluate(cdp,`(async()=>{const r=await fetch('/api/v9/work/current',{headers:{Authorization:${auth},Accept:'application/json'},cache:'no-store'});return r.json();})()`,{awaitPromise:true});
    if(delivered?.phase!=='DELIVERED'||delivered?.active!==false||delivered?.terminal!==true)throw new Error(`work did not terminate only after ACK: ${JSON.stringify(delivered)}`);
    const receipt={schema:'ikant-reactive-browser-liveness/v1-test',status:'PASS',real_browser_execution:true,production_reactive_http:true,running_phase:running.phase,sealed_phase:sealed.phase,terminal_phase:delivered.phase};
    console.log(JSON.stringify(receipt));return receipt;
  }catch(error){throw new Error(`reactive browser liveness failed: ${String(error?.message||error)}; browser=${stderr}; fixture=${fixture.getStderr()}`);}
  finally{try{ws?.close();}catch{}child.kill('SIGKILL');fixture.child.kill('SIGKILL');try{fs.rmSync(profile,{recursive:true,force:true});}catch{}}
}
