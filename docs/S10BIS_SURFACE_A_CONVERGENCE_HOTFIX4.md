# S10bis hotfix4 — Surface A generation convergence and progressive disclosure

## Observed runtime state

The managed runtime now reaches all seven bootstrap gates and `llama-server` is READY with the pinned b10344 CPU artifact and Qwen3.5-0.8B-Q4_0 model. The next observed failure is therefore not bootstrap failure: a first conversational turn can fall back to the operational message even though model readiness is healthy. The original web shell also rendered the whole HSPv2 dashboard as the primary chat viewport.

## Concrete findings

1. `EngineSupervisor.build_server_command()` left llama.cpp reasoning at default `auto`. Exact upstream b10344 supports `--reasoning on|off|auto`, maps `off` to `enable_thinking=false`, and prefers that switch over legacy chat-template kwargs.
2. `LocalModelBroker.complete_surface_a()` validated only generic Surface A shape. The stronger interaction contract — including identity-first and exact engine disclosure for `chi sei?` — was enforced only later, outside the model repair loop.
3. The operational fallback language heuristic did not recognize `ciao`, and identity fallbacks did not satisfy the interaction identity/engine ordering.
4. The browser rendered canonical `frame.text` directly in chat and showed no immediate pending state while inference was active.
5. During implementation, further concrete delivery survivors were found: the new conversation asset was initially absent from the bootstrap static route; the PWA cache namespace could retain the old UI; and the primary viewport still inherited terminal/monospace presentation.

## Minimal convergent reticulum

`user intent -> cognitive turn -> Surface A contract + interaction contract -> loopback Qwen3.5 reasoning OFF -> bounded repair -> validated Surface A -> deterministic primary projection -> chat`

The HSPv2 dashboard remains the single canonical sealed payload. Its `VERBATIM_TEXT` contract and exact ACK are preserved; the complete bytes are written into progressive disclosure. Primary chat is a derivative zero-authority projection with an orthogonal `PRIMARY_WITH_PROGRESSIVE_DISCLOSURE` mode:

- control output: `iKant: <concise control message>`;
- active pending TURN: `iKant: [PENDING - la risposta validata non e ancora stata emessa]`;
- closed validated TURN: `iKant: <validated Surface A>`.

No dashboard row, Surface B telemetry, readiness fact, evidence statement, approval, grant, lease or execution receipt may be promoted into primary chat.

## Runtime and UX changes

- `llama-server` starts with `--reasoning off`; tools, agent mode, web UI and browser model transport remain disabled.
- Model prompt contains both Surface A and interaction contracts; both validators share one bounded repair loop.
- Output token budget derives from the interaction word budget rather than a fixed 900-token ceiling.
- Fallback detects short Italian turns and satisfies identity/engine ordering while explicitly performing no material action.
- Generation provenance (`MODEL` or `OPERATIONAL_FALLBACK`) is bound only after successful cycle close and remains authority 0/0.
- `web_frame.project_primary_text()` derives the concise primary line while canonical `text` remains unchanged and exact-ACKed.
- Browser renders PENDING immediately on submit; Dettagli/Inspector contains the complete HSPv2 frame, receipt, projection contract and generation provenance.
- PWA cache namespace is bumped and includes the primary conversation asset.
- Bootstrap HTTP explicitly serves the conversation asset.
- Primary chat uses natural conversational typography; canonical technical detail remains monospace in disclosure.

## Falsification history

The convergence record keeps rejected matrices rather than hiding them.

- Run 1, 10M: rejected because mutation hits were counted outside applicability domains; 12 apparent survivors exposed the falsifier error.
- Run 2, 10M: `PRIMARY_DROP_IKANT_PREFIX` survived; prefix identity was made invariant across TURN/ERROR/EXIT control output.
- Run 3, 10M: `PENDING_AFTER_VALID` and `VALID_BEFORE_REPLY` survived; independent pending/validated cycle state was added.
- A subsequent engineering audit found three unmodeled delivery/presentation families: asset 404, stale service-worker cache, and terminal-style leakage. The candidate was not accepted until those families were added and the complete matrix was rerun.
- Final run: **10,000,000 trajectories + 10,000,000 mutation trials, 52/52 mutation classes fully killed, minimum 192,307 hits/kills per class, 0 baseline failures, 0 survivors, 368 semantic signatures, +1,000 no-novelty / 0 novelty**.

The final matrix covers reasoning mode, interaction contract loss, format-only validation, identity/engine disclosure, tool calls, empty/reasoning-only output, repair bounds, fallback action claims, stale source/cycle binding, Surface B cycle mismatch, dashboard leakage, progressive details, ACK integrity, voice leakage, pending/validated ordering, browser authority/readiness/model transport, remote endpoint, floating pins, retry rewriting, parallel reply, control-byte injection, primary asset delivery, PWA cache freshness and conversational presentation.

## Authority boundary

Model output, fallback output, primary projection, canonical HSPv2 detail, readiness and UI presentation remain epistemic authority 0.0 and execution authority 0.0. This corrective slice creates no evidence, permission, approval, grant, lease or execution capability.
