# iKant v0.23-test

iKant is a governed local epistemic agent runtime. Product v0.23 materializes **S1 Agency Kernel, S2 Local Embodiment, S3 Web Agency, S4 Native Agency, and S5 Managed Local Runtime & Model Supply Chain** on top of the existing Epistemic Core, Temporal Epistemics, Practical Reason, Planning, Execution Handoff and Host Conformance layers.

## Constitutional boundary

The v0.12 rights/access contract remains unchanged. S5 adds component acquisition and process supervision, not authority. The lattice remains non-collapsible:

`evidence != permission != approval != grant != lease != execution != world truth`.

Model output, downloaded component presence, engine health and runtime readiness all carry **zero epistemic and execution authority**. S1 grants/leases, S3 web effects and S4 native effects keep their existing explicit commit points. After ACTIVE, canonical human egress remains the sealed dashboard frame and machine output remains file-only.

`PRODUCT_CONTRACT.json` is the cumulative product-slice manifest; `ikant.invariants` is the cross-cutting invariant registry; `scripts/product_boundary.py` discovers and falsifies every registered slice without adding per-version workflows.

## One-command local runtime

```sh
./ikant.sh
```

S5 owns the complete language-engine lifecycle. On first launch it validates `MODEL_RUNTIME.json`, resumes or downloads exact pinned artifacts, enforces byte bounds, verifies SHA-256, atomically installs the pinned `llama.cpp` engine and Qwen GGUF, starts `llama-server` on a private loopback ephemeral port with a private API-key file and `--no-webui`, waits for health, then starts the local iKant daemon/PWA. If any step fails, startup is **BLOCKED**; no simulated fallback may declare READY.

The baseline model is `Qwen3.5-0.8B-Q4_0` (~563 MB, Apache-2.0). Components are stored outside the repository under `XDG_DATA_HOME/ikant` or `~/.local/share/ikant` (override with `IKANT_COMPONENT_HOME`). The project persists only a zero-authority binding projection in `.ikant/model-runtime.json`; model endpoint, API key and model-server output are not persisted or exposed to the browser.

Pre-ACTIVE acquisition progress is emitted by the launcher. A rich componentized browser installer is intentionally not introduced before the Human Surface Protocol v2 slice, because doing so would create a parallel semantic human surface under the current exact-frame egress contract.

Canonical CLI execution remains `python -m ikant`. See `IKANT_ACCESS_CONTRACT.md`, `RIGHTS.md`, `docs/S5_MANAGED_LOCAL_RUNTIME.md`, and the prior S3/S4 design notes.
