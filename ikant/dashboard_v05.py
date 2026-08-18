from __future__ import annotations
import json
import textwrap
from pathlib import Path
from typing import Any
from .dashboard import project_dashboard as project_dashboard_v04
from .incarnate import bind_dashboard
from .psyche import validate_functional_psyche
DASHBOARD_SCHEMA='ikant-humanistic-dashboard/v0.7-test'
def _pct(value:Any)->str:
 try:return f'{round(float(value)*100):d}%'
 except (TypeError,ValueError):return 'n/a'
def _signed(value:Any)->str:
 try:return f'{float(value):+.2f}'
 except (TypeError,ValueError):return 'n/a'
def _legacy_value(base:dict,key:str,default='n/a'):
 for row in base.get('kpis',[]):
  if row.get('key')==key:return row.get('display',default)
 return default
def project_dashboard(runtime:Any,*,backlog_paths=None,surface_a_text=None,cycle_id=None,surface_a_validated=False)->dict[str,Any]:
 base=project_dashboard_v04(runtime,backlog_paths=backlog_paths);state=runtime.runtime if isinstance(runtime.runtime,dict) else {};psyche=(state.get('cognitive') or {}).get('psyche') or {};ok,errors=(validate_functional_psyche(psyche) if psyche else (False,['psyche_missing']))
 if not ok:
  base.setdefault('warnings',[]).extend('psyche:'+x for x in errors);out={**base,'schema':DASHBOARD_SCHEMA,'psyche_available':False,'humanistic':{'io_pensante':'SELF_MODEL_PENDING'},'contract':{**base.get('contract',{}),'operational_self_projection':True,'felt_emotion_claim':False,'brain_one_to_one_claim':False}}
  return bind_dashboard(runtime,out,surface_a_text=surface_a_text,cycle_id=cycle_id,surface_a_validated=surface_a_validated)
 affect=psyche['affective_field'];acc=psyche['epistemic_accumulation'];ledger=psyche['collapse_emergence'];selfk=psyche['self_knowledge'];fac=psyche['faculties'];central_mode=selfk.get('central_mode') or base.get('central_mode');humanistic={'io_pensante':{'identity':selfk.get('identity'),'mode':central_mode,'self_model_confidence':selfk.get('self_model_confidence'),'runtime_status':selfk.get('runtime_status'),'engine':selfk.get('execution_engine')},'tono_interno':{'label':affect.get('label'),'valence':affect.get('valence'),'arousal':affect.get('arousal'),'tension':affect.get('tension'),'curiosity':affect.get('curiosity'),'control':affect.get('control'),'synthesis_trust':affect.get('synthesis_trust'),'felt_emotion_claim':False},'memoria':{'turns':acc.get('turns'),'maturity_mode':acc.get('maturity_mode'),'experience_depth':acc.get('experience_depth'),'adaptive_stability':acc.get('adaptive_stability'),'plasticity_budget':acc.get('plasticity_budget')},'sguardo_riflessivo':{'control':fac['reflective_monitor'].get('control'),'tension':fac['reflective_monitor'].get('tension'),'revision_trace':(acc.get('traces') or {}).get('revision'),'uncertainty_trace':(acc.get('traces') or {}).get('uncertainty'),'epistemic_debt_trace':(acc.get('traces') or {}).get('epistemic_debt')},'campo_implicito':{'tension':fac['implicit_tension'].get('tension'),'authority':'interpretive_only','retractable':True},'reticolo':{'mean_collapse':(ledger.get('summary') or {}).get('mean_collapse'),'max_collapse':(ledger.get('summary') or {}).get('max_collapse'),'high_collapse_count':(ledger.get('summary') or {}).get('high_collapse_count'),'emergence_event_count':(ledger.get('summary') or {}).get('emergence_event_count'),'irreducibility_proxy':(ledger.get('summary') or {}).get('reticular_irreducibility_proxy')},'limiti':list(selfk.get('known_limits') or [])};base['schema']=DASHBOARD_SCHEMA;base['psyche_available']=True;base['central_mode']=central_mode;base['humanistic']=humanistic;base['contract']={**base.get('contract',{}),'operational_self_projection':True,'functional_affect_only':True,'felt_emotion_claim':False,'brain_one_to_one_claim':False,'psyche_may_modify_evidence':False};return bind_dashboard(runtime,base,surface_a_text=surface_a_text,cycle_id=cycle_id,surface_a_validated=surface_a_validated)
def _fit(text:str,width:int)->str:return str(text)[:width].ljust(width)
def _wrapped_rows(label:str,text:str,width:int)->list[str]:
 prefix=f'{label} '
 chunks=textwrap.wrap(str(text),width=max(12,width-len(prefix)),replace_whitespace=False,drop_whitespace=False) or ['']
 rows=[]
 for i,chunk in enumerate(chunks):rows.append((prefix if i==0 else ' '*len(prefix))+chunk)
 return rows
