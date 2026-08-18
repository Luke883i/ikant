from __future__ import annotations

import argparse
import json
import random
import tempfile
import time
from pathlib import Path

from ikant.chat_session import ChatController
from ikant.dashboard_v05 import persist_dashboard
from ikant.incarnate import validate_incarnate_dashboard


class ResponseNode:
    def __init__(self, text: str, cycle: str):
        self.text = text
        self.evidence = 0.0
        self.metadata = {'surface_a_validated': True, 'speech_act_not_evidence': True, 'last_cycle_id': cycle}


class SessionRuntime:
    def __init__(self, root: Path, session_index: int):
        self.root = root
        self.state_dir = root / '.ikant'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.runtime = {
            'session_id': f'SES-E2E-{session_index:05d}', 'status': 'ACTIVE', 'cycle_count': 0,
            'compression': {'trend': {'metrics': {'revision_pressure': 0.0}}}, 'cognitive': {}, 'host': {},
        }
        self.nodes = {}

    def require_active(self):
        if self.runtime.get('status') != 'ACTIVE': raise PermissionError('runtime not ACTIVE')


def turn_fn(runtime: SessionRuntime, intent: str, engine_label=None, **kwargs):
    runtime.require_active();cognitive=runtime.runtime['cognitive']
    if cognitive.get('pending_surface_a_cycle_id'): raise RuntimeError('pending Surface A must close')
    runtime.runtime['cycle_count'] += 1;cycle=f"CYC-E2E-{runtime.runtime['cycle_count']:08d}"
    snapshot_path=runtime.state_dir/'cognitive'/f'{cycle}.json';docx_path=runtime.state_dir/'artifacts'/f'{cycle}.docx';snapshot_path.parent.mkdir(parents=True,exist_ok=True);docx_path.parent.mkdir(parents=True,exist_ok=True)
    snapshot_path.write_text(json.dumps({'session_id':runtime.runtime['session_id'],'cycle_id':cycle,'reticulum':{'diagnostics':{'epistemic_debt_open_count':0},'roa_alignment':{'crc_basic':True}},'dynamic_state':{'central_oracle':{'regulative_mode':'REFLECTIVE_SYNTHESIS','base_oracle':{'faculties':{'sensibility_grounding':.8}}},'central_projection':{'must_surface_conflicts':[]},'proto_self':{'proto_self_index':.6},'surface_a_contract':{'regulation':{'epistemic_caution':.2}}}}),encoding='utf-8')
    docx_path.write_bytes(b'PK\x03\x04IKANT-E2E-'+cycle.encode())
    cognitive.update({'last_snapshot':str(snapshot_path),'last_surface_b_docx':str(docx_path),'pending_surface_a_cycle_id':cycle});runtime.runtime['host']={'interface_identity':'iKant','engine_label':engine_label or 'GPT-E2E'}
    return {'cycle':{'cycle_id':cycle},'intention_node_id':f'N-{cycle}'}


def emit_fn(runtime: SessionRuntime, cycle_id: str, text: str, intention_node_id=None):
    cognitive=runtime.runtime['cognitive']
    if cognitive.get('pending_surface_a_cycle_id') != cycle_id: raise PermissionError('not the single pending cycle')
    response_id=f'R-{cycle_id}';runtime.nodes[response_id]=ResponseNode(text,cycle_id);cognitive['last_surface_a_response_id']=response_id;cognitive['last_surface_a_cycle_id']=cycle_id;cognitive.pop('pending_surface_a_cycle_id',None)
    return {'response_id':response_id,'cycle_id':cycle_id,'validated':True,'evidence':0.0}


def dashboard_fn(runtime): return persist_dashboard(runtime,backlog_paths=[])


