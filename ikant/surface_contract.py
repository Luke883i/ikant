from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from .foundation import FOUNDATION_SCHEMA, FOUNDATION_VERSION, load_experiment_config
from .public_v1 import public_projection
from .store import atomic_json_write, read_json

SURFACE_CONTRACT_SCHEMA="ikant-surface-contract/v1-test"
SURFACE_MANIFEST_SCHEMA="ikant-surface-manifest/v1-test"
CONFIG_EFFECT_SCHEMA="ikant-config-effect-receipt/v1-test"
ASSET_REVISION="v030-s17-runtime-provenance-epoch-1"
_CACHE_LOCK=threading.RLock();_STABLE_CACHE:dict[tuple[str,str],dict[str,Any]]={}

_ABSTRACTIONS=(
 ("admission_lifecycle",True,True,"canonical_admission_endpoints","admission_state_only","BOUNDED_BY_EXISTING_GOVERNANCE"),
 ("conversation_turn",True,True,"advanced_web_shell_single_writer","sealed_surface_a_turn","NONE"),
 ("generation_config",True,True,"revision_compare_and_swap","generation_only","NONE"),
 ("cognitive_trace",True,False,None,"derived_cycle_projection","NONE"),
 ("epistemic_workspace",True,False,None,"exact_ack_read_only_projection","NONE"),
 ("capability_catalog",True,False,None,"currently_demonstrable_services_only","NONE"),
 ("runtime_systems",True,False,None,"recognized_persisted_inspection_only","NONE"),
 ("enduser_identity_audit",True,False,None,"session_cycle_component_provenance_projection","NONE"),
 ("reactive_work",True,False,None,"derived_cognitive_moment_projection","NONE"),
 ("artifacts",True,False,None,"bounded_same_cycle_read_download","NONE"),
 ("bootstrap_diagnostics",True,False,None,"append_only_diagnostics_projection","NONE"),
 ("voice_candidate",True,True,"current_shell_candidate_only","transcript_candidate_never_auto_submit","NONE"),
)

def _canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def _sha(v:Any)->str:return hashlib.sha256(_canonical(v)).hexdigest()
def _runtime(root:Path)->dict[str,Any]:
 v=read_json(root/".ikant"/"runtime.json",{});return v if isinstance(v,dict) else {}
def _effect_path(root:Path)->Path:return root/".ikant"/"surface-config-effect.json"

def surface_manifest()->dict[str,Any]:
 rows=[{"id":i,"readable":r,"mutable":m,"writer":w,"effect_scope":e,"authority_effect":a,"surfaces":["webapp","floating_pwa_profile"]} for i,r,m,w,e,a in _ABSTRACTIONS]
 material={"schema":SURFACE_MANIFEST_SCHEMA,"abstractions":rows,"single_runtime":True,"presentation_profiles_are_not_separate_runtimes":True,"undeclared_controls_forbidden":True,"future_capabilities_omitted":True}
 digest=_sha(material)
 return {**material,"semantic_contract_sha256":digest,"asset_revision":ASSET_REVISION,"surface_profiles":[{"id":"webapp","semantic_contract_sha256":digest,"authority_effect":"NONE","layout_only":False},{"id":"floating_pwa_profile","semantic_contract_sha256":digest,"authority_effect":"NONE","layout_only":True,"native_os_overlay_claimed":False}],"epistemic_authority":0.0,"execution_authority":0.0}

