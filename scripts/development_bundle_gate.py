from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'IKANT_DEVELOPMENT_BUNDLE.json'
CONTRACT=ROOT/'PRODUCT_CONTRACT.json'
SCHEMA='ikant-development-continuity-bundle/v1-test'
REQUIRED_SLICE_KEYS={'id','name','foundation_links','expected_runtime','user_experience','technology_supply_chain','dod','success_metrics','checklist','ui_ux_prototype','prerequisites'}
REQUIRED_DOD={'local','intermediate','final'}
REQUIRED_MODES={'DEVELOP','ANTI_ENTROPY_REVIEW','HANDOFF'}
BLOCKING_SEVERITIES={'CRITICAL','HIGH'}

def _sha(value)->str:
 raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
 return hashlib.sha256(raw).hexdigest()

def _event_base_sha()->str|None:
 path=os.environ.get('GITHUB_EVENT_PATH')
 if not path:return None
 try:
  event=json.loads(Path(path).read_text(encoding='utf-8'))
  value=(((event.get('pull_request') or {}).get('base') or {}).get('sha'))
  return str(value) if value else None
 except Exception:return None

def _candidates(baseline:dict)->list[str]:
 raw=baseline.get('candidate_slices')
 if isinstance(raw,list) and raw and all(isinstance(x,str) and x for x in raw):return list(dict.fromkeys(raw))
 value=str(baseline.get('candidate_slice') or '')
 return [value] if value else []

def _campaign_errors(rows:list)->list[str]:
 errors=[]
 for row in rows:
  if not isinstance(row,dict):errors.append('modeled campaign shape drift');continue
  cases=row.get('cases');tail=row.get('tail');space=row.get('signature_space')
  if isinstance(cases,bool) or not isinstance(cases,int) or cases<1:errors.append('modeled campaign cases drift')
  if isinstance(tail,bool) or not isinstance(tail,int) or tail<0:errors.append('modeled campaign tail drift')
  if isinstance(space,bool) or not isinstance(space,int) or space<1 or row.get('signatures_observed')!=space:errors.append('modeled campaign coverage drift')
  if row.get('coverage_complete') is not True or row.get('tail_new_signatures')!=0:errors.append('modeled campaign convergence drift')
  if 'not' not in str(row.get('interpretation') or '').lower():errors.append('modeled campaign claim boundary drift')
 return errors

