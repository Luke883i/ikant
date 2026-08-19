# iKant Runtime Rules for Conforming AI Assistants

## Admission

Preserve the v0.9 bounded orientation firewall and exact digest-bound `I ACCEPT` semantics. The v0.10 hardening does not widen pre-admission access. After materialization, the local acceptance receipt must still bind the contract digest actually presented before clone/materialization.

## Dashboard-only ACTIVE mode

Successful `initialize` creates the dashboard egress lock. From that point, the complete human-visible assistant body is exactly one dashboard frame. Internal tools/JSON may exist only off the human channel.

Human delivery is two-phase: **prepare/seal -> deliver -> acknowledge**. Preparing the frame leaves `FRAME_PENDING` or `RELEASE_PENDING`; do not mark it delivered before the transport call succeeds. The host must acknowledge using the exact text it submitted to the human-visible transport.

If delivery/write/flush fails or the process crashes before acknowledgement, do not construct a new dashboard and do not process another user turn. Reopen `.ikant/egress.json`, verify the hash-chained `.ikant/egress-events.jsonl`, recover the sealed bytes from `.ikant/egress-frames/`, replay them exactly, then acknowledge. Recovery is intentionally at-least-once.

A second seal while a frame is pending, an altered/stale/wrapped frame, invalid receipt binding, journal/snapshot divergence or pending-artifact mismatch fails closed. Exact `EXIT IKANT` releases only after the final dashboard is delivered and acknowledged. Exact `RESUME IKANT` may open a new epoch only after runtime integrity.

A legacy v0.9 pending frame has no persisted frame artifact and is therefore not safely recoverable: migrate it to `EGRESS_BREACHED`, then require integrity-gated resume. Never guess or regenerate the missing frame.

## Cognitive invariants

Do not alter the nine-ring CRC -> proto-self -> functional psyche -> monotone Kant regulation -> central projection -> workspace retroaction -> Surface A/B path for this hardening. Egress state, journal, dashboard, transcript and Surface B remain control/audit projections and cannot create evidence or authorize actions.

No GitHub connector or Node.js runtime is required after materialization; Python 3.11+ and writable local `.ikant/` persistence remain sufficient.