def record_config_effect(root:str|Path,*,config:dict[str,Any],frame:dict[str,Any])->dict[str,Any]:
 """Persist the zero-authority config revision observed after canonical frame sealing."""
 base=Path(root).resolve();runtime=_runtime(base);session=str(runtime.get("session_id") or "")
 freceipt=frame.get("receipt") if isinstance(frame,dict) else None;cycle=str(freceipt.get("cycle_id") or "") if isinstance(freceipt,dict) else ""
 if not session or not cycle:raise ValueError("config effect receipt requires active session and sealed cycle")
 generation=frame.get("generation") if isinstance(frame,dict) and isinstance(frame.get("generation"),dict) else {}
 if not generation:
  cognitive=runtime.get("cognitive") if isinstance(runtime.get("cognitive"),dict) else {};candidate=cognitive.get("last_surface_a_generation") if isinstance(cognitive.get("last_surface_a_generation"),dict) else {}
  if str(candidate.get("cycle_id") or "")==cycle:generation=candidate
 source=str(generation.get("source") or "UNKNOWN");attempted=source in {"MODEL","OPERATIONAL_FALLBACK"};epoch=runtime.get("runtime_epoch") if isinstance(runtime.get("runtime_epoch"),dict) else {}
 out={"schema":CONFIG_EFFECT_SCHEMA,"runtime_session_id":session,"cycle_id":cycle,"runtime_epoch_id":str(epoch.get("epoch_id") or "") or None,"runtime_epoch_ordinal":epoch.get("ordinal") if isinstance(epoch.get("ordinal"),int) else None,"config_revision":int(config.get("revision") or 0),"config_sha256":_sha(config),"generation_source":source,"model_contract_attempted":attempted,"final_surface_effect_confirmed":source=="MODEL","binding_basis":"POST_SEAL_PRE_ACK_SERIALIZATION","effect_scope":"GENERATION_ONLY","receipt_is_not_authority":True,"epistemic_authority":0.0,"execution_authority":0.0}
 out["receipt_sha256"]=_sha(out);atomic_json_write(_effect_path(base),out);return out

def config_effect_projection(root:str|Path,*,config:dict[str,Any]|None=None)->dict[str,Any]:
 base=Path(root).resolve();runtime=_runtime(base);session=str(runtime.get("session_id") or "") or None;cognitive=runtime.get("cognitive") if isinstance(runtime.get("cognitive"),dict) else {};cycle=str(cognitive.get("last_surface_a_cycle_id") or "") or None;epoch=runtime.get("runtime_epoch") if isinstance(runtime.get("runtime_epoch"),dict) else {};current_epoch_id=str(epoch.get("epoch_id") or "") or None
 current=config if isinstance(config,dict) else load_experiment_config(base);current_rev=int(current.get("revision") or 0);raw=read_json(_effect_path(base),{})
 if not isinstance(raw,dict) or raw.get("schema")!=CONFIG_EFFECT_SCHEMA:return {"schema":CONFIG_EFFECT_SCHEMA,"status":"NO_CYCLE" if not cycle else "UNATTESTED_CYCLE","runtime_session_id":session,"cycle_id":cycle,"runtime_epoch_id":None,"runtime_epoch_binding":"UNATTESTED","current_runtime_epoch_id":current_epoch_id,"current_config_revision":current_rev,"cycle_config_revision":None,"final_surface_effect_confirmed":False,"epistemic_authority":0.0,"execution_authority":0.0}
 body=deepcopy(raw);actual=str(body.pop("receipt_sha256","") or "");valid=actual==_sha(body);body["receipt_sha256"]=actual;same_session=session is not None and body.get("runtime_session_id")==session;same_cycle=cycle is not None and body.get("cycle_id")==cycle;cycle_rev=body.get("config_revision") if isinstance(body.get("config_revision"),int) else None;receipt_epoch=str(body.get("runtime_epoch_id") or "") or None
 if not receipt_epoch:epoch_binding="UNATTESTED"
 elif receipt_epoch==current_epoch_id:epoch_binding="CURRENT"
 else:
  try:
   from .runtime_epoch import known_epoch_ids
   epoch_binding="PRIOR_KNOWN" if receipt_epoch in known_epoch_ids(base) else "UNKNOWN"
  except Exception:epoch_binding="UNKNOWN"
 if not valid:status="RECEIPT_INTEGRITY_BLOCKED"
 elif not same_session or not same_cycle:status="STALE_BINDING"
 elif body.get("generation_source")=="MODEL" and body.get("final_surface_effect_confirmed") is True:status="CONFIRMED_CURRENT" if cycle_rev==current_rev else "CONFIRMED_CYCLE_CONFIG_NOW_CHANGED"
 elif body.get("generation_source")=="OPERATIONAL_FALLBACK":status="MODEL_CONFIG_ATTEMPTED_FINAL_FALLBACK"
 else:status="BYPASSED_NON_MODEL_ROUTE"
 return {**body,"status":status,"runtime_epoch_binding":epoch_binding,"current_runtime_epoch_id":current_epoch_id,"current_config_revision":current_rev,"cycle_config_revision":cycle_rev,"same_session":same_session,"same_cycle":same_cycle,"integrity_verified":valid,"epistemic_authority":0.0,"execution_authority":0.0}

