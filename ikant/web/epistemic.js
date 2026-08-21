'use strict';
(() => {
  const EPI_INDEX_SCHEMA='ikant-epistemic-index/v0.28-test';
  const EPI_WORKSPACE_SCHEMA='ikant-epistemic-workspace/v0.28-test';
  const epi={index:null,cycle:null,layout:'graph',loading:false};
  const el=id=>document.getElementById(id);
  function escapeHTML(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function bindingHeaders(){
    const f=state?.shell?.last_acked_frame;
    if(!state?.shell?.shell_id||!f)throw new Error('epistemic view requires an exact acknowledged frame');
    return {
      'X-iKant-Shell-Id':state.shell.shell_id,
      'X-iKant-Client-Id':clientId,
      'X-iKant-Frame-Session':f.runtime_session_id,
      'X-iKant-Frame-Epoch':String(f.epoch),
      'X-iKant-Frame-Seq':String(f.frame_seq),
      'X-iKant-Frame-SHA256':f.frame_sha256,
    };
  }
  async function epiApi(path){return api(path,{headers:bindingHeaders()});}
  function ensureUI(){
    const host=el('inspector-artifacts');if(!host||host.dataset.s10Ready==='true')return;
    host.dataset.s10Ready='true';
    host.innerHTML=`
      <div class="epi-head"><div><p class="inspector-copy">Surface B · read-only · exact ACK bound</p><strong id="epi-cycle-title">Reticolo epistemico</strong></div><div class="epi-layout"><button id="epi-graph" type="button" class="epi-tab active">Graph</button><button id="epi-list" type="button" class="epi-tab">List</button></div></div>
      <div id="epi-summary" class="epi-summary" aria-live="polite"></div>
      <div class="epi-history-wrap"><label for="epi-history">Ciclo</label><select id="epi-history" class="epi-select" aria-label="Seleziona ciclo Surface B"></select></div>
      <div id="epi-canvas" class="epi-canvas"><p class="inspector-copy">Apri Artefatti dopo un TURN confermato per esplorare Surface B.</p></div>
      <div id="epi-peek" class="epi-peek" hidden></div>
      <div class="epi-actions"><button id="epi-json" class="secondary" type="button" disabled>JSON</button><button id="epi-docx" class="secondary" type="button" disabled>DOCX</button><button id="epi-refresh" class="text-button" type="button">Aggiorna</button></div>
      <details class="disclosure"><summary>Binding e integrità</summary><pre id="epi-integrity"></pre></details>`;
    el('epi-graph').addEventListener('click',()=>setLayout('graph'));
    el('epi-list').addEventListener('click',()=>setLayout('list'));
    el('epi-history').addEventListener('change',e=>loadCycle(e.target.value));
    el('epi-refresh').addEventListener('click',()=>loadIndex(true));
    el('epi-json').addEventListener('click',()=>downloadArtifact('JSON'));
    el('epi-docx').addEventListener('click',()=>downloadArtifact('DOCX'));
  }
  function setLayout(layout){epi.layout=layout;el('epi-graph')?.classList.toggle('active',layout==='graph');el('epi-list')?.classList.toggle('active',layout==='list');renderCycle();}
  function renderIndex(){
    const select=el('epi-history');if(!select||!epi.index)return;
    select.replaceChildren();
    for(const row of epi.index.cycles||[]){const o=document.createElement('option');o.value=row.cycle_id;o.textContent=`${row.current?'● ':''}${row.cycle_id} · ${row.object_count} obj · ${row.conflict_count} conflict`;select.appendChild(o);}
    const target=epi.index.current_cycle_id||(epi.index.cycles?.[0]?.cycle_id||'');if(target){select.value=target;loadCycle(target);}else{el('epi-canvas').innerHTML='<p class="inspector-copy">Nessuna Surface B disponibile nella sessione corrente.</p>';}
  }
  async function loadIndex(force=false){
    ensureUI();if(epi.loading&&!force)return;epi.loading=true;el('epi-summary').textContent='Sincronizzazione Surface B…';
    try{const out=await epiApi('/api/v4/epistemic/index');if(out?.schema!==EPI_INDEX_SCHEMA)throw new Error('invalid epistemic index');epi.index=out;renderIndex();}
    catch(_e){epi.index=null;epi.cycle=null;el('epi-summary').textContent='Surface B non disponibile per il frame ACK corrente.';el('epi-canvas').innerHTML='<p class="inspector-copy">Completa o sincronizza un TURN, poi riprova. La vista epistemica non forza il runtime.</p>';}
    finally{epi.loading=false;}
  }
  async function loadCycle(cycle){
    if(!cycle)return;el('epi-summary').textContent='Caricamento proiezione…';
    try{const out=await epiApi('/api/v4/epistemic/cycle?cycle_id='+encodeURIComponent(cycle));if(out?.schema!==EPI_WORKSPACE_SCHEMA)throw new Error('invalid epistemic cycle');epi.cycle=out;renderCycle();}
    catch(_e){epi.cycle=null;el('epi-summary').textContent='Ciclo non disponibile con questo binding.';}
  }
  function summaryChips(c){
    const s=c.summary||{};return `<span>mode <b>${escapeHTML(s.regulative_mode||'—')}</b></span><span>objects <b>${(c.objects||[]).length}</b></span><span>debt <b>${escapeHTML(s.epistemic_debt_open_count??'—')}</b></span><span>collapse <b>${escapeHTML(s.mean_collapse??'—')}</b></span>`;
  }
  function renderCycle(){
    const c=epi.cycle,canvas=el('epi-canvas');if(!c||!canvas)return;
    el('epi-cycle-title').textContent=(c.current?'Current · ':'')+c.cycle_id;el('epi-summary').innerHTML=summaryChips(c);
    el('epi-integrity').textContent=JSON.stringify({frame_binding:c.frame_binding,snapshot_sha256:c.snapshot_sha256,intent_sha256:c.intent_sha256,read_only:c.read_only,presentation_is_not_evidence:c.presentation_is_not_evidence,presentation_is_not_authorization:c.presentation_is_not_authorization},null,2);
    el('epi-json').disabled=!c.artifacts?.json?.available;el('epi-docx').disabled=!c.artifacts?.docx?.available;
    if(epi.layout==='list')renderList(c,canvas);else renderGraph(c,canvas);
  }
  function renderGraph(c,canvas){
    const nodes=c.graph?.nodes||[];canvas.className='epi-canvas graph';canvas.replaceChildren();
    const stage=document.createElement('div');stage.className='epi-orbit-stage';
    nodes.forEach((n,i)=>{const b=document.createElement('button');b.type='button';b.className='epi-node';b.style.setProperty('--i',String(i));b.style.setProperty('--n',String(Math.max(1,nodes.length)));b.innerHTML=`<span>R${i}</span><small>${escapeHTML(n.label)}</small>`;b.addEventListener('click',()=>peek({kind:'ring',label:n.label,source:'reticulum',confidence:n.confidence,evidence:n.evidence,activation:n.activation}));stage.appendChild(b);});
    const core=document.createElement('div');core.className='epi-core';core.innerHTML='<strong>Surface B</strong><small>read model</small>';stage.appendChild(core);canvas.appendChild(stage);
    const strip=document.createElement('div');strip.className='epi-object-strip';for(const o of (c.objects||[]).slice(0,18)){const b=document.createElement('button');b.type='button';b.className='epi-object '+escapeHTML(o.kind);b.textContent=o.kind;b.title=o.label;b.addEventListener('click',()=>peek(o));strip.appendChild(b);}canvas.appendChild(strip);
  }
  function renderList(c,canvas){
    canvas.className='epi-canvas list';canvas.replaceChildren();const list=document.createElement('div');list.className='epi-list';
    for(const o of c.objects||[]){const b=document.createElement('button');b.type='button';b.className='epi-row';b.innerHTML=`<span class="epi-kind">${escapeHTML(o.kind)}</span><strong>${escapeHTML(o.label)}</strong><small>${escapeHTML(o.source||'derived')} · conf ${escapeHTML(o.confidence??'—')} · ev ${escapeHTML(o.evidence??'—')}</small>`;b.addEventListener('click',()=>peek(o));list.appendChild(b);}canvas.appendChild(list);
  }
  function peek(o){const p=el('epi-peek');if(!p)return;p.hidden=false;p.innerHTML=`<button type="button" aria-label="Chiudi">×</button><span>${escapeHTML(o.kind||'object')}</span><strong>${escapeHTML(o.label||'')}</strong><small>source ${escapeHTML(o.source||'—')} · confidence ${escapeHTML(o.confidence??'—')} · evidence ${escapeHTML(o.evidence??'—')}</small>`;p.querySelector('button').addEventListener('click',()=>{p.hidden=true;});}
  async function downloadArtifact(kind){
    const cycle=epi.cycle?.cycle_id;if(!cycle)return;
    try{const headers={...bindingHeaders()};if(state.token)headers.Authorization='Bearer '+state.token;const response=await fetch(`/api/v4/epistemic/artifact?cycle_id=${encodeURIComponent(cycle)}&kind=${encodeURIComponent(kind)}`,{headers,cache:'no-store'});if(!response.ok)throw new Error('artifact unavailable');const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=kind==='DOCX'?`Surface_B_${cycle}.docx`:`Surface_B_${cycle}.json`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(_e){el('epi-summary').textContent='Artifact non disponibile con il binding corrente.';}
  }
  document.addEventListener('click',event=>{const button=event.target.closest?.('.orbit-item[data-view="artifacts"]');if(button)setTimeout(()=>loadIndex(),0);});
  document.addEventListener('keydown',event=>{if(event.code==='Space'&&!event.metaKey&&!event.ctrlKey&&!event.altKey&&state?.view==='artifacts'&&epi.cycle){const active=document.activeElement?.closest?.('.epi-row,.epi-object,.epi-node');if(active){event.preventDefault();active.click();}}});
  ensureUI();
})();
