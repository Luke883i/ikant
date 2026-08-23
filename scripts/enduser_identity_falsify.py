from __future__ import annotations
import argparse, json, random, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ikant.enduser_identity import enduser_projection

SEED=2026082314
FAMILIES=256


def base(i:int):
    sid=f'session-{i%97:02d}';cycle=f'cycle-{i%4093:04d}'
    trace={'schema':'ikant-cognitive-trace-projection/v1.3','cycle_id':cycle,'private_chain_of_thought':False,'raw_model_rationale':False,'stages':[
        {'id':'UNDERSTAND','label':'Capisco','status':'complete','facts':{'mined_objects':i%8}},
        {'id':'CONNECT','label':'Collego','status':'complete','facts':{'objects':i%13}},
        {'id':'CHECK','label':'Verifico','status':'complete','facts':{'conflicts':0}},
        {'id':'GOVERN','label':'Valuto','status':'complete','facts':{'material_action':'PROPOSE_ONLY'}},
        {'id':'FORMULATE','label':'Formulo','status':'complete','facts':{'route':'managed-local'}},
        {'id':'INTEGRATE','label':'Integro','status':'complete','facts':{'response_memory':True}},
    ]}
    conv={'status':'AVAILABLE','runtime_session_id':sid,'integrity_verified':True,'last_sha256':'a'*64,'record_count':40,'visible_record_count':32,'records':[{'role':'user','cycle_id':cycle,'text':'x'},{'role':'ikant','cycle_id':cycle,'text':'y'}]}
    exp={'runtime_session_id':sid,'cycle_id':cycle,'state':'Pronto','trace':trace,'timing':{'phases':[{'phase':'A'}]},'generation_route':'managed-local'}
    return conv,exp,{'cycle_id':cycle,'truth_certified':False},{'runtime_session_id':sid,'cycle_id':cycle,'services':[]}


def mutate(fid:int,conv,exp,epi,caps):
    group=fid//16;slot=fid%16;expected_degraded=True
    if group==0:exp['cycle_id']=f'drift-{slot}'
    elif group==1:exp['trace']['cycle_id']=f'drift-{slot}'
    elif group==2:epi['cycle_id']=f'drift-{slot}'
    elif group==3:conv['records'][-1]['cycle_id']=f'drift-{slot}'
    elif group==4:caps['cycle_id']=f'drift-{slot}'
    elif group==5:conv['runtime_session_id']=f'other-{slot}'
    elif group==6:caps['runtime_session_id']=f'other-{slot}'
    elif group==7:conv['integrity_verified']=False
    elif group==8:exp['trace']['schema']='wrong-schema'
    elif group==9:exp['trace']['private_chain_of_thought']=True
    elif group==10:exp['trace']['raw_model_rationale']=True
    elif group==11:epi['truth_certified']=True
    elif group==12:conv['record_count']=slot;conv['visible_record_count']=32
    elif group==13:exp['timing']['phases']=[{'phase':str(x)} for x in range(80)];expected_degraded=False
    elif group==14:exp['trace']['stages'][slot%6]['status']='garbage';expected_degraded=False
    else:exp['runtime_session_id']=''
    return expected_degraded


def _chunk(args):
    start_i,count,seed=args;rng=random.Random(seed);survivors=0;signatures=set();classes={}
    for offset in range(count):
        i=start_i+offset;fid=rng.randrange(FAMILIES);conv,exp,epi,caps=base(i);expected=mutate(fid,conv,exp,epi,caps);out=enduser_projection(conversation=conv,experience=exp,epistemic_value=epi,capabilities=caps);audit=out['audit'];ident=out['identity'];neuro=out['neuromodel'];group=fid//16
        if expected:killed=audit['status']=='DEGRADED'
        elif group==13:killed=audit['timing_phase_count']<=24
        else:killed=neuro['trace_schema_valid'] is False
        if group==15:killed=ident['status']=='UNAVAILABLE' and ident['consciousness_claimed'] is False
        if not killed:survivors+=1
        signatures.add((group,audit['status'],audit['cycle_coherent'],audit['session_coherent'],audit['conversation_integrity_verified'],audit['trace_contract_valid'],neuro['trace_schema_valid'],ident['status']));classes[group]=classes.get(group,0)+1
    return survivors,signatures,classes


def run(n:int,tail:int,seed:int,workers:int=8):
    started=time.perf_counter();workers=max(1,min(workers,n));q,r=divmod(n,workers);chunks=[];pos=0
    for idx in range(workers):count=q+(1 if idx<r else 0);chunks.append((pos,count,seed+idx*1000003));pos+=count
    with ProcessPoolExecutor(max_workers=workers) as pool:parts=list(pool.map(_chunk,chunks))
    survivors=sum(x[0] for x in parts);signatures=set();classes={}
    for _,sig,cls in parts:
        signatures.update(sig)
        for k,v in cls.items():classes[k]=classes.get(k,0)+v
    rng=random.Random(seed+99999991);novel=0
    for j in range(tail):
        fid=rng.randrange(FAMILIES);conv,exp,epi,caps=base(n+j);mutate(fid,conv,exp,epi,caps);out=enduser_projection(conversation=conv,experience=exp,epistemic_value=epi,capabilities=caps);a=out['audit'];neuro=out['neuromodel'];ident=out['identity'];sig=(fid//16,a['status'],a['cycle_coherent'],a['session_coherent'],a['conversation_integrity_verified'],a['trace_contract_valid'],neuro['trace_schema_valid'],ident['status'])
        if sig not in signatures:novel+=1;signatures.add(sig)
    return {'schema':'ikant-enduser-self-model-falsification/v1-test','status':'PASS' if survivors==0 and novel==0 and len(classes)==16 and sum(classes.values())==n else 'FAIL','seed':seed,'mutations':n,'families':FAMILIES,'kill_classes':16,'family_groups_seen':len(classes),'family_hits_total':sum(classes.values()),'survivors':survivors,'semantic_signatures':len(signatures),'no_novelty_tail':tail,'tail_novelty':novel,'workers':workers,'seconds':round(time.perf_counter()-started,3),'real_code_executed':True,'scope':'Production enduser_projection executed against cycle/session/integrity/trace/truth/history/timing mutations; browser rendering is a separate proof.'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int);ap.add_argument('--cases',type=int);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=SEED);ap.add_argument('--workers',type=int,default=8);a=ap.parse_args();n=a.mutations if a.mutations is not None else a.cases
    if n is None or n<1 or a.tail<0:raise SystemExit('positive --mutations or --cases required')
    result=run(n,a.tail,a.seed,a.workers);print(json.dumps(result,sort_keys=True));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