def _state_stamp(root:Path)->dict[str,Any]:
 runtime=_runtime(root);cog=runtime.get("cognitive") if isinstance(runtime.get("cognitive"),dict) else {};epoch=runtime.get("runtime_epoch") if isinstance(runtime.get("runtime_epoch"),dict) else {};config=load_experiment_config(root);transcript=root/".ikant"/"chat"/"transcript.jsonl"
 try:s=transcript.stat();t=[s.st_size,s.st_mtime_ns]
 except OSError:t=[0,0]
 return {"runtime_session_id":str(runtime.get("session_id") or "") or None,"runtime_status":str(runtime.get("status") or "") or None,"runtime_epoch_id":str(epoch.get("epoch_id") or "") or None,"runtime_epoch_ordinal":epoch.get("ordinal") if isinstance(epoch.get("ordinal"),int) else None,"cycle_id":str(cog.get("last_surface_a_cycle_id") or "") or None,"config_revision":int(config.get("revision") or 0),"transcript_stamp":t}

def _safe_product(service:Any)->dict[str,Any]:
 try:v=service.product_status()
 except Exception:return {}
 return v if isinstance(v,dict) else {}

def _foundation_from_public(public:dict[str,Any])->dict[str,Any]:
 return {"schema":FOUNDATION_SCHEMA,"foundation_version":FOUNDATION_VERSION,"config":deepcopy(public.get("config") or {}),"capabilities":deepcopy(public.get("capabilities") or {}),"epistemic_value":deepcopy(public.get("epistemic_value") or {}),"promise":{"local":True,"configurable_generation":True,"shown_services_are_runtime_demonstrable":True,"model_is_replaceable_zero_authority":True,"reported_outcome_is_not_world_truth":True},"epistemic_authority":0.0,"execution_authority":0.0}

def _work_identity(work:dict[str,Any]|None)->dict[str,Any]:
 v=work if isinstance(work,dict) else {};return {"work_id":v.get("work_id"),"phase":v.get("phase"),"active":bool(v.get("active")),"terminal":bool(v.get("terminal")),"cycle_id":v.get("cycle_id")}
def _snapshot_sha(v:dict[str,Any])->str:
 m=deepcopy(v);m.pop("snapshot_sha256",None);return _sha(m)

def _cache_get(root:Path,session:str)->dict[str,Any]|None:
 with _CACHE_LOCK:return deepcopy(_STABLE_CACHE.get((str(root),session))) if session else None
def _cache_put(root:Path,session:str,value:dict[str,Any])->None:
 if session:
  with _CACHE_LOCK:_STABLE_CACHE[(str(root),session)]=deepcopy(value)

def _epoch_file(root:Path)->dict[str,Any]:
 value=read_json(root/".ikant"/"runtime-epoch.json",{});return value if isinstance(value,dict) else {}

