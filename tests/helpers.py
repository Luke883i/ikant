from pathlib import Path
from ikant.admission import issue_receipt,save_receipt,probe,save_probe
from ikant.runtime import Runtime
from ikant.dynamics import DynamicsParameters

SOURCE_ROOT=Path(__file__).resolve().parents[1]
_ADMISSION_FIXTURE_FILES=('IKANT_ACCESS_CONTRACT.md','BOOTSTRAP.json','ADMISSION.json')

def materialized_fixture_root(tmp:Path)->Path:
    """Build a post-acceptance synthetic checkout that obeys the current admission policy."""
    root=tmp/'repo';root.mkdir();(root/'ikant').mkdir();(root/'ikant'/'runtime.py').write_text('# fixture',encoding='utf-8')
    for name in _ADMISSION_FIXTURE_FILES:
        (root/name).write_text((SOURCE_ROOT/name).read_text(encoding='utf-8'),encoding='utf-8')
    return root

def active_runtime(tmp:Path,*,durable=False,params=None):
    root=materialized_fixture_root(tmp);contract=(root/'IKANT_ACCESS_CONTRACT.md').read_text(encoding='utf-8');s=root/'.ikant'
    save_receipt(s,issue_receipt(contract,'I ACCEPT'));p=probe(root,s,contract)
    if p.get('overall')!='READY':raise RuntimeError(f"fixture admission probe blocked: {p.get('checks')}")
    save_probe(s,p);return Runtime.initialize(s,contract,durable=durable,params=params or DynamicsParameters())
