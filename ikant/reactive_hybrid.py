from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from copy import deepcopy
import hashlib,json,re,secrets,threading,time
from pathlib import Path
from typing import Any

SCHEMA='ikant-reactive-hybrid/v1-test'; WORK_SCHEMA='ikant-reactive-work-state/v1-test'; MAX_UNITS=24; MAX_EDGES=48; MAX_TARGETS=4; MAX_WORKS=64
_TOKEN=re.compile(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9_.'+-]{0,63}")
_SPLIT=re.compile(r"(?:\n\s*(?:[-*]|\d+[.)])\s+|(?<=[.!?;])\s+)")
_SECRET=re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|bearer\s+\S+|password\s*[:=]\s*\S+|api[_-]?key\s*[:=]\s*\S+|-----BEGIN )",re.I)
_PRIVATE=re.compile(r"(?:\b(?:mio|mia|miei|mie|my|mine|our|family|famiglia|salute|health|iban|salary|stipend\w*|religion\w*|politic\w*|partito|sindacat\w*|sexual\s+orientation|orientamento\s+sessuale|race|ethnic\w*|criminal\w*|biometric\w*)\b|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|(?:[A-Za-z]:\\|/home/|/Users/|/mnt/|~[/\\])\S+)",re.I)
_MATERIAL=re.compile(r"\b(?:compra|acquista|paga|invia|cancella|delete|purchase|send|execute|esegui)\w*",re.I)
_OPEN=re.compile(r"^\s*(?:apri|avvia|lancia|open|launch|start)\s+(.+?)\s*[.!]?\s*$",re.I)
_BAD_CMD=re.compile(r"(?:https?://|file://|[\\/]|--|\$\(|`|[<>|;]|\n|\r)",re.I)
_APPS={'firefox':'firefox','mozilla firefox':'firefox','chrome':'chrome','google chrome':'chrome','edge':'edge','microsoft edge':'edge','word':'word','microsoft word':'word','excel':'excel','microsoft excel':'excel','powerpoint':'powerpoint','microsoft powerpoint':'powerpoint','outlook':'outlook','microsoft outlook':'outlook','terminal':'terminal','terminale':'terminal','finder':'file_manager','esplora file':'file_manager','file explorer':'file_manager'}
_ABSTRACT=frozenset({'ANALYZE','COMPARE','SUMMARIZE','EXPLAIN','VERIFY'})
_OPS=(('COMPARE',re.compile(r'\b(?:confront|compar|versus|\bvs\b)',re.I)),('SUMMARIZE',re.compile(r'\b(?:riassum|sintetizz|summari[sz]|recap)',re.I)),('VERIFY',re.compile(r'\b(?:verific|controll|check|validat|test|stress)',re.I)),('EXPLAIN',re.compile(r'\b(?:spiega|descriv|explain|teach|chiarisc)',re.I)))
_MOMENTS={'ACCEPTED':('INTAKE','Ho preso in carico la richiesta.','Richiesta ricevuta dal runtime locale.'),'STRUCTURED':('ROUTING','Ho organizzato il lavoro necessario.','Il runtime ha costruito un percorso di lavoro tipizzato e limitato.'),'RUNNING':('BACKEND_WORK','Sto lavorando sui passaggi necessari.','Sono attive solo le route ammesse dal contratto del turno.'),'SEALED':('DELIVERY','La risposta è pronta; sto completando la consegna.','La superficie finale è stata prodotta e attende la consegna governata.'),'DELIVERED':('READY','Risposta consegnata.','La consegna governata del turno è terminata.'),'FAILED':('DEGRADED','Il lavoro si è fermato in modo controllato.','Il runtime ha chiuso il turno senza inventare avanzamento.')}
_RANK={'ACCEPTED':0,'STRUCTURED':1,'RUNNING':2,'SEALED':3,'DELIVERED':4}

def _sha(v:Any)->str:return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _op(t:str)->str:
 for name,rx in _OPS:
  if rx.search(t):return name
 return 'ANALYZE'
def _privacy(t:str)->str:
 if _SECRET.search(t):return 'P3_SECRET'
 if _PRIVATE.search(t):return 'P2_LOCAL_PRIVATE'
 return 'P1_DERIVED_EXPORTABLE'
def _capsule(t:str,op:str)->str:
 words=[]
 for x in _TOKEN.findall(t.casefold()):
  if len(x)>1 and not _SECRET.search(x) and '/' not in x and '\\' not in x and x not in words:words.append(x)
  if len(words)>=12:break
 return ('op='+op+'; keys='+','.join(words))[:240]

