# iKant v0.25-test

iKant is a governed local epistemic agent runtime. Product v0.25 materializes **S1 Agency Kernel, S2 Local Embodiment, S3 Web Agency, S4 Native Agency, S5 Managed Local Runtime & Model Supply Chain, S6 Temporal Autonomy, and S7 Human Surface Protocol v2** on top of the Epistemic Core, Temporal Epistemics, Practical Reason, Planning, Execution Handoff and Host Conformance layers.

## Constitutional boundary

The v0.12 rights/access contract and the v0.11 crash-recoverable dashboard egress remain unchanged. S7 does not add authority; it makes the meaning of every ACTIVE human frame explicit and machine-checkable.

`human presentation != authority != evidence != permission != approval != grant != lease != execution != world truth`

After ACTIVE, every semantic iKant output is one HSPv2 envelope rendered **inside the same sealed dashboard frame** and acknowledged by the existing exact-byte egress protocol. Raw model tokens, parallel notices and textual DOM error channels are not human output surfaces.

HSPv2 frame kinds are `INITIALIZE`, `DASHBOARD`, `TURN`, `NOTICE`, `APPROVAL_REQUEST`, `PROGRESS`, `ERROR`, `DEGRADED`, `RECOVERY`, `EXIT`, and `RESUME`. Each frame has one exclusive typed payload. A `TURN` requires validated Surface A plus a same-cycle bound Surface B JSON/DOCX pair. Progress, degraded state, errors and recovery are zero-authority control projections.

An `APPROVAL_REQUEST` can display only a valid current-session S1 `HumanFrame`. Displaying it does not record a decision, issue a grant, create a lease or execute anything; the existing authenticated human-interaction and Agency Kernel path remains authoritative.

`PRODUCT_CONTRACT.json` is the cumulative product-slice manifest; `ikant.invariants` is the cross-cutting invariant registry; `scripts/product_boundary.py` derives all registered slices and executes the current slice's contract-declared saturation budget without per-version workflow accretion.

## One-command local runtime

```sh
./ikant.sh
```

S5 owns the verified model/engine lifecycle and S6 owns control-only temporal wake semantics. S7 owns only the ACTIVE human presentation protocol. The browser still renders the sealed frame verbatim and acknowledges the exact DOM `textContent`; HSPv2 changes the semantic envelope, not the transport trust boundary.

If an ACTIVE backend operation fails, the server attempts to materialize an HSPv2 `ERROR` frame. If the transport itself is unavailable, the browser does not fabricate an iKant message outside the sealed dashboard; it freezes controls and recovers the last server-owned frame when possible.

`EXIT IKANT` remains release-after-frame-ACK and `RESUME IKANT` remains integrity-gated. S7 does not weaken Surface B DOCX requirements, S1 grants/leases, S3 web execution, S4 native execution, S5 runtime supply-chain verification or S6 temporal freshness barriers.

The S5 baseline model remains `Qwen3.5-0.8B-Q4_0`; `MODEL_RUNTIME.json` retains its historical S5/v0.23 identity. Canonical CLI execution remains `python -m ikant`.

See `IKANT_ACCESS_CONTRACT.md`, `RIGHTS.md`, `docs/S5_MANAGED_LOCAL_RUNTIME.md`, `docs/S6_TEMPORAL_AUTONOMY.md`, and `docs/S7_HUMAN_SURFACE_PROTOCOL_V2.md`.
