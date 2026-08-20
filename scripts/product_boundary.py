from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).parents[1]
EXPECTED_SCHEMA='ikant-product-contract/v0.22-test'
EXPECTED_SLICES=('S1','S2','S3','S4')

def fail(msg:str)->None:
    raise SystemExit(msg)

def load_contract()->dict:
    p=ROOT/'PRODUCT_CONTRACT.json'
    try:data=json.loads(p.read_text(encoding='utf-8'))
    except Exception as exc:fail('product contract unreadable: '+str(exc))
    if data.get('schema')!=EXPECTED_SCHEMA:fail('product contract schema drift')
    if tuple(x.get('id') for x in data.get('slices',[]))!=EXPECTED_SLICES:fail('product slice order/coverage drift')
    return data

def validate_paths(data:dict)->list[str]:
    errors=[]
    for s in data['slices']:
        test=ROOT/(s['machine_test'].replace('.','/')+'.py')
        if not test.is_file():errors.append(f"{s['id']} missing machine test")
        for key in ('stress','mutations','edges'):
            if not (ROOT/s[key]).is_file():errors.append(f"{s['id']} missing {key}")
    return errors

def run_harnesses(data:dict,cases:int,tail:int,seed:int)->None:
    for s in data['slices']:
        commands=(
            [sys.executable,s['stress'],'--cases',str(cases),'--tail',str(tail),'--seed',str(seed)],
            [sys.executable,s['mutations'],'--mutations',str(cases),'--tail',str(tail),'--seed',str(seed)],
            [sys.executable,s['edges'],'--cases',str(cases),'--tail',str(tail),'--seed',str(seed)],
        )
        for cmd in commands:subprocess.run(cmd,cwd=ROOT,check=True)

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
    data=load_contract();errors=validate_paths(data)
    if errors:fail('; '.join(errors))
    from ikant.invariants import PRODUCT_VERSION,INVARIANT_REGISTRY_SCHEMA,critical_ids
    if data.get('product_version')!=PRODUCT_VERSION:fail('product version drift')
    if INVARIANT_REGISTRY_SCHEMA!='ikant-invariant-registry/v0.22-test':fail('registry schema drift')
    required={'AGY-001','AGY-002','AGY-003','EMB-001','EMB-002','WEB-001','WEB-002','NAT-001','NAT-002','NAT-003'}
    if not required.issubset(set(critical_ids())):fail('S1-S4 invariant coverage drift')
    if a.execute:run_harnesses(data,a.cases,a.tail,a.seed)
    print(json.dumps({'schema':'ikant-product-boundary/v0.22-test','status':'PASS','product_version':PRODUCT_VERSION,'slices':list(EXPECTED_SLICES),'harnesses_executed':bool(a.execute)},sort_keys=True))
    return 0
if __name__=='__main__':raise SystemExit(main())
