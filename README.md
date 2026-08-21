# iKant v0.26-test

iKant is a governed local epistemic agent runtime. Product v0.26 materializes **S1 Agency Kernel, S2 Local Embodiment, S3 Web Agency, S4 Native Agency, S5 Managed Local Runtime & Model Supply Chain, S6 Temporal Autonomy, S7 Human Surface Protocol v2, and S8 Advanced Web Shell** on top of the Epistemic Core, Temporal Epistemics, Practical Reason, Planning, Execution Handoff and Host Conformance layers.

## Constitutional boundary

The v0.12 rights/access contract and the v0.11 crash-recoverable dashboard egress remain unchanged. S8 does not add authority; it removes browser concurrency/retry ambiguity around the existing S7 human-surface path.

`browser shell != semantic output != evidence != permission != approval != grant != lease != execution != world truth`

After ACTIVE, every semantic iKant output remains one HSPv2 envelope rendered **inside the same sealed dashboard frame** and acknowledged by the existing exact-byte egress protocol. The Advanced Web Shell adds a paired, runtime-session-bound, single-writer control protocol around that frame: monotonic operation sequence, whole-session idempotency keys, exact previous-frame binding, pending-response replay and exact shell-bound ACK.

The canonical PWA uses `/api/v2/shell/open`, `/api/v2/shell/command`, and `/api/v2/shell/ack` for ACTIVE flow. Once S8 claims the writer, legacy ACTIVE mutation routes cannot bypass shell sequencing. Shell chrome/status is zero-authority control state; it is not a second human semantic surface.

S8 operations are deliberately bounded to `SYNC`, `TURN`, `EXIT`, and `RESUME`. It does not add arbitrary JavaScript, arbitrary HTTP, downloads, POST/form submission, model transport, native process execution, secrets, approvals, grants, leases or direct S3 web-execution authority.

`PRODUCT_CONTRACT.json` is the cumulative product-slice manifest; `ikant.invariants` is the cross-cutting invariant registry; `scripts/product_boundary.py` derives all registered slices and executes the current slice's contract-declared saturation budget without per-version workflow accretion.

## One-command local runtime

```sh
./ikant.sh
```

S5 owns the verified model/engine lifecycle, S6 owns control-only temporal wake semantics, S7 owns ACTIVE human presentation, and S8 owns the canonical browser shell sequencing/replay boundary. The browser still renders the sealed frame verbatim and acknowledges actual DOM `textContent`; S8 changes control coordination, not semantic authority or the transport trust boundary.

`EXIT IKANT` remains release-after-frame-ACK and `RESUME IKANT` remains integrity-gated. S8 does not weaken Surface B DOCX requirements, S1 grants/leases, S3 web execution, S4 native execution, S5 runtime supply-chain verification, S6 temporal freshness barriers or S7 HSPv2.

The S5 baseline model remains `Qwen3.5-0.8B-Q4_0`; `MODEL_RUNTIME.json` retains its historical S5/v0.23 identity. Canonical CLI execution remains `python -m ikant`.

See `IKANT_ACCESS_CONTRACT.md`, `RIGHTS.md`, `docs/S5_MANAGED_LOCAL_RUNTIME.md`, `docs/S6_TEMPORAL_AUTONOMY.md`, `docs/S7_HUMAN_SURFACE_PROTOCOL_V2.md`, and `docs/S8_ADVANCED_WEB_SHELL.md`.
