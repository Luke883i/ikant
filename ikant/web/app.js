'use strict';

const $=id=>document.getElementById(id);
const state={token:sessionStorage.getItem('ikantBearer')||'', frame:null, recording:false, recorder:null, chunks:[]};

function setError(id,message=''){ $(id).textContent=String(message||''); }
function show(id,on=true){ $(id).hidden=!on; }

async function api(path,{method='GET',body=null,raw=null,contentType='application/json'}={}){
  const headers={};
  if(state.token) headers.Authorization='Bearer '+state.token;
  if(raw!==null){ headers['Content-Type']=contentType; }
  else if(body!==null){ headers['Content-Type']='application/json'; }
  const response=await fetch(path,{method,headers,body:raw!==null?raw:(body!==null?JSON.stringify(body):undefined),cache:'no-store'});
  const type=response.headers.get('content-type')||'';
  const payload=type.includes('application/json')?await response.json():{error:await response.text()};
  if(!response.ok) throw new Error(payload.error||('HTTP '+response.status));
  return payload;
}

async function pair(code){
  const payload=await api('/api/v1/pair',{method:'POST',body:{code}});
  state.token=payload.bearer_token;
  sessionStorage.setItem('ikantBearer',state.token);
  history.replaceState(null,'',location.pathname+location.search);
  show('pair-panel',false); show('pair-reset',true);
  await refresh();
}

function updateSteps(lifecycle){
  const s=lifecycle.state;
  $('step-accept').classList.toggle('done',['ACCEPTED','PROBED','ACTIVE'].includes(s));
  $('step-probe').classList.toggle('done',['PROBED','ACTIVE'].includes(s));
  $('step-init').classList.toggle('done',s==='ACTIVE');
  $('probe-button').disabled=!['ACCEPTED','PROBED'].includes(s);
  $('init-button').disabled=s!=='PROBED';
  $('accept-text').disabled=s!=='AWAITING_ACCEPTANCE';
}

async function loadAdmission(lifecycle){
  show('active-panel',false); show('admission-panel',true); show('released-panel',false);
  const admission=await api('/api/v1/admission');
  $('terms').textContent=admission.terms;
  $('terms-digest').textContent=admission.terms_sha256;
  updateSteps(lifecycle);
  $('preactive-status').textContent=JSON.stringify({state:lifecycle.state,model:lifecycle.model,voice:lifecycle.voice},null,2);
}

function buildAck(frame){
  const r=frame.receipt||{};
  const visible=$('dashboard').textContent;
  return {
    schema:'ikant-web-human-ack/v0.20-test',
    runtime_session_id:r.runtime_session_id,
    epoch:r.epoch,
    frame_seq:r.frame_seq,
    frame_sha256:r.frame_sha256,
    visible_text:visible,
    visible_text_sha256:r.frame_sha256,
    epistemic_authority:0.0,
    execution_authority:0.0
  };
}

async function renderFrame(frame){
  if(frame.released){
    state.frame=null;
    $('dashboard').textContent='';
    $('intent').disabled=true; $('send-button').disabled=true; $('voice-button').disabled=true; $('exit-button').disabled=true;
    show('released-panel',true);
    return;
  }
  if(frame.schema!=='ikant-web-human-frame/v0.20-test') throw new Error('Unexpected human frame schema');
  state.frame=frame;
  $('dashboard').textContent=frame.text;
  show('released-panel',false);
  // The acknowledgement is built from the actual DOM textContent, not from a parallel projection.
  await api('/api/v1/frame/ack',{method:'POST',body:buildAck(frame)});
  $('intent').disabled=false; $('send-button').disabled=false; $('voice-button').disabled=false; $('exit-button').disabled=false;
}

async function loadActive(){
  show('admission-panel',false); show('active-panel',true); show('pair-reset',true);
  const frame=await api('/api/v1/frame');
  await renderFrame(frame);
}

async function refresh(){
  if(!state.token){ show('pair-panel',true); show('admission-panel',false); show('active-panel',false); return; }
  try{
    const lifecycle=await api('/api/v1/state');
    if(lifecycle.state==='ACTIVE') await loadActive(); else await loadAdmission(lifecycle);
  }catch(error){
    if(String(error.message).includes('pairing')){
      state.token='';sessionStorage.removeItem('ikantBearer');show('pair-panel',true);show('admission-panel',false);show('active-panel',false);
    }else setError('pair-error',error.message);
  }
}

