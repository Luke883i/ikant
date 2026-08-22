# ECF1.3 runtime convergence

Base: `main@4583483e3e3668a127e2de72ae3bf75f6bddab72` (merged PR #39).

## Purpose

ECF1.3 reuses the current cognition, authority, S8 single-writer transport, exact ACK, local model, voice, bootstrap observability and epistemic workspace. It changes the projection and critical path, not the authority model.

The public product grammar is `state -> task/request when present -> conversation -> composer -> details`. Internal protocol and cognitive taxonomy are not ordinary navigation labels.

## Runtime path

`intent -> cognitive compile -> bounded generation contract -> local model/local kernel/fallback -> validation -> sealed canonical frame -> structured primary projection -> exact ACK -> zero-evidence response memory`

A new zero-authority `ExperienceProjection` exposes current state, primary text, causal timing and a `CognitiveTraceProjection`. The trace contains only deterministic facts derived from persisted cycle/runtime state. Its six public labels are `Capisco -> Collego -> Verifico -> Valuto -> Formulo -> Integro`. It is not chain-of-thought and contains no model rationale.

Validated language output still re-enters the reticulum only through the existing response-memory path: `RESPONSE / MEMORY / runtime_derived / evidence=0.0`.

## Latency boundary

PR #39 proved that local llama-server generation can be sub-second while the visible turn still feels slow. ECF1.3 therefore records causal phase timing rather than inferring end-to-end latency from model timing alone.

Server phases: `TURN_ACCEPTED`, `COGNITIVE_START`, `SEMANTIC_SLICE_DONE`, `CRC_DONE`, `GOVERNANCE_DONE`, `SNAPSHOT_JSON_DONE`, `MODEL_START`, `MODEL_DONE`, `VALIDATION_DONE`, `FRAME_SEALED`, `PRIMARY_DELIVERED`, `ACK_DONE`.

The same-cycle JSON snapshot remains synchronous. DOCX rendering is removed from the pre-primary path and scheduled only after the exact ACK; one existing artifact per cycle suppresses duplicate export.

## Browser ownership

`app.js` is the single ACTIVE interaction owner. `conversation.js` is a compatibility no-op. Existing exact S8 commands/ACK, bounded liveness diagnostics, local speech constraints and recovery remain intact. The service-worker namespace is bumped while retaining the S10bis lineage marker.

Voice remains input-only: attested on-device `SpeechRecognition` or configured loopback STT produces a transcript candidate; the human explicitly sends it. TTS is post-ACK and only uses voices reported as `localService`.

## Future supply boundary

Browser companion, native messaging, OS semantic adapters and the floating shell are defined only as zero-authority future-supply contracts. This slice activates none of them. The contracts require untrusted page/content data, exact native origins, bounded typed messages, platform permission mediation, a projection-only floating shell and pinned/verified component updates.

## Falsification

The exact candidate source is bound by `scripts/ecf13_runtime_falsify.py`. The converged local run executed 10,000,000 semantic mutation trials over 200 families in 20 domains, killed 10,000,000/10,000,000, covered all 200 families, saturated 12,800/12,800 semantic signatures and produced zero novelty in a +10,000 tail. This is source-bound semantic/adversarial falsification, not ten million real browser or OS executions.

## Acceptance boundary

The draft PR is source-complete for all 30 ECF1.3 invariants. Merge still requires repository CI and the exact-head browser/accessibility/runtime checks; a failed environmental check is a corrective finding, not grounds to weaken the contract.
