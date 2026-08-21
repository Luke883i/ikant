# S9 — Product Experience / E2E Human Workspace (v0.27)

S9 is the first iKant slice whose primary deliverable is the end-to-end human product experience. It does **not** create a new authority path. It composes S5 managed local runtime, S7 HSPv2 and S8 Advanced Web Shell into a local application that opens immediately from `./ikant.sh`, explains setup progressively, preserves the existing T&C -> PROBE -> INITIALIZE contract and reaches a chat-first ACTIVE workspace.

## Product thesis

The S9 interface combines familiar interaction primitives with a deliberately compressed cognitive workspace:

- familiar center: conversation, composer, microphone, status and explicit actions;
- novel shell: orbit rail, contextual inspector and command palette;
- progressive disclosure: setup, artifacts, epistemic/system inspection and traditional controls exist on demand rather than occupying the default viewport;
- one semantic surface: the only ACTIVE iKant semantic output remains the exact sealed HSPv2 dashboard frame;
- local-first presentation: no CDN or remote frontend dependency and no browser-to-model protocol;
- accessibility: keyboard-first core actions, responsive layout and reduced-motion behavior.

The guiding separation is:

`presentation != readiness != diagnostics != evidence != permission != approval != grant != lease != execution != world truth`

## Canonical end-to-end path

```text
./ikant.sh
  -> local HTTP product opens immediately
  -> ProductBootstrapCoordinator starts verified S5 runtime asynchronously
  -> setup progress / BLOCKED / retry remain zero-authority control state
  -> T&C
  -> PROBE
  -> INITIALIZE
  -> S8 single-writer shell claim
  -> chat-first workspace
  -> one HSPv2 sealed semantic frame
  -> exact visible-text ACK
  -> optional local rendering / progressive inspection
```

A failed model download, verification or readiness transition does not require the product process to disappear. The product remains visible in `BLOCKED` and exposes an explicit retry. The browser cannot declare readiness; readiness is derived only from the verified managed runtime.

## Voice boundary

Voice input is an **input candidate**, never a decision modality.

Primary browser path may use on-device speech recognition when the browser exposes local processing. Optional iKant STT fallback is loopback-only and is bound to the same S8 writer/session before transcription is returned. In both cases the transcript only fills the composer: it is not automatically submitted and cannot approve a capability or action.

Voice output is optional assistive rendering, not a second semantic message. S9 permits speech only when all of the following hold:

1. the user enabled local speech output;
2. the selected browser voice reports local service;
3. the frame receipt is a `TURN`;
4. the exact S8/HSP visible-text ACK has already completed;
5. spoken text is extracted from the same sealed Surface A.

A `SYNC`, setup notice, error, dashboard refresh or already-ACKed historical state therefore cannot become an accidental new spoken iKant answer.

## Progressive disclosure contract

Default ACTIVE view is intentionally small: one conversation response viewport and one composer. Additional complexity is navigable through disclosure rather than removed:

- orbit rail: conversation / artifacts / system context;
- inspector: current frame and zero-authority diagnostic/control projections;
- command palette: keyboard access to advanced commands;
- traditional controls: sync, exit, pairing/reset and detailed diagnostics on demand;
- setup surface: verified local-runtime progress before readiness.

Opening, closing or navigating these controls has zero epistemic/execution authority.

## Constitutional invariants

- **EXP-001 — bootstrap non-collapse:** the product may be visible before model readiness; progress, diagnostics and retry never create readiness or authority.
- **EXP-002 — single semantic viewport:** advanced UI remains chrome around exactly one sealed HSPv2 semantic viewport. No remote frontend or browser-to-model path is introduced.
- **EXP-003 — voice non-collapse:** voice input never auto-submits or approves; voice output is local, post-ACK and same-TURN bound.
- **EXP-004 — product continuity:** T&C -> PROBE -> INITIALIZE, S8 writer/replay rules, keyboard accessibility, responsive/reduced-motion behavior and explicit degraded recovery remain intact under progressive disclosure.

## Falsification model

S9 stress/mutation counts are semantic adversarial instances over the S9 product-experience lattice. They are **not** claimed to be compiled Python AST mutants.

The current contract requires:

- 10,000,000 onto-epistemic stress worlds;
- 16 deterministic diversified sub-seeds derived from the contract seed;
- 10,000,000 logical/functional mutation instances;
- 96 mutation families across 12 kill classes;
- 100,000 real-code convergence/edge journeys;
- 1,000 no-novelty tail;
- exhaustive minimality search across 262,144 candidate UI architectures plus a 1,000-candidate no-better-compression tail.

Mutation classes include semantic-viewport duplication, readiness/UI authority collapse, admission-order bypass, second-writer paths, voice approval/autosubmit, non-local TTS, pre-ACK TTS, remote frontend/model transport, recovery re-execution, diagnostic authority and mouse-only access.

The stress harness uses deterministic round-robin family coverage and seed fan-out so random selection cannot falsely report family saturation.

## Definition of Done

### Global

- `./ikant.sh` opens a useful local product before managed-model readiness;
- verified component acquisition/readiness remains S5-owned and fail-closed;
- T&C -> PROBE -> INITIALIZE remains unchanged;
- ACTIVE uses the S8 writer and one sealed HSPv2 semantic viewport;
- text and voice input work without turning voice into approval;
- local voice output is post-ACK same-TURN rendering only;
- advanced functions are progressively disclosed with traditional controls available on demand;
- no CDN, remote frontend dependency or browser-to-model transport;
- keyboard, responsive and reduced-motion paths exist;
- Product Boundary executes the contract-declared S9 saturation on the PR synthetic merge SHA.

### Local / intermediate

- bootstrap progress is bounded/redacted and zero-authority;
- BLOCKED setup stays visible and retry is explicit;
- second browser writer remains denied by S8;
- pending frame recovery never re-executes a TURN;
- UI has exactly one `#dashboard` semantic viewport;
- command palette and inspector do not create semantic output;
- voice transcript does not auto-submit;
- TTS call occurs only after exact ACK;
- minimality search finds no lower-cost architecture preserving the required feature set.

## Historical compatibility

S9 does not bump the v0.12 repository access contract, v0.11 egress transport, v0.23 model-runtime manifest, v0.24 temporal protocol, v0.25 HSPv2 protocol or v0.26 Advanced Web Shell protocol. S1-S8 remain historical constitutional prefixes and retain their prior authority separations and saturation receipts.