def main()->int:
 parser=argparse.ArgumentParser();parser.add_argument('--require-ready',action='store_true');parser.add_argument('--require-complete',action='store_true');parser.add_argument('--require-advance',action='store_true');args=parser.parse_args()
 errors=[]
 bundle=json.loads(BUNDLE.read_text(encoding='utf-8'));contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
 if bundle.get('schema')!=SCHEMA:errors.append('bundle schema drift')
 baseline=bundle.get('baseline') if isinstance(bundle.get('baseline'),dict) else {}
 main_sha=str(baseline.get('main_sha') or '');merged_slice=str(baseline.get('merged_slice') or '');baseline_slice=str(baseline.get('product_contract_current_slice') or '')
 if merged_slice!=baseline_slice:errors.append('baseline merged/product slice drift')
 if baseline.get('product_contract_version')!=contract.get('contract_version'):errors.append('bundle/candidate contract-version drift')
 event_base=_event_base_sha();git_mode='DEFERRED_TO_PRODUCT_BOUNDARY'
 if event_base:
  git_mode='GITHUB_EVENT_BASE'
  if event_base!=main_sha:errors.append('baseline main differs from pull_request.base.sha')
 roadmap=bundle.get('roadmap') if isinstance(bundle.get('roadmap'),list) else [];ids=[]
 for row in roadmap:
  if not isinstance(row,dict) or not REQUIRED_SLICE_KEYS.issubset(row):errors.append('roadmap slice shape drift');continue
  ids.append(str(row.get('id') or ''));dod=row.get('dod') if isinstance(row.get('dod'),dict) else {}
  if set(dod)!=REQUIRED_DOD:errors.append('roadmap DoD shape drift')
 if not ids or len(ids)!=len(set(ids)):errors.append('roadmap identity drift')
 candidates=_candidates(baseline)
 if not candidates or any(x not in ids for x in candidates):errors.append('candidate slice set missing from roadmap')
 dag=bundle.get('dependency_dag') if isinstance(bundle.get('dependency_dag'),dict) else {};edges=dag.get('causal_edges') if isinstance(dag.get('causal_edges'),list) else []
 if any(not isinstance(e,list) or len(e)!=2 or e[0] not in ids or e[1] not in ids for e in edges):errors.append('dependency DAG edge drift')
 if len(candidates)>1 and set(candidates) not in [set(x) for x in dag.get('commutable_siblings',[]) if isinstance(x,list)]:errors.append('composite candidate set is not declared commutable')
 contract_slice=str(contract.get('constitutional_convergence') or '');contract_ids=[str(x.get('id') or '') for x in contract.get('slices',[]) if isinstance(x,dict)]
 if contract_slice==baseline_slice:registration='DEVELOPMENT_CANDIDATE_SET' if len(candidates)>1 else 'DEVELOPMENT_CANDIDATE'
 elif candidates and contract_slice==candidates[-1] and contract_ids[-len(candidates):]==candidates:registration='REGISTERED_CANDIDATE_SET' if len(candidates)>1 else 'REGISTERED_CANDIDATE'
 else:registration='INVALID';errors.append('bundle/product promotion drift')
 protocol=bundle.get('iteration_protocol') if isinstance(bundle.get('iteration_protocol'),dict) else {};modes=set((protocol.get('modes') or {}).keys()) if isinstance(protocol.get('modes'),dict) else set()
 if modes!=REQUIRED_MODES or set(protocol.get('end_of_iteration_choices') or [])!=REQUIRED_MODES:errors.append('iteration protocol drift')
 findings=bundle.get('audit_findings') if isinstance(bundle.get('audit_findings'),list) else [];open_rows=[r for r in findings if isinstance(r,dict) and r.get('status')=='OPEN' and r.get('severity') in BLOCKING_SEVERITIES];candidate_set=set(candidates)
 objectives=[r for r in open_rows if r.get('owner_slice') in candidate_set]
 blockers=[r for r in open_rows if r.get('owner_slice') not in candidate_set and candidate_set.intersection(r.get('blocks_slices') if isinstance(r.get('blocks_slices'),list) else [])]
 future=[r for r in open_rows if r not in objectives and r not in blockers]
 errors.extend(_campaign_errors(bundle.get('modeled_campaigns') if isinstance(bundle.get('modeled_campaigns'),list) else []))
 ready=not errors and not blockers;complete=not errors and not objectives;registered=registration in {'REGISTERED_CANDIDATE','REGISTERED_CANDIDATE_SET'};advance=ready and complete and registered
 out={'schema':'ikant-development-continuity-gate/v5-test','status':'PASS' if not errors else 'FAIL','candidate_slice':candidates[0] if candidates else None,'candidate_slices':candidates,'candidate_registration_state':registration,'ready_to_develop_candidate':ready,'candidate_complete':complete,'ready_to_advance':advance,'bundle_sha256':_sha(bundle),'baseline_main_sha':main_sha,'baseline_merged_pr':baseline.get('merged_pr'),'baseline_merged_slice':merged_slice,'baseline_product_contract_current_slice':baseline_slice,'product_contract_current_slice':contract_slice,'roadmap':ids,'candidate_entry_blockers':[x.get('id') for x in blockers],'candidate_open_objectives':[x.get('id') for x in objectives],'future_open_risks':[x.get('id') for x in future],'errors':errors,'registered_candidate_is_not_merged_main':registered,'git_baseline_checked':git_mode=='GITHUB_EVENT_BASE','git_baseline_check_mode':git_mode,'full_history_lineage_deferred_to_product_boundary':True,'model_receipts_are_not_runtime_oracles':True,'composite_candidate_support':True}
 print(json.dumps(out,sort_keys=True))
 if errors:return 2
 if args.require_ready and not ready:return 3
 if args.require_complete and not complete:return 4
 if args.require_advance and not advance:return 5
 return 0

if __name__=='__main__':raise SystemExit(main())
