import fs from 'node:fs';
import http from 'node:http';
import {spawn,spawnSync} from 'node:child_process';

const sourcePath=process.argv[2]||'ikant/web/public-v1.js';
const cdpTimeoutMs=Number(process.env.IKANT_CDP_TIMEOUT_MS||12000);
const startupTimeoutMs=Number(process.env.IKANT_BROWSER_STARTUP_TIMEOUT_MS||30000);
const conditionTimeoutMs=Number(process.env.IKANT_BROWSER_CONDITION_TIMEOUT_MS||10000);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function findBrowser(){if(process.env.IKANT_BROWSER)return process.env.IKANT_BROWSER;for(const name of ['google-chrome','chromium','chromium-browser']){const r=spawnSync('sh',['-c',`command -v ${name}`],{encoding:'utf8'});if(r.status===0&&r.stdout.trim())return r.stdout.trim();}throw new Error('Chromium-compatible browser not found');}
function getJson(url){return new Promise((resolve,reject)=>{const req=http.get(url,res=>{let data='';res.setEncoding('utf8');res.on('data',d=>data+=d);res.on('end',()=>{try{resolve(JSON.parse(data));}catch(e){reject(e);}});});req.on('error',reject);req.setTimeout(1000,()=>req.destroy(new Error('DevTools HTTP timeout')));});}
async function waitForActivePort(profile,deadline=Date.now()+startupTimeoutMs){const path=`${profile}/DevToolsActivePort`;while(Date.now()<deadline){try{const lines=fs.readFileSync(path,'utf8').trim().split(/\r?\n/);const port=Number(lines[0]);if(Number.isInteger(port)&&port>0)return port;}catch{}await sleep(50);}throw new Error('DevToolsActivePort unavailable');}
async function waitJson(url,deadline=Date.now()+startupTimeoutMs){let last='';while(Date.now()<deadline){try{return await getJson(url);}catch(error){last=String(error?.message||error);}await sleep(80);}throw new Error(`DevTools endpoint unavailable: ${last}`);}
function extractFunction(src,name){const needle=`function ${name}(`,start=src.indexOf(needle);if(start<0)throw new Error(`missing ${name}`);const brace=src.indexOf('{',start);let depth=0,quote='',escape=false;for(let i=brace;i<src.length;i++){const c=src[i];if(quote){if(escape){escape=false;continue;}if(c==='\\'){escape=true;continue;}if(c===quote)quote='';continue;}if(c==='"'||c==="'"||c==='`'){quote=c;continue;}if(c==='{')depth++;else if(c==='}'){depth--;if(depth===0)return src.slice(start,i+1);}}throw new Error(`unterminated ${name}`);}
class CDP{constructor(ws){this.ws=ws;this.id=0;this.pending=new Map();ws.onmessage=e=>{const msg=JSON.parse(e.data);if(msg.id&&this.pending.has(msg.id)){const p=this.pending.get(msg.id);clearTimeout(p.timer);this.pending.delete(msg.id);msg.error?p.reject(new Error(msg.error.message)):p.resolve(msg.result);}};ws.onclose=()=>{for(const [id,p] of this.pending){clearTimeout(p.timer);p.reject(new Error('websocket closed'));this.pending.delete(id);}};}call(method,params={},ms=cdpTimeoutMs){return new Promise((resolve,reject)=>{const id=++this.id,timer=setTimeout(()=>{this.pending.delete(id);reject(new Error(`${method} timeout after ${ms}ms`));},ms);this.pending.set(id,{resolve,reject,timer});this.ws.send(JSON.stringify({id,method,params}));});}}
async function waitValue(cdp,expression,predicate,label,deadline=Date.now()+conditionTimeoutMs){let last;while(Date.now()<deadline){const out=await cdp.call('Runtime.evaluate',{expression,returnByValue:true});last=out.result.value;if(predicate(last))return last;await sleep(25);}throw new Error(`${label} condition timeout; last=${JSON.stringify(last)}`);}