def render_dashboard_ascii(dashboard:dict[str,Any],*,width:int=96)->str:
 if width<80:raise ValueError('humanistic dashboard width must be >= 80')
 inner=width-4;line='+'+'-'*(width-2)+'+';h=dashboard.get('humanistic') or {};selfs=h.get('io_pensante') or {};aff=h.get('tono_interno') or {};mem=h.get('memoria') or {};ref=h.get('sguardo_riflessivo') or {};imp=h.get('campo_implicito') or {};ret=h.get('reticolo') or {};inc=dashboard.get('incarnate') or {};out=[line,'|'+'> iKant: stato interno'.center(width-2)+'|',line]
 if not dashboard.get('psyche_available'):
  out.append('| '+_fit('Io pensante: SELF_MODEL_PENDING',inner)+' |')
 else:
  rows=[f"Io pensante       {selfs.get('mode','?')} | continuita {_pct(selfs.get('self_model_confidence'))} | motore {selfs.get('engine','?')}",f"Tono interno      {aff.get('label','?')} | valenza {_signed(aff.get('valence'))} | tensione {_pct(aff.get('tension'))} | curiosita {_pct(aff.get('curiosity'))}",f"Memoria           {mem.get('maturity_mode','?')} | esperienza {_pct(mem.get('experience_depth'))} | stabilita {_pct(mem.get('adaptive_stability'))} | turni {mem.get('turns','?')}",f"Sguardo riflessivo controllo {_pct(ref.get('control'))} | incertezza {_pct(ref.get('uncertainty_trace'))} | revisione {_pct(ref.get('revision_trace'))}",f"Campo implicito   tensione {_pct(imp.get('tension'))} | autorita interpretativa | sempre ritrattabile",f"Reticolo          collasso {_pct(ret.get('mean_collapse'))} | picco {_pct(ret.get('max_collapse'))} | emergenze {ret.get('emergence_event_count','?')} | irr {_pct(ret.get('irreducibility_proxy'))}",f"Epistemica        ancoraggio {_legacy_value(dashboard,'grounding')} | cautela {_legacy_value(dashboard,'caution')} | conflitti {_legacy_value(dashboard,'conflicts')} | debito {_legacy_value(dashboard,'debt')}","Limiti            stato interno != prova | no azione autonoma | no sentienza | no cervello 1:1"]
  out.extend('| '+_fit(r,inner)+' |' for r in rows)
 backlog=dashboard.get('backlog') or {};out.append(line);out.append('| '+_fit(f"Backlog runtime   DOCX {backlog.get('document_count',0)} | errori parse {len(backlog.get('errors',[]))} | proiezione non-evidenziale",inner)+' |')
 out.append(line)
 a=inc.get('surface_a') or {};astatus=a.get('status','EMPTY');out.append('| '+_fit(f"SUPERFICIE A      [{astatus}] ciclo {inc.get('cycle_id') or '-'}",inner)+' |')
 if astatus=='VALIDATED':
  for row in _wrapped_rows('> iKant:',str(a.get('text') or ''),inner):out.append('| '+_fit(row,inner)+' |')
 elif astatus=='PENDING':out.append('| '+_fit('> iKant: [PENDING - la risposta validata non e ancora stata emessa]',inner)+' |')
 else:out.append('| '+_fit('> iKant: [nessuna Surface A associata]',inner)+' |')
 out.append(line)
 b=inc.get('surface_b') or {};docx=b.get('docx') or {};bind='BOUND' if b.get('bound') else 'UNBOUND';sha=str(docx.get('sha256') or '')[:16] or '-';out.append('| '+_fit(f"SUPERFICIE B      [{bind}] {docx.get('name') or '-'} | sha256 {sha} | ciclo {b.get('cycle_id') or '-'}",inner)+' |')
 if docx.get('path'):out.append('| '+_fit(f"Artifact DOCX     {docx.get('path')}",inner)+' |')
 if inc.get('errors'):out.append('| '+_fit('EGRESS BLOCK      '+', '.join(inc.get('errors') or []),inner)+' |')
 out.append('| '+_fit(f"Incarnate         {inc.get('state','?')} | single egress | same-cycle A/B | no concurrent pending turn",inner)+' |')
 out.append(line);return '\n'.join(out)
def persist_dashboard(runtime:Any,*,backlog_paths=None,surface_a_text=None,cycle_id=None,surface_a_validated=False)->dict[str,Any]:
 dash=project_dashboard(runtime,backlog_paths=backlog_paths,surface_a_text=surface_a_text,cycle_id=cycle_id,surface_a_validated=surface_a_validated);state_dir=Path(runtime.state_dir);json_path=state_dir/'dashboard.json';text_path=state_dir/'dashboard.txt';state_dir.mkdir(parents=True,exist_ok=True);tmp=json_path.with_suffix('.json.tmp');tmp.write_text(json.dumps(dash,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');tmp.replace(json_path);ttmp=text_path.with_suffix('.txt.tmp');ttmp.write_text(render_dashboard_ascii(dash)+'\n',encoding='utf-8');ttmp.replace(text_path);dash['persisted']={'json':str(json_path),'text':str(text_path)};return dash
