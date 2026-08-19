from __future__ import annotations
from pathlib import Path
from typing import Any
from .host_negotiation import certify_host
from .execution_receipts import validate_revalidation_receipt

HOST_SDK_SCHEMA='ikant-host-sdk/v0.18-test'

class HostRuntimeBinding:
    def __init__(self,adapter,*,persist_path=None):
        self.adapter=adapter;self.certification=certify_host(adapter,persist_path=persist_path)
    def require(self,profile:str)->dict[str,Any]:
        p=str(profile or '').upper();n=(self.certification.get('negotiations') or {}).get(p)
        if n is None:
            # certify all profiles lazily without changing adapter/config
            self.certification=certify_host(self.adapter,profiles=[p])
            n=(self.certification.get('negotiations') or {}).get(p)
        if not n or n.get('status')!='CONFORMING':raise PermissionError('host profile not conforming: '+p)
        return n
    def legacy_resume_attestation(self):
        self.require('BREACH_RESUME')
        if not hasattr(self.adapter,'legacy_attestation'):raise PermissionError('adapter cannot materialize legacy transport attestation')
        return self.adapter.legacy_attestation()
    def revalidate_execution(self,envelope:dict[str,Any])->dict[str,Any]:
        self.require('EXECUTION_HANDOFF');receipt=self.adapter.revalidate(envelope);ok,errs=validate_revalidation_receipt(envelope,receipt)
        if not ok:raise PermissionError('adapter produced invalid execution revalidation: '+'; '.join(errs))
        return receipt
    def status(self)->dict[str,Any]:
        return {'schema':HOST_SDK_SCHEMA,'adapter_id':self.certification.get('manifest',{}).get('adapter_id'),'status':self.certification.get('status'),'epistemic_authority':0.0,'execution_authority':0.0,'actor_authenticated':False,'production_transport_attested':False,'runtime_executes_actions':False}
