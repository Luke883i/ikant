from __future__ import annotations
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.invariants import registry_manifest,CONTRACT_SCHEMA,CONTRACT_VERSION,EGRESS_SCHEMA,PRODUCT_VERSION
from ikant.rights_policy import validate_repository_rights,RIGHTS_SCHEMA
from ikant.component_manifest import load_manifest,MODEL_RUNTIME_SCHEMA

def fail(msg):raise SystemExit(msg)
def contract_head(text):
 out={}
 for line in text.splitlines()[1:]:
  if line.strip()=='---':break
  if ':' in line:k,v=line.split(':',1);out[k.strip()]=v.strip()
 return out
contract=(ROOT/'IKANT_ACCESS_CONTRACT.md').read_text(encoding='utf-8');head=contract_head(contract)
if head.get('schema')!=CONTRACT_SCHEMA or head.get('contract_version')!=CONTRACT_VERSION:fail('contract registry drift')
if head.get('rights_policy_schema')!=RIGHTS_SCHEMA:fail('rights schema drift')
product=json.loads((ROOT/'PRODUCT_CONTRACT.json').read_text(encoding='utf-8'))
if product.get('schema')!='ikant-product-contract/v0.24-test' or product.get('product_version')!=PRODUCT_VERSION:fail('product contract drift')
slice_ids=[x.get('id') for x in product.get('slices',[])]
if slice_ids!=['S1','S2','S3','S4','S5','S6']:fail('product slice coverage drift')
if product.get('constitutional_convergence')!='S6':fail('product convergence drift')
# MODEL_RUNTIME is the immutable S5 component contract; a later product version must not rewrite its identity.
model_runtime=load_manifest(ROOT/'MODEL_RUNTIME.json')
if model_runtime.get('schema')!=MODEL_RUNTIME_SCHEMA or model_runtime.get('product_version')!='0.23.0a1':fail('historical S5 managed runtime manifest drift')
for name in ('ADMISSION.json','BOOTSTRAP.json'):
 m=json.loads((ROOT/name).read_text(encoding='utf-8'))
 if m.get('contract_version')!=CONTRACT_VERSION:fail(f'{name} contract drift')
 if (m.get('active_human_egress') or {}).get('schema')!=EGRESS_SCHEMA:fail(f'{name} egress drift')
 if (m.get('invariant_registry') or {}).get('schema')!=registry_manifest()['schema']:fail(f'{name} registry schema drift')
 pc=m.get('product_contract') or {}
 if pc.get('schema')!=product['schema'] or pc.get('product_version')!=PRODUCT_VERSION or pc.get('materialized_slices')!=slice_ids:fail(f'{name} product contract drift')
 if (m.get('practical_reason') or {}).get('schema')!='ikant-practical-reason/v0.15-test':fail(f'{name} practical reason drift')
 if (m.get('planning') or {}).get('schema')!='ikant-planning/v0.16-test':fail(f'{name} planning drift')
 if (m.get('execution_protocol') or {}).get('schema')!='ikant-execution-protocol/v0.17-test':fail(f'{name} execution protocol drift')
 if (m.get('host_conformance') or {}).get('schema')!='ikant-host-conformance-receipt/v0.18-test':fail(f'{name} host conformance drift')
 if (m.get('agency_kernel') or {}).get('schema')!='ikant-capability-grant/v0.19-test' or (m.get('agency_kernel') or {}).get('one_shot_leases') is not True:fail(f'{name} agency kernel drift')
 if (m.get('local_embodiment') or {}).get('schema')!='ikant-local-embodiment/v0.20-test' or (m.get('local_embodiment') or {}).get('model_output_is_authority') is not False:fail(f'{name} embodiment drift')
 if (m.get('web_agency') or {}).get('schema')!='ikant-web-execution/v0.21-test' or (m.get('web_agency') or {}).get('requires_fresh_s1_lease') is not True:fail(f'{name} web agency drift')
 if (m.get('native_agency') or {}).get('schema')!='ikant-native-execution/v0.22-test' or (m.get('native_agency') or {}).get('requires_fresh_s1_lease') is not True:fail(f'{name} native agency drift')
 mlr=m.get('managed_local_runtime') or {}
 if mlr.get('schema')!=MODEL_RUNTIME_SCHEMA or mlr.get('immutable_component_pins_required') is not True or mlr.get('digest_verification_required') is not True or mlr.get('loopback_private_engine') is not True or mlr.get('browser_model_transport') is not False or mlr.get('api_key_persisted') is not False or mlr.get('fake_ready_allowed') is not False or mlr.get('model_output_is_authority') is not False or mlr.get('epistemic_authority')!=0.0 or mlr.get('execution_authority')!=0.0:fail(f'{name} managed runtime drift')
 tmp=m.get('temporal_autonomy') or {}
 expected_tmp={'schema':'ikant-temporal-autonomy/v0.24-test','hash_chained':True,'session_bound':True,'human_action_confirmation_required':True,'fixed_duration_recurring_only':True,'miss_policy':'COALESCE','wall_clock_epoch_ms':True,'monotonic_wait':True,'clock_rollback_blocks':True,'requires_locked_egress_to_poll':True,'hardware_wake':False,'os_background_service':False,'model_called_by_scheduler':False,'material_execution_bridge':False,'pre_wake_approval_reusable':False,'pre_wake_grant_reusable':False,'pre_wake_lease_reusable':False,'fresh_host_revalidation_required':True,'automatic_material_retry':False,'epistemic_authority':0.0,'execution_authority':0.0}
 for key,value in expected_tmp.items():
  if tmp.get(key)!=value:fail(f'{name} temporal autonomy {key} drift')
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
for path in ('ikant/provenance.py','ikant/calibration.py','ikant/hybrid_retrieval.py','ikant/causal_crc.py','ikant/epistemic_core.py','ikant/temporal_memory.py','ikant/commitments.py','ikant/dependency_invalidation.py','ikant/temporal_replay.py','ikant/temporal_core.py','ikant/authority.py','ikant/approvals.py','ikant/action_governance.py','ikant/practical_reason.py','ikant/plan_graph.py','ikant/world_model.py','ikant/decision_lattice.py','ikant/planning.py','ikant/execution_handoff.py','ikant/execution_receipts.py','ikant/outcome_reconciliation.py','ikant/execution_protocol.py','ikant/host_capabilities.py','ikant/host_adapter.py','ikant/host_conformance.py','ikant/host_negotiation.py','ikant/host_sdk.py','ikant/human_frame.py','ikant/agency_kernel.py','ikant/local_service.py','ikant/web_agency.py','ikant/native_agency.py','ikant/component_manifest.py','ikant/component_store.py','ikant/download_manager.py','ikant/model_manager.py','ikant/engine_supervisor.py','ikant/managed_runtime.py','ikant/temporal_autonomy.py'):
 if not (ROOT/path).is_file():fail('missing constitutional module '+path)
print(json.dumps({'schema':'ikant-invariant-registry-check/v0.24-test','ok':True,'product_version':PRODUCT_VERSION,'critical_count':len([x for x in registry_manifest()['invariants'] if x['severity']=='CRITICAL']),'rights_policy':RIGHTS_SCHEMA,'agency_kernel':'v0.19','local_embodiment':'v0.20','web_agency':'v0.21','native_agency':'v0.22','managed_local_runtime':'v0.23','temporal_autonomy':'v0.24'},indent=2))
