# S10bis hotfix4 — Surface A generation convergence and progressive disclosure

## Observed runtime state

The managed runtime now reaches all seven bootstrap gates and `llama-server` is READY with the pinned b10344 CPU artifact and Qwen3.5-0.8B-Q4_0 model. The next observed failure is therefore not bootstrap failure: a first conversational turn can fall back to the operational message even though model readiness is healthy. The original web shell then renders the whole HSPv2 dashboard as the primary chat viewport, so the user sees internal status rows such as `SUPERFICIE A [VALIDATED]` instead of a concise conversation.

## Concrete findings

1. `EngineSupervisor.build_server_command()` left llama.cpp reasoning in its default `auto` mode. Exact upstream b10344 code supports `--reasoning on|off|auto`, maps `off` to `enable_thinking=false`, and explicitly prefers this switch over legacy chat-template kwargs. Qwen3.5 upstream reports show reasoning/template modes can move output into reasoning channels or otherwise interfere with constrained final output.
2. `LocalModelBroker.complete_surface_a()` validated only the generic Surface A format. The stronger interaction contract — identity-first and exact engine disclosure for questions such as `chi sei?` — was enforced later at interaction close, outside the model repair loop. A response could therefore be format-valid yet interaction-invalid.
3. The operational fallback language heuristic did not recognize `ciao`, so an Italian turn could receive the English fallback. Identity fallbacks also lacked the exact iKant/engine ordering required by the interaction contract.
4. The web client rendered `frame.text`, the complete sealed HSPv2 dashboard, directly into the chat viewport. It also waited for the TURN request to complete before displaying any pending state.

## Minimal convergent reticulum

`user intent -> cognitive turn -> Surface A contract + interaction contract -> loopback Qwen3.5 with reasoning OFF -> bounded repair loop -> validated Surface A -> deterministic primary projection -> chat`

The canonical HSPv2 frame remains byte-for-byte sealed and exact-ACKed, but is shown only under progressive disclosure in Inspector. The primary chat projection is derivative and zero-authority. Its allowed states are intentionally tiny:

- control output: `iKant: <concise control message>`;
- active pending TURN: `iKant: [PENDING - la risposta validata non e ancora stata emessa]`;
- closed validated TURN: `iKant: <validated Surface A>`.

No dashboard row, Surface B telemetry, readiness fact, evidence statement, approval, grant, lease or execution receipt may be promoted into the primary chat by this projection.

## Runtime changes

- `llama-server` is started with `--reasoning off`; tools, agent mode, web UI and browser model transport remain disabled.
- The model prompt contains both the Surface A and interaction contracts. Generic and interaction validation share the same bounded repair loop.
- Output token budget is bounded from the interaction word budget instead of always allowing 900 tokens.
- Italian fallback detection recognizes short natural turns such as `ciao`; identity fallback says iKant first and discloses the bound engine label.
- Generation source is persisted as zero-authority runtime telemetry (`MODEL` or `OPERATIONAL_FALLBACK`) bound to the cycle.
- `web_frame.project_primary_text()` derives the primary chat line from the canonical sealed dashboard without modifying it.
- The browser displays PENDING immediately on submit. Full HSPv2 text plus receipt/render contract remains available through Dettagli/Inspector.

## Falsification history

The convergence receipt intentionally records rejected matrices rather than hiding them.

- Run 1, 10M: rejected because mutation hits were counted outside applicability domains. Twelve apparent survivors exposed the falsifier error.
- Run 2, 10M: `PRIMARY_DROP_IKANT_PREFIX` survived. The primary identity invariant was strengthened across TURN, ERROR and EXIT.
- Run 3, 10M: `PENDING_AFTER_VALID` and `VALID_BEFORE_REPLY` survived because pending/validated cycle state was not modeled independently from text. State binding was added.
- Final run, 10M trajectories + 10M mutation trials: 49/49 mutation classes fully killed, minimum 204,081 hits and kills per class, 0 baseline failures, 0 survivors, 368 semantic signatures, +1,000 no-novelty with 0 novelty.

The falsifier covers reasoning mode, interaction contract loss, format-only validation, identity/engine disclosure, tool calls, empty/reasoning-only output, repair bounds, fallback action claims, stale source/cycle binding, Surface B cycle mismatch, dashboard leakage, missing progressive details, ACK digest mismatch, voice leakage, pending/validated ordering, browser authority/readiness/model transport, remote endpoint, floating supply-chain pins, retry history rewriting, parallel reply and control-byte injection.

## Authority boundary

Model output, fallback output, primary projection, canonical HSPv2 details, readiness and UI presentation remain epistemic authority 0.0 and execution authority 0.0. The hotfix does not create evidence, permission, approval, grant, lease or execution capability. It changes generation conformance and presentation only.