const src=fs.readFileSync(sourcePath,'utf8');
const funcs=['setHidden','keepAcceptanceWritable','syncAdmission','installAdmissionRepair'].filter(n=>src.includes(`function ${n}(`)).map(n=>extractFunction(src,n)).join('\n');
const browser=findBrowser(),profile=`/tmp/ikant-browser-liveness-${process.pid}-${Date.now()}`;
const child=spawn(browser,['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run',`--user-data-dir=${profile}`,'--remote-debugging-port=0','--remote-allow-origins=*','about:blank'],{stdio:['ignore','ignore','pipe']});
let stderr='',ws;
child.stderr?.on('data',chunk=>{stderr=(stderr+chunk.toString('utf8')).slice(-4096);});
try{
  const port=await waitForActivePort(profile),targets=await waitJson(`http://127.0.0.1:${port}/json/list`),target=targets.find(x=>x.type==='page')||targets[0];
  if(!target?.webSocketDebuggerUrl)throw new Error('DevTools page target unavailable');
  ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(new Error('websocket open timeout')),5000);ws.onopen=()=>{clearTimeout(t);resolve();};ws.onerror=()=>{clearTimeout(t);reject(new Error('websocket error'));};});
  const cdp=new CDP(ws);
  const setup=`document.body.innerHTML=\`<section id="pair-panel"><form id="pair-form"><input id="pair-code"></form><p id="pair-error"></p></section><section id="admission-panel" hidden><span id="step-accept"></span><span id="step-probe"></span><form id="accept-form"><input id="accept-text"><button type="submit">Accetta</button></form><button id="probe-button">Probe</button><button id="init-button">Init</button><p id="admission-copy"></p></section>\`;const $=id=>document.getElementById(id);${funcs};installAdmissionRepair();setTimeout(()=>document.body.dataset.ikantTick='1',0);'installed'`;
  await cdp.call('Runtime.evaluate',{expression:setup,returnByValue:true});
  const tick=await waitValue(cdp,'document.body.dataset.ikantTick||""',value=>value==='1','event-loop tick');
  await cdp.call('Runtime.evaluate',{expression:'document.getElementById("pair-code").focus();document.getElementById("pair-code").value="";true',returnByValue:true});
  await cdp.call('Input.insertText',{text:'ikant-liveness'});
  const typed=await waitValue(cdp,'document.getElementById("pair-code").value',value=>value==='ikant-liveness','native input');
  await cdp.call('Runtime.evaluate',{expression:'document.getElementById("step-accept").classList.add("done");true',returnByValue:true});
  await waitValue(cdp,'document.querySelector("#accept-form button").hidden===true&&document.getElementById("probe-button").hidden===false',Boolean,'admission transition');
  const admission=(await cdp.call('Runtime.evaluate',{expression:'({acceptHidden:document.querySelector("#accept-form button").hidden,probeHidden:document.getElementById("probe-button").hidden,initHidden:document.getElementById("init-button").hidden,copy:document.getElementById("admission-copy").textContent})',returnByValue:true})).result.value;
  console.log(JSON.stringify({schema:'ikant-public-browser-liveness/v1-test',status:'PASS',event_loop_tick:tick,input_value:typed,admission,source:sourcePath,real_browser_execution:true,bounds:{startup_ms:startupTimeoutMs,cdp_ms:cdpTimeoutMs,condition_ms:conditionTimeoutMs}}));
}catch(error){console.error(JSON.stringify({schema:'ikant-public-browser-liveness/v1-test',status:'FAIL',error:String(error?.message||error),browser_stderr:stderr,source:sourcePath,real_browser_execution:true}));process.exitCode=1;}finally{try{ws?.close();}catch{}child.kill('SIGKILL');try{fs.rmSync(profile,{recursive:true,force:true});}catch{}}
