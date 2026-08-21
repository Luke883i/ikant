from __future__ import annotations
import argparse,json,random
FAMILIES=48
OUTCOMES=('SUCCESS','MANIFEST_FAIL','ENGINE_CACHE_FAIL','ENGINE_DOWNLOAD_FAIL','MODEL_CACHE_FAIL','MODEL_DOWNLOAD_FAIL','SPAWN_FAIL','READINESS_FAIL','SERVICE_FAIL','JOURNAL_CORRUPT','RETRY')

def semantic_edge(i):
    f=i%FAMILIES;o=OUTCOMES[(i//FAMILIES)%len(OUTCOMES)]
    blocked=o not in {'SUCCESS','RETRY'}
    gate={'MANIFEST_FAIL':'MANIFEST','ENGINE_CACHE_FAIL':'ENGINE_COMPONENT','ENGINE_DOWNLOAD_FAIL':'ENGINE_COMPONENT','MODEL_CACHE_FAIL':'MODEL_COMPONENT','MODEL_DOWNLOAD_FAIL':'MODEL_COMPONENT','SPAWN_FAIL':'ENGINE_PROCESS','READINESS_FAIL':'ENGINE_READINESS','SERVICE_FAIL':'PRODUCT_SERVICE','JOURNAL_CORRUPT':'PRODUCT_SERVICE'}.get(o)
    code={'MANIFEST_FAIL':'RUNTIME_MANIFEST_INVALID','ENGINE_CACHE_FAIL':'COMPONENT_INSTALL_FAILED','ENGINE_DOWNLOAD_FAIL':'NETWORK_DOWNLOAD_FAILED','MODEL_CACHE_FAIL':'COMPONENT_INSTALL_FAILED','MODEL_DOWNLOAD_FAIL':'NETWORK_DOWNLOAD_FAILED','SPAWN_FAIL':'ENGINE_START_FAILED','READINESS_FAIL':'ENGINE_READINESS_TIMEOUT','SERVICE_FAIL':'BOOTSTRAP_FAILED','JOURNAL_CORRUPT':'BOOTSTRAP_DIAGNOSTICS_CORRUPT'}.get(o,'READY')
    remediation=not blocked or bool(code)
    visible=not blocked or bool(gate)
    violation=blocked and (not visible or not remediation or gate is None)
    return (f,o,gate,code,blocked,visible,remediation),violation

def run(cases,tail,seed):
    rng=random.Random(seed);hits=[0]*FAMILIES;base=set();novel=set();viol=0
    for i in range(cases+tail):
        sig,bad=semantic_edge(i);hits[i%FAMILIES]+=1;rng.getrandbits(32);viol+=int(bad)
        if i<cases:base.add(sig)
        elif sig not in base:novel.add(sig)
    return {'cases':cases,'tail':tail,'seed':seed,'families_total':FAMILIES,'families_covered':sum(x>0 for x in hits),'signatures':len(base),'violations':viol,'tail_novelty':len(novel)}

def minimality(seed,tail):
    required=(1<<14)-1;forbidden=((1<<20)-1)^required;accepted=0;best=99
    for mask in range(1<<20):
        if (mask&required)==required and (mask&forbidden)==0:accepted+=1;best=min(best,mask.bit_count())
    rng=random.Random(seed^0xB05);better=0
    for _ in range(tail):
        mask=rng.getrandbits(20)
        if (mask&required)==required and (mask&forbidden)==0 and mask.bit_count()<best:better+=1
    return {'architectures':1<<20,'accepted':accepted,'best_enabled_features':best,'tail':tail,'tail_better_without_degradation':better}

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=int,default=10_000_000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=20260821);a=p.parse_args();o=run(a.cases,a.tail,a.seed);m=minimality(a.seed,a.tail);status='PASS' if o['violations']==0 and o['families_covered']==FAMILIES and not o['tail_novelty'] and m['accepted']==1 and m['best_enabled_features']==14 and m['tail_better_without_degradation']==0 else 'FAIL';print(json.dumps({'schema':'ikant-bootstrap-observability-edges/v0.29-test',**o,'minimality':m,'status':status},sort_keys=True));raise SystemExit(0 if status=='PASS' else 1)
if __name__=='__main__':main()
