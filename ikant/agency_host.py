from __future__ import annotations
from typing import Any
from .agency_kernel import AgencyKernel,AgencyAuthorityError

AGENCY_HOST_SCHEMA='ikant-agency-host-binding/v0.19-test'

class AgencyHostBinding:
    """Conjunctive bridge: v0.18 host conformance AND current v0.19 execution lease.

    It never executes a material action. It only returns a revalidation bundle for an external host.
    """
    def __init__(self,host_binding:Any,agency:AgencyKernel):
        self.host=host_binding;self.agency=agency
    def revalidate_execution(self,envelope:dict[str,Any],lease:dict[str,Any],*,now:float|None=None)->dict[str,Any]:
        ok,errors=self.agency.validate_lease(lease,envelope,now=now)
        if not ok:raise AgencyAuthorityError('agency lease invalid: '+'; '.join(errors))
        host_receipt=self.host.revalidate_execution(envelope)
        return {'schema':AGENCY_HOST_SCHEMA,'session_id':envelope.get('session_id'),'handoff_id':envelope.get('handoff_id'),'lease_id':lease.get('lease_id'),'lease_sha256':lease.get('sha256'),'host_revalidation':host_receipt,'agency_lease_valid':True,'host_conformance_required':True,'execution_performed':False,'epistemic_authority':0.0,'execution_authority':0.0,'actor_authenticated':False,'human_identity_proven':False}
    def recover_pending(self,*,now:float|None=None)->list[dict[str,Any]]:
        return self.agency.pending_outbox(now=now)
