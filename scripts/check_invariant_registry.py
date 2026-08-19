from __future__ import annotations
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT))
from ikant.invariants import registry_manifest,CONTRACT_SCHEMA,CONTRACT_VERSION,EGRESS_SCHEMA,PRODUCT_VERSION
from ikant.rights_policy import validate_repository_rights,RIGHTS_SCHEMA

def fail(msg):raise SystemExit(msg)
contract=(ROOT/'IKANT_ACCESS_CONTRACT.md').read_text(encoding='utf-8');head={}
for line in contract.splitlines()[1:]:
 if line.strip()=='---':break
 if ':' in line:k,v=line.split(':',1);head[k.strip()]=v.strip()
if head.get('schema')!=CONTRACT_SCHEMA or head.get('contract_version')!=CONTRACT_VERSION:fail('contract registry drift')
if head.get('rights_policy_schema')!=RIGHTS_SCHEMA:fail('rights schema drift')
for name in ('ADMISSION.json','BOOTSTRAP.json'):
 m=json.loads((ROOT/name).read_text(encoding='utf-8'))
 if m.get('contract_version')!=CONTRACT_VERSION:fail(f'{name} contract drift')
 if (m.get('active_human_egress') or {}).get('schema')!=EGRESS_SCHEMA:fail(f'{name} egress drift')
 if (m.get('invariant_registry') or {}).get('schema')!=registry_manifest()['schema']:fail(f'{name} registry schema drift')
 if (m.get('practical_reason') or {}).get('schema')!='ikant-practical-reason/v0.15-test':fail(f'{name} practical reason drift')
 if (m.get('planning') or {}).get('schema')!='ikant-planning/v0.16-test':fail(f'{name} planning drift')
 if float((m.get('planning') or {}).get('epistemic_authority',1))!=0.0:fail(f'{name} planning epistemic authority drift')
 exe=m.get('execution_protocol') or {}
 if exe.get('schema')!='ikant-execution-protocol/v0.17-test':fail(f'{name} execution protocol drift')
 if float(exe.get('epistemic_authority',1))!=0.0 or float(exe.get('execution_authority',1))!=0.0:fail(f'{name} execution authority drift')
 if exe.get('runtime_executes_actions') is not False:fail(f'{name} execution runtime drift')
 if exe.get('receipt_digest_authenticates_actor') is not False or exe.get('host_transport_authentication_external') is not True:fail(f'{name} receipt authentication boundary drift')
rights_ok,rights_errors=validate_repository_rights(ROOT,contract)
if not rights_ok:fail('rights policy drift: '+'; '.join(rights_errors))
if f'version = "{PRODUCT_VERSION}"' not in (ROOT/'pyproject.toml').read_text():fail('package version drift')
if PRODUCT_VERSION not in (ROOT/'ikant'/'__init__.py').read_text():fail('__version__ drift')
for path in ('ikant/__main__.py','ikant/app_cli.py','ikant/session_host.py'):
 text=(ROOT/path).read_text()
 if re.search(r'\b(?:v05_cli|host_v05|dashboard_v05|cognitive_v05)\b',text):fail(f'versioned canonical import in {path}')
for inv in registry_manifest()['invariants']:
 target=inv['machine_test'].replace('.','/')
 if inv['severity']=='CRITICAL' and not ((ROOT/(target+'.py')).exists() or inv['machine_test'].startswith('scripts.')):fail('missing critical machine test '+inv['id'])
for path in ('ikant/provenance.py','ikant/calibration.py','ikant/hybrid_retrieval.py','ikant/causal_crc.py','ikant/epistemic_core.py'):
 if not (ROOT/path).is_file():fail('missing epistemic core module '+path)
for path in ('ikant/temporal_memory.py','ikant/commitments.py','ikant/dependency_invalidation.py','ikant/temporal_replay.py','ikant/temporal_core.py'):
 if not (ROOT/path).is_file():fail('missing temporal epistemics module '+path)
for path in ('ikant/authority.py','ikant/approvals.py','ikant/action_governance.py','ikant/practical_reason.py'):
 if not (ROOT/path).is_file():fail('missing practical reason module '+path)
for path in ('ikant/plan_graph.py','ikant/world_model.py','ikant/decision_lattice.py','ikant/planning.py'):
 if not (ROOT/path).is_file():fail('missing planning module '+path)
for path in ('ikant/execution_handoff.py','ikant/execution_receipts.py','ikant/outcome_reconciliation.py','ikant/execution_protocol.py'):
 if not (ROOT/path).is_file():fail('missing execution protocol module '+path)
print(json.dumps({'schema':'ikant-invariant-registry-check/v0.17-test','ok':True,'critical_count':len([x for x in registry_manifest()['invariants'] if x['severity']=='CRITICAL']),'rights_policy':RIGHTS_SCHEMA,'epistemic_core':'ikant-epistemic-core/v0.13-test','temporal_epistemics':'ikant-temporal-epistemics/v0.14-test','practical_reason':'ikant-practical-reason/v0.15-test','planning':'ikant-planning/v0.16-test','execution_protocol':'ikant-execution-protocol/v0.17-test'},indent=2))
