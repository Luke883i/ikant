from __future__ import annotations
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.invariants import registry_manifest,CONTRACT_SCHEMA,CONTRACT_VERSION,EGRESS_SCHEMA,PRODUCT_VERSION,critical_ids
from ikant.rights_policy import validate_repository_rights,RIGHTS_SCHEMA
from ikant.component_manifest import load_manifest,MODEL_RUNTIME_SCHEMA
from ikant.bootstrap_runtime import BOOTSTRAP_OBSERVABILITY_SCHEMA

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
if product.get('schema')!='ikant-product-contract/v0.29-test' or product.get('product_version')!=PRODUCT_VERSION:fail('product contract drift')
slice_ids=[x.get('id') for x in product.get('slices',[])]
expected=['S1','S2','S3','S4','S5','S6','S7','S8','S9','S10','S10bis','S11']
if slice_ids!=expected:fail('product slice coverage drift')
if product.get('constitutional_convergence')!='S11':fail('product convergence drift')
if set(product['slices'][-1].get('invariants') or [])-set(critical_ids()):fail('ECF1.3 invariant registry drift')
model_runtime=load_manifest(ROOT/'MODEL_RUNTIME.json')
if model_runtime.get('schema')!=MODEL_RUNTIME_SCHEMA or model_runtime.get('product_version')!='0.23.0a1':fail('historical S5 managed runtime manifest drift')
for name in ('ADMISSION.json','BOOTSTRAP.json'):
 m=json.loads((ROOT/name).read_text(encoding='utf-8'))
 if m.get('contract_version')!=CONTRACT_VERSION:fail(f'{name} contract drift')
 if (m.get('active_human_egress') or {}).get('schema')!=EGRESS_SCHEMA:fail(f'{name} egress drift')
 if (m.get('invariant_registry') or {}).get('schema')!=registry_manifest()['schema']:fail(f'{name} registry schema drift')
 pc=m.get('product_contract') or {};materialized=pc.get('materialized_slices') or []
 if pc.get('schema')!=product['schema'] or pc.get('product_version')!=PRODUCT_VERSION or materialized!=slice_ids[:len(materialized)] or materialized!=slice_ids[:-1]:fail(f'{name} historical product contract prefix drift')
 bos=m.get('bootstrap_observability') or {}
 if bos.get('schema')!=BOOTSTRAP_OBSERVABILITY_SCHEMA or not bos.get('hash_chained') or not bos.get('read_only_diagnostics') or not bos.get('authenticated_diagnostics') or not bos.get('journal_corruption_blocks_bootstrap') or bos.get('epistemic_authority')!=0.0 or bos.get('execution_authority')!=0.0:fail(f'{name} bootstrap observability drift')
rights_ok,rights_errors=validate_repository_rights(ROOT,contract)
if not rights_ok:fail('rights policy drift: '+'; '.join(rights_errors))
if f'version = "{PRODUCT_VERSION}"' not in (ROOT/'pyproject.toml').read_text():fail('package version drift')
if PRODUCT_VERSION not in (ROOT/'ikant'/'__init__.py').read_text():fail('__version__ drift')
for path in ('ikant/__main__.py','ikant/app_cli.py','ikant/session_host.py','ikant/local_app.py'):
 if re.search(r'\b(?:v05_cli|host_v05|dashboard_v05|cognitive_v05)\b',(ROOT/path).read_text()):fail(f'versioned canonical import in {path}')
for inv in registry_manifest()['invariants']:
 target=inv['machine_test'].replace('.','/')
 if inv['severity']=='CRITICAL' and not ((ROOT/(target+'.py')).exists() or inv['machine_test'].startswith('scripts.')):fail('missing critical machine test '+inv['id'])
for path in ('ikant/bootstrap_observability.py','ikant/bootstrap_runtime.py','ikant/bootstrap_http.py','ikant/experience_projection.py','ikant/future_supply.py'):
 if not (ROOT/path).is_file():fail('missing registered module '+path)
print(json.dumps({'schema':'ikant-invariant-registry-check/v0.29-test','ok':True,'product_version':PRODUCT_VERSION,'critical_count':len([x for x in registry_manifest()['invariants'] if x['severity']=='CRITICAL']),'rights_policy':RIGHTS_SCHEMA,'slices':slice_ids},indent=2))
