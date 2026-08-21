from __future__ import annotations
from typing import Any
from ._invariants_base import *
from ._invariants_base import Invariant, _INVARIANTS as _BASE_INVARIANTS

PRODUCT_VERSION = "0.26.0a1"
INVARIANT_REGISTRY_SCHEMA = "ikant-invariant-registry/v0.26-test"

_S8_INVARIANTS = (
    Invariant("AWS-001","web_shell","The canonical ACTIVE PWA is bound to one paired runtime-session shell writer; same-client reopen is idempotent while second-client takeover and runtime-session drift fail closed.","CRITICAL","tests.test_advanced_web_shell_v26"),
    Invariant("AWS-002","web_shell","Shell operations are monotonically sequenced, whole-session idempotency-key unique and exactly bound to the last acknowledged sealed frame; a pending exact replay never re-executes the underlying turn and legacy ACTIVE mutation routes cannot bypass the claimed shell.","CRITICAL","tests.test_advanced_web_shell_v26"),
    Invariant("AWS-003","web_shell","Browser shell state and chrome have zero epistemic and execution authority; semantic iKant output remains only the HSPv2 sealed dashboard frame, whose shell ACK must bind the exact pending operation and frame.","CRITICAL","tests.test_advanced_web_shell_v26"),
)

_INVARIANTS = _BASE_INVARIANTS + _S8_INVARIANTS

def invariants() -> tuple[Invariant, ...]: return _INVARIANTS
def critical_ids() -> tuple[str, ...]: return tuple(x.id for x in _INVARIANTS if x.severity == "CRITICAL")
def registry_manifest() -> dict[str, Any]:
    return {"schema":INVARIANT_REGISTRY_SCHEMA,"product_version":PRODUCT_VERSION,"contract_version":CONTRACT_VERSION,"contract_schema":CONTRACT_SCHEMA,"admission_policy_schema":ADMISSION_POLICY_SCHEMA,"egress_schema":EGRESS_SCHEMA,"max_frame_bytes":MAX_FRAME_BYTES,"exit_command":EXIT_COMMAND,"resume_command":RESUME_COMMAND,"invariants":[asdict(x) for x in _INVARIANTS]}
