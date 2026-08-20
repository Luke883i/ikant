# iKant v0.22-test

iKant is a governed local epistemic agent runtime for conforming AI session-chat hosts. The current product line includes the Epistemic Core, Temporal Epistemics, Practical Reason, Planning, Execution Handoff, Host Conformance, and the first four agency slices: **S1 Agency Kernel, S2 Local Embodiment, S3 Web Agency, S4 Native Agency**.

## Constitutional boundary

The v0.12 rights/access contract remains the owner-authorization contract. Product v0.22 does not weaken it. After ACTIVE, canonical human egress remains the sealed dashboard frame and machine output remains file-only. Runtime-derived state, model output, control receipts, grants, leases and execution reports carry no independent epistemic authority.

The authority lattice is intentionally non-collapsible:

`evidence != permission != approval != grant != lease != execution != world truth`.

S1 issues exact session-bound capability grants and one-shot execution leases. S2 provides the loopback-only local browser/PWA embodiment and zero-authority local model/voice adapters. S3 adds capability-bound web observation/action. S4 adds a deliberately narrow native filesystem boundary (`read` existing regular UTF-8 files and `create` absent UTF-8 files) without generic process, shell, credential or secret authority.

`PRODUCT_CONTRACT.json` is the product-slice manifest. `ikant.invariants` remains the canonical cross-cutting invariant registry. `scripts/product_boundary.py` verifies that every materialized agency slice is registered, has its machine tests and stress/mutation/edge harnesses, and preserves the authority boundary.

## Local execution

The current S2 launcher is:

```sh
./ikant.sh
```

It starts the local iKant daemon/PWA. At v0.22 the language model endpoint is still an already-running loopback OpenAI-compatible service; managed model download, weight lifecycle and inference-engine supervision are intentionally deferred to the next product slice rather than being silently implied here.

Canonical CLI execution remains `python -m ikant`. See `IKANT_ACCESS_CONTRACT.md`, `RIGHTS.md`, `docs/S3_WEB_AGENCY.md`, and `docs/S4_NATIVE_AGENCY.md`.
