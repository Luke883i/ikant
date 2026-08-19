# iKant v0.13 — Epistemic Core

v0.13 moves iKant from a primarily boundary-hardened reticular runtime toward an explicitly inspectable epistemic control plane. The release does not change the v0.12 access contract. It changes how admitted runtime state represents source attribution, uncertainty, memory retrieval and causal sensitivity.

## Slice 1 — provenance graph

Content identity and source identity are separate objects. A content-addressed claim may have several observations from different sources without changing its content node id. `provenance.json` records source entities, observations, claim bindings and typed derivation/control edges. Provenance is attribution metadata: it has zero independent epistemic authority and never creates evidence by itself. Derived sources can never self-promote to external sources.

The runtime may bind explicit `provenance_key`, path/URL/source locator metadata, and existing corroboration keys. Multiple observations of the same content remain distinguishable. This makes source independence auditable instead of inferring it from repeated text.

## Slice 2 — calibrated uncertainty

Calibration is computed from actual recorded `FEEDBACK` events and the confidence of the cycle that received the feedback. Success maps to 1, failure/correction to 0, partial to 0.5, and unknown outcomes are excluded. The profile exposes sample count, mean confidence, empirical success, Brier mean, calibration gap and a bounded risk adjustment.

Calibration is deliberately monotone toward caution. Sparse history and poor calibration may raise `epistemic_caution` and `claim_threshold`. Calibration can never lower either value, change evidence, or upgrade a derived claim.

## Slice 3 — hybrid memory retrieval

Pre-cycle retrieval combines six bounded signals: lexical overlap, a character-ngram semantic proxy (replaceable by an explicit host adapter), provenance quality, temporal/stability relevance, graph-neighbour relevance and conflict relevance. The result is an auditable ranking and bounded activation boost before the normal concentric cycle.

Retrieval changes availability only. Evidence is snapshotted before and after the operation and a change is a runtime error. The trace stores only an intent SHA-256, not raw user text.

## Slice 4 — causal CRC diagnostics

CRC keeps its structural reticulum, but v0.13 adds executable counterfactual diagnostics. The runtime removes selected high-support nodes and source classes, reruns the reticulum, and measures changes in CRC-basic, collapse, epistemic debt and functional coherence. It reports mean/max counterfactual dependency plus single-point and source-class dependency.

These are intervention tests over the runtime representation. They are not proof of real-world causality, ontological closure, consciousness, causal sufficiency, or neural equivalence. The diagnostic object has zero epistemic authority.

## Integration order

A canonical cognitive turn now follows:

1. ingest and source-bind the human intention and mined atoms;
2. materialize provenance and perform hybrid retrieval;
3. execute the concentric cycle;
4. derive feedback-bound calibration and monotonically regulate caution;
5. evaluate CRC and run causal ablations;
6. derive proto-self, functional psyche, central regulation and projection;
7. apply workspace retroaction without evidence mutation;
8. persist Surface B with an `epistemic_core` slice and emit Surface A through the existing hardened egress path.

No second cognitive pipeline is introduced. The canonical implementation remains `ikant.cognitive_runtime.compile_cognitive_turn` and existing compatibility modules remain compatibility surfaces.

## Saturation contract

The v0.13 reticular gate adds a dedicated Epistemic Core job. For each release seed it executes 100,000 semantic scenarios plus a 100,000-case no-novelty tail and 100,000 mutation instances plus a 100,000-instance tail. The gate fails on provenance authority escalation, calibration relaxation, retrieval evidence mutation, raw-intent leakage, missing ablation sensitivity, or ontological overclaim.
