# iKant v0.24-test

iKant is a governed local epistemic agent runtime. Product v0.24 materializes **S1 Agency Kernel, S2 Local Embodiment, S3 Web Agency, S4 Native Agency, S5 Managed Local Runtime & Model Supply Chain, and S6 Temporal Autonomy** on top of the Epistemic Core, Temporal Epistemics, Practical Reason, Planning, Execution Handoff and Host Conformance layers.

## Constitutional boundary

The v0.12 rights/access contract remains unchanged. S6 adds durable temporal control, not authority. The lattice remains non-collapsible:

`time != authority != evidence != permission != approval != grant != lease != execution != world truth`.

A due task or wake envelope can make an intention eligible for fresh consideration only. It cannot reuse a pre-wake approval, capability grant or execution lease, cannot satisfy host revalidation, and cannot perform a material action. Future material work starts again from a fresh human interaction and the existing S1-S4 execution gates.

`PRODUCT_CONTRACT.json` is the cumulative product-slice manifest; `ikant.invariants` is the cross-cutting invariant registry; `scripts/product_boundary.py` derives all registered slices and can execute the current slice's contract-declared saturation budget without adding per-version workflows.

## One-command local runtime

```sh
./ikant.sh
```

S5 still owns the verified model/engine lifecycle. S6 additionally starts a local temporal-control runner after the local service is constructed. It polls only while the runtime is ACTIVE and dashboard egress is exactly `DASHBOARD_LOCKED`; pending output, release, egress breach or `EXIT IKANT` suspend temporal polling.

Temporal tasks are current-session, exact human `ACTION_CONFIRMATION` controls. One-shot and bounded fixed-duration recurrence are supported. Missed recurring intervals coalesce into one wake; wall-clock rollback blocks the scheduler until the prior clock floor is reached; process waiting uses a monotonic clock. The hash-chained temporal journal is canonical and `.ikant/temporal-autonomy.json` is a zero-authority rebuildable projection.

S6 does **not** install an OS background daemon and does not wake a powered-off or sleeping machine. If iKant is restarted later, persisted tasks are replayed and an overdue recurrence is coalesced into one control wake. Rich human presentation and work-item consumption of these wakes remain intentionally deferred to S7 Human Surface Protocol v2, avoiding a second human egress surface.

The S5 baseline model remains `Qwen3.5-0.8B-Q4_0` (~563 MB, Apache-2.0); `MODEL_RUNTIME.json` retains its historical S5/v0.23 identity even though the product has advanced to v0.24.

Canonical CLI execution remains `python -m ikant`. See `IKANT_ACCESS_CONTRACT.md`, `RIGHTS.md`, `docs/S5_MANAGED_LOCAL_RUNTIME.md`, and `docs/S6_TEMPORAL_AUTONOMY.md`.
