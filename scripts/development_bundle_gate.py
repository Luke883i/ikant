from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'IKANT_DEVELOPMENT_BUNDLE.json';CONTRACT=ROOT/'PRODUCT_CONTRACT.json';SCHEMA='ikant-development-continuity-bundle/v1-test'
REQUIRED_SLICE_KEYS={'id','name','foundation_links','expected_runtime','user_experience','technology_supply_chain','dod','success_metrics','checklist','ui_ux_prototype','prerequisites'}
REQUIRED_DOD={'local','intermediate','final'};REQUIRED_MODES={'DEVELOP','ANTI_ENTROPY_REVIEW','HANDOFF'};BLOCKING_SEVERITIES={'CRITICAL','HIGH'};COMMIT_RE=re.compile(r'^[0-9a-f]{40}$')
def canonical(v)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def sha(v)->str:return hashlib.sha256(canonical(v)).hexdigest()
def _open_blocking(rows):return [r for r in rows if isinstance(r,dict) and r.get('status')=='OPEN' and r.get('severity') in BLOCKING_SEVERITIES]
def _git(*args):return subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True,check=False)

def _verify_baseline(main_sha:str,merged_pr)->tuple[str,list[str]]:
 errors=[]
 if not COMMIT_RE.fullmatch(main_sha):return 'INVALID',['baseline main sha invalid']
 exists=_git('cat-file','-e',main_sha+'^{commit}').returncode==0
 if exists:
  if _git('merge-base','--is-ancestor',main_sha,'HEAD').returncode!=0:errors.append('baseline main is not ancestor of checkout')
  subject=_git('show','-s','--format=%s',main_sha).stdout.strip()
  if isinstance(merged_pr,int) and f'#{merged_pr}' not in subject:errors.append('baseline main merge subject/pr drift')
  return 'FULL_HISTORY',errors
 parents=_git('show','-s','--format=%P','HEAD').stdout.strip().split()
 if main_sha in parents:return 'SYNTHETIC_MERGE_PARENT',errors
 errors.append('baseline main commit unavailable and not a synthetic-merge parent');return 'UNVERIFIED',errors

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--require-ready',action='store_true');ap.add_argument('--require-complete',action='store_true');ap.add_argument('--require-advance',action='store_true');args=ap.parse_args();errors=[]
 try:bundle=json.loads(BUNDLE.read_text(encoding='utf-8'))
 except Exception as exc:raise SystemExit('development bundle unreadable: '+str(exc))
 try:contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
 except Exception as exc:raise SystemExit('product contract unreadable: '+str(exc))
 if bundle.get('schema')!=SCHEMA:errors.append('bundle schema drift')
 baseline=bundle.get('baseline') if isinstance(bundle.get('baseline'),dict) else {}
 if baseline.get('product_contract_version')!=contract.get('contract_version'):errors.append('bundle/candidate contract-version drift')
 main_sha=str(baseline.get('main_sha') or '');merged_pr=baseline.get('merged_pr');merged_slice=str(baseline.get('merged_slice') or '');baseline_slice=str(baseline.get('product_contract_current_slice') or '')
 git_mode,git_errors=_verify_baseline(main_sha,merged_pr);errors.extend(git_errors)
 if merged_slice!=baseline_slice:errors.append('baseline merged/product slice drift')
 roadmap=bundle.get('roadmap') if isinstance(bundle.get('roadmap'),list) else [];ids=[]
 for row in roadmap:
  if not isinstance(row,dict) or not REQUIRED_SLICE_KEYS.issubset(row):errors.append('roadmap slice shape drift');continue
  sid=str(row.get('id') or '');ids.append(sid);dod=row.get('dod') if isinstance(row.get('dod'),dict) else {}
  if set(dod)!=REQUIRED_DOD:errors.append(f'{sid} DoD shape drift')
 if len(ids)!=len(set(ids)) or not ids:errors.append('roadmap identity drift')
 candidate=str(baseline.get('candidate_slice') or '')
 if not candidate or candidate not in ids:errors.append('candidate slice missing from roadmap')
 contract_slice=str(contract.get('constitutional_convergence') or '')
 if contract_slice==baseline_slice:registration_state='DEVELOPMENT_CANDIDATE'
 elif candidate and contract_slice==candidate:registration_state='REGISTERED_CANDIDATE'
 else:registration_state='INVALID';errors.append('bundle/product promotion drift')
 dag=bundle.get('dependency_dag') if isinstance(bundle.get('dependency_dag'),dict) else {};edges=dag.get('causal_edges') if isinstance(dag.get('causal_edges'),list) else []
 for edge in edges:
  if not isinstance(edge,list) or len(edge)!=2 or edge[0] not in ids or edge[1] not in ids:errors.append('dependency DAG edge drift');break
 protocol=bundle.get('iteration_protocol') if isinstance(bundle.get('iteration_protocol'),dict) else {};modes=set((protocol.get('modes') or {}).keys()) if isinstance(protocol.get('modes'),dict) else set()
 if modes!=REQUIRED_MODES:errors.append('iteration modes drift')
 choices=protocol.get('end_of_iteration_choices')
 if not isinstance(choices,list) or set(choices)!=REQUIRED_MODES:errors.append('end-of-iteration choice drift')
 findings=bundle.get('audit_findings') if isinstance(bundle.get('audit_findings'),list) else [];open_blocking=_open_blocking(findings);candidate_objectives=[r for r in open_blocking if r.get('owner_slice')==candidate];candidate_entry_blockers=[r for r in open_blocking if r.get('owner_slice')!=candidate and candidate in (r.get('blocks_slices') if isinstance(r.get('blocks_slices'),list) else [])];future_open_risks=[r for r in open_blocking if r not in candidate_objectives and r not in candidate_entry_blockers]
 campaigns=bundle.get('modeled_campaigns') if isinstance(bundle.get('modeled_campaigns'),list) else []
 for row in campaigns:
  if row.get('cases')!=10_000_000 or row.get('tail')!=100_000 or row.get('coverage_complete') is not True or row.get('tail_new_signatures')!=0:errors.append('modeled campaign receipt drift')
 status='PASS' if not errors else 'FAIL';ready=not errors and not candidate_entry_blockers;complete=not errors and not candidate_objectives;advance=ready and complete and registration_state=='REGISTERED_CANDIDATE'
 out={'schema':'ikant-development-continuity-gate/v4-test','status':status,'candidate_slice':candidate,'candidate_registration_state':registration_state,'ready_to_develop_candidate':ready,'candidate_complete':complete,'ready_to_advance':advance,'bundle_sha256':sha(bundle),'baseline_main_sha':main_sha,'baseline_merged_pr':merged_pr,'baseline_merged_slice':merged_slice,'baseline_product_contract_current_slice':baseline_slice,'product_contract_current_slice':contract_slice,'roadmap':ids,'candidate_entry_blockers':[x.get('id') for x in candidate_entry_blockers],'candidate_open_objectives':[x.get('id') for x in candidate_objectives],'future_open_risks':[x.get('id') for x in future_open_risks],'errors':errors,'registered_candidate_is_not_merged_main':registration_state=='REGISTERED_CANDIDATE','git_baseline_checked':git_mode in {'FULL_HISTORY','SYNTHETIC_MERGE_PARENT'},'git_baseline_check_mode':git_mode,'full_history_lineage_deferred_to_product_boundary':git_mode=='SYNTHETIC_MERGE_PARENT','model_receipts_are_not_runtime_oracles':True}
 print(json.dumps(out,sort_keys=True))
 if errors:return 2
 if args.require_ready and not ready:return 3
 if args.require_complete and not complete:return 4
 if args.require_advance and not advance:return 5
 return 0
if __name__=='__main__':raise SystemExit(main())
