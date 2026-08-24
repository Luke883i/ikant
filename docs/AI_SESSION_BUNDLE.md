# iKant AI Session Development Bundle

This document binds the session-delivered workbook `iKant_AI_Session_Development_Bundle.xlsx` to repository development practice. The workbook is a bootstrap/control artifact, not a second source of runtime or Git truth.

## First rule

A fresh AI session MUST reconstruct current repository truth before developing:

1. fetch current `main` SHA and branch/ruleset protection;
2. read `PRODUCT_CONTRACT.json`, `AGENTS.md`, `IKANT_DEVELOPMENT_BUNDLE.json`, this manifest/document and the final-workbook manifest;
3. audit the ten latest merged PRs in merge order, including corrective `bis`/hotfix lessons;
4. audit every open/draft PR, head/base relationship and exact CI before creating or continuing a branch;
5. compare those live facts with the workbook snapshot and classify drift rather than silently treating stale workbook values as current;
6. confirm, split or mutate the candidate semantic slice from repository evidence and a focused falsification model;
7. only then implement the minimum causally closed vertical slice.

Repository/Git/CI facts outrank static workbook snapshots. Conversation memory is optional context only.

## Human / AI decision boundary

Luke883i self-describes as an `IT dummy` and explicitly delegates engineering entropy to the active local AI session.

The AI session owns architecture and implementation choices: storage, protocol, schemas, APIs, dependencies, migrations, recovery semantics, test strategy, CI/CD details, slice partitioning and corrective `bis` insertion. Do not ask Luke to choose frameworks, databases, retry semantics, hashing, queues, workflow syntax, OAuth internals or similar engineering mechanisms.

Luke remains the product-intent authority. Ask him only when a genuine user-facing/product-level choice cannot be safely inferred. Present at most three short, plain-language outcomes, recommend a default, and explain consequences rather than implementation.

Approximate terminology, overlapping requests, changing emphasis or broad feature requests from the human are treated as `HUMAN_INPUT_ENTROPY`: preserve the invariant product intent and normalize the technical interpretation locally.

## Current snapshot

At workbook materialization:

- `main`: `175908a3b6c2472e911cd42a0220de71d785a645` (merged PR52)
- Product Contract: S17 / `0.18.0`
- open/draft PRs: 0
- branch protection: not enforced
- current `IKANT_DEVELOPMENT_BUNDLE.json`: known stale baseline (PR50)
- next semantic runtime candidate: **S17bis — Runtime Recovery & Surface Closure**

These values are historical snapshot evidence and MUST be refreshed in every new session.

## Adaptive candidate chain

`S17 → S17bis Recovery & Surface Closure → S18 Durable Cognitive State / Causal Ledger → {S19 Memory, S20 Temporal} → S21 Plan Reconciliation → {S22 Hybrid, S23 Connector Fabric} → S24 Material Transactions → S25 Native Presence → S26 Release Hardening`

Future IDs are candidates only. Numbering is traceability; causal dependencies control development order. Evidence may split, merge, insert or rename future slices without changing the final product intent.

### S17bis boundary

S17bis adds no new user faculty. It must recover derivative shell/work/surface state from existing durable runtime session, epoch, egress journal/pending frame and chat/cycle state, while independently censusing the production semantic surface.

It must not introduce a parallel canonical WorkStore, shell store or surface cache; it must not solve the later cross-file cognitive causal transaction; and recovery must never silently re-run the model, planner or a material driver.

Final S17bis evidence requires real process restart and real Chromium recovery/canonical-fault/surface-census oracles in addition to exact synthetic-merge Hosted, Reticular, Product Boundary and full-unit gates.

## Evidence rule

Modeled mutation/simulation coverage is useful for declared-vocabulary saturation and roadmap falsification only. It is not production reliability, formal verification, browser execution, process-restart execution, OS evidence, provider evidence, connector evidence or user-study evidence.

Every material claim requires an executable oracle at the same boundary named by the claim.

## Iteration handoff

A development iteration ends only after recording:

- exact current `main`, branch, PR head and synthetic merge SHA;
- latest-ten-PR trajectory delta and all open/draft PRs;
- Product Contract / development-bundle / workbook drift;
- architecture decisions taken by the AI and falsified alternatives;
- modeled evidence separately from executable/physical evidence;
- atomic semantic commits and exact CI truth;
- closed/open risks and the next candidate slice.

The human-facing close should remain compressed: current state, what changed, any blocker, next slice, and—only if necessary—a simple product outcome choice.
