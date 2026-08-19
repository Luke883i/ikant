from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
PRODUCT_VERSION = "0.17.0a1"
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
INVARIANT_REGISTRY_SCHEMA = "ikant-invariant-registry/v0.17-test"
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
    Invariant("EPI-003","epistemic","Content identity and source identity remain separate; provenance may attribute and count independent observations but cannot itself create evidence.","CRITICAL","tests.test_epistemic_core_v13"),
    Invariant("CAL-001","calibration","Empirical calibration is feedback-bound and may only raise caution or claim thresholds; sparse or poor calibration never upgrades factual authority.","CRITICAL","tests.test_epistemic_core_v13"),
    Invariant("MEM-001","memory","Hybrid retrieval combines lexical/semantic-proxy, provenance, temporal, graph and conflict relevance while changing availability only, never evidence.","CRITICAL","tests.test_epistemic_core_v13"),
    Invariant("MEM-002","memory","Temporal memory classification and lifecycle transitions change availability and vigenza only; history, summaries and lifecycle metadata never become evidence.","CRITICAL","tests.test_temporal_epistemics_v14"),
    Invariant("MEM-003","memory","Superseded, retracted, forgotten, source-revoked and dependency-invalidated nodes are not current retrieval/directive candidates even when their lexical relevance is high.","CRITICAL","tests.test_temporal_epistemics_v14"),
    Invariant("COM-001","commitment","Commitment succession is explicit, acyclic per transition and fail-closed; an old commitment cannot remain current after supersession or retraction.","CRITICAL","tests.test_temporal_epistemics_v14"),
    Invariant("INV-001","provenance","Source revocation suppresses a claim only when no independent unrevoked external support remains and propagates only into dependent derived runtime state.","CRITICAL","tests.test_temporal_epistemics_v14"),
    Invariant("RPL-001","persistence","Temporal state is deterministically replayable from journal events; replay divergence blocks temporal-core finalization.","CRITICAL","tests.test_temporal_epistemics_v14"),
    Invariant("ACT-001","action","Epistemic score, evidence, provenance, public visibility and rights/conformance state never create material-action authority.","CRITICAL","tests.test_practical_reason_v15"),
    Invariant("ACT-002","action","Material actions require explicitly linked current user/repository commitments and exact required capabilities; wildcard, prefix, derived or stale authority is invalid.","CRITICAL","tests.test_practical_reason_v15"),
    Invariant("ACT-003","action","Material action approval is current-turn, user-attributed and action-fingerprint-bound; approval never grants missing capabilities and a derived proposal requires a separately targeted user approval constraint.","CRITICAL","tests.test_practical_reason_v15"),
    Invariant("ACT-004","action","Unresolved human impact, unknown reversibility, missing rollback or missing declared effects/failure modes prevents host execution eligibility; irreversible or high-impact actions remain human-execution-only.","CRITICAL","tests.test_practical_reason_v15"),
    Invariant("ACT-005","action","The Action Ledger is a zero-epistemic-authority control projection. HOST_EXECUTION_ELIGIBLE is not execution; v0.15 performs no material action and the host must recheck higher-priority system, safety, law and tool capability.","CRITICAL","tests.test_practical_reason_v15"),
    Invariant("PLN-001","planning","Multi-step plans are explicit DAGs over v0.15 ActionCandidates; cycles, unknown dependencies, duplicate steps and mixed decision problems fail closed, and planning cannot upgrade action governance.","CRITICAL","tests.test_planning_v16"),
    Invariant("PLN-002","planning","Symbolic world-state applies only declared predicates and explicit negation; pre/postcondition simulation is a zero-epistemic-authority counterfactual projection, never an observed-world claim.","CRITICAL","tests.test_planning_v16"),
    Invariant("PLN-003","planning","Same-turn action approval never becomes a reusable plan token. PLAN_HOST_REVALIDATION_REQUIRED is not execution eligibility and every material step requires fresh host/action revalidation.","CRITICAL","tests.test_planning_v16"),
    Invariant("PLN-004","planning","Rollback graphs reverse plan dependencies where rollback instructions exist; rollback text is not proof of restoration and irreversible or uncovered steps remain explicit.","CRITICAL","tests.test_planning_v16"),
    Invariant("PLN-005","planning","Decision comparison is Pareto-only within an explicit decision problem; no scalar utility or cross-problem dominance may silently choose a winner.","CRITICAL","tests.test_planning_v16"),
    Invariant("PLN-006","planning","Assumption ablation measures dependency of the declared plan model only and must never be presented as real-world causality or factual evidence.","CRITICAL","tests.test_planning_v16"),
    Invariant("EXE-001","execution","Every material execution handoff is exactly bound to the current session, cycle, intent, action fingerprint, approval receipt, action-ledger digest, plan-ledger digest, plan and step identity; missing or drifting bindings fail closed.","CRITICAL","tests.test_execution_v17"),
    Invariant("EXE-002","execution","Execution handoff preserves v0.15 action and v0.16 plan governance. It never upgrades host/human authority, and dependent material steps remain predecessor-reconciliation-gated.","CRITICAL","tests.test_execution_v17"),
    Invariant("EXE-003","execution","Host revalidation receipts must bind current system/safety/law and tool-capability checks to the exact handoff. Receipt digests provide payload integrity only; host/transport authentication remains external.","CRITICAL","tests.test_execution_v17"),
    Invariant("EXE-004","execution","Execution receipts never cause runtime execution or grant runtime authority. Host EXECUTED/FAILED receipts require a valid exact revalidation receipt; human-execution receipts remain actor-bound.","CRITICAL","tests.test_execution_v17"),
    Invariant("EXE-005","execution","Receipt acceptance is replay-safe at the control layer: identical same-key replay is idempotent, conflicting same-key terminal receipts fail closed, and terminal receipt state remains zero-authority.","CRITICAL","tests.test_execution_v17"),
    Invariant("EXE-006","execution","Outcome reconciliation uses only explicit reported predicates and explicit negation, treats execution references and host reports as non-independent control observations, creates no evidence, verifies no world truth and never auto-advances a successor step.","CRITICAL","tests.test_execution_v17"),
    Invariant("CRC-001","epistemic","CRC causal diagnostics are executable node/source ablations with explicit intervention sensitivity and must never be presented as ontological causality, consciousness or proof of closure.","CRITICAL","tests.test_epistemic_core_v13"),
    Invariant("PSY-001","psyche","Functional psyche may preserve or increase caution but cannot relax a practical/horizon block.","CRITICAL","tests.test_psyche_v05"),
    Invariant("SUR-001","surface","Validated Surface A and Surface B must be same-session/same-cycle and Surface B DOCX is mandatory for substantive human turns.","CRITICAL","tests.test_incarnate_v07"),
    Invariant("EGR-001","egress","After ACTIVE, the human channel is one canonical dashboard frame only until exact release.","CRITICAL","tests.test_session_egress_v10"),
    Invariant("EGR-002","egress","Delivery is two-phase: seal/persist, transport write+flush, then exact acknowledgement.","CRITICAL","tests.test_session_host_v10"),
    Invariant("EGR-003","egress","A required egress guard cannot be silently recreated after deletion or loss.","CRITICAL","tests.test_reticular_v11"),
    Invariant("EGR-004","egress","A breached egress epoch may resume only with runtime integrity and a valid host/transport attestation.","CRITICAL","tests.test_reticular_v11"),
    Invariant("TRN-001","transport","Human and machine outputs use distinct explicit sinks; ACTIVE machine JSON is file-only and never stdout/stderr.","CRITICAL","tests.test_reticular_v11"),
    Invariant("CLI-001","host","ACTIVE pre-admission commands cannot bypass dashboard egress.","CRITICAL","tests.test_reticular_v11"),
    Invariant("ARC-001","architecture","Canonical runtime entrypoints and imports are version-neutral; historical version modules are compatibility shims only.","HIGH","scripts.architecture_compression_v11"),
    Invariant("CI-001","validation","One version-neutral reticular boundary workflow owns historical and current boundary regressions; release workflows do not accrete per version.","HIGH","scripts.execution_mutations"),
)
def invariants() -> tuple[Invariant, ...]: return _INVARIANTS
def critical_ids() -> tuple[str, ...]: return tuple(x.id for x in _INVARIANTS if x.severity == "CRITICAL")
def registry_manifest() -> dict[str, Any]: return {"schema":INVARIANT_REGISTRY_SCHEMA,"product_version":PRODUCT_VERSION,"contract_version":CONTRACT_VERSION,"contract_schema":CONTRACT_SCHEMA,"admission_policy_schema":ADMISSION_POLICY_SCHEMA,"egress_schema":EGRESS_SCHEMA,"max_frame_bytes":MAX_FRAME_BYTES,"exit_command":EXIT_COMMAND,"resume_command":RESUME_COMMAND,"invariants":[asdict(x) for x in _INVARIANTS]}
