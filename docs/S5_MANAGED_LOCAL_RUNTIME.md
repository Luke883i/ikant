# S5 — Managed Local Runtime & Model Supply Chain (v0.23)

## Intent

S5 turns the S2 model adapter from “connect to an already-running endpoint” into an iKant-owned, deterministic local component lifecycle. It adds no user, epistemic, grant, lease or actuator authority.

## Runtime chain

`./ikant.sh → MODEL_RUNTIME.json → ComponentStore → resumable verified acquisition → atomic engine/model install → EngineSupervisor → private authenticated loopback llama-server → managed ModelBroker → Local Embodiment → T&C → PROBE(MODEL_RUNTIME) → INITIALIZE → ACTIVE`

The browser never receives the model endpoint, API key, filesystem component paths or process handle. `llama-server` is started with an argv vector (`shell=False`), loopback-only, ephemeral port, private key file, WebUI disabled and with no iKant-enabled agent/tool surface.

## Supply-chain contract

- engine release tag, platform artifact URL and SHA-256 are immutable and exact;
- model repository revision is a full commit and the GGUF URL/SHA-256 are exact;
- floating `latest`, model `main`, HTTP transport and digest drift fail closed;
- `.partial` downloads resume with Range; a server ignoring Range restarts safely;
- byte ceilings bound disk acquisition; archive member count and expansion are bounded;
- tar traversal, links, devices and FIFOs are rejected;
- installed engine trees are content/mode hashed on every reuse so post-install tamper causes rejection/reinstall;
- verified model SHA is rechecked on reuse;
- model/runtime projections have zero epistemic and execution authority.

## Lifecycle and recovery

Shared components live outside the repository. `.ikant/model-runtime.json` records only non-secret identity/digest/status. The API key is a 0600 no-follow runtime file and is removed when supervision stops. A failed or crashed startup remains BLOCKED/STOPPED and is safe to retry: complete verified components are reused, valid partial downloads resume, invalid partials are discarded, and every launch revalidates the installed tree/model before process start.

`PROBE` in the managed launcher adds a live `MODEL_RUNTIME` check and `INITIALIZE` repeats health immediately before ACTIVE, preventing a stale bootstrap-ready state from becoming an ACTIVE session.

## Falsification / DoD

- product identity and invariant registry converge to v0.23 while access contract stays v0.12;
- S1–S4 historical prefix remains constitutional;
- `MLR-001..003` are CRITICAL and machine-tested;
- S5 participates in the single version-neutral Product Boundary;
- PR gate: 3 seeds × 100,000 cases + 10,000 tail across every registered stress/mutation/edge harness;
- additional 100,000 + 100,000 no-novelty gate;
- S5 focused families cover immutable pins, corrupt/partial downloads, archive attacks, post-install tamper, private key handling, environment injection, loopback binding, UI/agent/tool enablement, browser transport and zero-authority drift;
- Hosted, Reticular and Product Boundary must PASS the same current synthetic merge SHA before merge;
- real release acceptance remains: clean supported host → `./ikant.sh` → component acquisition → real Qwen health/turn → T&C/PROBE/INITIALIZE → ACTIVE → shutdown/restart → verified reuse.
