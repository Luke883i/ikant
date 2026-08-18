# iKant v0.7 Incarnate Egress

## Product invariant

A conforming interactive host has one human-facing egress: the dashboard. Every substantive turn is represented as one cycle-bound pair: validated Surface A embedded in the dashboard and Surface B persisted as JSON plus downloadable DOCX telemetry.

The host state machine is:

`OPEN -> B_MATERIALIZED -> A_PENDING -> A_VALIDATED -> CLOSED -> DASHBOARD_READY`

The transition to `DASHBOARD_READY` fails closed if the Surface B JSON or DOCX is missing, unreadable, stale, session-mismatched or bound to a different cycle. A second pending turn is forbidden.

## Surface A

Surface A remains natural-language prose subject to the existing interaction and Surface A validators. The incarnate layer does not author or upgrade claims. It only permits a validated speech act to become human-visible after close and places that speech act inside the dashboard.

A dashboard shown between begin and close renders Surface A as `PENDING`. Candidate text is not exposed as validated A.

## Surface B

Surface B is generated before Surface A close by the existing cognitive runtime. The incarnate layer requires both the persisted JSON snapshot and DOCX artifact. It records file availability, byte size and SHA-256 for the DOCX and checks snapshot cycle/session binding. Hashes are integrity metadata, not epistemic evidence.

## Refresh and persistence

After close, `ikant dashboard` recovers the last validated Surface A from the persisted response node (`last_surface_a_response_id` / `last_surface_a_cycle_id`) and rebinds it to the last Surface B. A refresh therefore cannot silently erase A or show an unbound closed turn.

## Machine channel

`--json` is an explicit engineering/machine channel. It may expose structured diagnostics but is not Surface A and is not the normal human interaction path. Human defaults for `turn`, `emit-surface-a`, `dashboard`, `self`, `history`, `shell` and `integrity` remain dashboard-mediated.

## Saturation gate

`scripts/incarnate_stress.py` exercises 10,000 deterministic/randomized egress cases followed by a 1,000-case independent-seed no-novelty tail. It covers valid close, pending turns, idle state, missing JSON/DOCX, cycle/session mismatch, pending-cycle mismatch, premature validation, empty A, Unicode A and artifact byte variation. Release requires zero oracle mismatch and zero new tail signatures.
