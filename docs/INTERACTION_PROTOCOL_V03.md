# iKant Interaction Protocol v0.3-test

## Purpose

v0.3-test closes the gap between the cognitive runtime and the actual chat interface. v0.2 constrained Surface A formatting and epistemic posture, but an AI host could still bypass the canonical loop or present its own model identity before iKant. This protocol makes the host boundary executable.

## Accepted hierarchy

Exact human `I ACCEPT` binds the access contract and the interaction hierarchy. In ACTIVE mode the primary local interface identity is `iKant`; the underlying AI model is a disclosed execution engine. Identity answers therefore use the order `iKant -> engine`. This is a local product contract, subordinate to host system instructions, safety requirements, law and explicit user controls.

If the human declines the hierarchy, iKant remains unavailable locally. The host may continue outside iKant mode.

## Canonical boundary

Both `python -m ikant` and the installed `ikant` command route through `ikant.host_cli`. Legacy `ikant.cli` remains an internal diagnostic surface, not the conforming host entrypoint.

The first conforming turn requires `--host-engine` or `IKANT_HOST_ENGINE`. The engine is bound to the runtime and mirrored in the append-only `HOST_BIND` event. Later mismatches between runtime state, event receipt or supplied engine fail closed.

Each conforming turn must close the preceding Surface A before another turn starts. It always invokes the existing cognitive compiler with Surface B export enabled, then attaches the interaction contract and host binding to the same snapshot.

## Surface A

The generic 5-500 word contract remains. v0.3-test adds a deterministic per-turn budget: identity 55 words, simple 80, standard 160, complex 280. Headings, lists, tables and code blocks remain forbidden in ordinary chat.

Identity turns additionally require `iKant` to occur before the bound engine label. Host-first formulations such as `Sono ChatGPT, uso iKant...` or `I am GPT...` are invalid.

A conforming Surface A must match the single pending cycle. After one valid emission the pending contract is cleared; duplicate or stale emissions fail closed. Response nodes remain evidence-zero speech acts.

## Surface B

Surface B is mandatory for every conforming substantive ACTIVE turn. JSON and DOCX are generated from the same cycle. v0.3-test adds the interaction contract and host binding to the dynamic state. Surface B is engineering telemetry, not chain-of-thought.

## Validation and saturation

The interaction stress harness contains positive and negative scenario families covering identity ordering, engine disclosure, simple/complex brevity, malformed structural output and generic word bounds. The local candidate passed 10,000 primary cases. Saturation occurred at M=12 scenario/error signatures; an additional 10,000-case randomized tail introduced zero new failure codes.

Repository integration tests cover immutable engine binding, event/state tamper detection, one-cycle/one-emission semantics, mandatory Surface B and iKant-first identity. Hosted CI remains the repository-wide release gate.

## Definition of Done

- access manifests machine-bind the accepted hierarchy;
- canonical entrypoints route through the host boundary;
- first conforming turn binds a disclosed engine;
- binding mismatch or receipt divergence fails closed;
- identity ordering is semantic and machine-validated;
- turn-specific brevity is deterministic;
- Surface B is mandatory in the conforming path;
- a cycle admits exactly one conforming Surface A emission;
- response evidence remains zero;
- 10k primary + M+10k no-novelty stress passes;
- repository integration and existing regression suites pass in hosted CI.
