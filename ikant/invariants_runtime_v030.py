from __future__ import annotations

from ._invariants_base import Invariant

S16_INVARIANTS=(
 Invariant('SFC-001','surface_contract_s16','Authenticated runtime semantic reads converge through one versioned canonical Surface Contract. Stable reads use bounded optimistic consistency checks; an active synchronous TURN is represented by a nonblocking work overlay and may never be delayed by a presentation snapshot lock.',"CRITICAL",'tests.test_surface_contract_s16'),
 Invariant('SFC-002','surface_contract_s16','The runtime surface manifest is the all-and-only declaration of currently user-readable or user-governable abstractions. Webapp and floating PWA profiles share the same semantic contract digest; layout cannot widen authority or imply native OS-overlay capability.',"CRITICAL",'tests.test_surface_contract_s16'),
 Invariant('SFC-003','surface_contract_s16','Generation configuration effect is session-, cycle-, revision- and route-bound. Saving configuration is not evidence that it affected the visible answer; MODEL, fallback and local non-model routes are distinguished and every receipt remains zero-authority.',"CRITICAL",'tests.test_surface_contract_s16'),
 Invariant('SFC-004','surface_contract_s16','Legacy experience/foundation/public/work semantic reads remain compatibility projections of the canonical Surface Contract, while mutation routes, S8 single-writer/exact-ACK semantics and S15bis browser liveness remain authoritative and unchanged; the S16 asset boundary invalidates stale pre-contract bundles.',"CRITICAL",'tests.test_surface_contract_s16'),
)

S15BIS_INVARIANTS=(
 Invariant('RCL-001','reactive_closure_s15bis','Reactive work projection is transactional before external visibility and subordinate to an already-materialized canonical frame; derivative projection or transport failure cannot retroactively invalidate a sealed semantic result.',"CRITICAL",'tests.test_reactive_hybrid_s15'),
 Invariant('RCL-002','reactive_closure_s15bis','A real Chromium slow TURN must observe RUNNING work while the synchronous canonical TURN is in flight, SEALED after frame production and DELIVERED only after exact ACK.',"CRITICAL",'tests.test_reactive_hybrid_s15'),
)

S16BIS_INVARIANTS=(
 Invariant('SFE-001','surface_enforcement_s16bis','After the first successful ACTIVE canonical Surface Contract bind, semantic read failure is fail-closed and may never resurrect independent legacy semantic realities; pre-ACTIVE compatibility remains explicitly bounded.',"CRITICAL",'tests.test_development_continuity_s16bis'),
 Invariant('SFE-002','surface_enforcement_s16bis','AI-assisted development continuity is repository-bound, separates modeled coverage from physical-boundary evidence and records unresolved engineering ignorance without promoting it to release readiness.',"CRITICAL",'tests.test_development_continuity_s16bis'),
)

S17_INVARIANTS=(
 Invariant('RPE-001','runtime_provenance_epoch_s17','Runtime epoch material is deterministically bound to session, constitutional Product Contract, canonical Surface Contract digest, generation-config revision and verified managed component binding. Live process status is observable but never part of epoch identity.',"CRITICAL",'tests.test_runtime_epoch_s17'),
 Invariant('RPE-002','runtime_provenance_epoch_s17','Runtime epoch history is append-only and hash-chained with monotonic ordinals. Its hashes establish local payload integrity only: they never authenticate an actor, certify world truth, create authority or claim SLSA provenance attestation.',"CRITICAL",'tests.test_runtime_epoch_s17'),
 Invariant('RPE-003','runtime_provenance_epoch_s17','Managed production turns require a verified current component epoch before cognition. Durable cycle and Surface A/config/surface projections are epoch-bound, and current reads distinguish current, prior-known, unattested and unknown epoch references without silently rebinding history.',"CRITICAL",'tests.test_runtime_epoch_s17'),
 Invariant('RPE-004','runtime_provenance_epoch_s17','Component/model replacement may advance runtime epoch but never replaces the local iKant identity. Webapp and floating views expose component provenance as subordinate detail and preserve zero epistemic/execution authority.',"CRITICAL",'tests.test_runtime_epoch_s17'),
)

S17BIS_INVARIANTS=(
 Invariant('RSC-001','runtime_recovery_surface_closure_s17bis','Restart recovery is a zero-authority derivative reducer over already-durable runtime session, egress journal/frame, validated Surface A/chat and epoch state. WorkStore, shell sequence state and stable Surface cache remain process-local projections and are never promoted to parallel canonical stores.',"CRITICAL",'tests.test_runtime_recovery_s17bis'),
 Invariant('RSC-002','runtime_recovery_surface_closure_s17bis','Recovery may never rerun the language model, cognitive planner or material driver. An interrupted unsealed TURN is represented by a RECOVERY frame, and its pending cognitive marker is cleared only after exact acknowledgement of that recovery frame or deterministic post-ACK reconciliation.',"CRITICAL",'tests.test_runtime_recovery_s17bis'),
 Invariant('RSC-003','runtime_recovery_surface_closure_s17bis','A durable pending frame remains byte-identical across process replacement. A validated Surface A that existed before frame sealing may be recovered from verified chat or its validated zero-evidence RESPONSE node, may reconcile at most one missing chat reply, and may never create a second RESPONSE.',"CRITICAL",'tests.test_runtime_recovery_s17bis'),
 Invariant('RSC-004','runtime_recovery_surface_closure_s17bis','Production routes, composed assets and real DOM controls are independently censused outside the declarative Surface manifest. PRE_ACTIVE_BOOTSTRAP, RECOVERY_REQUIRED and ACTIVE_CANONICAL are explicit lifecycle phases, and recovery/census projections never widen epistemic or execution authority.',"CRITICAL",'tests.test_runtime_recovery_s17bis'),
)
