# iKant v0.30 — Closed Runtime

## Purpose

This frontier treats `session-chat` as out of scope and converges the two installable/user-facing forms that exist today: the web application and its floating/standalone PWA presentation profile. They are not two independent runtimes. They must be two projections of the same local governed runtime contract.

`Closed Runtime` means more than “the page loads” or “a unit test passes”. A surface functions only when it is reachable, causally closed, effect-observable, complete-but-minimal, authority-safe, recoverable and bound to executable oracles at the same runtime boundary as its claims.

## What the user should finally be able to expect

1. Launch, pair, setup, admission and ACTIVE converge or fail with an actionable bounded reason.
2. Conversation, work progress, identity, runtime status, epistemic state, memory/governance, temporal activity and available capabilities describe one coherent versioned runtime snapshot.
3. Every displayed mutable control is real. Saving a behavior-changing configuration produces a revision that is later observable as the revision consumed by the relevant cycle.
4. Every displayed service is executable or inspectable now under its declared capability contract; candidate/future functions are absent or explicitly labelled non-active.
5. Webapp and floating expose the same semantic state and writer. Floating may compress layout, but may not invent or omit authority-relevant state.
6. Material behavior continues through evidence -> permission -> approval -> grant -> lease -> fresh host revalidation -> execution -> reconciliation. UI state never shortcuts that chain.
7. Restart, reload, stale assets, model replacement and transport loss do not silently fork runtime identity or state.
8. A material DoD statement is mergeable only when an executable oracle crosses the same boundary. Source-bound mutation coverage cannot stand in for a browser, transport, provider or host boundary that the claim explicitly names.

## Current closure audit

The existing PWA is already strong in several places: one-shot pairing recovery, managed local model setup, governed admission, one AdvancedWebShell writer, exact frame ACK, bounded conversation, read-only exact-ACK epistemic inspection, revision-CAS generation preferences and zero-authority end-user identity/audit projections.

The remaining problem is not primarily missing UI. It is missing **causal closure between UI abstractions and runtime behavior**.

- The active product is assembled from several independently refreshed projections (`experience`, `foundation`, `public`, `work`). S14 detects cross-cycle/session inconsistency after the fact, but the browser does not consume one canonical revisioned surface snapshot.
- Foundation configuration is genuinely consumed by `ExperimentModelProxy`, but the end user sees “saved”, not a cycle-bound receipt proving which configuration revision produced a response.
- There is no single machine-readable surface manifest proving “all and only”: which runtime abstractions are readable, mutable, their effect scope, authority, revision and oracle.
- Memory and temporal autonomy exist in the runtime, but are not yet closed as complete user-governable surfaces.
- S15 builds a bounded work graph and deterministic command plan, but canonical TURN currently consumes the original TURN rather than that graph. Therefore the graph is useful classification/projection, not yet a behavioral control plane.
- S15 commercial/hybrid code is deliberately outside canonical TURN. It becomes a product function only after explicit activation, transport destination hardening and a cycle-bound routing receipt.
- `floating` is presently a PWA presentation profile. Native OS always-on-top behavior is not implemented and must remain outside product claims until a separately governed host exists.

## Minimal reticulum

The compressed runtime lattice is:

`H` human intent/control  
`G` admission/governance  
`S` canonical versioned surface snapshot  
`C` user-governable config  
`W` work/plan graph  
`K` local cognitive/runtime kernel  
`M` replaceable zero-authority model  
`E` epistemic/memory state  
`A` capability/authority boundary  
`F` sealed frame + exact ACK  
`P` local persistence  
`X` optional external/provider boundary

The required closed loops are:

`H -> G -> ACTIVE`

`H.intent -> W -> K -> M -> validated Surface A -> F -> exact ACK -> P -> S -> web/floating`

`H.config -> C(CAS) -> generation-contract revision -> K/M -> cycle effect receipt -> S`

