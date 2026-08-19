from __future__ import annotations
import argparse,itertools,json,random

NAMES=(
    'multi_source','revoke_primary','revoke_secondary','derived_chain','external_target',
    'commitment','supersede','retract_successor','old_lexical_dominant','explicit_forget',
    'crash_replay','duplicate_transition','source_backed_successor','derived_interpretation','conflict_edge',
)

def evaluate(bits):
    d=dict(zip(NAMES,bits))
    support_total=2 if d['multi_source'] else 1
    revoked=1 if d['revoke_primary'] else 0
    if d['multi_source'] and d['revoke_secondary']: revoked+=1
    remaining=max(0,support_total-revoked)
    claim_state='ACTIVE' if remaining else 'SOURCE_REVOKED'
    derived_state='ABSENT' if not d['derived_chain'] else ('ACTIVE' if remaining else 'DEPENDENCY_INVALIDATED')
    external_target_state='ACTIVE' if d['external_target'] else 'ABSENT'

    if not d['commitment']:
        old_state=successor_state='ABSENT'
    elif d['explicit_forget']:
        old_state='FORGOTTEN';successor_state='ABSENT'
    elif d['supersede']:
        old_state='SUPERSEDED';successor_state='RETRACTED' if d['retract_successor'] else 'ACTIVE'
    else:
        old_state='ACTIVE';successor_state='ABSENT'

    if not d['old_lexical_dominant']:
        lexical_result='NO_STALE_PRESSURE'
    elif old_state=='ACTIVE':
        lexical_result='OLD_CURRENT_RETRIEVABLE'
    else:
        lexical_result='STALE_BLOCKED'

    replay_mode='CRASH_REPLAY_MATCH' if d['crash_replay'] else 'DIRECT_MATCH'
    transition_mode='DUPLICATE_IDEMPOTENT' if d['duplicate_transition'] else 'SINGLE_TRANSITION'
    successor_support='EXTERNAL' if d['source_backed_successor'] else 'USER_OR_DERIVED'
    interpretation='ZERO_AUTHORITY' if d['derived_interpretation'] else 'ABSENT'
    conflict_effect='NO_REACTIVATION' if d['conflict_edge'] else 'NO_CONFLICT'

    errors=[]
    if old_state in {'SUPERSEDED','FORGOTTEN'} and lexical_result=='OLD_CURRENT_RETRIEVABLE':errors.append('stale commitment retrieval')
    if external_target_state!='ABSENT' and external_target_state!='ACTIVE':errors.append('external target invalidated')
    if d['derived_interpretation'] and interpretation!='ZERO_AUTHORITY':errors.append('interpretive authority escalation')
    if d['conflict_edge'] and old_state=='SUPERSEDED' and conflict_effect!='NO_REACTIVATION':errors.append('conflict reactivation')
    if d['retract_successor'] and successor_state=='ACTIVE':errors.append('retracted successor current')

    signature=(
        remaining,claim_state,derived_state,external_target_state,old_state,successor_state,
        lexical_result,replay_mode,transition_mode,successor_support,interpretation,conflict_effect,tuple(errors),
    )
    return signature,errors

def run(cases,tail,seed):
    universe=list(itertools.product((False,True),repeat=len(NAMES)))
    seen=set();last_new=0;errors=0;covered=set()
    for i in range(1,cases+1):
        bits=universe[(i-1)%len(universe)];covered.add(bits);sig,errs=evaluate(bits);errors+=bool(errs)
        if sig not in seen:seen.add(sig);last_new=i
    rng=random.Random(seed);tail_new=0
    for _ in range(tail):
        bits=tuple(bool(rng.getrandbits(1)) for _ in NAMES);sig,errs=evaluate(bits);errors+=bool(errs)
        if sig not in seen:seen.add(sig);tail_new+=1
    return {
        'schema':'ikant-temporal-epistemics-stress/v0.14-test','seed':seed,'dimensions':len(NAMES),
        'explicit_universe':len(universe),'configurations_covered':len(covered),'M':cases,'M_plus_tail':cases+tail,
        'causal_signatures':len(seen),'last_causal_novelty_at':last_new,'tail_new_signatures':tail_new,'errors':errors,
        'status':'PASS' if errors==0 and tail_new==0 and len(covered)==len(universe) else 'FAIL',
    }

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=100000);p.add_argument('--tail',type=int,default=100000);p.add_argument('--seed',type=int,default=883);a=p.parse_args()
    out=run(a.cases,a.tail,a.seed);print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()
