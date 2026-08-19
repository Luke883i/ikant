from __future__ import annotations
import argparse,copy,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.host_adapter import ReferenceCliHostAdapter
from ikant.host_capabilities import build_manifest,digest
from ikant.host_conformance import run_conformance,VECTOR_CAPABILITY,REQUIRED_VECTORS
from ikant.host_negotiation import negotiate_host
UNIVERSE=65536
DOMAINS=('python_cli','tty_wrapper','notebook_bridge','websocket_gateway','ci_runner','ide_terminal','remote_shell','batch_worker')
PROFILES=('HUMAN_EGRESS','MACHINE_OUTPUT','EXECUTION_HANDOFF','BREACH_RESUME')
VECTORS=('HUMAN_EXACT_WRITE','HUMAN_PARTIAL_REJECT','HUMAN_FLUSH_REJECT','MACHINE_FILE_ONLY','MACHINE_CHANNEL_SEPARATE','MACHINE_STDOUT_REJECT','EXEC_REVALIDATION_BIND','EXEC_ZERO_AUTHORITY','LEGACY_ATTESTATION_VALID','MANIFEST_INTEGRITY','CONFIG_BOUND')
BASE_A=ReferenceCliHostAdapter();BASE_M=BASE_A.manifest();BASE_R=run_conformance(BASE_A)

def scenario(idx):
 bits=[bool(idx&(1<<i)) for i in range(16)];domain=DOMAINS[(idx>>3)%len(DOMAINS)];profile=PROFILES[(idx>>1)%len(PROFILES)]
 r=copy.deepcopy(BASE_R);m=BASE_M.__dict__.copy()
 # Circumstances: declaration, tested vector quality, binding drift and forbidden authority/auth claims.
 if not bits[0]:m['capabilities']=[x for x in m['capabilities'] if x not in set([VECTOR_CAPABILITY[v] for v in REQUIRED_VECTORS[profile]])]
 if not bits[1]:r['adapter_id']='other-adapter'
 if not bits[2]:r['config_fingerprint']='other-config'
 for j,v in enumerate(VECTORS[:9],start=3):
  if not bits[j]:next(x for x in r['vectors'] if x['id']==v)['status']='FAIL'
 if not bits[12]:r['actor_authenticated']=True
 if not bits[13]:r['execution_authority']=1.0
 if not bits[14]:r['production_transport_attested']=True
 # bit15 controls whether internal derivation/digest is coherent after mutations
 if bits[15]:
  vec={x['id']:x['status'] for x in r['vectors']};r['profiles']={name:('PASS' if all(vec.get(v)=='PASS' for v in req) else 'FAIL') for name,req in REQUIRED_VECTORS.items()};r['overall_status']='PASS' if all(x=='PASS' for x in r['profiles'].values()) else 'FAIL';r.pop('sha256',None);r['sha256']=digest(r)
 # manifest mutations must be canonical/digest-bound if bit15, otherwise drift is intentional
 if bits[15]:
  try:mobj=build_manifest(adapter_id=m['adapter_id'],adapter_version=m['adapter_version'],config_fingerprint=m['config_fingerprint'],capabilities=m['capabilities'])
  except ValueError:mobj=m
 else:mobj=m
 n=negotiate_host(profile,mobj,r)
 # invariants across all realistic host contexts
 if n['epistemic_authority']!=0 or n['execution_authority']!=0 or n['grants_runtime_authority'] or n['actor_authenticated'] or n['production_transport_attested']:raise AssertionError('authority/auth leakage')
 sig=(domain,profile,n['status'],tuple(n['missing_capabilities']),tuple(n['failed_vectors']),bool(n['errors']))
 return sig

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=100000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);order=list(range(UNIVERSE));rng.shuffle(order);seen=set();covered=set()
 for i in range(a.cases):idx=order[i%UNIVERSE];covered.add(idx);seen.add(scenario(idx))
 before=len(seen);tail_new=0
 for i in range(a.tail):idx=order[(a.cases+i)%UNIVERSE];s=scenario(idx);tail_new+=s not in seen;seen.add(s)
 saturated=a.cases>=UNIVERSE;expected=min(a.cases,UNIVERSE);status='PASS' if len(covered)==expected and (not saturated or tail_new==0) else 'FAIL'
 out={'schema':'ikant-host-conformance-stress/v0.18-test','status':status,'seed':a.seed,'cases':a.cases,'tail':a.tail,'domains':len(DOMAINS),'profiles':len(PROFILES),'explicit_universe':UNIVERSE,'covered_configurations':len(covered),'expected_coverage':expected,'causal_signatures':len(seen),'signatures_before_tail':before,'tail_new_signatures':tail_new,'saturated':saturated};print(json.dumps(out,sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
