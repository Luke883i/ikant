from __future__ import annotations
from dataclasses import asdict
from typing import Any
from pathlib import Path
from .host_capabilities import validate_manifest,normalize_capability
from .host_conformance import validate_conformance_receipt,run_conformance,REQUIRED_VECTORS,VECTOR_CAPABILITY

HOST_NEGOTIATION_SCHEMA='ikant-host-negotiation/v0.18-test'
PROFILE_REQUIRED_CAPABILITIES={name:frozenset(VECTOR_CAPABILITY[v] for v in vecs) for name,vecs in REQUIRED_VECTORS.items()}

def negotiate_host(profile:str,manifest,receipt)->dict[str,Any]:
    profile=str(profile or '').upper();m=asdict(manifest) if hasattr(manifest,'__dataclass_fields__') else dict(manifest or {});mok,me=validate_manifest(m);rok,re=validate_conformance_receipt(receipt,m)
    req=PROFILE_REQUIRED_CAPABILITIES.get(profile);errors=[]
    if req is None:errors.append('unknown profile');req=frozenset()
    declared=set(m.get('capabilities',[]) or []);missing=sorted(req-declared)
    if missing:errors.extend('missing capability:'+x for x in missing)
    vectors={r.get('id'):r.get('status') for r in (receipt or {}).get('vectors',[]) or []};failed=sorted(v for v in REQUIRED_VECTORS.get(profile,frozenset()) if vectors.get(v)!='PASS')
    if failed:errors.extend('failed vector:'+x for x in failed)
    if not mok:errors.extend('manifest:'+x for x in me)
    if not rok:errors.extend('receipt:'+x for x in re)
    status='CONFORMING' if not errors else 'NON_CONFORMING'
    return {'schema':HOST_NEGOTIATION_SCHEMA,'profile':profile,'status':status,'required_capabilities':sorted(req),'missing_capabilities':missing,'failed_vectors':failed,'errors':errors,'epistemic_authority':0.0,'execution_authority':0.0,'grants_runtime_authority':False,'actor_authenticated':False,'production_transport_attested':False}


def certify_host(adapter,*,profiles=None,persist_path=None)->dict[str,Any]:
    manifest=adapter.manifest();receipt=run_conformance(adapter);wanted=list(profiles or PROFILE_REQUIRED_CAPABILITIES);negotiations={p:negotiate_host(p,manifest,receipt) for p in wanted}
    out={'schema':'ikant-host-certification/v0.18-test','manifest':asdict(manifest),'conformance':receipt,'negotiations':negotiations,'status':'CONFORMING' if all(x['status']=='CONFORMING' for x in negotiations.values()) else 'NON_CONFORMING','epistemic_authority':0.0,'execution_authority':0.0,'actor_authenticated':False,'production_transport_attested':False}
    if persist_path is not None:
        from .store import atomic_json_write
        atomic_json_write(Path(persist_path),out);out['path']=str(Path(persist_path))
    return out
