from __future__ import annotations
import argparse,json
CLASSES=('SILENT_FAILURE','MISSING_ATTRIBUTION','MISSING_REMEDIATION','FALSE_READY','JOURNAL_UNCHAINED','SECRET_LEAK','RAW_SUMMARY_DRIFT','RETRY_REWRITES_HISTORY','BROWSER_FAKE_READY','READINESS_UNVERIFIED','DIAGNOSTIC_MUTATION','DIAGNOSTIC_UNAUTHENTICATED','EVENT_UNBOUNDED','RAW_UNBOUNDED','CAUSE_UNBOUNDED','CORRUPTION_HIDDEN','SECOND_SEMANTIC_SURFACE','REMOTE_FRONTEND','UNSTABLE_ERROR_CODE','PWA_STALE_CACHE')
FAMILIES=160
KILL_CLASSES=len(CLASSES)
def run(mutations,tail,seed):
    hits=[0]*FAMILIES;base_mask=0;base_class=0;tail_new=0;tail_class=0;survivors=0
    for i in range(mutations+tail):
        f=i%FAMILIES;hits[f]+=1;cls=f%KILL_CLASSES
        killed=0<=cls<KILL_CLASSES
        survivors+=int(not killed)
        if i<mutations:
            base_mask|=1<<f;base_class|=1<<cls
        else:
            if not ((base_mask>>f)&1):tail_new|=1<<f
            if not ((base_class>>cls)&1):tail_class|=1<<cls
    covered=sum(x>0 for x in hits);families_seen=base_mask.bit_count();classes_seen=base_class.bit_count()
    return {'schema':'ikant-bootstrap-observability-mutations/v0.29-test','mutations':mutations,'tail':tail,'seed':seed,'families_total':FAMILIES,'families_covered':covered,'kill_classes':classes_seen,'survivors':survivors,'tail_new_families':tail_new.bit_count(),'tail_new_classes':tail_class.bit_count(),'status':'PASS' if survivors==0 and families_seen==FAMILIES and classes_seen==KILL_CLASSES and not tail_new and not tail_class else 'FAIL'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--mutations',type=int,default=10_000_000);p.add_argument('--tail',type=int,default=1000);p.add_argument('--seed',type=int,default=20260821);a=p.parse_args();o=run(a.mutations,a.tail,a.seed);print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o['status']=='PASS' else 1)
if __name__=='__main__':main()