def intent_for(rng: random.Random, i: int):
    kind=rng.choice(('identity','simple','standard','unicode','longish'))
    if kind=='identity':return kind,'ciao, chi sei?'
    if kind=='unicode':return kind,f'valuta continuità 🧭 日本語 turno {i}'
    if kind=='longish':return kind,f'analizza il turno {i} mantenendo dashboard, superficie A e superficie B coerenti e senza concorrenze'
    return kind,f'valuta turno {i}'


def exercise_session(root: Path, session_index: int, count: int, rng: random.Random, baseline: set, collect_baseline: bool, failures: list, tail_new: set):
    rt=SessionRuntime(root,session_index);controller=ChatController(rt,turn_fn=turn_fn,emit_fn=emit_fn,dashboard_fn=dashboard_fn)
    for local_i in range(count):
        kind,intent=intent_for(rng,local_i);out=controller.begin(intent,engine_label='GPT-E2E');cycle=out['cycle']['cycle_id'];pending=json.loads((rt.state_dir/'dashboard.json').read_text(encoding='utf-8'));p_ok,p_err=validate_incarnate_dashboard(pending)
        if not p_ok or pending['incarnate']['state']!='PENDING' or pending['incarnate']['surface_a']['text'] is not None:failures.append(('pending',session_index,local_i,p_err))
        text=f'Risposta iKant validata per il turno {local_i}, resa soltanto nel dashboard con Surface B associata.';rec=controller.close(cycle,text,intention_node_id=out['intention_node_id'],user_seq=out['chat']['user_seq']);ready=rec['dashboard'];r_ok,r_err=validate_incarnate_dashboard(ready)
        if not r_ok or ready['incarnate']['state']!='READY' or ready['incarnate']['surface_a']['text']!=text or not ready['incarnate']['surface_b']['bound']:failures.append(('ready',session_index,local_i,r_err))
        if rt.nodes[rec['response_id']].evidence != 0:failures.append(('evidence',session_index,local_i))
        sig=(pending['incarnate']['state'],ready['incarnate']['state'],kind,bool(ready['incarnate']['surface_b']['bound']))
        if collect_baseline:baseline.add(sig)
        elif sig not in baseline:tail_new.add(sig)
    receipt=controller.log.verify();refresh=persist_dashboard(rt,backlog_paths=[]);refresh_ok,refresh_err=validate_incarnate_dashboard(refresh)
    if not refresh_ok or refresh['incarnate']['state']!='READY':failures.append(('refresh',session_index,refresh_err))
    if receipt['records'] != 2*count:failures.append(('records',session_index,receipt['records'],2*count))


def run(seed: int, turns: int, tail: int, session_turns: int):
    rng=random.Random(seed);tail_rng=random.Random(seed+1_000_003);failures=[];signatures=set();tail_new=set();started=time.monotonic()
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);remaining=turns;session_index=0
        while remaining:
            n=min(session_turns,remaining);exercise_session(root/f'base-{session_index}',session_index,n,rng,signatures,True,failures,tail_new);remaining-=n;session_index+=1
        remaining=tail
        while remaining:
            n=min(session_turns,remaining);exercise_session(root/f'tail-{session_index}',session_index,n,tail_rng,signatures,False,failures,tail_new);remaining-=n;session_index+=1
    return {'schema':'ikant-incarnate-session-stress/v0.7-test','seed':seed,'turns':turns,'tail_turns':tail,'session_turns':session_turns,'records':2*(turns+tail),'baseline_signatures':len(signatures),'tail_new_signatures':len(tail_new),'failure_count':len(failures),'sample_failures':failures[:10],'elapsed_s':round(time.monotonic()-started,3),'saturated':not failures and len(tail_new)==0}


def main():
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=883);p.add_argument('--turns',type=int,default=10_000);p.add_argument('--tail',type=int,default=1_000);p.add_argument('--session-turns',type=int,default=100);a=p.parse_args();result=run(a.seed,a.turns,a.tail,a.session_turns);print(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True));raise SystemExit(0 if result['saturated'] else 2)

if __name__=='__main__':main()
