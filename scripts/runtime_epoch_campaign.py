from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from ikant.managed_runtime import _binding_digest
from ikant.runtime_epoch import compact_epoch, materialize_runtime_epoch, verify_epoch_ledger

MASK64=(1<<64)-1
FAMILIES=48;PHASES=8;CONTEXTS=4;MUTATION_CLASSES=4;SIGNATURE_SPACE=FAMILIES*PHASES*CONTEXTS*MUTATION_CLASSES
FAULT_FAMILIES=(
 "same_material_repeat","live_process_restart","engine_version_change","engine_artifact_change","model_id_change","model_revision_change","model_sha_change","manifest_change",
 "binding_digest_tamper","binding_missing","session_change","contract_version_change","contract_convergence_change","surface_digest_change","config_revision_change","config_digest_change",
 "config_revision_rollback","ledger_json_corruption","ledger_sequence_gap","ledger_predecessor_tamper","ledger_digest_tamper","material_digest_tamper","epoch_id_tamper","current_cache_deleted",
 "current_cache_tamper","crash_after_append","cross_session_receipt","prior_epoch_receipt","unknown_epoch_receipt","unattested_receipt","surface_cache_epoch_drift","running_epoch_rebase",
 "model_as_identity_copy","epoch_as_authority","hash_as_authentication","slsa_claim_without_attestation","browser_stale_component","browser_stale_epoch","service_worker_stale_asset","component_swap_same_session",
 "product_change_same_session","config_change_pending_ack","cycle_epoch_missing","surface_a_epoch_missing","surface_b_epoch_missing","managed_turn_unbound","public_projection_epoch_blocked","epoch_ledger_lock_contention",
)


def splitmix64(value:int)->int:
 value=(value+0x9E3779B97F4A7C15)&MASK64;value=((value^(value>>30))*0xBF58476D1CE4E5B9)&MASK64;value=((value^(value>>27))*0x94D049BB133111EB)&MASK64;return value^(value>>31)
def signature(word:int)->tuple[int,int]:
 family=word%FAMILIES;word//=FAMILIES;phase=word%PHASES;word//=PHASES;context=word%CONTEXTS;word//=CONTEXTS;mutation=word%MUTATION_CLASSES;return family+FAMILIES*(phase+PHASES*(context+CONTEXTS*mutation)),family
def modeled(total:int,tail:int,seed:int)->dict[str,Any]:
 seen=bytearray(SIGNATURE_SPACE);counts=[0]*FAMILIES
 for i in range(total):idx,f=signature(splitmix64(seed+i));seen[idx]=1;counts[f]+=1
 before=sum(seen);new=0
 for i in range(tail):idx,_=signature(splitmix64(seed+10_000_000_019+i));new+=int(not seen[idx]);seen[idx]=1
 return {"cases":total,"fault_families":FAMILIES,"semantic_signature_space":SIGNATURE_SPACE,"semantic_signatures":before,"family_min_hits":min(counts),"family_max_hits":max(counts),"tail":tail,"tail_new_signatures":new,"coverage_complete":before==SIGNATURE_SPACE,"model_results_are_production_reliability_estimates":False}
def _contract(root:Path)->None:(root/'PRODUCT_CONTRACT.json').write_text(json.dumps({'schema':'ikant-product-contract/v0.29-test','product_version':'0.29.0a1','contract_version':'0.18.0','constitutional_convergence':'S17','slices':[{'id':'S1'}]}),encoding='utf-8')
def _runtime(root:Path,epoch=None)->None:
 state=root/'.ikant';state.mkdir(parents=True,exist_ok=True);value={'status':'ACTIVE','session_id':'s17-falsifier','contract_sha256':'c'*64}
 if epoch:value['runtime_epoch']=compact_epoch(epoch)
 (state/'runtime.json').write_text(json.dumps(value),encoding='utf-8')
def _model(root:Path,model_id='model-a',sha='a'*64,status='READY')->None:
 binding={'manifest_sha256':'1'*64,'engine':{'id':'llama.cpp','version':'b9999','platform':'linux-x86_64','artifact_sha256':'2'*64},'model':{'id':model_id,'revision':'3'*40,'sha256':sha}};digest=_binding_digest(binding);payload={'schema':'ikant-managed-local-runtime/v0.23-test','status':status,'managed':True,'manifest_sha256':binding['manifest_sha256'],'binding_sha256':digest,'engine':binding['engine'],'model':binding['model'],'epistemic_authority':0.0,'execution_authority':0.0};(root/'.ikant'/'model-runtime.json').write_text(json.dumps(payload),encoding='utf-8')
def production_probe()->list[str]:
 errors=[]
 with tempfile.TemporaryDirectory(prefix='ikant-s17-probe-') as tmp:
  root=Path(tmp);_runtime(root);_contract(root);_model(root)
  try:
   a=materialize_runtime_epoch(root,require_managed_binding=True);b=materialize_runtime_epoch(root,require_managed_binding=True)
   if a['epoch_id']!=b['epoch_id'] or verify_epoch_ledger(root)['events']!=1:errors.append('stable_material_reused')
   raw=json.loads((root/'.ikant'/'model-runtime.json').read_text(encoding='utf-8'));raw['status']='RESTARTING';(root/'.ikant'/'model-runtime.json').write_text(json.dumps(raw),encoding='utf-8');c=materialize_runtime_epoch(root,require_managed_binding=True)
   if c['epoch_id']!=a['epoch_id']:errors.append('live_status_leaked_into_identity')
   _model(root,'model-b','b'*64);d=materialize_runtime_epoch(root,require_managed_binding=True)
   if d['ordinal']!=2 or d['epoch_id']==a['epoch_id']:errors.append('component_change_not_new_epoch')
   current=root/'.ikant'/'runtime-epoch.json';current.unlink();e=materialize_runtime_epoch(root,require_managed_binding=True)
   if e['epoch_id']!=d['epoch_id'] or verify_epoch_ledger(root)['events']!=2:errors.append('current_cache_recovery')
   if e.get('epistemic_authority')!=0.0 or e.get('execution_authority')!=0.0 or e.get('model_is_identity') is not False:errors.append('authority_or_identity_widening')
  except Exception as exc:errors.append('production_probe:'+type(exc).__name__)
 return errors
def run(mode:str,total:int,tail:int,seed:int)->dict[str,Any]:
 errors=production_probe();model=modeled(total,tail,seed)
 if total>=10_000_000 and not model['coverage_complete']:errors.append('semantic_signature_space_not_saturated')
 if model['tail_new_signatures']!=0:errors.append('tail_novelty')
 return {'schema':'ikant-runtime-epoch-falsification/v1-test','status':'PASS' if not errors else 'FAIL','mode':mode,'seed':seed,'production_epoch_code_executed':True,'errors':errors,**model}
