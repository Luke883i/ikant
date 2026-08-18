from __future__ import annotations
import hashlib,json,secrets
from collections import Counter
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
from .admission import load_probe,load_receipt,validate_receipt
from .dynamics import DEFAULT_DYNAMICS,DynamicsParameters,decay,recur,retrieve,feedback,homeostasis,salience
from .model import *
from .oracle import KantOracle,PRINCIPLES
from .store import atomic_json_write,append_jsonl,read_json,acquire_writer_lock

def now():return datetime.now(timezone.utc).isoformat()
def toks(s):return {x for x in ''.join(c if c.isalnum() else ' ' for c in s.casefold()).split() if len(x)>2}
def avg(xs):return sum(xs)/len(xs) if xs else 0.
class Runtime:
 def __init__(self,sdir,*,durable=True,params=None,_lock=None):
  self.state_dir=Path(sdir);self.root=self.state_dir.parent;self.durable=durable;self.lock=_lock or (acquire_writer_lock(self.root/'.ikant.writer.lock') if durable else None);self.runtime_path=self.state_dir/'runtime.json';self.graph_path=self.state_dir/'graph.json';self.events_path=self.state_dir/'events.jsonl';self.cycles_dir=self.state_dir/'cycles';self.derived_archive_path=self.state_dir/'derived_archive.jsonl';self.derived_archive_mem=[];self.runtime=read_json(self.runtime_path);stored=self.runtime.get('dynamics',{}).get('parameters');self.params=DynamicsParameters(**stored) if stored else (params or DEFAULT_DYNAMICS);self.params.validate()
  if params and stored and asdict(params)!=stored:self.close();raise ValueError('runtime dynamics parameter mismatch')
  self.graph=read_json(self.graph_path,{'nodes':{},'relations':{},'seq':0});self.nodes={k:node_from_dict(v) for k,v in self.graph['nodes'].items()};self.relations={k:relation_from_dict(v) for k,v in self.graph['relations'].items()};self.incoming={};self.tokens={k:toks(n.text) for k,n in self.nodes.items()};self.events_mem=[];self.cycles={}
  for rid,r in self.relations.items():self.incoming.setdefault(r.target,[]).append(rid)
  if durable and self.runtime.get('status')=='ACTIVE':
   try:self.integrity(raise_on_error=True)
   except Exception:
    self.close();raise
 @classmethod
 def initialize(cls,sdir,contract_text,*,durable=True,params=DEFAULT_DYNAMICS):
  sdir=Path(sdir);lock=acquire_writer_lock(sdir.parent/'.ikant.writer.lock') if durable else None
  try:
   receipt=load_receipt(sdir);ok,errs=validate_receipt(receipt,contract_text)
   if not ok:raise PermissionError('; '.join(errs))
   p=load_probe(sdir)
   if not p or p.get('overall')!='READY' or p.get('consumed'):raise PermissionError('fresh successful probe required')
   p['consumed']=True;atomic_json_write(sdir/'probe.json',p);state={'schema':'ikant-runtime/v0.1','session_id':'SES-'+secrets.token_hex(8),'status':'INITIALIZING','contract_sha256':receipt['contract_sha256'],'admission_receipt_id':receipt['receipt_id'],'probe_id':p['probe_id'],'cycle_count':0,'feedback_count':0,'calibration':{'n':0,'brier_sum':0.,'brier_mean':0.},'compression':{'count':0,'last_seq':0,'metrics':{'novelty_rate':0.,'revision_pressure':0.},'trend':{'samples':0,'metrics':{'novelty_rate':0.,'revision_pressure':0.}}},'dynamics':{'parameters':asdict(params),'biological_constants':False}};atomic_json_write(sdir/'runtime.json',state);rt=cls(sdir,durable=durable,params=params,_lock=lock);rt._event('INITIALIZE',state['session_id'],{})
   for pr in PRINCIPLES:
    text=f'{pr.name}: {pr.test}';n=Node(content_id(NodeKind.PRINCIPLE,Layer.KANT_ORACLE,text),NodeKind.PRINCIPLE,Layer.KANT_ORACLE,text,1,1,'repository',metadata={'principle_id':pr.id,'synthetic_archetype':True});rt._save(n);rt._event('ASSERT',n.id,{'kernel_seed':True})
   rt.runtime['status']='ACTIVE';rt._write_runtime();rt._event('INITIALIZE_COMPLETE',state['session_id'],{});return rt
  except Exception:
   if lock:lock.release()
   raise
 def close(self):
  if self.lock:self.lock.release();self.lock=None
 def require_active(self):
  if self.runtime.get('status')!='ACTIVE':raise PermissionError('runtime not ACTIVE')
 def _write_runtime(self):
  if self.durable:atomic_json_write(self.runtime_path,self.runtime)
 def _persist(self):
  if self.durable:atomic_json_write(self.graph_path,self.graph)
 def _save(self,n):self.nodes[n.id]=n;self.tokens[n.id]=toks(n.text);self.graph['nodes'][n.id]=node_to_dict(n)
 def _event(self,op,subject,payload):
  self.graph['seq']+=1;e={'seq':self.graph['seq'],'at':now(),'op':op,'subject':subject,'payload':payload};self.events_mem.append(e)
  if self.durable:append_jsonl(self.events_path,e)
  self._persist();return e['seq']
 def ingest(self,*,kind,layer,text,confidence,evidence,source_mode,metadata=None):
  self.require_active();nid=content_id(kind,layer,text)
  if nid in self.nodes:
   n=self.nodes[nid]
   if not n.active:raise PermissionError('explicit reinstatement required')
   n.recurrence+=1;recur(n,self.params);self._save(n);self._event('RECUR',nid,{});return n
  n=Node(nid,kind,layer,' '.join(text.split()),clamp01(confidence),clamp01(evidence),source_mode,metadata=metadata or {});self._save(n);self._event('ASSERT',nid,{'source_mode':source_mode});return n
 def corroborate(self,nid,*,provenance_key,strength,source_mode):
  if source_mode not in {'user','repository','document','live'}:raise PermissionError('external source required')
  n=self.nodes[nid]
  if not n.active:raise PermissionError('retracted node')
  seen=set(n.metadata.get('corroboration_keys',[]))
  if provenance_key not in seen:n.evidence=clamp01(n.evidence+self.params.corroboration_gain*clamp01(strength)*(1-n.evidence));seen.add(provenance_key);n.metadata['corroboration_keys']=sorted(seen);self._save(n);self._event('CORROBORATE',nid,{'provenance_key':provenance_key})
  return n
 def modulate_node(self,nid,*,source_mode,**kw):
  if source_mode not in {'user','repository','document','live'}:raise PermissionError('external source required')
  n=self.nodes[nid];d=asdict(n.modulators);d.update({k:v for k,v in kw.items() if v is not None});m=Modulators(**d);m.validate();n.modulators=m;self._save(n);self._event('MODULATE',nid,asdict(m));return n
 def relate(self,s,t,kind,weight):
  if s not in self.nodes or t not in self.nodes:raise KeyError('endpoint')
  if s==t:raise ValueError('self relation')
  rid=relation_id(s,t,kind);r=Relation(rid,s,t,kind,clamp01(weight));new=rid not in self.relations;self.relations[rid]=r;self.graph['relations'][rid]=relation_to_dict(r)
  if new:self.incoming.setdefault(t,[]).append(rid)
  self._event('RELATE',rid,{});return r
 def retract_node(self,nid,*,reason):
  n=self.nodes[nid]
  if n.kind==NodeKind.PRINCIPLE and n.layer==Layer.KANT_ORACLE:raise PermissionError('kernel immutable')
  n.active=False;n.activation=0;self._save(n);self._event('RETRACT',nid,{'reason':reason});return n
 def reinstate_node(self,nid,*,reason,source_mode):
  if source_mode not in {'user','repository','document','live'}:raise PermissionError('external source required')
  n=self.nodes[nid];n.active=True;n.activation=min(n.activation_ceiling,.12);n.novelty=max(.35,n.novelty);self._save(n);self._event('REINSTATE',nid,{'reason':reason});return n
 def _strength(self,nid):
  n=self.nodes.get(nid);return 0 if not n or not n.active else min(n.ceiling,n.confidence*n.evidence)
 def score(self,nid):
  n=self.nodes[nid]
  if not n.active:return 0.
  x=n.confidence*n.evidence
  for rid in self.incoming.get(nid,[]):
   r=self.relations[rid];v=r.weight*self._strength(r.source);x+=(0.0 if r.kind==RelationKind.PRECEDES else (-.2 if r.kind in {RelationKind.CONTRADICTS,RelationKind.INHIBITS,RelationKind.FALSIFIES} else .15))*v
  return min(n.ceiling,clamp01(x))
 def slice(self,intent,*,limit=12):
  q=toks(intent);rows=[]
  for n in self.nodes.values():
   if n.active:
    epi=self.score(n.id);ov=len(q&self.tokens[n.id]);rows.append((salience(n,epi,ov,self.params),epi,n,ov))
  rows.sort(key=lambda x:(-x[0],-x[1],x[2].id));chosen=[];dc=ic=kc=0
  for x in rows:
   if len(chosen)>=limit:break
   n=x[2];d=n.source_mode=='runtime_derived';i=n.layer in {Layer.PSYCHODYNAMIC_HYPOTHESIS,Layer.ARCHETYPAL_HYPOTHESIS};k=n.kind==NodeKind.PRINCIPLE
   if d and dc>=max(1,int(limit*.25)):continue
   if i and ic>=max(1,int(limit*.25)):continue
   if k and kc>=1:continue
   chosen.append(x);dc+=d;ic+=i;kc+=k
  directives=[]
  for sa,epi,n,ov in chosen:
   if n.source_mode in {'user','repository'} and n.kind in {NodeKind.GOAL,NodeKind.CONSTRAINT}:
    st=.78*epi+.22*sa
    if st>=.3:directives.append({'type':n.kind.value,'text':n.text,'strength':round(st,4),'source_mode':n.source_mode})
  return {'schema':'ikant-semantic-slice/v0.1','intent_sha256':hashlib.sha256(intent.encode()).hexdigest(),'nodes':[{'id':n.id,'kind':n.kind.value,'layer':n.layer.value,'score':round(sa,4),'epistemic_score':round(epi,4),'activation':round(n.activation,4),'stability':round(n.stability,4),'novelty':round(n.novelty,4),'prediction_error':round(n.prediction_error,4),'modulators':asdict(n.modulators),'lexical_overlap':ov,'text':n.text,'source_mode':n.source_mode} for sa,epi,n,ov in chosen],'directives':directives}
 def _conflicts(self,ids):return [{'source':r.source,'target':r.target,'kind':r.kind.value} for r in self.relations.values() if r.active and r.kind in {RelationKind.CONTRADICTS,RelationKind.FALSIFIES} and r.source in ids and r.target in ids and self._strength(r.source)>0]
 def concentric_cycle(self,intent,*,limit=12):
  idx=self.runtime['cycle_count']+1
  for n in self.nodes.values():
   if n.active:decay(n,self.params);self._save(n)
  pre=self.slice(intent,limit=limit)
  for r in pre['nodes']:
   retrieve(self.nodes[r['id']],clamp01(.45*r['score']+.55*min(1,r['lexical_overlap']/3)),idx,self.params);self._save(self.nodes[r['id']])
  hs=homeostasis(self.nodes.values(),self.params);[self._save(n) for n in self.nodes.values()];sem=self.slice(intent,limit=limit);sel=[self.nodes[r['id']] for r in sem['nodes']];ids={n.id for n in sel};pairs=self._conflicts(ids);unc=1-avg([r['epistemic_score'] for r in sem['nodes']]);interp=avg([1 if n.layer in {Layer.PSYCHODYNAMIC_HYPOTHESIS,Layer.ARCHETYPAL_HYPOTHESIS} else 0 for n in sel]);impact=any(n.kind==NodeKind.ACTION and (n.modulators.social_relevance>=.5 or n.modulators.agency_relevance>=.5) and not n.metadata.get('human_impact_assessed') for n in sel);oracle=KantOracle().evaluate({'uncertainty':unc,'conflict_count':len(pairs),'interpretive_dependency':interp,'authorized_directives':len(sem['directives']),'human_impact_unknown':impact,'calibration_error':self.runtime['calibration']['brier_mean'],'mean_prediction_error':avg([n.prediction_error for n in sel]),'grounding_ratio':avg([1 if n.source_mode in {'user','repository','document','live'} else 0 for n in sel]),'self_continuity':avg([n.stability for n in sel if n.layer==Layer.REFLECTIVE_SELF])});trend=self.runtime['compression']['trend']['metrics'];caution=clamp01(.4*unc+.2*min(1,len(pairs)/2)+.15*interp+.1*self.runtime['calibration']['brier_mean']+.1*avg([n.prediction_error for n in sel])+.05*trend.get('revision_pressure',0));blocked=any(f['status']=='BLOCK' for f in oracle['findings']);policy={'schema':'ikant-output-policy/v0.1','mode':'ABSTAIN_OR_HUMAN_REVIEW' if blocked else ('VERIFY_AND_RESOLVE' if pairs or caution>=.62 else 'CONVERGE'),'epistemic_caution':round(caution,4),'claim_threshold':round(.42+.38*caution,4),'max_interpretive_share':round(max(.05,.22*(1-caution)),4),'surface_conflicts':bool(pairs),'prefer_verification':caution>=.5,'material_action':'BLOCK' if blocked else 'PROPOSE_ONLY','history_modulation':{'trend_revision_pressure':trend.get('revision_pressure',0),'derived_history_is_not_external_evidence':True}};thr=policy['claim_threshold'];derived=[r for r in sem['nodes'] if r['source_mode']=='runtime_derived'];inter=[r for r in sem['nodes'] if r['layer'] in {Layer.PSYCHODYNAMIC_HYPOTHESIS.value,Layer.ARCHETYPAL_HYPOTHESIS.value}];assertable=[r for r in sem['nodes'] if r not in derived+inter and r['epistemic_score']>=thr];proj={'assertable_node_ids':[r['id'] for r in assertable],'tentative_node_ids':[r['id'] for r in sem['nodes'] if r not in derived+inter+assertable],'derived_context_node_ids':[r['id'] for r in derived],'interpretive_hypothesis_node_ids':[r['id'] for r in inter],'authorized_directives':sem['directives'],'must_surface_conflicts':pairs,'render_constraints':{'never_present_derived_context_as_external_evidence':True}};caps=[1,.82,.66,.52,.4,.3,.22,.15,.1];trace=[{'layer':l.value,'capacity':caps[i],'observables':{'selected_count':len(sel),'uncertainty':round(unc,4),'conflicts':len(pairs),'homeostatic_scale':round(hs,4)},'outputs':[n.id for n in sel if n.layer==l][:8],'falsifier':'Higher abstraction never creates factual evidence.'} for i,l in enumerate(CONCENTRIC_ORDER)];cid='CYC-'+hashlib.sha256(f'{self.runtime["session_id"]}|{sem["intent_sha256"]}|{idx}'.encode()).hexdigest()[:16];result={'schema':'ikant-concentric-cycle/v0.1','cycle_id':cid,'semantic_slice':sem,'epistemic_trace':trace,'kant_oracle':oracle,'output_policy':policy,'output_projection':proj,'oracle_retroaction':{'evidence_modified':False},'model_boundary':{'is_brain_simulation':False,'is_private_chain_of_thought':False,'freud_jung_are_hypothesis_namespaces':True,'kant_archetype_is_synthetic_regulative_kernel':True}};self.cycles[cid]=result
  if self.durable:self.cycles_dir.mkdir(parents=True,exist_ok=True);atomic_json_write(self.cycles_dir/f'{cid}.json',result)
  self._event('CYCLE',cid,{'selected_ids':[n.id for n in sel]});self.runtime['cycle_count']=idx;self._write_runtime()
  if idx%self.params.compression_interval_cycles==0:self.compress_history()
  return result
 def _cycle(self,cid):
  if cid in self.cycles:return self.cycles[cid]
  return read_json(self.cycles_dir/f'{cid}.json')
 def record_feedback(self,cid,*,outcome,prediction_error,target_node_ids=None,observed_effect=None,source_mode='user'):
  vals={'success':1.,'partial':.25,'unknown':0.,'failure':-1.,'corrected':-1.};c=self._cycle(cid);targets=target_node_ids or [r['id'] for r in c['semantic_slice']['nodes']];err=clamp01(prediction_error)
  for nid in targets:
   if nid in self.nodes and self.nodes[nid].active:feedback(self.nodes[nid],err,vals[outcome],self.params);self._save(self.nodes[nid])
  if observed_effect:
   obs=self.ingest(kind=NodeKind.OBSERVATION,layer=Layer.SIGNAL,text=observed_effect,confidence=.8,evidence=.7,source_mode=source_mode)
   if vals[outcome]<0:
    for nid in targets:
     if nid in self.nodes and self.nodes[nid].kind in {NodeKind.CLAIM,NodeKind.PREDICTION}:self.relate(obs.id,nid,RelationKind.CONTRADICTS,err or .25)
  self.runtime['feedback_count']+=1;self._event('FEEDBACK',cid,{'outcome':outcome});return {'cycle_id':cid,'outcome':outcome}
 def _compression_events_since(self,last):
  rows=[]
  if self.durable and self.events_path.exists():
   for line in self.events_path.read_text(encoding='utf-8').splitlines():
    if not line.strip():continue
    try:e=json.loads(line)
    except json.JSONDecodeError:continue
    if int(e.get('seq',0))>last:rows.append(e)
  rows.extend(e for e in self.events_mem if int(e.get('seq',0))>last)
  by={int(e.get('seq',0)):e for e in rows if int(e.get('seq',0))>0}
  return [by[k] for k in sorted(by)]
 def _upsert_derived_pattern(self,text,metadata):
  nid=content_id(NodeKind.PATTERN,Layer.METACOGNITION,text);n=self.nodes.get(nid)
  if n:
   if not n.metadata.get('compression_owned'):raise RuntimeError('derived pattern id collides with non-compression node')
   if not n.active:
    n.active=True;n.activation=min(n.activation_ceiling,.12);n.novelty=max(.35,n.novelty);op='DERIVED_REINSTATE'
   else:
    n.recurrence+=1;recur(n,self.params);op='DERIVED_RECUR'
   n.metadata.update(metadata);n.metadata['pattern_misses']=0;self._save(n);self._event(op,n.id,{'motif':metadata.get('motif')});return n
  n=Node(nid,NodeKind.PATTERN,Layer.METACOGNITION,text,.58,.18,'runtime_derived',metadata={**metadata,'compression_owned':True,'derivation_kind':'pattern','not_external_evidence':True,'pattern_misses':0});self._save(n);self._event('DERIVED_ASSERT',n.id,{'motif':metadata.get('motif')});return n
 def _archive_derived(self,n,reason):
  record={'at':now(),'reason':reason,'node':node_to_dict(n),'archived_at_seq':self.graph.get('seq',0)};self.derived_archive_mem.append(record)
  if self.durable:append_jsonl(self.derived_archive_path,record)
  for rid,r in list(self.relations.items()):
   if r.source==n.id or r.target==n.id:
    self.relations.pop(rid,None);self.graph['relations'].pop(rid,None)
    if r.target in self.incoming:self.incoming[r.target]=[x for x in self.incoming[r.target] if x!=rid]
  self.nodes.pop(n.id,None);self.tokens.pop(n.id,None);self.graph['nodes'].pop(n.id,None);self._event('DERIVED_ARCHIVE',n.id,{'reason':reason})
 def _maintain_derived_memory(self,observed_pattern_ids):
  for n in list(self.nodes.values()):
   if not n.metadata.get('compression_owned') or n.metadata.get('derivation_kind')!='pattern' or not n.active:continue
   if n.id in observed_pattern_ids:continue
   misses=int(n.metadata.get('pattern_misses',0))+1;n.metadata['pattern_misses']=misses
   if misses>=self.params.pattern_miss_retract_threshold:
    n.active=False;n.activation=0.;n.metadata['retired_reason']='pattern_not_reobserved';self._save(n);self._event('DERIVED_RETIRE',n.id,{'misses':misses})
   else:self._save(n)
  active_summaries=sorted([n for n in self.nodes.values() if n.active and n.metadata.get('compression_owned') and n.metadata.get('derivation_kind')=='summary'],key=lambda n:int(n.metadata.get('covered_seq',[0,0])[-1]))
  while len(active_summaries)>self.params.max_active_summaries:
   n=active_summaries.pop(0);n.active=False;n.activation=0.;n.metadata['retired_reason']='summary_working_set_limit';self._save(n);self._event('DERIVED_RETIRE',n.id,{'reason':'summary_working_set_limit'})
  inactive=sorted([n for n in self.nodes.values() if not n.active and n.metadata.get('compression_owned')],key=lambda n:(int(n.metadata.get('covered_seq',[0,0])[-1]) if n.metadata.get('covered_seq') else int(n.metadata.get('last_seen_seq',0)),n.id))
  while len(inactive)>self.params.max_inactive_derived_nodes:
   self._archive_derived(inactive.pop(0),'inactive_derived_working_set_limit')
  self._persist()
 def compress_history(self):
  last=int(self.runtime['compression']['last_seq']);raw=self._compression_events_since(last)
  if not raw:return None
  raw=raw[:self.params.compression_event_window];cursor_end=int(raw[-1]['seq'])
  ev=[e for e in raw if e.get('op')!='COMPRESS' and not str(e.get('op','')).startswith('DERIVED_') and not (e.get('op')=='ASSERT' and e.get('payload',{}).get('source_mode')=='runtime_derived')]
  self.runtime['compression']['last_seq']=cursor_end
  if not ev:
   self._write_runtime();return {'status':'NO_ANALYTIC_EVENTS','covered_seq':[int(raw[0]['seq']),cursor_end]}
  ops=Counter(e['op'] for e in ev);rev=ops['RETRACT']+sum(1 for e in ev if e['op']=='FEEDBACK' and e.get('payload',{}).get('outcome') in {'failure','corrected'});novelty=ops['ASSERT']/max(1,ops['ASSERT']+ops['RECUR']);revision=clamp01(rev/max(1,len(ev)//8));osc=clamp01((ops['RETRACT']+ops['REINSTATE'])/max(1,len(ev)//10));metrics={'novelty_rate':novelty,'revision_pressure':revision,'oscillation_pressure':osc}
  motifs=[]
  if novelty>=.62:motifs.append('exploratory_expansion')
  if ops['RECUR']>=max(4,ops['ASSERT']):motifs.append('echo_recurrence')
  if revision>=.45:motifs.append('revision_loop')
  if osc>=.45:motifs.append('state_oscillation')
  if ops['CYCLE']>=3 and revision<.2 and novelty<.55:motifs.append('convergent_processing')
  metrics['emergent_motif_pressure']=clamp01(len(motifs)/3)
  prior=self.runtime['compression']['trend']['metrics'];a=self.params.compression_trend_alpha;trend={k:clamp01(a*v+(1-a)*prior.get(k,0)) for k,v in metrics.items()};start,end=int(ev[0]['seq']),int(ev[-1]['seq'])
  summary=self.ingest(kind=NodeKind.SUMMARY,layer=Layer.MEMORY,text=f'Runtime compression {start}-{end}: '+','.join(f'{k}={v}' for k,v in sorted(ops.items())),confidence=.72,evidence=.20,source_mode='runtime_derived',metadata={'covered_seq':[start,end],'compression_owned':True,'derivation_kind':'summary','not_external_evidence':True})
  observed=set()
  for motif in motifs:
   pattern=self._upsert_derived_pattern(f'Runtime process motif: {motif}',{'motif':motif,'last_seen_seq':end,'covered_seq':[start,end]});observed.add(pattern.id)
  self.runtime['compression']['count']+=1;self.runtime['compression']['metrics']=metrics;self.runtime['compression']['trend']={'samples':self.runtime['compression']['trend']['samples']+1,'metrics':trend};self.runtime['compression']['last_motifs']=motifs;self._write_runtime();self._event('COMPRESS',f'CMP-{start}-{cursor_end}',{'analytic_seq':[start,end],'cursor_end':cursor_end,'motifs':motifs});self._maintain_derived_memory(observed);return {'summary_node_id':summary.id,'pattern_node_ids':sorted(observed),'metrics':metrics,'trend':trend,'motifs':motifs,'covered_seq':[start,cursor_end]}
 def integrity(self,*,raise_on_error=False):
  errs=[];receipt=load_receipt(self.state_dir);probe=load_probe(self.state_dir)
  if self.runtime.get('status')!='ACTIVE':errs.append('runtime not ACTIVE')
  contract_path=self.root/'IKANT_ACCESS_CONTRACT.md'
  if contract_path.exists():
   ok,receipt_errors=validate_receipt(receipt,contract_path.read_text(encoding='utf-8'))
   if not ok:errs.extend('admission '+x for x in receipt_errors)
  if receipt.get('receipt_id')!=self.runtime.get('admission_receipt_id'):errs.append('receipt binding')
  if probe.get('probe_id')!=self.runtime.get('probe_id') or not probe.get('consumed'):errs.append('probe binding')
  expected={p.id for p in PRINCIPLES};actual={n.metadata.get('principle_id') for n in self.nodes.values() if n.active and n.kind==NodeKind.PRINCIPLE}
  if actual!=expected:errs.append('Kant kernel')
  for r in self.relations.values():
   if r.source not in self.nodes or r.target not in self.nodes:errs.append('relation endpoint missing');break
  if self.durable:
   seqs=[]
   try:
    if self.events_path.exists():
     for line in self.events_path.read_text(encoding='utf-8').splitlines():
      if line.strip():seqs.append(int(json.loads(line)['seq']))
   except (ValueError,KeyError,json.JSONDecodeError):errs.append('event log malformed')
   if seqs:
    if seqs!=list(range(1,len(seqs)+1)):errs.append('event sequence non-contiguous')
    if seqs[-1]!=self.graph.get('seq'):errs.append('event/graph sequence mismatch')
   elif self.graph.get('seq',0)!=0:errs.append('event log missing')
  out={'schema':'ikant-integrity/v0.1','ok':not errs,'errors':list(dict.fromkeys(errs)),'graph_seq':self.graph['seq'],'node_count':len(self.nodes),'relation_count':len(self.relations)}
  if errs and raise_on_error:raise RuntimeError(';'.join(out['errors']))
  return out
 def status(self):
  xs=[n for n in self.nodes.values() if n.active];return {**self.runtime,'node_count':len(self.nodes),'active_node_count':len(xs),'relation_count':len(self.relations),'event_seq':self.graph['seq'],'mean_activation':round(avg([n.activation for n in xs]),6),'concentric_layers':[x.value for x in CONCENTRIC_ORDER]}
