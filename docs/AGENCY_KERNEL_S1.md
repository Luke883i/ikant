# S1 Agency Kernel

S1 adds a minimal authority boundary between v0.17 execution handoffs and future browser/native actuators without changing the v0.12 access contract, v0.15 action governance, v0.16 planning, v0.17 execution semantics or v0.18 host conformance.

## Semantic chain

`HumanFrame -> explicit interaction receipt -> CapabilityGrant -> ExecutionLease -> v0.18 host revalidation -> external actuator`

Each arrow is conjunctive. No upstream object implies the next one.

### HumanFrame

A HumanFrame is a deterministic presentation object. Presentation has zero epistemic and execution authority. A capability grant requires an explicit compatible decision bound to the exact frame, current runtime session and configured local interaction channel. The interaction MAC authenticates possession of the configured channel secret; it does not prove civil, biometric or production-host identity.

### CapabilityGrant

A grant contains exact `(capability, resource)` entitlements. Wildcards, prefix expansion and traversal scopes are rejected. Grants are session-bound, usage-bounded, optionally expiring and explicitly revocable. Revocation increments a monotonic epoch; a lease bound to an older epoch becomes invalid.

### ExecutionLease

A lease is a one-shot execution precondition, never execution authority. It is exactly bound to the v0.17 session, cycle, intent, handoff, idempotency key, action fingerprint, Action Ledger digest, Plan Ledger digest, plan and step. It also binds exact entitlement pairs and the current grant digests/epochs. Terminal, expired, revoked or drifted leases fail closed.

Pending leases reserve grant uses, so concurrent handoffs cannot oversubscribe the final use. Cancellation releases the reservation. Consumption is terminal.

### Recovery / outbox

`.ikant/agency-events.jsonl` is the canonical append-only SHA-256-chained journal. `.ikant/agency.json` is rebuildable. A PENDING lease is a durable outbox record; recovery only returns it for inspection/revalidation. Recovery never executes an action and a recovered handoff must pass fresh host revalidation before an external actuator may act.

## Boundary with v0.18

`AgencyHostBinding` is conjunctive: a current valid S1 lease is required before the existing v0.18 host binding is asked for exact execution revalidation. The binding returns a zero-authority bundle containing the lease digest and host receipt. It performs no material action.

## Validation

Targeted unit tests: 15/15 PASS.

Semantic stress: 100,000 cases + 10,000 no-novelty tail; complete 65,536-state explicit universe; 17 consequence signatures; 0 violations; tail novelty 0.

Edge saturation: 100,000 cases + 10,000 tail; complete 32,768-state universe; 576 signatures; 0 violations; tail novelty 0.

Semantic mutation campaign: 100,000 mutations + 10,000 tail across 40 authority/replay/revocation/recovery families; 0 survivors; 0 tail-new families. This is an executable semantic mutation model, not a generic AST mutation engine.

## Deferred by design

S1 does not implement a PWA, voice runtime, browser automation, native OS access, scheduler or autonomous execution. Those are later adapters/slices and must consume S1 leases rather than inventing new authorization paths.