def _running_overlay(service:Any,work:dict[str,Any])->dict[str,Any]:
 root=Path(service.root).resolve();stamp=_state_stamp(root);session=str(stamp.get("runtime_session_id") or "");manifest=surface_manifest();cached=_cache_get(root,session);epoch=_epoch_file(root)
 cached_epoch=((cached or {}).get("revision_vector") or {}).get("runtime_epoch_id") if isinstance(cached,dict) else None
 if cached is None or (stamp.get("runtime_epoch_id") and cached_epoch!=stamp.get("runtime_epoch_id")):
  config=load_experiment_config(root);consistency="NONBLOCKING_NO_STABLE_BASE" if cached is None else "NONBLOCKING_EPOCH_REBASE_REQUIRED";out={"schema":SURFACE_CONTRACT_SCHEMA,"version":"S17","asset_revision":ASSET_REVISION,"snapshot_mode":"WORK_OVERLAY","consistency":consistency,"semantic_contract_sha256":manifest["semantic_contract_sha256"],"revision_vector":{**stamp,"work":_work_identity(work)},"manifest":manifest,"runtime_epoch":epoch or None,"product":{},"foundation":{"schema":FOUNDATION_SCHEMA,"foundation_version":FOUNDATION_VERSION,"config":config},"public":None,"work":deepcopy(work),"config_effect":config_effect_projection(root,config=config),"presentation_is_authority":False,"epistemic_authority":0.0,"execution_authority":0.0};out["snapshot_sha256"]=_snapshot_sha(out);return out
 base_sha=cached.get("snapshot_sha256");cached["snapshot_mode"]="WORK_OVERLAY";cached["consistency"]="NONBLOCKING_OVER_STABLE_BASE";cached["base_snapshot_sha256"]=base_sha;cached["runtime_epoch"]=epoch or cached.get("runtime_epoch");cached["work"]=deepcopy(work);vector=dict(cached.get("revision_vector") or {});vector.update(stamp);vector["work"]=_work_identity(work);cached["revision_vector"]=vector;cached["snapshot_sha256"]=_snapshot_sha(cached);return cached

def _stable(service:Any,work:dict[str,Any])->dict[str,Any]:
 root=Path(service.root).resolve();manifest=surface_manifest();public={};before=after=_state_stamp(root);consistency="STABLE"
 for attempt in range(2):
  before=_state_stamp(root);public=public_projection(service);after=_state_stamp(root)
  if before==after:consistency="STABLE" if attempt==0 else "STABLE_AFTER_RETRY";break
  consistency="DRIFT_AFTER_RETRY"
 foundation=_foundation_from_public(public);config=foundation.get("config") if isinstance(foundation.get("config"),dict) else load_experiment_config(root);product=_safe_product(service);conversation=public.get("conversation") if isinstance(public.get("conversation"),dict) else {};epoch=public.get("runtime_epoch") if isinstance(public.get("runtime_epoch"),dict) else None
 vector={**after,"conversation_last_sha256":conversation.get("last_sha256"),"product_stage":product.get("stage"),"product_attempt":product.get("attempt"),"work":_work_identity(work)}
 out={"schema":SURFACE_CONTRACT_SCHEMA,"version":"S17","asset_revision":ASSET_REVISION,"snapshot_mode":"STABLE","consistency":consistency,"semantic_contract_sha256":manifest["semantic_contract_sha256"],"revision_vector":vector,"manifest":manifest,"runtime_epoch":epoch,"product":product,"foundation":foundation,"public":public,"work":deepcopy(work),"config_effect":config_effect_projection(root,config=config),"presentation_is_authority":False,"epistemic_authority":0.0,"execution_authority":0.0};out["snapshot_sha256"]=_snapshot_sha(out)
 if consistency!="DRIFT_AFTER_RETRY":_cache_put(root,str(after.get("runtime_session_id") or ""),out)
 return out

def surface_snapshot(service:Any,*,work:dict[str,Any]|None=None)->dict[str,Any]:
 current=work if isinstance(work,dict) else {}
 return _running_overlay(service,current) if current.get("active") is True and current.get("phase")=="RUNNING" else _stable(service,current)
