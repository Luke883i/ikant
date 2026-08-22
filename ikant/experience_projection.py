from __future__ import annotations
from typing import Any

EXPERIENCE_PROJECTION_SCHEMA='ikant-experience-projection/v1.3'
COGNITIVE_TRACE_SCHEMA='ikant-cognitive-trace-projection/v1.3'
TURN_TIMING_SCHEMA='ikant-turn-timing/v1.3'
PUBLIC_STAGES=(
 ('UNDERSTAND','Capisco'),('CONNECT','Collego'),('CHECK','Verifico'),
 ('GOVERN','Valuto'),('FORMULATE','Formulo'),('INTEGRATE','Integro'),
)

def _n(value:object, default=0):
    return value if isinstance(value,(int,float)) and not isinstance(value,bool) else default

def _bounded(value:object,limit=160):
    text=' '.join(str(value or '').replace('\x00',' ').split())
    return text[:limit]

def timing_start(origin:float)->dict[str,Any]:
    return {'schema':TURN_TIMING_SCHEMA,'origin':'SERVER_MONOTONIC','phases':[],
            'client_phases_expected':['PRIMARY_DELIVERED','ACK_DONE'],
            'docx_pre_primary':False,'epistemic_authority':0.0,'execution_authority':0.0,
            '_origin':float(origin)}

def timing_mark(timing:dict[str,Any],phase:str,now:float)->None:
    origin=float(timing.get('_origin',now));elapsed=max(0.0,(float(now)-origin)*1000)
    rows=timing.setdefault('phases',[])
    if not any(r.get('phase')==phase for r in rows):rows.append({'phase':phase,'elapsed_ms':round(elapsed,3)})

def timing_public(timing:dict[str,Any])->dict[str,Any]:
    out={k:v for k,v in dict(timing or {}).items() if not str(k).startswith('_')}
    out['phases']=list(out.get('phases') or [])[:24]
    return out

def cognitive_trace(cognitive:dict[str,Any],generation:dict[str,Any]|None=None,response_receipt:dict[str,Any]|None=None)->dict[str,Any]:
    cycle=cognitive.get('cycle') or {}; sem=cycle.get('semantic_slice') or {}; crc=cognitive.get('crc') or {}
    central=cognitive.get('central_projection') or {}; practical=cognitive.get('practical_reason') or {}
    generation=generation or {}; receipt=response_receipt or {}
    conflicts=central.get('must_surface_conflicts') if isinstance(central.get('must_surface_conflicts'),list) else []
    actions=(practical.get('action_ledger') or {}).get('candidates') if isinstance(practical.get('action_ledger'),dict) else []
    stages=[
      {'id':'UNDERSTAND','label':'Capisco','status':'complete','facts':{'intent_bound':bool(cognitive.get('intention_node_id')),'mined_objects':len(cognitive.get('mined_atoms') or [])}},
      {'id':'CONNECT','label':'Collego','status':'complete','facts':{'selected_objects':len(sem.get('nodes') or []),'directives':len(sem.get('directives') or [])}},
      {'id':'CHECK','label':'Verifico','status':'complete','facts':{'conflicts':len(conflicts),'horizon_exceeded':bool(crc.get('horizon_exceeded')),'crc_basic':bool((crc.get('roa_alignment') or {}).get('crc_basic'))}},
      {'id':'GOVERN','label':'Valuto','status':'complete','facts':{'material_action':_bounded(practical.get('material_action') or central.get('material_action') or 'PROPOSE_ONLY',48),'candidate_actions':len(actions or [])}},
      {'id':'FORMULATE','label':'Formulo','status':'complete' if generation else 'pending','facts':{'route':_bounded(generation.get('source') or 'pending',48),'generation_ms':_n((generation.get('model_metrics') or {}).get('total_ms'))}},
      {'id':'INTEGRATE','label':'Integro','status':'complete' if receipt else 'pending','facts':{'response_memory':bool(receipt),'evidence':0.0 if receipt else None,'speech_act_not_evidence':bool(receipt)}},
    ]
    return {'schema':COGNITIVE_TRACE_SCHEMA,'cycle_id':cycle.get('cycle_id'),'stages':stages,
            'private_chain_of_thought':False,'raw_model_rationale':False,
            'epistemic_authority':0.0,'execution_authority':0.0}

def experience_projection(*,runtime_session_id:str,cycle_id:str|None,primary_text:str,state:str,
                          trace:dict[str,Any]|None,timing:dict[str,Any]|None,generation:dict[str,Any]|None=None)->dict[str,Any]:
    return {'schema':EXPERIENCE_PROJECTION_SCHEMA,'runtime_session_id':str(runtime_session_id),
            'cycle_id':cycle_id,'state':_bounded(state,48),'primary_text':_bounded(primary_text,65536),
            'trace':trace,'timing':timing_public(timing or {}),'generation_route':_bounded((generation or {}).get('source') or '',48) or None,
            'epistemic_authority':0.0,'execution_authority':0.0}

