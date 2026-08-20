# S6 — Temporal Autonomy (v0.24)

## Intent

S6 gives iKant durable temporal continuity without granting autonomous material authority. A schedule can become **due** and create a durable wake envelope; elapsed time can never become evidence, permission, approval, a capability grant, an execution lease, host revalidation, or execution.

The minimal runtime lattice is:

`Human schedule confirmation -> Durable task -> Due edge -> Wake envelope -> Freshness barrier -> Future human interaction -> existing S1-S4 material gates`.

There is deliberately no direct edge from `Wake envelope` to an actuator.

## Exact schedule authorization

A task is created only from a valid current-session `ACTION_CONFIRMATION` frame and interaction receipt bound to the SHA-256 fingerprint of the complete canonical schedule. Schedule confirmation may not contain capability entitlements or an execution handoff. Cancellation uses a separately fingerprinted current-session `ACTION_CONFIRMATION`.

Bounds are part of the contract: intent <= 16 KiB; recurrence is fixed-duration only; interval 60 seconds through 366 days; max 1000 fires; max 5 years future horizon; max five control-delivery attempts. Cron, civil-time timezone rules and ambient OS scheduling are intentionally excluded from the kernel.

## Clock model

Durable due times use integer Unix epoch milliseconds. The runner uses `time.monotonic_ns()` only to pace process-local polling; monotonic values are never persisted as absolute schedule identity.

Wall-clock rollback beyond a two-second tolerance transitions the scheduler into `CLOCK_BLOCKED`. Polling/claim/completion remains blocked until the observed wall clock reaches the pre-rollback clock floor. Forward jumps never replay every missed interval: recurrence uses `COALESCE`, producing one wake with an explicit missed-interval count and advancing the next due boundary beyond the current wall time.

## Durable state machine

Canonical state is a session-bound SHA-256 chained journal:

- `TASK_SCHEDULED`
- `WAKE_ISSUED`
- `WAKE_CLAIMED`
- `WAKE_RETRY`
- `WAKE_DELIVERED` / `WAKE_FAILED` / `WAKE_CANCELLED`
- `TASK_CANCELLED`
- `CLOCK_BLOCKED` / `CLOCK_RESUMED`

`.ikant/temporal-autonomy.json` is rebuildable control projection only. Replay, task presence, due state, clock state and wake state all have epistemic/execution authority `0.0`.

A claimed wake has a bounded control claim TTL. Crash/stale claim recovery may retry delivery of the **wake control item only**. An expired claim cannot later complete successfully. Explicit task cancellation terminalizes any pending, retry-pending or claimed wake.

## Freshness barrier

Every wake states explicitly:

- new human interaction required before material execution;
- pre-wake approval is not reusable;
- pre-wake grant is not reusable;
- pre-wake lease is not reusable;
- fresh host revalidation is required;
- execution eligibility is false;
- no material execution bridge exists.

This intentionally remains stricter than S1 grant lifetime. Even if a historical grant itself has not expired, S6 will not treat it as temporal authorization for future material work.

## Runtime integration and egress

`TemporalAutonomyRunner` starts inside the one-command local runtime, but advances state only when `.ikant/runtime.json` is ACTIVE and the session-matched egress state is exactly `DASHBOARD_LOCKED`. `FRAME_PENDING`, `RELEASE_PENDING`, `RELEASED` and `EGRESS_BREACHED` pause polling. Therefore `EXIT IKANT` also stops temporal advancement without introducing a parallel output channel.

The runner does not call the model, AgencyKernel, Web/Native hosts, execution protocol or dashboard transport. S6 ends at durable wake creation/control state; richer presentation and work-item consumption are S7 responsibilities.

S6 is not an OS daemon and does not promise hardware wake or power-on scheduling. Restart replay can detect overdue persisted tasks after the local iKant process is launched again.

## Falsification and saturation

The development lattice was refined after an initial rejected mutation generator correlated PRNG state with family selection and covered only 12/48 mutation families. The final generator guarantees round-robin family coverage and uses deterministic pseudo-randomness only for within-family boundary perturbation.

Pre-publication S6 saturation executed:

- unit/runtime boundary tests: PASS after iterative fixes;
- semantic mutations: **10,000,000 evaluated / 10,000,000 killed**, 48/48 families;
- irreducible operational kill classes: 9;
- saturation frontier: mutation 48;
- no-novelty tail: **+100,000**, zero new families and zero new semantic kill classes;
- stress: 1,000,000 cases, 16/16 families +100,000 no-novelty tail;
- edge: 1,000,000 cases, 16/16 families +100,000 no-novelty tail.

The nine retained kill classes are: authority barrier, human binding, bounded specification, clock discipline, recurrence/coalescing, idempotence/concurrency, journal integrity, retry-control-only, and session/egress boundary. Merging any of these classes further would erase a distinct fail-closed response and therefore reduce diagnostic/contractual fidelity.

These are semantic adversarial mutation instances over the S6 contract lattice; they are not a claim that ten million Python AST source mutants were compiled.

## Non-goals

S6 adds no new web/native capability, no credential access, no material-action retry, no model-initiated schedule approval, no cron parser, no timezone database, no OS background service, no hardware wake, no third human surface and no relaxation of S1-S5 invariants.
