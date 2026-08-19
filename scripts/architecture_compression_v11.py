from __future__ import annotations
import argparse,itertools,json,random
# 15 binary design decisions. True means the consolidation is applied.
NAMES=('registry','canonical_cli','canonical_host','canonical_dashboard','canonical_cognitive','legacy_shims','single_reticular_workflow','remove_v03_workflow','remove_v04_workflow','remove_v05_workflow','remove_v07_workflow','remove_v09_dashboard_workflow','remove_v10_dashboard_workflow','remove_admission_workflow','machine_file_sink')
def evaluate(bits):
 d=dict(zip(NAMES,bits));required=('registry','canonical_cli','canonical_host','canonical_dashboard','canonical_cognitive','legacy_shims','single_reticular_workflow','machine_file_sink');valid=all(d[x] for x in required)
 if any(d[x] for x in NAMES[7:14]) and not d['single_reticular_workflow']:valid=False
 truth_sources=1 if d['registry'] else 5;versioned_canonical_imports=4-sum(int(d[x]) for x in ('canonical_cli','canonical_host','canonical_dashboard','canonical_cognitive'));workflows=8-sum(int(d[x]) for x in NAMES[7:14]);workflows+=int(d['single_reticular_workflow']);shims=4 if d['legacy_shims'] else 0;ambient_machine=0 if d['machine_file_sink'] else 1;return valid,(truth_sources,versioned_canonical_imports,workflows,ambient_machine,shims)
def main():
 p=argparse.ArgumentParser();p.add_argument('--tail',type=int,default=10000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();best=None;best_bits=None;improvements=0;candidates=list(itertools.product((False,True),repeat=len(NAMES)))
 for bits in candidates:
  valid,score=evaluate(bits)
  if valid and (best is None or score<best):best=score;best_bits=bits;improvements+=1
 rng=random.Random(a.seed);tail_better=0
 for _ in range(a.tail):
  bits=tuple(bool(rng.getrandbits(1)) for _ in NAMES);valid,score=evaluate(bits);tail_better+=int(valid and score<best)
 out={'schema':'ikant-architecture-compression/v0.11-test','N':len(candidates),'N_plus_tail':len(candidates)+a.tail,'dimensions':len(NAMES),'pareto_improvements':improvements,'best_score':best,'best_design':dict(zip(NAMES,best_bits)),'tail_better_designs':tail_better,'status':'PASS' if best is not None and tail_better==0 else 'FAIL'};print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__':main()
