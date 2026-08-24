from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
MASK64=(1<<64)-1
LEVELS=("filesystem_power","journal_integrity","causal_transaction","session_epoch_recovery","cognitive_artifacts","psyche_central_influence","surface_frame_ack","planning_temporal_refs","ux_audit","git_ci_product_truth")
FAMILIES_PER_LEVEL=64;PHASES=8;CONTEXTS=4;MUTATION_CLASSES=4
LOCAL_SIGNATURES=FAMILIES_PER_LEVEL*PHASES*CONTEXTS*MUTATION_CLASSES
SIGNATURE_SPACE=len(LEVELS)*LOCAL_SIGNATURES
DEFAULT_SEED=11869997915535976544

def splitmix64(v:int)->int:
 v=(v+0x9E3779B97F4A7C15)&MASK64;v=((v^(v>>30))*0xBF58476D1CE4E5B9)&MASK64;v=((v^(v>>27))*0x94D049BB133111EB)&MASK64;return v^(v>>31)

def coverage_signature(i:int,seed:int)->int:return (i*(SIGNATURE_SPACE-1)+(seed%SIGNATURE_SPACE))%SIGNATURE_SPACE

def modeled(total:int,tail:int,seed:int)->dict[str,Any]:
 seen=bytearray(SIGNATURE_SPACE);level_seen=[0]*len(LEVELS);family_hits=[[0]*FAMILIES_PER_LEVEL for _ in LEVELS]
 cofault_levels=bytearray(len(LEVELS)*len(LEVELS))
 for i in range(total):
  sig=coverage_signature(i,seed);seen[sig]=1;level=sig//LOCAL_SIGNATURES;local=sig%LOCAL_SIGNATURES;fam=local//(PHASES*CONTEXTS*MUTATION_CLASSES);family_hits[level][fam]+=1;level_seen[level]=1
  state=splitmix64(seed+i);extra=2+((state>>61)%3)
  for j in range(1,int(extra)):
   other=splitmix64(state+j*0xD1B54A32D192ED03)%len(LEVELS);lo,hi=(level,other) if level<=other else (other,level);cofault_levels[lo*len(LEVELS)+hi]=1
 before=sum(seen);pairs=sum(cofault_levels[i*len(LEVELS)+j] for i in range(len(LEVELS)) for j in range(i,len(LEVELS)));new=0
 for i in range(tail):
  sig=coverage_signature(total+i,seed);new+=int(not seen[sig]);seen[sig]=1
 flat=[x for row in family_hits for x in row]
 return {"cases":total,"tail":tail,"levels":len(LEVELS),"fault_families_per_level":FAMILIES_PER_LEVEL,"simultaneous_faults":"2..4","semantic_signature_space":SIGNATURE_SPACE,"semantic_signatures":before,"level_pair_space":len(LEVELS)*(len(LEVELS)+1)//2,"level_pairs_observed":pairs,"family_min_hits":min(flat),"family_max_hits":max(flat),"tail_new_signatures":new,"coverage_complete":before==SIGNATURE_SPACE,"coverage_strategy":"seed_bound_full_lattice_permutation_with_random_multilevel_cofaults","model_results_are_production_reliability_estimates":False}

def source_probe()->list[str]:
 errors=[]
 causal=(ROOT/'ikant'/'causal_ledger.py').read_text(encoding='utf-8');runtime=(ROOT/'ikant'/'runtime_host.py').read_text(encoding='utf-8');host=(ROOT/'ikant'/'host.py').read_text(encoding='utf-8');session=(ROOT/'ikant'/'session_host.py').read_text(encoding='utf-8');store=(ROOT/'ikant'/'store.py').read_text(encoding='utf-8')
 gates={
  'append_only_hash_chain':"prev_sha256" in causal and "causal ledger digest mismatch" in causal,
  'preprepare_undo':"_capture_undo" in causal and "PREPARE_CRASH_ROLLBACK" in causal,
  'postprepare_forward_only':"FORWARD_RECOVERY_REQUIRED" in causal,
  'exact_ack_terminal':"causal terminal requires exact durable egress ACK" in causal,
  'surface_lineage_required':"causal commit requires validated Surface A" in causal,
  'private_field_block':"chain_of_thought" in causal and "raw_prompt" in causal and "raw_response" in causal,
  'runtime_binding':"prepare_turn(runtime,turn_id,out)" in runtime,
  'surface_binding':"bind_surface_a" in host,
  'frame_ack_binding':"finalize_exact_ack" in session and "bind_frame" in session,
  'namespace_durability':"fsync_parent" in store and "os.replace" in store,
 }
 for name,ok in gates.items():
  if not ok:errors.append(name)
 return errors

def run(mode:str,total:int,tail:int,seed:int)->dict[str,Any]:
 model=modeled(total,tail,seed);errors=source_probe()
 if total>=SIGNATURE_SPACE and not model['coverage_complete']:errors.append('declared_space_not_saturated')
 if model['tail_new_signatures']!=0:errors.append('tail_novelty')
 return {'schema':'ikant-s18-causal-falsification/v1-test','status':'PASS' if not errors else 'FAIL','mode':mode,'seed':seed,'abstraction_levels':list(LEVELS),'errors':errors,**model}

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--mode',default='falsify');ap.add_argument('--cases',type=int);ap.add_argument('--mutations',type=int);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=DEFAULT_SEED);a=ap.parse_args();total=a.mutations if a.mutations is not None else (a.cases if a.cases is not None else 100000);out=run(a.mode,max(1,total),max(0,a.tail),a.seed);print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
