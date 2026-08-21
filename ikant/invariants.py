from __future__ import annotations
from typing import Any
from ._invariants_base import *
from ._invariants_base import Invariant, _INVARIANTS as _BASE_INVARIANTS

PRODUCT_VERSION = "0.27.0a1"
INVARIANT_REGISTRY_SCHEMA = "ikant-invariant-registry/v0.27-test"

_S8_INVARIANTS = (
    Invariant("AWS-001","web_shell","The canonical ACTIVE PWA is bound to one paired runtime-session shell writer; same-client reopen is idempotent while second-client takeover and runtime-session drift fail closed.","CRITICAL","tests.test_advanced_web_shell_v26"),
    Invariant("AWS-002","web_shell","Shell operations are monotonically sequenced, whole-session idempotency-key unique and exactly bound to the last acknowledged sealed frame; a pending exact replay never re-executes the underlying turn and legacy ACTIVE mutation routes cannot bypass the claimed shell.","CRITICAL","tests.test_advanced_web_shell_v26"),
    Invariant("AWS-003","web_shell","Browser shell state and chrome have zero epistemic and execution authority; semantic iKant output remains only the HSPv2 sealed dashboard frame, whose shell ACK must bind the exact pending operation and frame.","CRITICAL","tests.test_advanced_web_shell_v26"),
)

_S9_INVARIANTS = (
    Invariant("EXP-001","product_experience","The local product shell is available before managed-model readiness; setup, download progress, diagnostics and retry are redacted control projections with zero epistemic/execution authority and the browser cannot mark the runtime READY.","CRITICAL","tests.test_product_experience_v27"),
    Invariant("EXP-002","product_experience","The S9 workspace is chat-first with exactly one ACTIVE semantic viewport containing the existing sealed HSPv2 frame; inspector, orbit rail, command palette, artifacts, diagnostics and traditional controls are progressively disclosed zero-authority chrome and cannot create a parallel semantic channel or browser-to-model path.","CRITICAL","tests.test_product_experience_v27"),
    Invariant("EXP-003","product_experience","Voice input is local/on-device or loopback, bound to the current S8 writer when brokered by iKant, never auto-submits and cannot approve authority; voice output is optional local-service rendering only after exact ACK of the same sealed TURN Surface A and never becomes a second semantic message.","CRITICAL","tests.test_product_experience_v27"),
    Invariant("EXP-004","product_experience","The canonical product path preserves T&C -> PROBE -> INITIALIZE, S8 single-writer recovery/idempotence, keyboard access, responsive/reduced-motion behavior and explicit degraded/setup recovery while progressive disclosure never collapses presentation, readiness, diagnostics or convenience into authority.","CRITICAL","tests.test_product_experience_v27"),
)

_INVARIANTS = _BASE_INVARIANTS + _S8_INVARIANTS + _S9_INVARIANTS

def invariants() -> tuple[Invariant, ...]: return _INVARIANTS
def critical_ids() -> tuple[str, ...]: return tuple(x.id for x in _INVARIANTS if x.severity == "CRITICAL")
def registry_manifest() -> dict[str, Any]:
    return {"schema":INVARIANT_REGISTRY_SCHEMA,"product_version":PRODUCT_VERSION,"contract_version":CONTRACT_VERSION,"contract_schema":CONTRACT_SCHEMA,"admission_policy_schema":ADMISSION_POLICY_SCHEMA,"egress_schema":EGRESS_SCHEMA,"max_frame_bytes":MAX_FRAME_BYTES,"exit_command":EXIT_COMMAND,"resume_command":RESUME_COMMAND,"invariants":[asdict(x) for x in _INVARIANTS]}
