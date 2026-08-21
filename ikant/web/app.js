'use strict';

const $=id=>document.getElementById(id);
const SHELL_SCHEMA='ikant-advanced-web-shell/v0.26-test';
const SHELL_COMMAND_SCHEMA='ikant-advanced-web-shell-command/v0.26-test';
const SHELL_ACK_SCHEMA='ikant-advanced-web-shell-ack/v0.26-test';
const WEB_FRAME_SCHEMA='ikant-web-human-frame/v0.20-test';
const WEB_ACK_SCHEMA='ikant-web-human-ack/v0.20-test';

function randomId(prefix){
  if(!window.crypto||!crypto.getRandomValues)throw new Error('secure browser randomness unavailable');
  if(crypto.randomUUID)return prefix+'-'+crypto.randomUUID();
  const bytes=new Uint8Array(18);crypto.getRandomValues(bytes);return prefix+'-'+Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
}
const clientId=sessionStorage.getItem('ikantShellClient')||randomId('client');sessionStorage.setItem('ikantShellClient',clientId);
const state={token:sessionStorage.getItem('ikantBearer')||'',frame:null,shell:null,recovering:false};

function setError(id,message=''){const el=$(id);if(el)el.textContent=String(message||'');}
function show(id,on=true){$(id).hidden=!on;}
function freezeActive(){for(const id of ['intent','send-button','exit-button','sync-button']){const el=$(id);if(el)el.disabled=true;}}
function enableActive(){for(const id of ['intent','send-button','exit-button','sync-button']){const el=$(id);if(el)el.disabled=false;}}
function shellStatus(label){const el=$('shell-status');if(el)el.textContent='LOCAL CONTROL · '+String(label);}
function released(on){show('released-panel',on);if(on)freezeActive();}

async function api(path,{method='GET',body=null,raw=null,contentType='application/json'}={}){
  const headers={};if(state.token)headers.Authorization='Bearer '+state.token;
  if(raw!==null)headers['Content-Type']=contentType;else if(body!==null)headers['Content-Type']='application/json';
  const response=await fetch(path,{method,headers,body:raw!==null?raw:(body!==null?JSON.stringify(body):undefined),cache:'no-store'});
  const type=response.headers.get('content-type')||'';const payload=type.includes('application/json')?await response.json():{error:await response.text()};
  if(!response.ok)throw new Error(payload.error||('HTTP '+response.status));return payload;
}

async function apiRetry(path,options){try{return await api(path,options);}catch(_first){return api(path,options);}}

async function pair(code){
  const payload=await api('/api/v1/pair',{method:'POST',body:{code}});state.token=payload.bearer_token;sessionStorage.setItem('ikantBearer',state.token);history.replaceState(null,'',location.pathname+location.search);show('pair-panel',false);show('pair-reset',true);await refresh();
}

function updateSteps(lifecycle){
  const s=lifecycle.state;$('step-accept').classList.toggle('done',['ACCEPTED','PROBED','ACTIVE'].includes(s));$('step-probe').classList.toggle('done',['PROBED','ACTIVE'].includes(s));$('step-init').classList.toggle('done',s==='ACTIVE');$('probe-button').disabled=!['ACCEPTED','PROBED'].includes(s);$('init-button').disabled=s!=='PROBED';$('accept-text').disabled=s!=='AWAITING_ACCEPTANCE';
}

async function loadAdmission(lifecycle){
  state.shell=null;show('active-panel',false);show('admission-panel',true);show('released-panel',false);const admission=await api('/api/v1/admission');$('terms').textContent=admission.terms;$('terms-digest').textContent=admission.terms_sha256;updateSteps(lifecycle);$('preactive-status').textContent=JSON.stringify({state:lifecycle.state,model:lifecycle.model,voice:lifecycle.voice},null,2);
}

function buildWebAck(frame){
  const r=frame.receipt||{};const visible=$('dashboard').textContent;return {schema:WEB_ACK_SCHEMA,runtime_session_id:r.runtime_session_id,epoch:r.epoch,frame_seq:r.frame_seq,frame_sha256:r.frame_sha256,visible_text:visible,visible_text_sha256:r.frame_sha256,epistemic_authority:0.0,execution_authority:0.0};
}

async function renderLegacyFrame(frame){
  if(!frame||frame.schema!==WEB_FRAME_SCHEMA)throw new Error('Unexpected activation frame schema');state.frame=frame;$('dashboard').textContent=frame.text;await apiRetry('/api/v1/frame/ack',{method:'POST',body:buildWebAck(frame)});
}

function bindShell(opened){
  if(!opened||opened.schema!==SHELL_SCHEMA||opened.client_id!==clientId||!opened.shell_id)throw new Error('Advanced web shell binding failed');
  state.shell={shell_id:opened.shell_id,client_id:clientId,next_seq:opened.next_seq,last_acked_frame:opened.last_acked_frame||null};
}