def _load_json(path):
    import json
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return {}

def runtime_projection(root)->dict[str,Any]:
    from pathlib import Path
    from .chat_session import ChatLog
    root=Path(root).resolve(); state=root/'.ikant'; runtime=_load_json(state/'runtime.json'); session=str(runtime.get('session_id') or '')
    cog=runtime.get('cognitive') if isinstance(runtime.get('cognitive'),dict) else {}; cycle_id=str(cog.get('last_surface_a_cycle_id') or '') or None
    snapshot=_load_json(state/'cognitive'/f'{cycle_id}.json') if cycle_id else {}; dyn=snapshot.get('dynamic_state') if isinstance(snapshot.get('dynamic_state'),dict) else {}; ret=snapshot.get('reticulum') if isinstance(snapshot.get('reticulum'),dict) else {}
    central=dyn.get('central_projection') if isinstance(dyn.get('central_projection'),dict) else {}; practical=dyn.get('practical_reason') if isinstance(dyn.get('practical_reason'),dict) else {}; generation=cog.get('last_surface_a_generation') if isinstance(cog.get('last_surface_a_generation'),dict) else {}
    primary='';
    if session:
        try:
            log=ChatLog(state/'chat'/'transcript.jsonl',runtime_session_id=session);log.verify()
            for row in reversed(log.rows()):
                if row.get('role')=='ikant' and (cycle_id is None or str(row.get('cycle_id') or '')==cycle_id):primary='iKant: '+str(row.get('text') or '').strip();break
        except Exception:pass
    sem_nodes=[]
    for obj in dyn.get('mined_atoms',[]) if isinstance(dyn.get('mined_atoms'),list) else []:
        if isinstance(obj,dict):sem_nodes.append(obj)
    conflicts=central.get('must_surface_conflicts') if isinstance(central.get('must_surface_conflicts'),list) else []
    actions=(practical.get('action_ledger') or {}).get('candidates') if isinstance(practical.get('action_ledger'),dict) else []
    diag=ret.get('diagnostics') if isinstance(ret.get('diagnostics'),dict) else {}; roa=ret.get('roa_alignment') if isinstance(ret.get('roa_alignment'),dict) else {}
    receipt=bool(primary)
    stages=[
      {'id':'UNDERSTAND','label':'Capisco','status':'complete' if cycle_id else 'idle','facts':{'intent_bound':bool(dyn.get('intention_node_id')),'mined_objects':len(sem_nodes)}},
      {'id':'CONNECT','label':'Collego','status':'complete' if cycle_id else 'idle','facts':{'objects':len(sem_nodes),'collapse':_n(diag.get('mean_coefficient_of_collapse'))}},
      {'id':'CHECK','label':'Verifico','status':'complete' if cycle_id else 'idle','facts':{'conflicts':len(conflicts),'epistemic_debt':_n(diag.get('epistemic_debt_open_count')),'closure':bool(roa.get('crc_basic'))}},
      {'id':'GOVERN','label':'Valuto','status':'complete' if cycle_id else 'idle','facts':{'material_action':_bounded(practical.get('material_action') or central.get('material_action') or 'PROPOSE_ONLY',48),'candidate_actions':len(actions or [])}},
      {'id':'FORMULATE','label':'Formulo','status':'complete' if generation else 'idle','facts':{'route':_bounded(generation.get('source') or '',48) or None,'generation_ms':_n((generation.get('model_metrics') or {}).get('total_ms'))}},
      {'id':'INTEGRATE','label':'Integro','status':'complete' if receipt else 'idle','facts':{'response_memory':receipt,'evidence':0.0 if receipt else None}},
    ]
    trace={'schema':COGNITIVE_TRACE_SCHEMA,'cycle_id':cycle_id,'stages':stages,'private_chain_of_thought':False,'raw_model_rationale':False,'epistemic_authority':0.0,'execution_authority':0.0}
    timing=cog.get('last_turn_timing') if isinstance(cog.get('last_turn_timing'),dict) else {'schema':TURN_TIMING_SCHEMA,'phases':[],'docx_pre_primary':False}
    state_label='Pronto' if runtime.get('status')=='ACTIVE' else _bounded(runtime.get('status') or 'Avvio',48)
    return experience_projection(runtime_session_id=session,cycle_id=cycle_id,primary_text=primary,state=state_label,trace=trace,timing=timing,generation=generation)
