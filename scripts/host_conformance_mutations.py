from __future__ import annotations
import argparse,copy,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.host_adapter import ReferenceCliHostAdapter
from ikant.host_capabilities import build_manifest,digest,CAPABILITIES
from ikant.host_conformance import run_conformance,REQUIRED_VECTORS,VECTOR_CAPABILITY,validate_conformance_receipt
from ikant.host_negotiation import negotiate_host,PROFILE_REQUIRED_CAPABILITIES
A=ReferenceCliHostAdapter();M=A.manifest();R=run_conformance(A)

def reseal(r):r.pop('sha256',None);r['sha256']=digest(r);return r

def degrade_vector(v):
 r=copy.deepcopy(R);next(x for x in r['vectors'] if x['id']==v)['status']='FAIL';vec={x['id']:x['status'] for x in r['vectors']};r['profiles']={n:('PASS' if all(vec.get(q)=='PASS' for q in req) else 'FAIL') for n,req in REQUIRED_VECTORS.items()};r['overall_status']='PASS' if all(x=='PASS' for x in r['profiles'].values()) else 'FAIL';return reseal(r)

def family(i):
 # 0-10: every vector failure must be detected by validation/profile where required
 if i<11:
  v=list(VECTOR_CAPABILITY)[i];r=degrade_vector(v);ok,_=validate_conformance_receipt(r,M);req_profiles=[p for p,vs in REQUIRED_VECTORS.items() if v in vs];return ok and all(negotiate_host(p,M,r)['status']=='NON_CONFORMING' for p in req_profiles)
 # 11-21: remove every declared capability; affected profile cannot conform
 if i<22:
  cap=sorted(CAPABILITIES)[i-11];caps=[x for x in CAPABILITIES if x!=cap];m=build_manifest(adapter_id=M.adapter_id,adapter_version=M.adapter_version,config_fingerprint=M.config_fingerprint,capabilities=caps);affected=[p for p,cs in PROFILE_REQUIRED_CAPABILITIES.items() if cap in cs];binding_rejected=not validate_conformance_receipt(R,m)[0];return binding_rejected and all(negotiate_host(p,m,R)['status']=='NON_CONFORMING' for p in affected)
 # 22-31: receipt binding/security tamper without reseal must be rejected
 if i<32:
  keys=['adapter_id','adapter_version','config_fingerprint','manifest_sha256','epistemic_authority','execution_authority','actor_authenticated','production_transport_attested','tested_adapter_only','digest_is_integrity_not_authentication'];k=keys[i-22];r=copy.deepcopy(R);r[k]=('evil' if k in keys[:4] else 1 if 'authority' in k else True if k in {'actor_authenticated','production_transport_attested'} else False);return not validate_conformance_receipt(r,M)[0]
 # 32-42: vector status/capability/authority mutation rejected
 if i<43:
  j=i-32;r=copy.deepcopy(R);row=r['vectors'][j%len(r['vectors'])];mode=j%4
  if mode==0:row['status']='SKIP'
  elif mode==1:row['capability']='host.magic'
  elif mode==2:row['epistemic_authority']=1
  else:row['execution_authority']=1
  return not validate_conformance_receipt(r,M)[0]
 # 43-50: profile derivation tamper rejected
 if i<51:
  r=copy.deepcopy(R);p=list(REQUIRED_VECTORS)[(i-43)%4];r['profiles'][p]='FAIL' if r['profiles'][p]=='PASS' else 'PASS';return not validate_conformance_receipt(r,M)[0]
 # 51-58: same valid receipt cannot cross adapter/config/version/manifest
 if i<59:
  variant=i-51
  modes=(('other',M.adapter_version,M.config_fingerprint),(M.adapter_id,'9',M.config_fingerprint),(M.adapter_id,M.adapter_version,'other'),('other','9',M.config_fingerprint),('other',M.adapter_version,'other'),(M.adapter_id,'9','other'),('other','9','other'),('other-v2','10','other-v2'))
  aid,ver,cfg=modes[variant];m=build_manifest(adapter_id=aid,adapter_version=ver,config_fingerprint=cfg,capabilities=CAPABILITIES);return not validate_conformance_receipt(R,m)[0]
 # 59-66: declaration alone/missing receipt/unknown profile must fail closed
 if i<67:
  p=list(PROFILE_REQUIRED_CAPABILITIES)[(i-59)%4];return negotiate_host(p,M,{} )['status']=='NON_CONFORMING' and negotiate_host('UNKNOWN',M,R)['status']=='NON_CONFORMING'
 # 67-74: authority/authentication claims can never appear in negotiation
 p=list(PROFILE_REQUIRED_CAPABILITIES)[(i-67)%4];n=negotiate_host(p,M,R);return n['status']=='CONFORMING' and not n['grants_runtime_authority'] and n['execution_authority']==0 and n['epistemic_authority']==0 and not n['actor_authenticated'] and not n['production_transport_attested']

FAMILIES=75

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);seen=set();survivors=[]
 for i in range(a.mutations):k=rng.randrange(FAMILIES);seen.add(k);
 # evaluate each family at least once plus randomized repetitions
 for k in range(FAMILIES):
  if not family(k):survivors.append(k)
 for i in range(a.mutations):
  k=rng.randrange(FAMILIES)
  if not family(k):survivors.append(k)
 before=len(seen);tail_new=0
 for i in range(a.tail):k=rng.randrange(FAMILIES);tail_new+=k not in seen;seen.add(k);survivors += ([] if family(k) else [k])
 out={'schema':'ikant-host-conformance-mutations/v0.18-test','status':'PASS' if not survivors and len(seen)==FAMILIES and tail_new==0 else 'FAIL','seed':a.seed,'mutations':a.mutations,'tail':a.tail,'families':FAMILIES,'families_seen':len(seen),'tail_new_families':tail_new,'survivors':sorted(set(survivors))};print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
