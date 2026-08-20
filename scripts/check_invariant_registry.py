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
 if (m.get('product_contract') or {}).get('schema')!='ikant-product-contract/v0.22-test':fail(f'{name} product contract drift')
 if (m.get('product_contract') or {}).get('product_version')!=PRODUCT_VERSION:fail(f'{name} product version drift')
 for key,schema in (('practical_reason','ikant-practical-reason/v0.15-test'),('planning','ikant-planning/v0.16-test'),('execution_protocol','ikant-execution-protocol/v0.17-test')):
  if (m.get(key) or {}).get('schema')!=schema:fail(f'{name} {key} drift')
 host=m.get('host_conformance') or {}
 if host.get('schema')!='ikant-host-conformance-receipt/v0.18-test':fail(f'{name} host conformance drift')
 agency=m.get('agency_kernel') or {}
 if agency.get('schema')!='ikant-capability-grant/v0.19-test' or agency.get('one_shot_leases') is not True:fail(f'{name} agency kernel drift')
 embodiment=m.get('local_embodiment') or {}
 if embodiment.get('schema')!='ikant-local-embodiment/v0.20-test' or embodiment.get('model_output_is_authority') is not False:fail(f'{name} embodiment drift')
 web=m.get('web_agency') or {}
 if web.get('schema')!='ikant-web-agency/v0.21-test' or web.get('requires_fresh_s1_lease') is not True:fail(f'{name} web agency drift')
 native=m.get('native_agency') or {}
 if native.get('schema')!='ikant-native-agency/v0.22-test' or native.get('requires_fresh_s1_lease') is not True:fail(f'{name} native agency drift')
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
for path in ('ikant/provenance.py','ikant/calibration.py','ikant/hybrid_retrieval.py','ikant/causal_crc.py','ikant/epistemic_core.py','ikant/temporal_memory.py','ikant/commitments.py','ikant/dependency_invalidation.py','ikant/temporal_replay.py','ikant/temporal_core.py','ikant/authority.py','ikant/approvals.py','ikant/action_governance.py','ikant/practical_reason.py','ikant/plan_graph.py','ikant/world_model.py','ikant/decision_lattice.py','ikant/planning.py','ikant/execution_handoff.py','ikant/execution_receipts.py','ikant/outcome_reconciliation.py','ikant/execution_protocol.py','ikant/host_capabilities.py','ikant/host_adapter.py','ikant/host_conformance.py','ikant/host_negotiation.py','ikant/host_sdk.py','ikant/human_frame.py','ikant/agency_kernel.py','ikant/local_service.py','ikant/web_agency.py','ikant/native_agency.py'):
 if not (ROOT/path).is_file():fail('missing constitutional module '+path)
print(json.dumps({'schema':'ikant-invariant-registry-check/v0.22-test','ok':True,'product_version':PRODUCT_VERSION,'critical_count':len([x for x in registry_manifest()['invariants'] if x['severity']=='CRITICAL']),'rights_policy':RIGHTS_SCHEMA,'agency_kernel':'v0.19','local_embodiment':'v0.20','web_agency':'v0.21','native_agency':'v0.22'},indent=2))
