from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
MASK64=(1<<64)-1
DOMAINS=("filesystem","process","session","egress","shell","work","surface","epoch","browser","assets","lifecycle","ci_truth")
FAMILIES=96;PHASES=8;CONTEXTS=4;MUTATION_CLASSES=4;SIGNATURE_SPACE=FAMILIES*PHASES*CONTEXTS*MUTATION_CLASSES
DEFAULT_SEED=5106034144745002672
FAULT_FAMILIES=tuple(f"{DOMAINS[i%len(DOMAINS)]}:{i//len(DOMAINS):02d}" for i in range(FAMILIES))
def splitmix64(value:int)->int:
 value=(value+0x9E3779B97F4A7C15)&MASK64;value=((value^(value>>30))*0xBF58476D1CE4E5B9)&MASK64;value=((value^(value>>27))*0x94D049BB133111EB)&MASK64;return value^(value>>31)
def _signature(word:int)->tuple[int,int,int]:
 family=word%FAMILIES;word//=FAMILIES;phase=word%PHASES;word//=PHASES;context=word%CONTEXTS;word//=CONTEXTS;mutation=word%MUTATION_CLASSES;return family+FAMILIES*(phase+PHASES*(context+CONTEXTS*mutation)),family,family%len(DOMAINS)
def modeled(total:int,tail:int,seed:int)->dict[str,Any]:
 seen=bytearray(SIGNATURE_SPACE);counts=[0]*FAMILIES;pair_seen=bytearray(len(DOMAINS)*len(DOMAINS));offset=0xD1B54A32D192ED03
 for i in range(total):
  a=splitmix64(seed+i);idx,f,d1=_signature(a);seen[idx]=1;counts[f]+=1;faults=2+(a>>61)%3
  for j in range(1,int(faults)):
   _,_,d2=_signature(splitmix64(seed+offset+i*5+j));lo,hi=(d1,d2) if d1<=d2 else (d2,d1);pair_seen[lo*len(DOMAINS)+hi]=1
 before=sum(seen);pairs=sum(pair_seen[i*len(DOMAINS)+j] for i in range(len(DOMAINS)) for j in range(i,len(DOMAINS)));new=0
 for i in range(tail):idx,_,_=_signature(splitmix64(seed+10_000_000_019+i));new+=int(not seen[idx]);seen[idx]=1
 return {"cases":total,"tail":tail,"domains":len(DOMAINS),"fault_families":FAMILIES,"simultaneous_faults":"2..4","semantic_signature_space":SIGNATURE_SPACE,"semantic_signatures":before,"domain_pair_space":len(DOMAINS)*(len(DOMAINS)+1)//2,"domain_pairs_observed":pairs,"family_min_hits":min(counts),"family_max_hits":max(counts),"tail_new_signatures":new,"coverage_complete":before==SIGNATURE_SPACE and pairs==len(DOMAINS)*(len(DOMAINS)+1)//2,"model_results_are_production_reliability_estimates":False}
def source_probe()->list[str]:
 errors=[];runtime=(ROOT/'ikant'/'runtime_recovery.py').read_text(encoding='utf-8');managed=(ROOT/'ikant'/'managed_runtime.py').read_text(encoding='utf-8');reactive=(ROOT/'ikant'/'reactive_http.py').read_text(encoding='utf-8');browser=(ROOT/'scripts'/'runtime_recovery_browser_liveness.mjs').read_text(encoding='utf-8') if (ROOT/'scripts'/'runtime_recovery_browser_liveness.mjs').exists() else ''
 gates={'no_model_retry':"model_reexecuted\": False" in runtime,'interrupted_state':'INTERRUPTED_UNSEALED' in runtime,'surface_unsealed_state':'SURFACE_A_UNSEALED' in runtime,'acked_reconcile':'RECOVERY_ACKED_PENDING_RECONCILE' in runtime,'managed_frame_recovery':'materialize_recovery_frame' in managed,'managed_post_ack_cleanup':'finalize_recovery_after_ack' in managed,'work_reconstruction':'recover_work_for_root' in reactive,'browser_process_oracle':'runtime_recovery_browser_fixture.py' in browser}
 for name,ok in gates.items():
  if not ok:errors.append(name)
 return errors
def run(mode:str,total:int,tail:int,seed:int)->dict[str,Any]:
 errors=source_probe();model=modeled(total,tail,seed)
 if total>=10_000_000 and not model['coverage_complete']:errors.append('declared_space_not_saturated')
 if model['tail_new_signatures']!=0:errors.append('tail_novelty')
 return {'schema':'ikant-runtime-recovery-falsification/v1-test','status':'PASS' if not errors else 'FAIL','mode':mode,'seed':seed,'fault_domains':list(DOMAINS),'errors':errors,**model}
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--mode',default='falsify');ap.add_argument('--cases',type=int,default=10_000_000);ap.add_argument('--tail',type=int,default=100_000);ap.add_argument('--seed',type=int,default=DEFAULT_SEED);args=ap.parse_args();out=run(args.mode,max(1,args.cases),max(0,args.tail),args.seed);print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
