from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

PRODUCT_VERSION = "0.11.0a1"
CONTRACT_VERSION = "0.11.0"
CONTRACT_SCHEMA = "ikant-access-contract/v0.11"
ADMISSION_POLICY_SCHEMA = "ikant-pre-admission-firewall/v0.9-test"
EGRESS_SCHEMA = "ikant-dashboard-session-egress/v0.11-test"
LEGACY_EGRESS_SCHEMA = "ikant-dashboard-session-egress/v0.10-test"
V09_EGRESS_SCHEMA = "ikant-dashboard-session-egress/v0.9-test"
FRAME_SCHEMA = "ikant-dashboard-frame/v0.11-test"
JOURNAL_SCHEMA = "ikant-dashboard-egress-journal/v0.11-test"
LEGACY_JOURNAL_SCHEMA = "ikant-dashboard-egress-journal/v0.10-test"
TRANSPORT_ATTESTATION_SCHEMA = "ikant-host-transport-attestation/v0.11-test"
INVARIANT_REGISTRY_SCHEMA = "ikant-invariant-registry/v0.11-test"
MAX_FRAME_BYTES = 128 * 1024
EXIT_COMMAND = "EXIT IKANT"
RESUME_COMMAND = "RESUME IKANT"

@dataclass(frozen=True)
class Invariant:
    id: str
    domain: str
    statement: str
    severity: str
    machine_test: str

_INVARIANTS = (
    Invariant("ADM-001","admission","Exact current-session human I ACCEPT is required and bound to the presented terms digest.","CRITICAL","tests.test_admission_v09"),
    Invariant("ADM-002","admission","Pre-acceptance repository capability is bounded, accounted, frozen after terms presentation and deny-by-default.","CRITICAL","tests.test_pre_admission_v08"),
    Invariant("EPI-001","epistemic","Runtime-derived, psyche, dashboard and audit telemetry never create external evidence or independent corroboration.","CRITICAL","tests.test_crc_v02"),
    Invariant("PSY-001","psyche","Functional psyche may preserve or increase caution but cannot relax a practical/horizon block.","CRITICAL","tests.test_psyche_v05"),
    Invariant("SUR-001","surface","Validated Surface A and Surface B must be same-session/same-cycle and Surface B DOCX is mandatory for substantive human turns.","CRITICAL","tests.test_incarnate_v07"),
    Invariant("EGR-001","egress","After ACTIVE, the human channel is one canonical dashboard frame only until exact release.","CRITICAL","tests.test_session_egress_v10"),
    Invariant("EGR-002","egress","Delivery is two-phase: seal/persist, transport write+flush, then exact acknowledgement.","CRITICAL","tests.test_session_host_v10"),
    Invariant("EGR-003","egress","A required egress guard cannot be silently recreated after deletion or loss.","CRITICAL","tests.test_reticular_v11"),
    Invariant("EGR-004","egress","A breached egress epoch may resume only with runtime integrity and a valid host/transport attestation.","CRITICAL","tests.test_reticular_v11"),
    Invariant("TRN-001","transport","Human and machine outputs use distinct explicit sinks; ACTIVE machine JSON is file-only and never stdout/stderr.","CRITICAL","tests.test_reticular_v11"),
    Invariant("CLI-001","host","ACTIVE pre-admission commands cannot bypass dashboard egress.","CRITICAL","tests.test_reticular_v11"),
    Invariant("ARC-001","architecture","Canonical runtime entrypoints and imports are version-neutral; historical version modules are compatibility shims only.","HIGH","scripts.architecture_compression_v11"),
    Invariant("CI-001","validation","One reticular workflow owns historical boundary regressions; version-specific workflow duplication is not a release dependency.","HIGH","scripts.architecture_compression_v11"),
)

def invariants() -> tuple[Invariant, ...]: return _INVARIANTS
def critical_ids() -> tuple[str, ...]: return tuple(x.id for x in _INVARIANTS if x.severity == "CRITICAL")
def registry_manifest() -> dict[str, Any]:
    return {"schema":INVARIANT_REGISTRY_SCHEMA,"product_version":PRODUCT_VERSION,"contract_version":CONTRACT_VERSION,"contract_schema":CONTRACT_SCHEMA,"admission_policy_schema":ADMISSION_POLICY_SCHEMA,"egress_schema":EGRESS_SCHEMA,"max_frame_bytes":MAX_FRAME_BYTES,"exit_command":EXIT_COMMAND,"resume_command":RESUME_COMMAND,"invariants":[asdict(x) for x in _INVARIANTS]}
