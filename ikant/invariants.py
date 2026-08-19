from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

PRODUCT_VERSION = "0.12.0a1"
CONTRACT_VERSION = "0.12.0"
CONTRACT_SCHEMA = "ikant-access-contract/v0.12"
ADMISSION_POLICY_SCHEMA = "ikant-pre-admission-firewall/v0.9-test"
EGRESS_SCHEMA = "ikant-dashboard-session-egress/v0.11-test"
LEGACY_EGRESS_SCHEMA = "ikant-dashboard-session-egress/v0.10-test"
V09_EGRESS_SCHEMA = "ikant-dashboard-session-egress/v0.9-test"
FRAME_SCHEMA = "ikant-dashboard-frame/v0.11-test"
JOURNAL_SCHEMA = "ikant-dashboard-egress-journal/v0.11-test"
LEGACY_JOURNAL_SCHEMA = "ikant-dashboard-egress-journal/v0.10-test"
TRANSPORT_ATTESTATION_SCHEMA = "ikant-host-transport-attestation/v0.11-test"
INVARIANT_REGISTRY_SCHEMA = "ikant-invariant-registry/v0.12-test"
MAX_FRAME_BYTES = 128 * 1024
EXIT_COMMAND = "EXIT IKANT"
RESUME_COMMAND = "RESUME IKANT"

@dataclass(frozen=True)
class Invariant:
    id: str; domain: str; statement: str; severity: str; machine_test: str

_INVARIANTS = (
    Invariant("ADM-001","admission","Exact current-session human I ACCEPT is required and bound to the presented terms digest.","CRITICAL","tests.test_admission_v09"),
    Invariant("ADM-002","admission","Pre-acceptance repository capability is bounded, accounted, frozen after terms presentation and deny-by-default.","CRITICAL","tests.test_pre_admission_v08"),
    Invariant("ADM-003","admission","The current contract and probe bind a machine-readable rights policy; rights-policy drift blocks readiness.","CRITICAL","tests.test_rights_policy_v12"),
    Invariant("RGT-001","rights","Public visibility does not constitute the owner's permission for substantive AI-assisted study; owner authorization is reserved unless the current iKant contract, clean admission and technical conformance all hold.","CRITICAL","tests.test_rights_policy_v12"),
    Invariant("RGT-002","rights","Manual human review is outside the iKant AI-admission gate and does not create any additional copyright licence.","CRITICAL","tests.test_rights_policy_v12"),
    Invariant("RGT-003","rights","Mandatory statutory exceptions, direct platform grants and separate licences are external legal bases: iKant does not adjudicate them and they never self-promote into iKant conformance.","CRITICAL","tests.test_rights_policy_v12"),
    Invariant("RGT-004","rights","The iKant contract does not itself grant owner permission for model training or training-dataset construction; a separate licence or independent external basis is required.","CRITICAL","tests.test_rights_policy_v12"),
    Invariant("EPI-001","epistemic","Runtime-derived, psyche, dashboard and audit telemetry never create external evidence or independent corroboration.","CRITICAL","tests.test_crc_v02"),
    Invariant("EPI-002","epistemic","Rights, admission and conformance control slices have zero epistemic authority and cannot become factual evidence.","CRITICAL","tests.test_rights_policy_v12"),
    Invariant("PSY-001","psyche","Functional psyche may preserve or increase caution but cannot relax a practical/horizon block.","CRITICAL","tests.test_psyche_v05"),
    Invariant("SUR-001","surface","Validated Surface A and Surface B must be same-session/same-cycle and Surface B DOCX is mandatory for substantive human turns.","CRITICAL","tests.test_incarnate_v07"),
    Invariant("EGR-001","egress","After ACTIVE, the human channel is one canonical dashboard frame only until exact release.","CRITICAL","tests.test_session_egress_v10"),
    Invariant("EGR-002","egress","Delivery is two-phase: seal/persist, transport write+flush, then exact acknowledgement.","CRITICAL","tests.test_session_host_v10"),
    Invariant("EGR-003","egress","A required egress guard cannot be silently recreated after deletion or loss.","CRITICAL","tests.test_reticular_v11"),
    Invariant("EGR-004","egress","A breached egress epoch may resume only with runtime integrity and a valid host/transport attestation.","CRITICAL","tests.test_reticular_v11"),
    Invariant("TRN-001","transport","Human and machine outputs use distinct explicit sinks; ACTIVE machine JSON is file-only and never stdout/stderr.","CRITICAL","tests.test_reticular_v11"),
    Invariant("CLI-001","host","ACTIVE pre-admission commands cannot bypass dashboard egress.","CRITICAL","tests.test_reticular_v11"),
    Invariant("ARC-001","architecture","Canonical runtime entrypoints and imports are version-neutral; historical version modules are compatibility shims only.","HIGH","scripts.architecture_compression_v11"),
    Invariant("CI-001","validation","One version-neutral reticular boundary workflow owns historical and current boundary regressions; release workflows do not accrete per version.","HIGH","scripts.semantic_access_mutations"),
)

def invariants() -> tuple[Invariant, ...]: return _INVARIANTS
def critical_ids() -> tuple[str, ...]: return tuple(x.id for x in _INVARIANTS if x.severity == "CRITICAL")
def registry_manifest() -> dict[str, Any]: return {"schema":INVARIANT_REGISTRY_SCHEMA,"product_version":PRODUCT_VERSION,"contract_version":CONTRACT_VERSION,"contract_schema":CONTRACT_SCHEMA,"admission_policy_schema":ADMISSION_POLICY_SCHEMA,"egress_schema":EGRESS_SCHEMA,"max_frame_bytes":MAX_FRAME_BYTES,"exit_command":EXIT_COMMAND,"resume_command":RESUME_COMMAND,"invariants":[asdict(x) for x in _INVARIANTS]}
