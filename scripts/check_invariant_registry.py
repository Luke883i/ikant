from __future__ import annotations
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.invariants import registry_manifest,CONTRACT_SCHEMA,CONTRACT_VERSION,EGRESS_SCHEMA,PRODUCT_VERSION
from ikant.rights_policy import validate_repository_rights,RIGHTS_SCHEMA
from ikant.component_manifest import load_manifest,MODEL_RUNTIME_SCHEMA
from ikant.advanced_web_shell import ADVANCED_WEB_SHELL_SCHEMA
from ikant.product_experience import PRODUCT_EXPERIENCE_SCHEMA

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
if product.get('schema')!='ikant-product-contract/v0.27-test' or product.get('product_version')!=PRODUCT_VERSION:fail('product contract drift')
slice_ids=[x.get('id') for x in product.get('slices',[])]
if slice_ids!=['S1','S2','S3','S4','S5','S6','S7','S8','S9']:fail('product slice coverage drift')
if product.get('constitutional_convergence')!='S9':fail('product convergence drift')
model_runtime=load_manifest(ROOT/'MODEL_RUNTIME.json')
if model_runtime.get('schema')!=MODEL_RUNTIME_SCHEMA or model_runtime.get('product_version')!='0.23.0a1':fail('historical S5 managed runtime manifest drift')

expected_shell={'schema':ADVANCED_WEB_SHELL_SCHEMA,'single_writer':True,'runtime_session_bound':True,'monotonic_sequence':True,'whole_session_idempotency_keys':True,'exact_previous_frame_binding':True,'legacy_active_mutations_blocked_after_claim':True,'semantic_output_channel':'HSPV2_SEALED_DASHBOARD_ONLY','browser_is_authority':False,'shell_state_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}
expected_experience={'schema':PRODUCT_EXPERIENCE_SCHEMA,'setup_visible_before_model_ready':True,'browser_may_mark_ready':False,'single_semantic_viewport':True,'progressive_disclosure':True,'traditional_controls_on_demand':True,'remote_frontend_dependencies':False,'browser_model_transport':False,'voice_input_auto_submit':False,'voice_input_is_approval':False,'voice_output_requires_local_service':True,'voice_output_requires_post_ack_turn':True,'diagnostics_are_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}
for name in ('ADMISSION.json','BOOTSTRAP.json'):
 m=json.loads((ROOT/name).read_text(encoding='utf-8'))
 if m.get('contract_version')!=CONTRACT_VERSION:fail(f'{name} contract drift')
 if (m.get('active_human_egress') or {}).get('schema')!=EGRESS_SCHEMA:fail(f'{name} egress drift')
 if (m.get('invariant_registry') or {}).get('schema')!=registry_manifest()['schema']:fail(f'{name} registry schema drift')
 pc=m.get('product_contract') or {}
 if pc.get('schema')!=product['schema'] or pc.get('product_version')!=PRODUCT_VERSION or pc.get('materialized_slices')!=slice_ids:fail(f'{name} product contract drift')
 if (m.get('agency_kernel') or {}).get('schema')!='ikant-capability-grant/v0.19-test':fail(f'{name} agency kernel drift')
 if (m.get('local_embodiment') or {}).get('schema')!='ikant-local-embodiment/v0.20-test':fail(f'{name} local embodiment drift')
 if (m.get('web_agency') or {}).get('schema')!='ikant-web-execution/v0.21-test':fail(f'{name} web agency drift')
 if (m.get('native_agency') or {}).get('schema')!='ikant-native-execution/v0.22-test':fail(f'{name} native agency drift')
 if (m.get('managed_local_runtime') or {}).get('schema')!=MODEL_RUNTIME_SCHEMA:fail(f'{name} managed runtime drift')
 if (m.get('temporal_autonomy') or {}).get('schema')!='ikant-temporal-autonomy/v0.24-test':fail(f'{name} temporal autonomy drift')
 if (m.get('human_surface_protocol') or {}).get('schema')!='ikant-human-surface-protocol/v0.25-test':fail(f'{name} human surface drift')
 shell=m.get('advanced_web_shell') or {}
 for key,value in expected_shell.items():
  if shell.get(key)!=value:fail(f'{name} advanced web shell {key} drift')
 experience=m.get('product_experience') or {}
 for key,value in expected_experience.items():
  if experience.get(key)!=value:fail(f'{name} product experience {key} drift')
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
for path in ('ikant/agency_kernel.py','ikant/local_service.py','ikant/web_agency.py','ikant/native_agency.py','ikant/managed_runtime.py','ikant/temporal_autonomy.py','ikant/human_surface_protocol.py','ikant/advanced_web_shell.py','ikant/product_experience.py'):
 if not (ROOT/path).is_file():fail('missing constitutional module '+path)
print(json.dumps({'schema':'ikant-invariant-registry-check/v0.27-test','ok':True,'product_version':PRODUCT_VERSION,'critical_count':len([x for x in registry_manifest()['invariants'] if x['severity']=='CRITICAL']),'rights_policy':RIGHTS_SCHEMA,'slices':slice_ids},indent=2))