`E/P -> K` and `E -> S`; complete user control is not claimed until memory governance is explicit.

`W.material -> A -> host -> execution receipt -> reconciliation -> S` only after the existing authority chain has made execution eligible.

`X` enters canonical TURN only through explicit activation and remains zero-authority evidence/computation.

## Modeled convergence

The fault model contains 48 repository-derived families. Twenty-two are currently not closed against the target contract. A 10,000,000-scenario Monte Carlo campaign sampled 1–4 simultaneous fault families and covered all 9,108 possible semantic signatures formed by the declared unclosed families; a +100,000 tail produced no new signature. This is a fault-space coverage result, not a measured production failure rate.

A Markov stress model over `PAIR -> SETUP -> ADMISSION -> ACTIVE_IDLE -> TURN_RUNNING -> FRAME_PENDING -> POST_ACK`, with `DEGRADED` absorbing, estimates comparative completion under the declared injected-fault universe. At injection intensities 0.02 / 0.10 / 0.25, the as-is model completes at 0.9443135 / 0.7376457 / 0.421875. The target lattice reaches 1.0 only because it explicitly closes every fault family in this declared model; unknown failure families remain outside that statement.

For design compression, 20 candidate interventions were exhaustively composed: `M = 2^20 = 1,048,576` architectures. 729 covered the complete declared gap. The unique minimum inside this vocabulary has weighted cost 36 and 14 interventions. A further +100,000 random architecture tail found no lower-cost or equal-cost non-isomorphic alternative. This is a vocabulary-bounded engineering minimality claim, not proof over every imaginable future architecture.

The retained interventions are: transactional work state; canonical delivery binding; real-browser slow-TURN oracle; versioned surface snapshot; config-effect receipt; runtime surface manifest; shared web/floating contract; versioned asset bundle; provider redirect lock; identity component epoch; memory governance; temporal control projection; turn-plan binding; hybrid activation gate.

## Runtime/UI timing

The current setup cadence (~900 ms) is already reasonable; retain a 750–1000 ms bounded range. Reactive work polling at 280 ms is also appropriate for perceived liveness; retain roughly 250–300 ms while a TURN is active.

The inefficiency is the independent 4.5–5 s semantic polling performed by multiple projections. S16 should replace those with a single revisioned snapshot: event/revision-triggered refresh where possible, approximately 2 s idle fallback and ~250 ms only while active work requires perceptual liveness.

## Semantic slice sequence

### S15bis — Runtime Closure / Oracle Repair

Make work registration transactional, make derivative work state monotonic with respect to an already-created canonical frame, and execute the S15 slow-TURN observability claim in real Chromium against production `reactive_http`. This slice changes no authority path.

### S16 — Surface Contract

Create the all-and-only runtime surface manifest and one versioned snapshot consumed by both web and floating. Add same-cycle configuration effect receipts and one asset-bundle revision. The browser should stop reconstructing a coherent runtime from independently timed semantic projections.

### S17 — State Governance

Expose component/identity epochs, memory read/forget policy and temporal task/wake state through typed, bounded controls. Mutation must remain explicit and authority-neutral unless it crosses an existing governed action boundary.

### S18 — Reactive Plan Binding

Bind the S15 work graph to canonical TURN routing. Deterministic plans become actual runtime inputs rather than discarded classification results. Material plans still stop at the capability/authority boundary when no execution faculty is available.

### S19 — Hybrid Opt-in

Harden effective provider destination/redirect handling, add explicit local activation/configuration, surface the selected route in a cycle receipt, reject provider tools and retain local fallback. Only then does commercial abstract assist become a closed product function.

## Release discipline

The umbrella version is **iKant v0.30 — Closed Runtime**. S15bis is only the first corrective slice and must not claim v0.30 completion. The public identity `v1.0-closed-runtime-test` should be adopted only after S16–S19 have executable boundary evidence and the web/floating surface contract is complete.
