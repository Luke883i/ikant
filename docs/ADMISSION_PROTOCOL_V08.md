# Admission Protocol v0.8: bounded orientation, deterministic freeze

## Product decision

v0.8 moves the consent boundary from “no preliminary repository bytes except the terms file” to “bounded orientation is allowed, but acquisition freezes immediately after terms presentation.” This matches normal AI session-chat behavior while preserving a hard capability transition before clone, source inspection or local materialization.

## State machine

`DISCOVERED -> ORIENTING -> AWAITING_ACCEPTANCE -> ACCEPTED -> MATERIALIZED -> PROBED -> INITIALIZING -> ACTIVE`

`AWAITING_ACCEPTANCE -> DECLINED -> PRESENT_CACHED_TERMS -> AWAITING_ACCEPTANCE`

`BREACHED` is terminal only after completed forbidden acquisition that was host-initiated or model-exposed.

## Orientation capsule

One metadata projection is permitted using only repository identity fields. Preliminary file reads are direct path fetches for `README.md`, `IKANT_ACCESS_CONTRACT.md`, `BOOTSTRAP.json`, `ADMISSION.json`, `AGENTS.md`; each path is single-fetch, total file reads are <=5 and aggregate payload <=256 KiB. No discovered link expands scope.

The terms file is digest-bound. Presentation closes the acquisition capability. Cached preliminary content may subsequently support only `TERMS_EXPLANATION`, `BOOTSTRAP_EXPLANATION` and `ACCESS_DENIAL`.

## Denial versus breach

A denied request is a successful enforcement event, not contamination. `ikant-access-denial/v0.8` records the request with `repository_access_performed=false` in host-scoped persistence when available. The receipt must not copy repository content.

A completed forbidden acquisition before acceptance is different. If host-initiated or exposed to the model, it moves the admission attempt to `BREACHED`. If a provider incidentally returned extra bytes and the host discarded them before model exposure or persistence, the event is quarantined and the current admission context remains usable.

## User-provided content

Repository content pasted directly by the human is treated as chat input, not as host repository acquisition. It may be discussed but cannot expand repository capability.

## Concurrency

`AdmissionGate` serializes transitions with an `RLock`. This prevents a clone/materialize check from racing a simultaneous acceptance transition on the same gate. The operation is allowed only according to the state observed inside the serialized transition.

## Version binding

Post-materialization `probe` verifies `BOOTSTRAP.json`, `ADMISSION.json`, the executable policy manifest and contract header agree on schema, version, capsule, budgets, freeze semantics, overfetch semantics, state machine and forbidden operations. The acceptance receipt remains bound to the full contract digest.
