# S10 — Epistemic Workspace / Surface B Explorer (v0.28)

S10 materializes a bounded, read-only epistemic workspace over the Surface B JSON/DOCX artifacts that iKant already produces for substantive cognitive turns. It does **not** create new cognition, evidence, permission, approval, grant, lease or execution authority. It turns persisted, cycle-bound Surface B state into a progressively disclosed inspection surface inside the S9 product workspace.

## Product thesis

The S9 chat remains primary and the HSPv2 sealed dashboard remains the only ACTIVE semantic iKant output. S10 adds an **epistemic lens**, not another response channel.

The user may open `Artefatti` and inspect the current or recent Surface B through:

- graph and list views;
- bounded cycle history;
- object peek cards;
- conflicts, hypotheses and runtime backlog;
- confidence/evidence/source metadata already present in the snapshot;
- reticulum/ring state and selected diagnostics;
- exact frame/session/cycle binding information;
- same-origin downloads of the bound Surface B JSON and DOCX artifacts.

The guiding separation is:

`Surface B source snapshot != projection != presentation != evidence != permission != approval != grant != lease != execution != world truth`

## Canonical read path

```text
S9 ACTIVE workspace
  -> current paired S8 shell writer
  -> exact last acknowledged sealed frame
  -> no pending frame
  -> GET /api/v4/epistemic/index|cycle|artifact
  -> runtime-session binding
  -> cycle-id validation
  -> generated .ikant/cognitive / .ikant/artifacts path
  -> bounded Surface B read
  -> zero-authority projection
  -> graph/list/peek/artifact UI
```

Any writer drift, frame drift, runtime-session drift, pending sealed frame, malformed cycle identifier, path escape, missing companion data or size-bound violation fails closed.

## Read-model boundaries

S10 deliberately reuses existing persistence. No new epistemic database or duplicated source of truth is introduced.

Current bounds:

- cycle history: at most 64 entries;
- projected epistemic objects: at most 96;
- Surface B JSON snapshot: at most 4 MiB;
- projected free text: bounded and normalized;
- artifact download: at most 16 MiB;
- event projection: only a small diagnostic key vocabulary is exposed.

The event projection never reflects arbitrary payload keys or values. The supported metadata vocabulary is limited to bounded diagnostics such as `phase`, `reason`, `status`, `kind`, `count` and `validated`.

## DOCX companion rule

A DOCX filename being present is insufficient. Before serving a Surface B DOCX, S10 re-opens the companion JSON snapshot and verifies the same runtime session and cycle. A stale/colliding DOCX cannot be projected independently of its canonical Surface B companion.

## UI contract

S10 does not modify `#dashboard`, the HSPv2 visible-text ACK, the composer or the S8 command sequence. It mounts only inside the S9 `Artefatti` inspector area.

The lens provides:

- `Graph` / `List` dual view;
- keyboard-selectable nodes;
- bounded Peek detail;
- cycle history selector;
- diagnostic/binding disclosure;
- JSON/DOCX artifact buttons.

All UI elements are read projections with epistemic authority `0.0` and execution authority `0.0`. Opening a node, switching views or downloading a Surface B artifact cannot become evidence or authorization.

The browser continues to have no model protocol. S10 assets are same-origin and framework/CDN-free. The PWA cache key is advanced to `ikant-s10-epistemic-v1` so an installed S9 client cannot silently retain the old UI.

## Constitutional invariants

- **EPW-001 — exact-reader binding:** Surface B inspection requires the current S8 writer and exact last acknowledged frame; pending frames and writer/frame/session drift fail closed.
- **EPW-002 — bounded source binding:** reads are same-session/cycle, generated-path-only and bounded; DOCX requires a same-session/cycle JSON companion.
- **EPW-003 — projection non-collapse:** graph/list/peek/history/artifact presentation has zero authority, is not evidence/authorization and creates no second semantic surface or browser-model path.
- **EPW-004 — source/projection continuity:** projection is not source truth; arbitrary event metadata is not exposed; stale PWA assets are invalidated; S8/S9 semantics remain unchanged outside the derived read adapter.

## Falsification and saturation

S10 uses semantic adversarial mutation and state-space harnesses over the epistemic-workspace contract lattice. They are not represented as compiled Python AST mutation counts.

The contract-declared current-slice budget is:

- 10,000,000 stress worlds;
- 16 deterministic diversified sub-seeds;
- 10,000,000 logical/functional mutation instances;
- 128 mutation families across 16 kill classes;
- 10,000,000 edge/convergence cases across 40 families;
- +1,000 no-novelty tail;
- exhaustive minimality search across 1,048,576 candidate architectures plus +1,000 no-better-compression perturbations.

The converged architecture has one minimal valid 13-feature set. The requested additional independent campaign also completed 1,000,000 stress cases with seed `314159265`, with zero violations and zero new semantic signatures.

A concrete survivor found during implementation was a stale DOCX path that could otherwise be read without revalidating its JSON companion. It was killed by requiring the companion snapshot on every DOCX read and is covered by unit tests.

## Definition of Done

### Global

- S1-S9 remain historical constitutional prefixes;
- S9 chat/HSPv2 remains the only ACTIVE semantic surface;
- Surface B can be inspected without introducing new persistence or authority;
- exact ACK/current-writer/no-pending-frame are mandatory read preconditions;
- all source reads are same-session/cycle, generated-path-only and bounded;
- JSON/DOCX artifact access is integrity-bound;
- UI remains progressive, keyboard-usable, responsive and local-only;
- Product Boundary reruns the contract-declared S10 saturation on the PR candidate.

### Local / intermediate

- history <= 64;
- objects <= 96;
- snapshot <= 4 MiB;
- artifact <= 16 MiB;
- arbitrary event payload metadata is not exposed;
- graph/list/peek do not touch `#dashboard`;
- HTTP S10 adds no mutation endpoint;
- DOCX fails closed without a valid same-session/cycle JSON companion;
- PWA cache invalidates the S9 asset generation;
- no lower-cost architecture preserving the required feature set is found.

## Historical compatibility

S10 advances the cumulative product identity to v0.28 but does not bump the v0.12 repository access contract, v0.11 egress transport, v0.23 model-runtime manifest, v0.24 temporal protocol, v0.25 HSPv2 protocol, v0.26 Advanced Web Shell protocol or v0.27 Product Experience schema. S1-S9 retain their original authority separations and recorded saturation evidence.