def compile_command(text:str)->dict[str,Any]|None:
 raw=str(text or '')
 if not raw.strip() or len(raw)>320 or _BAD_CMD.search(raw):return None
 m=_OPEN.fullmatch(raw)
 if not m:return None
 parts=[" ".join(x.casefold().split()) for x in re.split(r"\s*(?:,|\be\b|\band\b|\+|&)\s*",m.group(1)) if x.strip()]
 if not parts or len(parts)>MAX_TARGETS:return None
 targets=[]
 for p in parts:
  app=_APPS.get(p)
  if not app:return None
  if app not in targets:targets.append(app)
 out={'schema':'ikant-essential-command-plan/v1-test','verb':'OPEN_APP','targets':targets,'target_count':len(targets),'inference_required':False,'host_resolution_required':True,'requires_capabilities':['native.app.open'],'requires_s1_lease':True,'requires_fresh_host_revalidation':True,'execution_authority':0.0,'epistemic_authority':0.0}
 out['sha256']=_sha(out);return out

def build_graph(text:str)->dict[str,Any]:
 raw=str(text);cmd=compile_command(raw)
 if cmd:
  unit={'id':'u01-'+_sha(cmd)[:10],'operation':'OPEN_APP','privacy':'P1_DERIVED_EXPORTABLE','authority':'MATERIAL_REVIEW_REQUIRED','route':'DETERMINISTIC_COMMAND_MAP','capsule':'verb=OPEN_APP; targets='+','.join(cmd['targets']),'depends_on':[]}
  return {'schema':SCHEMA,'graph_id':'wg-'+_sha([raw,unit])[:24],'units':[unit],'edges':[],'command_plan':cmd,'truncated':False,'epistemic_authority':0.0,'execution_authority':0.0}
 all_parts=[" ".join(x.split()) for x in _SPLIT.split(raw) if x.strip()];parts=all_parts[:MAX_UNITS];units=[];edges=[]
 for i,p in enumerate(parts):
  op=_op(p);privacy=_privacy(p);material=bool(_MATERIAL.search(p));uid=f'u{i+1:02d}-'+_sha(p)[:10];deps=[]
  if i and re.search(r'\b(?:poi|dopo|then|after|next)\b',p,re.I) and len(edges)<MAX_EDGES:deps=[units[-1]['id']];edges.append([units[-1]['id'],uid])
  units.append({'id':uid,'operation':op,'privacy':privacy,'authority':'MATERIAL_REVIEW_REQUIRED' if material else 'PROPOSE_ONLY','route':'LOCAL_GOVERNED' if material or privacy in {'P2_LOCAL_PRIVATE','P3_SECRET'} else 'LOCAL_LLM_ELIGIBLE','capsule':_capsule(p,op),'depends_on':deps})
 return {'schema':SCHEMA,'graph_id':'wg-'+_sha([raw,units,edges])[:24],'units':units,'edges':edges,'command_plan':None,'truncated':len(all_parts)>MAX_UNITS,'epistemic_authority':0.0,'execution_authority':0.0}

