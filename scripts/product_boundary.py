from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));HARNESS_KEYS=('stress','mutations','edges');SCHEMA_RE=re.compile(r'^ikant-product-contract/(v0\.\d+-test)$');SLICE_RE=re.compile(r'^S([1-9]\d*)(bis)?$')
def fail(msg:str)->None:raise SystemExit(msg)
def valid_lineage(ids:list[str])->bool:
 if not ids or ids[0]!='S1':return False
 prev_n=1;prev_bis=False
 for sid in ids[1:]:
  m=SLICE_RE.fullmatch(sid)
  if not m:return False
  n=int(m.group(1));bis=bool(m.group(2))
  if prev_bis:
   if bis or n!=prev_n+1:return False
  else:
   if bis:
    if n!=prev_n:return False
   elif n!=prev_n+1:return False
  prev_n,prev_bis=n,bis
 return True
def load_contract()->dict:
 p=ROOT/'PRODUCT_CONTRACT.json'
 try:data=json.loads(p.read_text(encoding='utf-8'))
 except Exception as exc:fail('product contract unreadable: '+str(exc))
 match=SCHEMA_RE.fullmatch(str(data.get('schema') or ''))
 if not match:fail('product contract schema drift')
 slices=data.get('slices')
 if not isinstance(slices,list) or not slices:fail('product slices missing')
 ids=[str(x.get('id') or '') for x in slices]
 if not valid_lineage(ids):fail('product slice order/coverage drift')
 if data.get('constitutional_convergence')!=ids[-1]:fail('constitutional convergence must equal current slice')
 return data
def validate_paths(data:dict)->list[str]:
 errors=[];owned=set()
 for s in data['slices']:
  sid=str(s.get('id') or '');match=SLICE_RE.fullmatch(sid);corrective=bool(match and match.group(2))
  test=ROOT/(str(s.get('machine_test') or '').replace('.','/')+'.py')
  if not test.is_file():errors.append(f"{sid} missing machine test")
  seeded=s.get('seeded_harnesses')
  if not isinstance(seeded,list) or any(x not in HARNESS_KEYS for x in seeded) or len(set(seeded))!=len(seeded):errors.append(f"{sid} invalid seeded_harnesses")
  inv=s.get('invariants')
  if not isinstance(inv,list) or not inv or len(set(inv))!=len(inv):errors.append(f"{sid} invalid invariant ownership")
  else:
   inv_set=set(inv);overlap=owned&inv_set
   if overlap:
    if not corrective or overlap!=inv_set:errors.append(f"{sid} duplicate invariant ownership: {','.join(sorted(overlap))}")
   else:owned.update(inv_set)
  for key in HARNESS_KEYS:
   if not (ROOT/str(s.get(key) or '')).is_file():errors.append(f"{sid} missing {key}")
 return errors
def command_for(s:dict,key:str,cases:int,tail:int,seed:int)->list[str]:
 size_arg='--mutations' if key=='mutations' else '--cases';cmd=[sys.executable,s[key],size_arg,str(cases),'--tail',str(tail)]
 if key in s['seeded_harnesses']:cmd.extend(('--seed',str(seed)))
 return cmd
def run_harnesses(data:dict,cases:int,tail:int,seed:int)->None:
 for s in data['slices']:
  for key in HARNESS_KEYS:subprocess.run(command_for(s,key,cases,tail,seed),cwd=ROOT,check=True)
def run_current_saturation(data:dict)->dict:
 current=data['slices'][-1];sat=current.get('saturation')
 if not isinstance(sat,dict):fail('current slice saturation contract missing')
 required={'cases','mutations','edges','tail','seed'}
 if set(sat)!=required or any(isinstance(sat[k],bool) or not isinstance(sat[k],int) for k in required):fail('current slice saturation contract invalid')
 if min(sat.values())<0 or sat['cases']<1 or sat['mutations']<1 or sat['edges']<1:fail('current slice saturation bounds invalid')
 sizes={'stress':sat['cases'],'mutations':sat['mutations'],'edges':sat['edges']}
 for key in HARNESS_KEYS:subprocess.run(command_for(current,key,sizes[key],sat['tail'],sat['seed']),cwd=ROOT,check=True)
 return {'slice':current['id'],**sat}
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--deep-current',action='store_true');ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();data=load_contract();errors=validate_paths(data)
 if errors:fail('; '.join(errors))
 from ikant.invariants import PRODUCT_VERSION,INVARIANT_REGISTRY_SCHEMA,critical_ids
 if data.get('product_version')!=PRODUCT_VERSION:fail('product version drift')
 suffix=SCHEMA_RE.fullmatch(data['schema']).group(1)
 if INVARIANT_REGISTRY_SCHEMA!='ikant-invariant-registry/'+suffix:fail('registry schema drift')
 required={inv for s in data['slices'] for inv in s['invariants']}
 if not required.issubset(set(critical_ids())):fail('registered slice invariant coverage drift')
 if a.execute and a.deep_current:fail('--execute and --deep-current are mutually exclusive')
 if a.execute:run_harnesses(data,a.cases,a.tail,a.seed)
 saturation=run_current_saturation(data) if a.deep_current else None
 print(json.dumps({'schema':'ikant-product-boundary/'+suffix,'status':'PASS','product_version':PRODUCT_VERSION,'slices':[s['id'] for s in data['slices']],'harnesses_executed':bool(a.execute),'current_saturation':saturation},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())