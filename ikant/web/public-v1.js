'use strict';
(()=>{
const $=id=>document.getElementById(id);
const CONTINUITY_KEY='ikantBearerContinuityV1';
let timer=null,refreshing=false,lastConversationSha='',fallbackPairing=false;

function sessionToken(){
  try{return sessionStorage.getItem('ikantBearer')||'';}catch(_){return '';}
}
function rememberedToken(){
  try{
    const raw=localStorage.getItem(CONTINUITY_KEY);
    if(!raw)return '';
    const value=JSON.parse(raw);
    return value&&value.origin===location.origin&&typeof value.token==='string'?value.token:'';
  }catch(_){return '';}
}
function rememberToken(value){
  const token=String(value||'');
  if(!token)return;
  try{localStorage.setItem(CONTINUITY_KEY,JSON.stringify({token,origin:location.origin,remembered_at:Date.now()}));}catch(_){/* continuity is best-effort */}
}
function forgetToken(){
  try{localStorage.removeItem(CONTINUITY_KEY);}catch(_){/* no-op */}
  try{sessionStorage.removeItem('ikantBearer');}catch(_){/* no-op */}
}
function controllerAvailable(){try{return typeof state!=='undefined'&&typeof pairedUI==='function'&&typeof setStatus==='function';}catch(_){return false;}}
function token(){
  const live=sessionToken();
  if(live)return live;
  if(controllerAvailable()&&state.token)return String(state.token);
  return rememberedToken();
}
function pairFragment(){
  try{return String(new URLSearchParams(location.hash.replace(/^#/,'' )).get('pair')||'').trim();}catch(_){return '';}
}
function setPairMessage(message){const err=$('pair-error');if(err)err.textContent=String(message||'');}
function ensurePairInputInteractive(){const input=$('pair-code');if(!input)return;input.disabled=false;input.readOnly=false;input.tabIndex=0;input.removeAttribute('disabled');input.removeAttribute('readonly');input.setAttribute('aria-disabled','false');input.style.pointerEvents='auto';input.style.userSelect='text';input.style.position='relative';input.style.zIndex='2';}

async function publicPairStatus(){
  const r=await fetch('/api/v1/public',{headers:{Accept:'application/json'},cache:'no-store'});
  if(!r.ok)throw new Error('pairing status unavailable');
  return r.json();
}
async function fallbackPair(code){
  if(fallbackPairing)return false;
  const candidate=String(code||'').trim();
  if(!candidate){setPairMessage('Inserisci il codice mostrato dal processo iKant.');return false;}
  fallbackPairing=true;
  try{
    const r=await fetch('/api/v1/pair',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify({code:candidate}),cache:'no-store'});
    const raw=await r.text();let out={};if(raw){try{out=JSON.parse(raw);}catch(_){out={};}}
    if(!r.ok||!out.bearer_token)throw new Error(String(out.error||out.message||('HTTP '+r.status)));
    try{sessionStorage.setItem('ikantBearer',out.bearer_token);}catch(_){}
    rememberToken(out.bearer_token);
    history.replaceState(null,'',location.pathname+location.search);
    location.reload();
    return true;
  }catch(error){fallbackPairing=false;throw error;}
}
async function validateRememberedSession(){
  const live=sessionToken();
  const remembered=rememberedToken();
  if(pairFragment())return;
  if(!live&&remembered){
    try{sessionStorage.setItem('ikantBearer',remembered);}catch(_){return;}
    location.reload();
    return;
  }
  if(!live)return;
  try{
    const r=await fetch('/api/v1/state',{headers:{Authorization:'Bearer '+live,Accept:'application/json'},cache:'no-store'});
    if(r.ok){rememberToken(live);return;}
    if(r.status!==401)return;
    forgetToken();
    if(controllerAvailable()){
      state.token='';
      if(state.setupTimer)clearTimeout(state.setupTimer);
      pairedUI(false);
      setStatus('Connetti','');
    }
    const status=await publicPairStatus().catch(()=>null);
    if(status?.paired){
      setPairMessage('Questa istanza locale è già collegata a una sessione browser precedente. Riavvia iKant per generare un nuovo link di connessione.');
    }else{
      setPairMessage('La sessione browser precedente non è più valida. Apri il nuovo link completo mostrato dal processo iKant.');
    }
    $('pair-code')?.focus();
  }catch(_){/* existing transport diagnostics remain authoritative */}
}

function installContinuity(){
  const pairPanel=$('pair-panel');
  if(pairPanel){
    new MutationObserver(()=>{
      if(pairPanel.hidden&&controllerAvailable()&&state.token)rememberToken(state.token);
    }).observe(pairPanel,{attributes:true,attributeFilter:['hidden']});
  }
  $('pair-reset')?.addEventListener('click',forgetToken,{capture:true});
  if(controllerAvailable()&&state.token)rememberToken(state.token);
  validateRememberedSession();
}

function installControllerFallback(){
  if(controllerAvailable())return;
  const status=$('status-label');if(status&&status.textContent==='Avvio')status.textContent='Connetti';
  const dot=$('status-dot');if(dot)dot.className='status-dot blocked';
  ensurePairInputInteractive();
  const fragment=pairFragment();
  const input=$('pair-code');if(input&&fragment)input.value=fragment;
  setPairMessage(fragment?'Ripristino del collegamento locale…':'Il controller web non è stato inizializzato. Inserisci il codice locale per tentare un recupero sicuro.');
  const form=$('pair-form');
  if(!form||form.dataset.fallbackBound==='true')return;
  form.dataset.fallbackBound='true';
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    event.stopImmediatePropagation();
    setPairMessage('');
    try{await fallbackPair($('pair-code')?.value);}catch(error){setPairMessage(String(error?.message||'Collegamento non riuscito').slice(0,180));$('pair-code')?.focus();}
  },{capture:true});
  if(fragment){
    queueMicrotask(()=>fallbackPair(fragment).catch(error=>{setPairMessage(String(error?.message||'Collegamento non riuscito').slice(0,180));$('pair-code')?.focus();}));
  }else{
    input?.focus();
  }
}

function reveal(el){if(!el||el.hidden)return;el.classList.remove('view-enter');void el.offsetWidth;el.classList.add('view-enter');}
function installTransitions(){for(const id of ['pair-panel','setup-panel','admission-panel','active-panel','released-panel']){const el=$(id);if(!el)continue;new MutationObserver(()=>{if(!el.hidden)reveal(el);}).observe(el,{attributes:true,attributeFilter:['hidden']});if(!el.hidden)reveal(el);}}
function keepAcceptanceWritable(){const input=$('accept-text');if(!input)return;if(input.disabled)input.disabled=false;input.removeAttribute('disabled');input.setAttribute('aria-disabled','false');}
function syncAdmission(){keepAcceptanceWritable();const accepted=$('step-accept')?.classList.contains('done')===true,probed=$('step-probe')?.classList.contains('done')===true;const form=$('accept-form'),acceptButton=form?.querySelector('button[type="submit"]'),probe=$('probe-button'),init=$('init-button'),copy=$('admission-copy');if(acceptButton){acceptButton.hidden=accepted;acceptButton.textContent='Accetta';}if(probe)probe.hidden=!accepted||probed;if(init)init.hidden=!probed;if(form)form.classList.toggle('accepted',accepted);if(copy)copy.textContent=!accepted?'Scrivi I ACCEPT per continuare.':!probed?'Condizioni registrate. Ora verifica l’ambiente locale.':'Ambiente verificato. Puoi avviare iKant.';}
function installAdmissionRepair(){const root=$('admission-panel');if(!root)return;const observer=new MutationObserver(syncAdmission);observer.observe(root,{subtree:true,attributes:true,attributeFilter:['disabled','class','hidden']});syncAdmission();}
function installPairRecovery(){const err=$('pair-error'),input=$('pair-code');if(!err)return;new MutationObserver(()=>{const v=String(err.textContent||'').toLowerCase();if(v.includes('already consumed')||v.includes('consumed')){err.textContent='Questo codice monouso è già stato usato. Se questa scheda era già collegata, iKant prova a recuperare la sessione; altrimenti riavvia il processo per un nuovo link.';history.replaceState(null,'',location.pathname+location.search);if(input){input.value='';input.focus();}}}).observe(err,{childList:true,characterData:true,subtree:true});}
function clear(el){while(el?.firstChild)el.firstChild.remove();}
function renderConversation(c){const host=$('conversation-log'),empty=$('empty-state'),dash=$('dashboard');if(!host)return;const rows=Array.isArray(c?.records)?c.records:[];const sha=String(c?.last_sha256||'');if(sha&&sha===lastConversationSha)return;lastConversationSha=sha;clear(host);for(const row of rows){const wrap=document.createElement('article');wrap.className='message message-'+(row.role==='user'?'user':'ikant');const bubble=document.createElement('div');bubble.className='message-bubble';bubble.textContent=String(row.text||'');const meta=document.createElement('span');meta.className='message-role';meta.textContent=row.role==='user'?'Tu':'iKant';wrap.append(meta,bubble);host.appendChild(wrap);}if(rows.length){if(empty)empty.hidden=true;const last=rows.at(-1);if(dash&&!dash.classList.contains('pending')&&last?.role==='ikant'){const d=String(dash.textContent||'').replace(/^iKant:\s*/,'').trim();if(d&&d===String(last.text||'').trim())dash.textContent='';}requestAnimationFrame(()=>{const w=$('semantic-window')||host.parentElement;if(w)w.scrollTop=w.scrollHeight;});}else if(empty&&!String(dash?.textContent||'').trim())empty.hidden=false;}
function metric(label,value,tone=''){const span=document.createElement('span');span.className='insight-chip'+(tone?' '+tone:'');span.innerHTML=`<strong>${Number(value||0)}</strong><small>${label}</small>`;return span;}
function renderEpistemic(v){const strip=$('insight-strip');if(!strip)return;if(!v||v.status!=='AVAILABLE'){strip.hidden=true;return;}clear(strip);strip.append(metric('supporti',v.direct_support,'support'),metric('derivazioni',v.derived_items),metric('conflitti',v.open_conflicts,v.open_conflicts?'warn':''),metric('incerti',v.uncertain_items));strip.hidden=false;const label=$('epistemic-caption');if(label)label.textContent=String(v.label||'Valore epistemico disponibile');}
function renderSystems(r){const host=$('foundation-systems');if(!host)return;clear(host);const rows=Array.isArray(r?.systems)?r.systems:[];for(const s of rows){const row=document.createElement('div');row.className='system-row';const dot=document.createElement('span');dot.className='system-dot';const copy=document.createElement('div');const strong=document.createElement('strong');strong.textContent=String(s.label||s.id||'Sistema');const small=document.createElement('small');small.textContent=String(s.status||'PRESENT');copy.append(strong,small);row.append(dot,copy);host.appendChild(row);}const section=$('runtime-systems-section');if(section)section.hidden=!rows.length;}
function renderRelease(out){const badge=$('release-badge');if(badge)badge.textContent=String(out.release||'v1.0-public-test');const cap=$('empty-caption');const services=out?.capabilities?.services||[];if(cap)cap.textContent=services.length?`${services.length} servizi locali dimostrati · chiedi, esplora, configura`:'Ambiente locale pronto';}
async function request(path){const h={Accept:'application/json'};if(token())h.Authorization='Bearer '+token();const r=await fetch(path,{headers:h,cache:'no-store'});const raw=await r.text();let out={};if(raw){try{out=JSON.parse(raw);}catch(_){out={};}}if(!r.ok)throw new Error(String(out.message||out.error||('HTTP '+r.status)).slice(0,180));return out;}
async function refresh(){if(refreshing||!token()||$('active-panel')?.hidden)return;refreshing=true;try{const out=await request('/api/v8/public');if(out?.schema!=='ikant-public-experience/v1-test')return;renderRelease(out);renderConversation(out.conversation);renderEpistemic(out.epistemic_value);renderSystems(out.runtime_systems);}catch(_){/* existing diagnostics own error presentation */}finally{refreshing=false;}}
function installRefreshHooks(){const dash=$('dashboard');if(dash)new MutationObserver(()=>setTimeout(refresh,80)).observe(dash,{childList:true,characterData:true,subtree:true});const active=$('active-panel');if(active)new MutationObserver(()=>{if(!active.hidden)refresh();}).observe(active,{attributes:true,attributeFilter:['hidden']});document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});timer=setInterval(refresh,4500);window.addEventListener('beforeunload',()=>clearInterval(timer));}
function installServiceNavigation(){const host=$('foundation-services');if(!host)return;host.addEventListener('click',e=>{const row=e.target.closest('[data-service]');if(!row)return;const id=row.dataset.service;if(id==='local_conversation'){$('inspector-close')?.click();$('intent')?.focus();}else if(['cognitive_trace'].includes(id))document.querySelector('[data-inspector-view="conversation"]')?.click();else if(['epistemic_inspection','json_snapshot','docx_artifact'].includes(id))document.querySelector('[data-inspector-view="artifacts"]')?.click();else if(id==='experiment_config')$('foundation-config-disclosure')?.setAttribute('open','');else if(id==='bootstrap_diagnostics')$('runtime-disclosure')?.setAttribute('open','');else if(id==='loopback_voice')$('voice-button')?.focus();});}

ensurePairInputInteractive();
installControllerFallback();
installContinuity();
installTransitions();
installAdmissionRepair();
installPairRecovery();
installRefreshHooks();
installServiceNavigation();
refresh();
})();