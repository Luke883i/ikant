import fs from 'node:fs';
import {spawn,spawnSync} from 'node:child_process';

const browser=['google-chrome','chromium','chromium-browser'].map(name=>spawnSync('sh',['-c',`command -v ${name}`],{encoding:'utf8'})).find(r=>r.status===0)?.stdout.trim();
if(!browser)throw new Error('Chromium-compatible browser not found');
const source=fs.readFileSync(process.argv[2]||'ikant/web/enduser.js','utf8');
const profile=`/tmp/ikant-enduser-browser-${process.pid}`;
const child=spawn(browser,['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',`--user-data-dir=${profile}`,'--remote-debugging-port=0','--remote-allow-origins=*','about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let port,ws;
try{
  for(let i=0;i<250;i++){try{const raw=fs.readFileSync(profile+'/DevToolsActivePort','utf8').trim().split(/\n/);if(raw[0]){port=Number(raw[0]);break}}catch{}await sleep(40)}
  if(!port)throw new Error('DevToolsActivePort unavailable');
  const list=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();const target=list.find(x=>x.type==='page')||list[0];ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(new Error('websocket timeout')),5000);ws.onopen=()=>{clearTimeout(t);resolve()};ws.onerror=reject});
  let id=0;const pending=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result)}};
  const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));setTimeout(()=>{if(pending.delete(n))reject(new Error(method+' timeout'))},5000)});
  const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.text||'evaluation failed');return r};
  const payload={enduser:{schema:'ikant-enduser-self-model/v1-test',identity:{status:'AVAILABLE',label:'iKant locale',fingerprint:'abc123def456'},neuromodel:{trace_schema_valid:true,stages:[{id:'UNDERSTAND',label:'Capisco',status:'complete',facts:{mined_objects:2}},{id:'CONNECT',label:'Collego',status:'complete',facts:{objects:3}},{id:'CHECK',label:'Verifico',status:'complete',facts:{conflicts:0}},{id:'GOVERN',label:'Valuto',status:'complete',facts:{material_action:'PROPOSE_ONLY'}},{id:'FORMULATE',label:'Formulo',status:'complete',facts:{route:'managed-local'}},{id:'INTEGRATE',label:'Integro',status:'complete',facts:{response_memory:true}}]},audit:{status:'CONSISTENT',cycle_id:'cycle-1',conversation_last_sha256:'a'.repeat(64),session_coherent:true,cycle_coherent:true,conversation_integrity_verified:true,record_count:40,visible_record_count:32,conversation_truncated:true,record_counts_coherent:true,generation_route:'managed-local'}}};
  const expression=`(()=>{document.body.innerHTML='<section id="active-panel"><div><span id="shell-status">Pronto</span></div><div id="conversation-log"></div><div id="inspector-overview"><section class="context-card"><h3>Valore epistemico</h3></section></div></section>';const sessionStorage={getItem:(k)=>k==='ikantBearer'?'t':'',setItem:()=>{}};const localStorage={getItem:()=>'',setItem:()=>{},removeItem:()=>{}};const fetch=async()=>({ok:true,json:async()=>(${JSON.stringify(payload)})});${source}})()`;
  await evaluate(expression);let value={};
  for(let i=0;i<100;i++){const r=await evaluate(`(()=>({identity:document.querySelector('#enduser-identity-label')?.textContent||'',fingerprint:document.querySelector('#enduser-identity-fingerprint')?.textContent||'',stages:document.querySelectorAll('#enduser-neuromodel-stages .trace-step').length,audit:[...document.querySelectorAll('#enduser-audit-chips .insight-chip')].map(x=>x.textContent),disclaimer:document.querySelector('#enduser-neuromodel-caption')?.textContent||'',details:document.querySelector('#enduser-audit')?.open===true}))()`);value=r.result.value;if(value.stages===6)break;await sleep(30)}
  const ok=value.identity==='iKant locale'&&value.fingerprint.includes('abc123')&&value.stages===6&&value.audit.some(x=>x.includes('32/40'))&&value.disclaimer.includes('non prova coscienza')&&value.details===false;
  console.log(JSON.stringify({schema:'ikant-enduser-browser-audit/v1-test',status:ok?'PASS':'FAIL',real_browser:true,...value}));if(!ok)process.exitCode=1;
}finally{try{ws?.close()}catch{};child.kill('SIGKILL')}