def hybrid_membrane(graph:dict[str,Any],*,enabled:bool=False,opt_in:bool=False,provider:str|None=None)->dict[str,Any]:
 reasons=[];units=graph.get('units') or []
 if not enabled:reasons.append('disabled')
 if not opt_in:reasons.append('no_explicit_opt_in')
 if provider not in {'openai','anthropic','deepseek'}:reasons.append('provider_unavailable')
 if any(u.get('privacy') not in {'P0_PUBLIC','P1_DERIVED_EXPORTABLE'} for u in units):reasons.append('turn_private')
 if any(u.get('authority')!='PROPOSE_ONLY' for u in units):reasons.append('material_or_governed')
 if any(u.get('operation') not in _ABSTRACT for u in units):reasons.append('non_abstract_operation')
 allow=bool(units) and not reasons
 return {'schema':'ikant-hybrid-abstraction-membrane/v1-test','route':'HYBRID_ABSTRACT' if allow else 'LOCAL_ONLY','provider':provider if allow else None,'reasons':reasons,'whole_turn_quarantine':not allow,'raw_prompt_exportable':False,'transcript_exportable':False,'local_identifiers_exportable':False,'tool_calls_allowed':False,'remote_result_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}

@dataclass
class _Work: work_id:str;session:str;phase:str;created:float;cycle:str|None=None;facts:dict[str,Any]|None=None;terminal:bool=False
class WorkStore:
 def __init__(self,max_works:int=MAX_WORKS):self._lock=threading.RLock();self._by_session={};self._works={};self._order=deque();self._max=max(4,min(int(max_works),256))
 def _make_room(self):
  while len(self._works)>=self._max:
   victim=next((wid for wid in self._order if self._works.get(wid) and self._works[wid].terminal),None)
   if victim is None:raise RuntimeError('work-state capacity exhausted by active sessions')
   self._order.remove(victim);record=self._works.pop(victim)
   if self._by_session.get(record.session)==victim:self._by_session.pop(record.session,None)
 def begin(self,session:str,text:str)->tuple[str,dict[str,Any]]:
  # Compile before mutating the registry: a failed structuring pass must not orphan an active work item.
  g=build_graph(text)
  with self._lock:
   old=self._works.get(self._by_session.get(session,''))
   if old and not old.terminal:raise RuntimeError('one in-flight work item allowed per runtime session')
   self._make_room();wid='work-'+secrets.token_urlsafe(18)
   facts={'unit_count':len(g['units']),'command_count':int(bool(g['command_plan'])),'route':'COMMAND_COMPILED' if g['command_plan'] else 'LOCAL_RETICULAR'}
   # ACCEPTED -> STRUCTURED -> RUNNING is an atomic intake transaction from the external observer's perspective.
   w=_Work(wid,session,'RUNNING',time.monotonic(),facts=facts);self._works[wid]=w;self._by_session[session]=wid;self._order.append(wid)
  return wid,g
 def active(self,session:str)->bool:
  with self._lock:
   w=self._works.get(self._by_session.get(session,''));return bool(w and not w.terminal)
 def bind_cycle(self,wid:str,cycle:str)->None:
  with self._lock:
   w=self._works[wid]
   if w.cycle and w.cycle!=cycle:raise RuntimeError('cycle binding immutable')
   w.cycle=cycle
 def seal_from_canonical(self,wid:str,cycle:str|None=None)->None:
  """Mirror an already-materialized canonical frame without being able to invalidate it."""
  with self._lock:
   w=self._works[wid]
   if w.terminal:return
   if w.phase not in {'RUNNING','SEALED'}:raise RuntimeError('canonical frame cannot seal work from current phase')
   c=str(cycle or '')
   if c:
    if w.cycle and w.cycle!=c:w.facts['projection_degraded']='cycle_binding_drift'
    else:w.cycle=c
   w.phase='SEALED'
 def advance(self,wid:str,phase:str,**facts:Any)->None:
  with self._lock:
   w=self._works[wid]
   if w.terminal:raise RuntimeError('terminal work cannot advance')
   if phase not in _RANK or _RANK[phase]<_RANK.get(w.phase,-1) or _RANK[phase]>_RANK.get(w.phase,-1)+1:raise RuntimeError('invalid work phase transition')
   w.phase=phase;w.facts.update({k:v for k,v in facts.items() if k in {'unit_count','command_count','route','provider','projection_degraded'}});w.terminal=phase=='DELIVERED'
 def fail(self,wid:str)->None:
  with self._lock:w=self._works[wid];w.phase='FAILED';w.terminal=True
 def deliver_current(self,session:str)->None:
  with self._lock:
   w=self._works.get(self._by_session.get(session,''));wid=w.work_id if w and w.phase=='SEALED' and not w.terminal else None
  if wid:self.advance(wid,'DELIVERED')
 def projection(self,session:str)->dict[str,Any]:
  with self._lock:w=self._works.get(self._by_session.get(session,''));w=deepcopy(w) if w else None
  if not w:return {'schema':WORK_SCHEMA,'phase':'IDLE','moment':'READY','active':False,'terminal':True,'message':'','detail':'','facts':{},'progress_fraction':None,'identifiers_exposed':False,'private_chain_of_thought':False,'epistemic_authority':0.0,'execution_authority':0.0}
  moment,msg,detail=_MOMENTS.get(w.phase,('BACKEND_WORK','Sto lavorando.','Stato runtime disponibile.'))
  return {'schema':WORK_SCHEMA,'phase':w.phase,'moment':moment,'active':not w.terminal,'terminal':w.terminal,'message':msg,'detail':detail,'facts':w.facts or {},'cycle_bound':bool(w.cycle),'elapsed_ms':round((time.monotonic()-w.created)*1000,3),'progress_fraction':None,'identifiers_exposed':False,'private_chain_of_thought':False,'raw_prompt_exposed':False,'presentation_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}

_REGISTRY_LOCK=threading.RLock();_REGISTRY={}
def store_for_root(root:str|Path)->WorkStore:
 key=str(Path(root).resolve())
 with _REGISTRY_LOCK:
  if key not in _REGISTRY:_REGISTRY[key]=WorkStore()
  return _REGISTRY[key]
def active_session(root:str|Path)->str:
 value=json.loads((Path(root).resolve()/'.ikant'/'runtime.json').read_text(encoding='utf-8'));session=str(value.get('session_id') or '') if isinstance(value,dict) and value.get('status')=='ACTIVE' else ''
 if not session:raise RuntimeError('ACTIVE runtime session required')
 return session