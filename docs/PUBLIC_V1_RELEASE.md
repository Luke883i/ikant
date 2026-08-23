# iKant Public v1.0 Test — S13 Runtime/UX Convergence

Public release identity: `v1.0-public-test`

## Intent

S13 turns the already-governed local runtime into one bounded, legible and truthful human workspace. It does not create new execution faculties. Every visible service must be backed by persisted runtime state, an authenticated local API, or a client-local capability attestation that iKant can verify at use time.

## Audit evidence and root causes

The pre-S13 product could render pairing, setup, admission, active workspace and release controls in one vertically scrolling document. The immediate cause was CSS display rules overriding the HTML `hidden` attribute. This allowed mutually exclusive lifecycle stages to remain laid out together. The admission controller also disabled the acceptance input outside exactly one state, making recovery and state transition opaque. The active workspace exposed only the latest dashboard text while a verified append-only visible chat transcript already existed below the product layer. Diagnostics exposed capability/evidence summaries, but they were too sparse and detached from the conversation to communicate the runtime's real value.

S13 treats those as end-to-end reconciliation defects, not styling defects.

## Public workspace contract

The normal product has one viewport and one primary task surface. Pairing, preparation and admission are mutually exclusive stage views. ACTIVE is a persistent conversation workspace: verified visible transcript in the center, current cognitive/epistemic signal beside the task, runtime-backed services and configuration in a side inspector, and no browser-level capability invented from presentation.

The UI follows five product rules:

1. **One lifecycle stage at a time.** `[hidden]` is absolute and page-level vertical stacking cannot resurrect inactive surfaces.
2. **Conversation is persistent context.** The visible timeline comes from the session-bound, hash-verified `ChatLog`; the dashboard remains the sealed current primary frame and is de-duplicated once persistence catches up.
3. **Only demonstrated services appear.** Service affordances derive from Foundation capability projection or bounded client-local attestation. Missing capabilities are absent rather than disabled promises.
4. **Epistemic evidence is useful but modest.** Direct support, derivation, conflict and uncertainty are presented as provenance/value signals; they never certify truth, permission or action authority.
5. **Configuration is scoped.** Meta-prompt and user guardrails alter generation preferences only. They cannot enable tools, widen capabilities, create evidence, or cross exact-ACK/single-writer governance.

The interaction pattern is intentionally aligned with current frontier workspace conventions: persistent project context, a conversation-first center, and contextual/configuration surfaces beside the work rather than a chain of independent pages. The implementation is original to iKant and remains constrained by its local runtime and authority model.

## Runtime → projection → UI reconciliation

| Runtime fact | Projection | Public UI | Authority |
| --- | --- | --- | --- |
| ACTIVE runtime + verified managed model | Foundation capability catalog | Conversation workspace | zero browser/model authority |
| Hash-verified `ChatLog` | public conversation projection | User/iKant timeline | visible record only |
| Current cognitive cycle | Experience/Foundation projections | cognitive path + epistemic chips | derived, zero epistemic authority |
| Exact acknowledged same-cycle snapshot | epistemic workspace/capability catalog | Rete / JSON / DOCX when available | read-only |
| Persisted recognized runtime JSON | public runtime-system projection | Ambiente cards | inspect-only |
| Experiment config revision | Foundation config | Configura | generation-only |
| Local/on-device voice attestation | server/client capability evidence | Voice only when available | transcript-only until Send |

Unknown, stale, malformed or unavailable state produces absence or a bounded recovery state. It never creates a capability card or success state.

## Release DoD

### Local DoD

- Mutually exclusive lifecycle surfaces cannot co-render.
- `I ACCEPT` remains writable whenever admission is visible; server state, not disabled text input, governs acceptability.
- A consumed pairing code produces a concise recoverable state and clears stale pairing material.
- Normal interaction fits one bounded application viewport; internal panes scroll, not the whole lifecycle document.
- Focus-visible, keyboard path and reduced-motion behavior remain available.
- Motion represents actual transitions/state only and is removable with `prefers-reduced-motion`.
- No second TURN controller, browser-model path, or alternate semantic writer is introduced.

### Reticular DoD

- Conversation history is session-bound and hash-verified before projection.
- Services shown in UI are a subset of currently demonstrable runtime capabilities.
- Runtime cards are from a fixed persisted-projection allowlist and are inspect-only.
- Exact ACK, single writer, artifact gating and post-ACK artifact generation remain unchanged.
- Evidence UI distinguishes direct support, derivation, conflict and uncertainty and never claims truth certification.
- Experiment configuration is revision-bound and generation-only.
- No lifecycle, UI, timing, model output or control state promotes itself into evidence/permission/approval/grant/lease/execution.

### Global DoD

- Existing constitutional/unit/product-boundary gates pass on exact PR head.
- S13 source-bound mutation gates pass on exact PR head.
- Browser smoke/accessibility sanity must pass before merge; modeled trials are not a substitute for real browser execution.
- Service-worker cache boundary invalidates the pre-S13 shell.
- S1–S12 evidence and authority contracts remain historical prefixes rather than being rewritten.

## Saturation receipt

The exact S13 candidate was exercised with varied deterministic seeds over four distinct source/runtime-contract campaigns:

- UX end-to-end: **10,000,000** modeled trajectories, 320 mutation families / 25 domains, 0 survivors.
- Onto-epistemic overall: **10,000,000** modeled trajectories, 320 mutation families / 25 domains, 0 survivors.
- UI↔runtime surface census: **3,000,000** modeled trajectories, 192 families / 24 domains, 0 survivors.
- Edge cases: **100,000** modeled trajectories, 256 families / 32 domains, 0 survivors.
- No-novelty tail: **100,000**, 0 new semantic signatures.
- Minimality search: **1,024** faculty architectures; exactly one valid minimum, 0 better non-degrading compressions in the tail.

Seeds: `2026082301`, `2026082307`, `2026082313`, `2026082379`.

Receipt SHA-256: `e14ee194c1a177563ac78d795584a46f1b97346b13338ca839bd469066f35132`.

These are deterministic source-bound semantic/runtime/UX falsification models. They are **not** a claim of 23.1 million real browser, GPU, operating-system, accessibility-tree or physical-device executions.

## Merge boundary

S13 is a `v1.0-public-test` candidate, not a claim of production maturity. Merge requires the exact PR head to preserve all inherited governance and pass repository CI; any real-browser defect that contradicts the local/reticular DoD is a release blocker even if the modeled mutation receipt remains green.
