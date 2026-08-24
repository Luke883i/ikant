from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'IKANT_DEVELOPMENT_BUNDLE.json'
CONTRACT=ROOT/'PRODUCT_CONTRACT.json'
SCHEMA='ikant-development-continuity-bundle/v1-test'
REQUIRED_SLICE_KEYS={'id','name','foundation_links','expected_runtime','user_experience','technology_supply_chain','dod','success_metrics','checklist','ui_ux_prototype','prerequisites'}
REQUIRED_DOD={'local','intermediate','final'}
REQUIRED_MODES={'DEVELOP','ANTI_ENTROPY_REVIEW','HANDOFF'}

def canonical(value)->bytes:return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def sha(value)->str:return hashlib.sha256(canonical(value)).hexdigest()

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--require-ready',action='store_true');a=ap.parse_args();errors=[]
 try:bundle=json.loads(BUNDLE.read_text(encoding='utf-8'))
 except Exception as exc:raise SystemExit('development bundle unreadable: '+str(exc))
 try:contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
 except Exception as exc:raise SystemExit('product contract unreadable: '+str(exc))
 if bundle.get('schema')!=SCHEMA:errors.append('bundle schema drift')
 baseline=bundle.get('baseline') if isinstance(bundle.get('baseline'),dict) else {}
 if baseline.get('product_contract_current_slice')!=contract.get('constitutional_convergence'):errors.append('bundle/product current-slice drift')
 if baseline.get('product_contract_version')!=contract.get('contract_version'):errors.append('bundle/product contract-version drift')
 roadmap=bundle.get('roadmap') if isinstance(bundle.get('roadmap'),list) else []
 ids=[]
 for row in roadmap:
  if not isinstance(row,dict) or not REQUIRED_SLICE_KEYS.issubset(row):errors.append('roadmap slice shape drift');continue
  ids.append(str(row.get('id') or ''))
  dod=row.get('dod') if isinstance(row.get('dod'),dict) else {}
  if set(dod)!=REQUIRED_DOD:errors.append(f"{row.get('id')} DoD shape drift")
 if len(ids)!=len(set(ids)) or not ids:errors.append('roadmap identity drift')
 protocol=bundle.get('iteration_protocol') if isinstance(bundle.get('iteration_protocol'),dict) else {}
 modes=set((protocol.get('modes') or {}).keys()) if isinstance(protocol.get('modes'),dict) else set()
 if modes!=REQUIRED_MODES:errors.append('iteration modes drift')
 end_choices=protocol.get('end_of_iteration_choices')
 if not isinstance(end_choices,list) or set(end_choices)!=REQUIRED_MODES:errors.append('end-of-iteration choice drift')
 findings=bundle.get('audit_findings') if isinstance(bundle.get('audit_findings'),list) else []
 open_blockers=[x for x in findings if isinstance(x,dict) and x.get('status')=='OPEN' and x.get('severity') in {'CRITICAL','HIGH'}]
 campaigns=bundle.get('modeled_campaigns') if isinstance(bundle.get('modeled_campaigns'),list) else []
 for row in campaigns:
  if row.get('cases')!=10000000 or row.get('tail')!=100000 or row.get('coverage_complete') is not True or row.get('tail_new_signatures')!=0:errors.append('modeled campaign receipt drift')
 status='PASS' if not errors else 'FAIL';ready=not errors and not open_blockers
 out={'schema':'ikant-development-continuity-gate/v1-test','status':status,'ready_to_advance':ready,'bundle_sha256':sha(bundle),'baseline_main_sha':baseline.get('main_sha'),'product_contract_current_slice':contract.get('constitutional_convergence'),'roadmap':ids,'open_high_or_critical_blockers':[x.get('id') for x in open_blockers],'errors':errors,'model_receipts_are_not_runtime_oracles':True}
 print(json.dumps(out,sort_keys=True))
 if errors:return 2
 if a.require_ready and not ready:return 3
 return 0
if __name__=='__main__':raise SystemExit(main())
