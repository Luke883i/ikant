# iKant v0.4-test Chat Design System

## Product mutation

v0.4 makes the initialized runtime legible as a persistent chat product without inventing a third cognitive surface. Surface A remains the validated natural-language payload. Surface B remains the audit snapshot. The DOS-like shell, transcript and dashboard are interface projections around those two surfaces.

The canonical self marker is literal `> iKant:`. It means "the iKant interface is speaking"; it is not a consciousness, sentience or biological-self claim. The model remains the disclosed execution engine underneath the accepted iKant-first hierarchy.

## Intent decomposition

The user request is atomized into six runtime rings:

1. **Transcript integrity** - append-only visible user/iKant records, session-bound and hash-chained.
2. **Shell chrome** - deterministic `> user:` / `> iKant:` rendering outside Surface A payload.
3. **Host binding** - one pending conforming turn, one validated Surface A, one transcript reply.
4. **Telemetry projection** - end-user KPIs derived from runtime state and the latest Surface B.
5. **DOCX backlog projection** - bounded, read-only indexing of local DOCX artifacts; category counts are operational telemetry only.
6. **Validation** - unit, negative, mutation, integration, stress and visual gates.

## Mutations kept / killed

| Candidate mutation | Decision | Reason |
| --- | --- | --- |
| Persist visible session chat | KEEP | Gives continuity and auditability without storing hidden reasoning. |
| Hash-chain transcript records | KEEP | Detects tamper/reordering and binds records to one runtime session. |
| Render `> iKant:` inside Surface A text | KILL | Would contaminate semantic payload with UI chrome. |
| Create a third cognitive "dashboard surface" | KILL | Violates the two-surface architecture. Dashboard is a view of Surface B/runtime. |
| Parse DOCX prose as evidence | KILL | Backlog documents may summarize telemetry but may never create epistemic evidence. |
| Auto-print dashboard on every answer | KILL | Adds noise and weakens Surface A compression. Dashboard is on demand and persistently available. |
| Store private chain-of-thought | KILL | Not required for audit; prohibited by product boundary. |
| Use terminal color as the only status cue | KILL | Accessibility and deterministic rendering require textual status labels. |

## Session interaction grammar

Normal host loop:

```text
> user: <visible human message>
  [host executes iKant conforming turn; Surface B is produced]
> iKant: <validated Surface A>
  [transcript + dashboard projection persist locally]
```

The transcript stores only visible speech acts and linkage metadata. If the runtime already has a pending Surface A, a second input is rejected before it is appended. A user record can have at most one iKant reply.

## Dashboard

The dashboard is persisted as `.ikant/dashboard.json` and `.ikant/dashboard.txt`. It is a deterministic end-user projection, not a new source of truth.

| KPI | Meaning | Typical state |
| --- | --- | --- |
| Runtime | Whether local iKant is ACTIVE | ACTIVE / BLOCK |
| Turns | Persisted cognitive cycle count | integer |
| Grounding | Functional attributable-content ratio exposed by the central oracle | % / n.a. |
| Caution | Current pressure to qualify, verify or abstain | % / n.a. |
| Conflicts | Explicit unresolved projected conflicts | count |
| Epistemic debt | Macrostates needing evidence/revision/retraction | count |
| Runtime integration | Proto-self software coordination proxy | %; never consciousness |
| CRC closure | Whether the declared representational path closes | SI/NO |
| Revision pressure | Recent correction/revision trend | % / n.a. |
| Pending reply | Whether one Surface A remains to be closed | SI/NO |

Overall status is deterministic: `BLOCKED` for inactive runtime or central material/horizon block; `WATCH` for warnings/debt/conflict/high caution/pending reply; otherwise `STABLE`.

## Backlog DOCX aggregation

The projection scans at most 64 `.docx` files from repository `backlog/` and runtime `.ikant/artifacts/`. It never extracts files, follows symlinks or evaluates relationships. It caps compressed/uncompressed/XML sizes, rejects DTD/entity declarations, and only counts bounded operational signal classes: decision, conflict, validation, risk, strategy and backlog. Raw document text is not copied into the end-user dashboard.

## Accessibility and terminal safety

The shell works without ANSI color and is readable at 80-120 columns. ANSI escapes, C0 controls, bidi overrides, zero-width spoofing controls and prompt-like user lines are neutralized at rendering time while raw visible speech acts remain hash-bound in the transcript. The prompt marker is therefore not forgeable by a rendered user message.

## Failure rules

Transcript corruption, session mismatch, duplicate reply binding, malformed hash chain and engine/pending-turn violations fail closed. Missing or corrupt Surface B degrades dashboard state to `WATCH`; it never fabricates telemetry. Dashboard calculation and DOCX indexing are read-only and must not change node evidence or authorize material action.
