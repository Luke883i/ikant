from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import Any

FUTURE_SUPPLY_SCHEMA='ikant-ecf1.3-future-supply/v1.3'

@dataclass(frozen=True)
class FutureSupplyContract:
    component:str
    status:str='DEFINED_NOT_ACTIVATED'
    authority_effect:str='NONE'
    epistemic_authority:float=0.0
    execution_authority:float=0.0
    constraints:tuple[str,...]=()
    def projection(self)->dict[str,Any]:return {'schema':FUTURE_SUPPLY_SCHEMA,**asdict(self)}

BROWSER_COMPANION=FutureSupplyContract('AUTHENTICATED_BROWSER_COMPANION',constraints=(
    'page_and_content_script_data_are_untrusted','privileged_operations_live_outside_page_context',
    'service_worker_restart_must_not_lose_safety_state','exact_typed_capability_schema','no_credential_scraping'))
NATIVE_MESSAGING=FutureSupplyContract('NATIVE_MESSAGING_BRIDGE',constraints=(
    'exact_allowed_origins_no_wildcards','bounded_typed_messages','no_raw_credentials','host_revalidates_every_privileged_request'))
OS_SEMANTIC_ADAPTERS=FutureSupplyContract('OS_SEMANTIC_ADAPTERS',constraints=(
    'platform_permission_surface_first','semantic_accessibility_api_before_pixel_input_fallback','capture_scope_is_session_bound','no_permission_is_authority'))
FLOATING_SHELL=FutureSupplyContract('FLOATING_SHELL',constraints=(
    'projection_of_same_local_runtime','owns_no_cognition','owns_no_grants','owns_no_scheduler','owns_no_receipt_store','idle_never_steals_focus'))
COMPONENT_SUPPLY=FutureSupplyContract('COMPONENT_SUPPLY',constraints=(
    'pinned_version','verified_digest_or_signature','update_cannot_widen_capability_without_new_contract','rollback_cannot_restore_revoked_authority'))
ALL_FUTURE_SUPPLY=(BROWSER_COMPANION,NATIVE_MESSAGING,OS_SEMANTIC_ADAPTERS,FLOATING_SHELL,COMPONENT_SUPPLY)

def future_supply_manifest()->dict[str,Any]:
    return {'schema':FUTURE_SUPPLY_SCHEMA,'activated':False,'components':[x.projection() for x in ALL_FUTURE_SUPPLY],
            'epistemic_authority':0.0,'execution_authority':0.0}
