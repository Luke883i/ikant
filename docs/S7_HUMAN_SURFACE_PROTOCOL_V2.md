# S7 — Human Surface Protocol v2

S7 turns the existing dashboard-only human egress into an explicit typed protocol without creating a second output channel or changing the v0.12 access contract.

## Constitutional statement

After ACTIVE, every semantic iKant human output is represented by one `ikant-human-surface-protocol/v0.25-test` envelope and rendered inside the exact dashboard bytes sealed by the existing v0.11 egress guard.

The transport boundary remains:

`project HSPv2 -> render dashboard bytes -> seal/persist -> transport write+flush -> exact visible-text ACK`

The authority boundary remains:

`presentation != decision != permission != approval != grant != lease != execution`

## Frame kinds

- `INITIALIZE` — ACTIVE entry notice.
- `DASHBOARD` — state-only dashboard refresh.
- `TURN` — validated Surface A plus same-cycle bound Surface B.
- `NOTICE` — bounded informational control message.
- `APPROVAL_REQUEST` — projection of a validated current-session `HumanFrame`; no decision is recorded by presentation.
- `PROGRESS` — bounded phase/label/fraction control state.
- `ERROR` — bounded typed runtime error.
- `DEGRADED` — bounded capability-loss projection.
- `RECOVERY` — replay-only control state for sealed-frame recovery semantics.
- `EXIT` — release request; release occurs only after exact frame acknowledgement.
- `RESUME` — integrity-gated return to locked dashboard egress.

Each kind has exactly one allowed payload slot (except state-only `DASHBOARD`). Multi-payload frames fail closed.

## Surface A / Surface B

A `TURN` is valid only when Incarnate already reports `READY`, Surface A is `VALIDATED`, Surface B JSON and DOCX are bound, and A/B share the exact cycle. HSPv2 does not weaken the historical Surface B requirement.

## Approval projection

`APPROVAL_REQUEST` accepts only a valid S1 `HumanFrame` whose session matches the runtime and whose purpose is one of `CAPABILITY_GRANT`, `CAPABILITY_REVOKE`, or `ACTION_CONFIRMATION`. The HSP projection explicitly records:

- `requires_explicit_decision: true`;
- `presentation_is_not_authorization: true`;
- `decision_recorded: false`;
- `grant_issued: false`;
- epistemic/execution authority `0.0`.

The authenticated interaction receipt and Agency Kernel remain the only path that can create a grant.

## Browser boundary

The PWA continues to render `frame.text` verbatim and ACK actual DOM `textContent`. S7 removes the ACTIVE `active-error` text path as a parallel response channel. Backend failures are converted to HSPv2 `ERROR` frames where the server is reachable. A pure transport outage cannot be truthfully resealed by client JavaScript, so the client freezes controls and attempts recovery without fabricating semantic output.

## Falsification model

The S7 mutation lattice covers 66 families compressed into eight operational classes:

1. single-egress;
2. envelope integrity;
3. TURN A/B binding;
4. approval non-collapse;
5. progress bounds;
6. message bounds;
7. release/recovery;
8. exact ACK.

The current-slice contract requires 1,000,000 stress cases, 10,000,000 semantic mutation instances, 1,000,000 edge cases and a +100,000 no-novelty tail. Family selection is round-robin; pseudo-random state perturbs within-family boundaries only, preventing the false-coverage defect previously found in S6.

These are semantic adversarial mutation instances over the HSPv2 contract lattice, not a claim of ten million compiled AST mutants.

## Explicit non-goals

S7 does not add arbitrary web actions, secret handling, general native process execution, a plugin protocol, OS notifications, TTS of ACTIVE output, or a second human communication surface. Those remain outside this slice.
