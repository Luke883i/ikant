'use strict';
(()=>{
const $=id=>document.getElementById(id);
const ENDUSER_SCHEMA='ikant-enduser-self-model/v1-test';
const CONTINUITY_KEY='ikantBearerContinuityV1';
let refreshing=false,timer=null,lastKey='';
function token(){
  try{const live=sessionStorage.getItem('ikantBearer')||'';if(live)return live;}catch(_){}
  try{const raw=localStorage.getItem(CONTINUITY_KEY);if(!raw)return '';const value=JSON.parse(raw);return value&&value.origin===location.origin&&typeof value.token==='string'?value.token:'';}catch(_){return '';}
}
function node(tag,className='',text=''){const el=document.createElement(tag);if(className)el.className=className;if(text)el.textContent=text;return el;}
function ensureSurface(){
  const overview=$('inspector-overview');if(!overview)return null;
  if(!$('enduser-identity')){
    const identity=node('section','context-card');identity.id='enduser-identity';identity.setAttribute('aria-label','Io locale');
    const head=node('div','foundation-head');head.append(node('h3','', 'Io locale'),node('span','foundation-version','runtime'));
    const label=node('strong');label.id='enduser-identity-label';const copy=node('p','epistemic-caption');copy.id='enduser-identity-copy';const fp=node('code');fp.id='enduser-identity-fingerprint';identity.append(head,label,copy,fp);
    overview.prepend(identity);
  }
  if(!$('enduser-neuromodel')){
    const card=node('section','context-card');card.id='enduser-neuromodel';card.setAttribute('aria-label','Modello cognitivo sintetico');
    card.append(node('h3','', 'Modello cognitivo sintetico'));
    const caption=node('p','epistemic-caption','Schema operativo del ciclo: non è una lettura biologica, non espone ragionamento privato e non prova coscienza.');caption.id='enduser-neuromodel-caption';
    const host=node('div','trace-strip');host.id='enduser-neuromodel-stages';card.append(caption,host);
    const first=overview.querySelector('.context-card');if(first?.nextSibling)overview.insertBefore(card,first.nextSibling);else overview.append(card);
  }
  if(!$('enduser-audit')){
    const details=node('details','disclosure');details.id='enduser-audit';const summary=node('summary','','Audit del ciclo');const copy=node('p','epistemic-caption','Coerenza di sessione/ciclo e integrità locale. Un hash verificato non certifica che la risposta sia vera.');
    const chips=node('div','insight-strip');chips.id='enduser-audit-chips';const hash=node('code');hash.id='enduser-audit-hash';details.append(summary,copy,chips,hash);overview.append(details);
  }
  if(!$('enduser-identity-inline')){
    const row=$('shell-status')?.parentElement;if(row){const pill=node('span','insight-chip');pill.id='enduser-identity-inline';pill.hidden=true;row.append(pill);}
  }
  return overview;
}
function short(value,n=8){const s=String(value||'');return s?s.slice(0,n):'';}
function renderIdentity(v){
  const label=$('enduser-identity-label'),copy=$('enduser-identity-copy'),fp=$('enduser-identity-fingerprint'),inline=$('enduser-identity-inline');if(!label)return;
  const available=v?.status==='AVAILABLE',epoch=v?.runtime_epoch||{},hasEpoch=Boolean(epoch?.epoch_id),relationSafe=!hasEpoch||epoch?.model_is_identity===false,ordinal=Number.isInteger(epoch?.ordinal)?epoch.ordinal:null,model=relationSafe?String(epoch?.model_id||'').trim():'';label.textContent=available?String(v.label||'iKant locale'):'Identità locale non disponibile';
  copy.textContent=!available?'Disponibile quando la sessione runtime locale è attiva.':relationSafe?'Identità operativa locale. Epoca e modello descrivono la provenance del runtime; il modello resta un componente sostituibile, non l’identità.':'Provenance componente non coerente: il modello non viene presentato come identità o dettaglio affidabile.';
  const facts=[];if(available&&v.fingerprint)facts.push('sessione '+String(v.fingerprint));if(ordinal!==null)facts.push('epoca '+ordinal+(epoch?.epoch_id?' · '+short(epoch.epoch_id,12):''));if(model)facts.push('modello '+model);fp.textContent=facts.join(' · ');
  if(inline){inline.hidden=!available;inline.textContent=available?'iKant locale'+(ordinal!==null?' · e'+ordinal:''):'';}
}
function factText(facts){
  const names={intent_bound:'intento',mined_objects:'oggetti',selected_objects:'collegati',objects:'collegati',conflicts:'conflitti',epistemic_debt:'debito',closure:'chiusura',material_action:'azione',candidate_actions:'azioni',route:'via',generation_ms:'ms',response_memory:'memoria'};
  return Object.entries(facts||{}).filter(([,v])=>v!==null&&v!==''&&v!==false).slice(0,2).map(([k,v])=>(names[k]||k.replaceAll('_',' '))+' '+String(v)).join(' · ');
}
function renderNeuromodel(v){
  const host=$('enduser-neuromodel-stages'),caption=$('enduser-neuromodel-caption');if(!host)return;host.replaceChildren();
  const stages=Array.isArray(v?.stages)?v.stages:[];for(const stage of stages){const row=node('div','trace-step');const strong=node('strong','',String(stage.label||stage.id||'Fase'));const small=node('small','',factText(stage.facts)||String(stage.status||'unknown'));row.dataset.status=String(stage.status||'unknown');row.append(strong,small);host.append(row);}
  if(caption&&v?.trace_schema_valid===false)caption.textContent='Trace non coerente con il contratto pubblico: l’overview resta degradato e non viene interpretato come stato cognitivo valido.';
}
function chip(label,value,tone=''){const el=node('span','insight-chip'+(tone?' '+tone:''));el.append(node('strong','',String(value)),node('small','',label));return el;}
function renderAudit(v){
  const host=$('enduser-audit-chips'),hash=$('enduser-audit-hash');if(!host)return;host.replaceChildren();const ok=v?.status==='CONSISTENT';
  host.append(chip('audit',ok?'coerente':String(v?.status||'—'),ok?'support':'warn'));
  host.append(chip('sessione',v?.session_coherent?'coerente':'drift',v?.session_coherent?'support':'warn'));
  host.append(chip('ciclo',v?.cycle_coherent?'coerente':'drift',v?.cycle_coherent?'support':'warn'));
  if(Number.isInteger(v?.runtime_epoch_ordinal))host.append(chip('epoca','e'+v.runtime_epoch_ordinal,'support'));
  host.append(chip('catena chat',v?.conversation_integrity_verified?'verificata':'non verificata',v?.conversation_integrity_verified?'support':'warn'));
  const visible=Number(v?.visible_record_count||0),total=Number(v?.record_count||0);host.append(chip('cronologia',`${visible}/${total}${v?.conversation_truncated?' · ultimi':''}`,v?.record_counts_coherent===false?'warn':''));
  if(v?.generation_route)host.append(chip('generazione',String(v.generation_route)));
  hash.textContent=v?.conversation_last_sha256?'sha256 · '+String(v.conversation_last_sha256).slice(0,16)+'…':'';
}
function renderEnduser(v){if(!v||v.schema!==ENDUSER_SCHEMA)return;ensureSurface();renderIdentity(v.identity);renderNeuromodel(v.neuromodel);renderAudit(v.audit);}
function renderSnapshot(snapshot){const enduser=snapshot?.public?.enduser;if(enduser)renderEnduser(enduser);}
async function refresh(){
  if(refreshing||!token()||$('active-panel')?.hidden)return;refreshing=true;try{const r=await fetch('/api/v8/public',{headers:{Authorization:'Bearer '+token(),Accept:'application/json'},cache:'no-store'});if(!r.ok)return;const out=await r.json();const epoch=out?.enduser?.identity?.runtime_epoch||{};const key=JSON.stringify([out?.enduser?.audit?.cycle_id,out?.enduser?.audit?.conversation_last_sha256,out?.enduser?.identity?.fingerprint,out?.enduser?.audit?.status,epoch?.epoch_id,epoch?.model_id]);if(key===lastKey)return;lastKey=key;renderEnduser(out?.enduser);}catch(_){/* the primary controller owns transport diagnostics */}finally{refreshing=false;}}
function install(){ensureSurface();const active=$('active-panel');if(active)new MutationObserver(()=>{if(!active.hidden)refresh();}).observe(active,{attributes:true,attributeFilter:['hidden']});const log=$('conversation-log');if(log)new MutationObserver(()=>queueMicrotask(refresh)).observe(log,{childList:true,subtree:true,characterData:true});document.addEventListener('ikant:surface-snapshot',event=>renderSnapshot(event.detail));document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});timer=setInterval(refresh,5000);window.addEventListener('beforeunload',()=>clearInterval(timer));refresh();}
install();
})();