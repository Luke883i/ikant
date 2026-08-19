from __future__ import annotations
import io,tempfile
from pathlib import Path
from typing import Any
from .host_capabilities import build_manifest,digest,CAPABILITIES
from .transport import deliver_human,write_machine_payload,build_reference_attestation,validate_transport_attestation
from .execution_receipts import REVALIDATION_RECEIPT_SCHEMA,seal_receipt,validate_revalidation_receipt

class _Partial(io.StringIO):
    def write(self,s):super().write(s[:-1]);return max(0,len(s)-1)
class _FlushFail(io.StringIO):
    def flush(self):raise OSError('forced flush failure')

class ReferenceCliHostAdapter:
    adapter_id='python-cli-reference-v0.18';adapter_version='0.18.0a1'
    def __init__(self,*,config_tag='stdio+file'):self.config_tag=str(config_tag)
    @property
    def config_fingerprint(self):return digest({'adapter_id':self.adapter_id,'adapter_version':self.adapter_version,'config_tag':self.config_tag})
    def manifest(self):return build_manifest(adapter_id=self.adapter_id,adapter_version=self.adapter_version,config_fingerprint=self.config_fingerprint,capabilities=CAPABILITIES)
    def probe_human(self,mode='normal'):
        stream=io.StringIO() if mode=='normal' else _Partial() if mode=='partial' else _FlushFail()
        try:n=deliver_human('frame-bytes',stream=stream);return {'accepted':True,'written':n,'value':stream.getvalue()}
        except Exception as exc:return {'accepted':False,'error':type(exc).__name__}
    def probe_machine(self,target):
        with tempfile.TemporaryDirectory() as td:
            path=target if target in {'stdout','stderr','-','/dev/stdout','/dev/stderr',''} else str(Path(td)/'machine.json')
            try:out=write_machine_payload(path,{'probe':True});return {'accepted':True,'path':out,'exists':Path(out).exists()}
            except Exception as exc:return {'accepted':False,'error':type(exc).__name__}
    def sample_handoff(self):return {'handoff_kind':'HOST','session_id':'S','cycle_id':'C','intent_sha256':'I','handoff_id':'H','idempotency_key':'K','action_fingerprint':'A','action_ledger_sha256':'AL','plan_ledger_sha256':'PL'}
    def revalidate(self,envelope):
        p={'schema':REVALIDATION_RECEIPT_SCHEMA,**{k:envelope.get(k) for k in ('session_id','cycle_id','intent_sha256','handoff_id','idempotency_key','action_fingerprint','action_ledger_sha256','plan_ledger_sha256')},'actor_type':'host','system_safety_law_checked':True,'tool_capability_checked':True,'current_action_status':'HOST_EXECUTION_ELIGIBLE','grants_runtime_execution_authority':False,'executes_action':False};return seal_receipt(p)
    def probe_revalidation(self,drift=False):
        env=self.sample_handoff();rec=self.revalidate(env)
        if drift:env={**env,'plan_ledger_sha256':'OTHER'}
        ok,errs=validate_revalidation_receipt(env,rec);return {'accepted':ok,'errors':errs,'receipt':rec}
    def legacy_attestation(self):return build_reference_attestation(machine_sink='disabled')
    def probe_legacy_attestation(self):
        att=self.legacy_attestation();ok,errs=validate_transport_attestation(att);return {'accepted':ok,'errors':errs}
