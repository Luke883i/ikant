from __future__ import annotations
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.invariants import registry_manifest,CONTRACT_SCHEMA,CONTRACT_VERSION,EGRESS_SCHEMA,PRODUCT_VERSION
from ikant.rights_policy import validate_repository_rights,RIGHTS_SCHEMA
from ikant.component_manifest import load_manifest,MODEL_RUNTIME_SCHEMA
from ikant.advanced_web_shell import ADVANCED_WEB_SHELL_SCHEMA
from ikant.product_experience import PRODUCT_EXPERIENCE_SCHEMA
from ikant.epistemic_projection import EPISTEMIC_WORKSPACE_SCHEMA

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
if product.get('schema')!='ikant-product-contract/v0.28-test' or product.get('product_version')!=PRODUCT_VERSION:fail('product contract drift')
slice_ids=[x.get('id') for x in product.get('slices',[])]
if slice_ids!=['S1','S2','S3','S4','S5','S6','S7','S8','S9','S10']:fail('product slice coverage drift')
if product.get('constitutional_convergence')!='S10':fail('product convergence drift')
model_runtime=load_manifest(ROOT/'MODEL_RUNTIME.json')
if model_runtime.get('schema')!=MODEL_RUNTIME_SCHEMA or model_runtime.get('product_version')!='0.23.0a1':fail('historical S5 managed runtime manifest drift')
expected_shell={'schema':ADVANCED_WEB_SHELL_SCHEMA,'single_writer':True,'runtime_session_bound':True,'monotonic_sequence':True,'whole_session_idempotency_keys':True,'exact_previous_frame_binding':True,'legacy_active_mutations_blocked_after_claim':True,'semantic_output_channel':'HSPV2_SEALED_DASHBOARD_ONLY','browser_is_authority':False,'shell_state_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}
expected_experience={'schema':PRODUCT_EXPERIENCE_SCHEMA,'setup_visible_before_model_ready':True,'browser_may_mark_ready':False,'single_semantic_viewport':True,'progressive_disclosure':True,'traditional_controls_on_demand':True,'remote_frontend_dependencies':False,'browser_model_transport':False,'voice_input_auto_submit':False,'voice_input_is_approval':False,'voice_output_requires_local_service':True,'voice_output_requires_post_ack_turn':True,'diagnostics_are_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}
expected_epistemic={'schema':EPISTEMIC_WORKSPACE_SCHEMA,'read_only':True,'requires_current_s8_writer':True,'requires_exact_last_ack':True,'pending_frame_blocks_read':True,'same_session_cycle_required':True,'history_limit':64,'object_limit':96,'snapshot_max_bytes':4194304,'artifact_download_max_bytes':16777216,'docx_requires_json_companion':True,'projection_is_source_truth':False,'presentation_is_evidence':False,'presentation_is_authorization':False,'second_semantic_surface':False,'persistence_added':False,'epistemic_authority':0.0,'execution_authority':0.0}
for name in ('ADMISSION.json','BOOTSTRAP.json'):
 m=json.loads((ROOT/name).read_text(encoding='utf-8'))
 if m.get('contract_version')!=CONTRACT_VERSION:fail(f'{name} contract drift')
 if (m.get('active_human_egress') or {}).get('schema')!=EGRESS_SCHEMA:fail(f'{name} egress drift')
 if (m.get('invariant_registry') or {}).get('schema')!=registry_manifest()['schema']:fail(f'{name} registry schema drift')
 pc=m.get('product_contract') or {}
 if pc.get('schema')!=product['schema'] or pc.get('product_version')!=PRODUCT_VERSION or pc.get('materialized_slices')!=slice_ids:fail(f'{name} product contract drift')
 for field,schema in (('agency_kernel','ikant-capability-grant/v0.19-test'),('local_embodiment','ikant-local-embodiment/v0.20-test'),('web_agency','ikant-web-execution/v0.21-test'),('native_agency','ikant-native-execution/v0.22-test'),('managed_local_runtime',MODEL_RUNTIME_SCHEMA),('temporal_autonomy','ikant-temporal-autonomy/v0.24-test'),('human_surface_protocol','ikant-human-surface-protocol/v0.25-test')):
  if (m.get(field) or {}).get('schema')!=schema:fail(f'{name} {field} drift')
 for field,expected in (('advanced_web_shell',expected_shell),('product_experience',expected_experience),('epistemic_workspace',expected_epistemic)):
  value=m.get(field) or {}
  for key,want in expected.items():
   if value.get(key)!=want:fail(f'{name} {field} {key} drift')
rights_ok,rights_errors=validate_repository_rights(ROOT,contract)
if not rights_ok:fail('rights policy drift: '+'; '.join(rights_errors))
if f'version = "{PRODUCT_VERSION}"' not in (ROOT/'pyproject.toml').read_text():fail('package version drift')
if PRODUCT_VERSION not in (ROOT/'ikant'/'__init__.py').read_text():fail('__version__ drift')
for path in ('ikant/__main__.py','ikant/app_cli.py','ikant/session_host.py','ikant/local_app.py'):
 text=(ROOT/path).read_text()
 if re.search(r'\b(?:v05_cli|host_v05|dashboard_v05|cognitive_v05)\b',text):fail(f'versioned canonical import in {path}')
for inv in registry_manifest()['invariants']:
 target=inv['machine_test'].replace('.','/')
 if inv['severity']=='CRITICAL' and not ((ROOT/(target+'.py')).exists() or inv['machine_test'].startswith('scripts.')):fail('missing critical machine test '+inv['id'])
for path in ('ikant/agency_kernel.py','ikant/local_service.py','ikant/web_agency.py','ikant/native_agency.py','ikant/managed_runtime.py','ikant/temporal_autonomy.py','ikant/human_surface_protocol.py','ikant/advanced_web_shell.py','ikant/product_experience.py','ikant/epistemic_projection.py','ikant/epistemic_workspace.py','ikant/epistemic_http.py'):
 if not (ROOT/path).is_file():fail('missing constitutional module '+path)
print(json.dumps({'schema':'ikant-invariant-registry-check/v0.28-test','ok':True,'product_version':PRODUCT_VERSION,'critical_count':len([x for x in registry_manifest()['invariants'] if x['severity']=='CRITICAL']),'rights_policy':RIGHTS_SCHEMA,'slices':slice_ids},indent=2))