async function renderShellResponse(response){
  if(!response||response.schema!==SHELL_SCHEMA)throw new Error('Unexpected S8 shell response');
  if(response.status==='RELEASED'&&response.frame===null){state.shell.next_seq=response.next_seq;state.shell.last_acked_frame=response.last_acked_frame||state.shell.last_acked_frame;shellStatus('RELEASED');released(true);return response;}
  const frame=response.frame;if(!frame||frame.schema!==WEB_FRAME_SCHEMA)throw new Error('S8 response missing canonical frame');
  state.frame=frame;$('dashboard').textContent=frame.text;released(false);
  const op=response.operation||{};const ack={schema:SHELL_ACK_SCHEMA,shell_id:state.shell.shell_id,client_id:clientId,seq:op.seq,idempotency_key:op.idempotency_key,frame_ack:buildWebAck(frame)};
  const confirmed=await apiRetry('/api/v2/shell/ack',{method:'POST',body:ack});
  if(!confirmed||confirmed.schema!==SHELL_SCHEMA||confirmed.acknowledged!==true)throw new Error('S8 exact ACK failed');
  state.shell.next_seq=confirmed.next_seq;state.shell.last_acked_frame=confirmed.last_acked_frame||null;
  if(confirmed.status==='RELEASED'){shellStatus('RELEASED');released(true);}else{shellStatus('READY');released(false);enableActive();}
  return confirmed;
}

async function shellCommand(op,payload={}){
  if(!state.shell)throw new Error('S8 shell not open');freezeActive();shellStatus('BUSY');
  const command={schema:SHELL_COMMAND_SCHEMA,shell_id:state.shell.shell_id,client_id:clientId,seq:state.shell.next_seq,op,idempotency_key:randomId('op'),expected_frame:state.shell.last_acked_frame,payload};
  const response=await apiRetry('/api/v2/shell/command',{method:'POST',body:command});return renderShellResponse(response);
}

async function openShell({synchronize=true}={}){
  freezeActive();shellStatus('BINDING');const opened=await apiRetry('/api/v2/shell/open',{method:'POST',body:{client_id:clientId}});bindShell(opened);
  if(opened.pending_response){shellStatus('RECOVERING');await renderShellResponse(opened.pending_response);return;}
  if(synchronize)await shellCommand('SYNC',{});else{shellStatus('READY');enableActive();}
}

async function recoverShell(){
  if(state.recovering)return;state.recovering=true;freezeActive();shellStatus('RECOVERING');
  try{await openShell({synchronize:true});}catch(_error){shellStatus('TRANSPORT BLOCKED');}
  finally{state.recovering=false;}
}

async function loadActive(){show('admission-panel',false);show('active-panel',true);show('pair-reset',true);await openShell({synchronize:true});}

async function refresh(){
  if(!state.token){show('pair-panel',true);show('admission-panel',false);show('active-panel',false);return;}
  try{const lifecycle=await api('/api/v1/state');if(lifecycle.state==='ACTIVE')await loadActive();else await loadAdmission(lifecycle);}
  catch(error){if(String(error.message).includes('pairing')||String(error.message).includes('HTTP 401')){state.token='';sessionStorage.removeItem('ikantBearer');state.shell=null;show('pair-panel',true);show('admission-panel',false);show('active-panel',false);}else setError('pair-error',error.message);}
}

$('pair-form').addEventListener('submit',async event=>{event.preventDefault();setError('pair-error');try{await pair($('pair-code').value.trim());}catch(error){setError('pair-error',error.message);}});
$('pair-reset').addEventListener('click',()=>{state.token='';state.shell=null;sessionStorage.removeItem('ikantBearer');location.reload();});
$('accept-form').addEventListener('submit',async event=>{event.preventDefault();setError('pair-error');try{await api('/api/v1/accept',{method:'POST',body:{phrase:$('accept-text').value,presented_terms_sha256:$('terms-digest').textContent}});await refresh();}catch(error){$('preactive-status').textContent=error.message;}});
$('probe-button').addEventListener('click',async()=>{try{const out=await api('/api/v1/probe',{method:'POST',body:{}});$('preactive-status').textContent=JSON.stringify(out,null,2);await refresh();}catch(error){$('preactive-status').textContent=error.message;}});
$('init-button').addEventListener('click',async()=>{try{const frame=await api('/api/v1/initialize',{method:'POST',body:{}});show('admission-panel',false);show('active-panel',true);try{await renderLegacyFrame(frame);}catch(_ack){}await openShell({synchronize:true});}catch(_error){await refresh();}});

$('turn-form').addEventListener('submit',async event=>{event.preventDefault();const text=$('intent').value;if(!text.trim())return;try{await shellCommand('TURN',{text});$('intent').value='';$('intent').focus();}catch(_error){await recoverShell();}});
$('exit-button').addEventListener('click',async()=>{try{await shellCommand('EXIT',{});}catch(_error){await recoverShell();}});
$('resume-button').addEventListener('click',async()=>{try{await shellCommand('RESUME',{});}catch(_error){await recoverShell();}});
$('sync-button').addEventListener('click',async()=>{try{await shellCommand('SYNC',{});}catch(_error){await recoverShell();}});
$('intent').addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){event.preventDefault();$('turn-form').requestSubmit();}});

if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
const hash=new URLSearchParams(location.hash.replace(/^#/,''));const code=hash.get('pair');if(code){$('pair-code').value=code;pair(code).catch(error=>setError('pair-error',error.message));}else refresh();
