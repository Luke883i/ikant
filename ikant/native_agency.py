from __future__ import annotations
from typing import Any
from .execution_receipts import EXECUTION_RECEIPT_SCHEMA,seal_receipt
from .native_actions import required_entitlements,validate_native_action

NATIVE_EXECUTION_SCHEMA='ikant-native-execution/v0.22-test'
class NativeAgencyError(PermissionError):pass

def _lease_entitlements(lease):return {(str(x.get('capability') or ''),str(x.get('resource') or '')) for x in lease.get('entitlements',[]) or []}

class NativeAgency:
    def __init__(self,*,driver,agency_kernel,agency_host_binding):self.driver=driver;self.agency=agency_kernel;self.host=agency_host_binding
    def observe(self,path):return self.driver.snapshot(path)
    def execute(self,action:dict[str,Any],envelope:dict[str,Any],lease:dict[str,Any])->dict[str,Any]:
        try:snapshot=self.driver.snapshot(action.get('path'))
        except Exception as exc:raise NativeAgencyError('native snapshot unavailable') from exc
        ok,e=validate_native_action(action,snapshot)
        if not ok:raise NativeAgencyError('native action invalid or stale: '+'; '.join(e))
        try:expected=set(required_entitlements(action,envelope))
        except (ValueError,TypeError) as exc:raise NativeAgencyError(str(exc)) from exc
        if _lease_entitlements(lease)!=expected:raise NativeAgencyError('S1 lease entitlements do not exactly bind native action')
        profile=getattr(self.driver,'security_profile',{})
        if not all(profile.get(k) is True for k in ('workspace_rooted','strong_path_binding','symlink_safe','shell_disabled','process_execution_disabled','secret_access_disabled')):raise NativeAgencyError('native driver security profile is not S4-conforming')
        preflight=self.driver.preflight(action)
        if preflight.snapshot['sha256']!=snapshot['sha256']:raise NativeAgencyError('native target drift during preflight')
        revalidation=self.host.revalidate_execution(envelope,lease)
        after=self.driver.snapshot(action['path'])
        if after['sha256']!=snapshot['sha256']:raise NativeAgencyError('native target drift after host revalidation')
        self.agency.consume_lease(lease['lease_id'],reason='S4 native actuator commit point reached')
        try:
            outcome=self.driver.commit(preflight);status='EXECUTED';ref=str(outcome.get('execution_ref') or '')
        except Exception as exc:
            outcome={'status':'FAILED','error_type':type(exc).__name__,'observed_predicates':[],'world_truth_verified':False,'epistemic_authority':0.0};status='FAILED';ref='native-failed-'+action['sha256'][:16]
        receipt=seal_receipt({'schema':EXECUTION_RECEIPT_SCHEMA,**{k:envelope.get(k) for k in ('session_id','cycle_id','intent_sha256','handoff_id','idempotency_key','action_fingerprint','action_ledger_sha256','plan_ledger_sha256')},'actor_type':'host','outcome':status,'execution_ref':ref,'observed_predicates':list(outcome.get('observed_predicates') or []),'runtime_epistemic_authority':0.0,'grants_runtime_execution_authority':False,'causes_runtime_execution':False})
        return {'schema':NATIVE_EXECUTION_SCHEMA,'action_sha256':action['sha256'],'target_snapshot_sha256':snapshot['sha256'],'lease_id':lease['lease_id'],'lease_consumed_before_external_commit':True,'host_revalidation':revalidation.get('host_revalidation') if isinstance(revalidation,dict) else revalidation,'native_outcome':outcome,'native_content_is_untrusted_observation':True,'world_truth_verified':False,'epistemic_authority':0.0,'execution_authority':0.0,'execution_receipt':receipt}
