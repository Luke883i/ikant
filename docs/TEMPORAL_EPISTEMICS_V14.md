# iKant v0.14 — Temporal Epistemics & Memory

v0.14 makes time, vigenza and revision explicit runtime concepts. The release builds on v0.13 provenance/calibration/retrieval/causal diagnostics and does not change the v0.12 access contract.

## Slice 1 — typed temporal memory

Every node can be projected into one of five memory classes: episodic, semantic, commitment, interpretive, or kernel. The projection is deterministic from node kind/source unless an allowed explicit class is present. Temporal lifecycle states are `ACTIVE`, `SUPERSEDED`, `RETRACTED`, `FORGOTTEN`, `SOURCE_REVOKED`, and `DEPENDENCY_INVALIDATED`.

Lifecycle transitions are availability controls. They never alter `evidence`. Non-current temporal states reuse the runtime's existing `active=False` semantics, while metadata records why the node is unavailable. This avoids introducing a second candidate-selection mechanism beside the canonical runtime.

## Slice 2 — commitment graph

Goals and constraints may be registered as commitments. Supersession is explicit and fail-closed: a successor must be a current active goal/constraint, self-supersession is forbidden, and a superseded commitment cannot be superseded again. Failed transitions have no temporal-journal side effects.

A new commitment does not automatically supersede a lexically or semantically similar prior commitment. Hosts may provide `metadata.supersedes_node_id` and an optional reason. This prevents the runtime from guessing normative intent.

## Slice 3 — dependency-aware invalidation

Source revocation is evaluated against the v0.13 provenance graph. If independent unrevoked external support remains, the content node stays available and records a partial revocation. If none remains, the node becomes `SOURCE_REVOKED`.

Invalidation may then propagate through derivational runtime edges into `runtime_derived`/inference/cache/demo targets as `DEPENDENCY_INVALIDATED`. External claims are never transitively suppressed merely because a revoked node supported them; their own provenance controls their status. Numeric evidence is unchanged throughout.

## Slice 4 — deterministic temporal replay

Temporal control events use a dedicated `.ikant/temporal-events.jsonl` journal with contiguous sequence numbers and a SHA-256 predecessor chain. This journal is separate from `events.jsonl`: memory bookkeeping must not enter cognitive compression denominators or reduce revision pressure/caution.

Before a cognitive turn ingests a new intention, v0.14 validates the temporal journal and replays its state. Journal tamper, non-contiguous sequence, hash-chain divergence, unjournaled commitment/lifecycle state, or missing persisted source-revocation state fails closed.

`.ikant/temporal-memory.json` is a derived projection. Canonical temporal behavior is represented by node metadata plus the temporal transition journal; the projection is rebuildable and has zero epistemic authority.

## Canonical turn integration

A v0.14 turn follows:

1. require ACTIVE and validate temporal replay before acquiring new intent;
2. ingest intention and mined atoms;
3. bind v0.13 provenance;
4. classify temporal memory and apply only explicit commitment transitions;
5. run v0.13 provenance/hybrid retrieval, then the concentric cycle;
6. apply calibrated uncertainty and CRC causal diagnostics;
7. finalize temporal memory/commitment projections and revalidate replay;
8. continue proto-self, functional psyche, central regulation and workspace;
9. persist Surface B with both `epistemic_core` and `temporal_epistemics` slices;
10. emit Surface A through the existing hardened egress path.

## Boundaries

- History and temporal metadata are not evidence.
- A high lexical/semantic match cannot revive a superseded, retracted, forgotten or invalidated node.
- Source revocation does not rewrite past evidence values or erase journal history.
- Replay proves deterministic control-state consistency, not truth about the external world.
- `FORGOTTEN` is a logical availability tombstone in v0.14, not a claim of cryptographic secure erasure.

## Validation contract

The release gate includes stateful temporal scenario saturation and semantic mutation tests. The full reticular workflow runs five seeds of 100,000 scenarios plus a 100,000-case no-novelty tail and five seeds of 100,000 mutations plus a 100,000-instance tail, in addition to inherited v0.13 and historical gates.
