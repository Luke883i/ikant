from __future__ import annotations
from .host_capabilities import build_manifest,digest
from .execution_receipts import REVALIDATION_RECEIPT_SCHEMA,seal_receipt,validate_revalidation_receipt
_SUPPORTED=frozenset({'native.fs.read','native.fs.create'})
_CAPS=frozenset({'execution.exact_revalidation_binding','execution.zero_runtime_authority','control.receipt_integrity','control.config_binding'})
class NativeExecutionHostAdapter:
    adapter_id='python-native-execution-v0.22';adapter_version='0.22.0a1'
    def __init__(self,*,driver_kind='posix-workspace',security_profile=None):self.driver_kind=str(driver_kind);self.security_profile=dict(security_profile or {})
    @property
    def config_fingerprint(self):return digest({'adapter_id':self.adapter_id,'adapter_version':self.adapter_version,'driver_kind':self.driver_kind,'security_profile':self.security_profile,'supported_capabilities':tuple(sorted(_SUPPORTED))})
    def manifest(self):return build_manifest(adapter_id=self.adapter_id,adapter_version=self.adapter_version,config_fingerprint=self.config_fingerprint,capabilities=_CAPS)
    def probe_human(self,mode='normal'):return {'accepted':False,'error':'UnsupportedProfile'}
    def probe_machine(self,target):return {'accepted':False,'error':'UnsupportedProfile'}
    def sample_handoff(self):return {'handoff_kind':'HOST','handoff_state':'HOST_REVALIDATION_REQUIRED','session_id':'S','cycle_id':'C','intent_sha256':'I','handoff_id':'H','idempotency_key':'K','action_fingerprint':'A','action_ledger_sha256':'AL','plan_ledger_sha256':'PL','action_status':'HOST_EXECUTION_ELIGIBLE','required_capabilities':['native.fs.read']}
    def revalidate(self,envelope):
        required={str(x).strip().casefold() for x in envelope.get('required_capabilities',[]) or []};eligible=envelope.get('handoff_kind')=='HOST' and envelope.get('handoff_state')=='HOST_REVALIDATION_REQUIRED' and envelope.get('action_status')=='HOST_EXECUTION_ELIGIBLE' and bool(required) and required.issubset(_SUPPORTED) and all(self.security_profile.get(k) is True for k in ('workspace_rooted','strong_path_binding','symlink_safe','shell_disabled','process_execution_disabled','secret_access_disabled')) and len(str(self.security_profile.get('workspace_fingerprint') or ''))>=16
        p={'schema':REVALIDATION_RECEIPT_SCHEMA,**{k:envelope.get(k) for k in ('session_id','cycle_id','intent_sha256','handoff_id','idempotency_key','action_fingerprint','action_ledger_sha256','plan_ledger_sha256')},'actor_type':'host','system_safety_law_checked':bool(eligible),'tool_capability_checked':bool(eligible),'current_action_status':'HOST_EXECUTION_ELIGIBLE' if eligible else 'BLOCKED','grants_runtime_execution_authority':False,'executes_action':False};return seal_receipt(p)
    def probe_revalidation(self,drift=False):
        env=self.sample_handoff();r=self.revalidate(env)
        if drift:env={**env,'plan_ledger_sha256':'OTHER'}
        ok,e=validate_revalidation_receipt(env,r);return {'accepted':ok,'errors':e,'receipt':r}
    def probe_legacy_attestation(self):return {'accepted':False,'errors':['unsupported profile']}