$('pair-form').addEventListener('submit',async event=>{
  event.preventDefault();setError('pair-error');
  try{await pair($('pair-code').value.trim());}catch(error){setError('pair-error',error.message);}
});

$('pair-reset').addEventListener('click',()=>{state.token='';sessionStorage.removeItem('ikantBearer');location.reload();});

$('accept-form').addEventListener('submit',async event=>{
  event.preventDefault();setError('pair-error');
  try{
    await api('/api/v1/accept',{method:'POST',body:{phrase:$('accept-text').value,presented_terms_sha256:$('terms-digest').textContent}});
    await refresh();
  }catch(error){$('preactive-status').textContent=error.message;}
});

$('probe-button').addEventListener('click',async()=>{
  try{const out=await api('/api/v1/probe',{method:'POST',body:{}});$('preactive-status').textContent=JSON.stringify(out,null,2);await refresh();}
  catch(error){$('preactive-status').textContent=error.message;}
});

$('init-button').addEventListener('click',async()=>{
  try{const frame=await api('/api/v1/initialize',{method:'POST',body:{}});show('admission-panel',false);show('active-panel',true);await renderFrame(frame);}
  catch(error){$('preactive-status').textContent=error.message;}
});

$('turn-form').addEventListener('submit',async event=>{
  event.preventDefault();setError('active-error');
  const text=$('intent').value;
  if(!text.trim()) return;
  $('send-button').disabled=true;$('voice-button').disabled=true;$('exit-button').disabled=true;
  try{const frame=await api('/api/v1/turn',{method:'POST',body:{text}});$('intent').value='';await renderFrame(frame);}
  catch(error){setError('active-error',error.message);$('send-button').disabled=false;$('voice-button').disabled=false;$('exit-button').disabled=false;}
});

$('exit-button').addEventListener('click',async()=>{
  setError('active-error');
  try{const frame=await api('/api/v1/turn',{method:'POST',body:{text:'EXIT IKANT'}});await renderFrame(frame);}
  catch(error){setError('active-error',error.message);}
});

$('resume-button').addEventListener('click',async()=>{
  setError('active-error');
  try{const frame=await api('/api/v1/resume',{method:'POST',body:{text:'RESUME IKANT'}});await renderFrame(frame);}
  catch(error){setError('active-error',error.message);}
});

async function startVoice(){
  if(!navigator.mediaDevices||!window.MediaRecorder) throw new Error('Registrazione audio non supportata dal browser');
  const stream=await navigator.mediaDevices.getUserMedia({audio:true});
  state.chunks=[];state.recorder=new MediaRecorder(stream);
  state.recorder.ondataavailable=e=>{if(e.data&&e.data.size)state.chunks.push(e.data);};
  state.recorder.onstop=async()=>{
    stream.getTracks().forEach(t=>t.stop());
    const blob=new Blob(state.chunks,{type:state.recorder.mimeType||'audio/webm'});
    try{
      const out=await api('/api/v1/voice/transcribe',{method:'POST',raw:blob,contentType:blob.type||'audio/webm'});
      if(out.schema==='ikant-web-human-frame/v0.20-test'){await renderFrame(out);return;}
      $('intent').value=out.text;
      $('intent').focus();
    }catch(error){setError('active-error',error.message);}
    finally{state.recording=false;$('voice-button').textContent='Voce input';}
  };
  state.recorder.start();state.recording=true;$('voice-button').textContent='Stop voce';
}

$('voice-button').addEventListener('click',async()=>{
  setError('active-error');
  try{if(state.recording){state.recorder.stop();}else await startVoice();}
  catch(error){setError('active-error',error.message);state.recording=false;$('voice-button').textContent='Voce input';}
});

if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
const hash=new URLSearchParams(location.hash.replace(/^#/,''));
const code=hash.get('pair');
if(code){$('pair-code').value=code;pair(code).catch(error=>setError('pair-error',error.message));}else refresh();
