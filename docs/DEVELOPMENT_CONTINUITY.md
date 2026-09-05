# iKant Development Continuity Bundle

## Purpose

`IKANT_DEVELOPMENT_BUNDLE.json` is the machine-readable anti-entropy handoff for AI-assisted development. A fresh session reconstructs the frontier from repository state rather than conversational memory. Repository/Git/CI facts outrank workbook or roadmap snapshots.

The bundle is control-plane state. Modeled simulations, hashes and design decisions never substitute for browser/OS/provider/world oracles.

## Start of every development iteration

After the admission/rights boundary in `AGENTS.md` permits repository study:

1. fetch current `main`, protection/rulesets, open/draft PRs and exact `PRODUCT_CONTRACT.json`;
2. read `AGENTS.md`, `PRODUCT_CONTRACT.json`, `IKANT_DEVELOPMENT_BUNDLE.json`, the current RTA receipt and candidate-owned code/tests;
3. run `python scripts/development_bundle_gate.py`;
4. if baseline/Product Contract/high-critical prerequisites drift, enter `ANTI_ENTROPY_REVIEW` before adding capability;
5. choose the smallest semantic slice whose authority, trust, persistence and physical-oracle boundaries can actually be exercised.

`--require-ready`, `--require-complete` and `--require-advance` are stricter gates; ordinary structural PASS may truthfully coexist with an unresolved external/admin blocker.

## Evidence hierarchy

Keep distinct: modeled coverage; unit/property tests; integration HTTP/process tests; real browser tests; real OS/native tests; real provider/connector tests; observed world read-back; repository governance. A stronger label may never be inferred from a weaker one.

## Current truth after merged S21 and RTA

`main@c46db91c968edbf2203a27de9f0f17de46c38108` is merged PR57 / S21. The current candidate is **S22**, but it is not ready while **G0 repository governance** remains externally unenforced and S22 itself is unimplemented.

The enterprise workbook v1 was falsified by the RTA campaign recorded in `backlog/rta/rta_200k_receipt.json`. The compressed frontier is:

`S21 -> {C0 product-truth/surface foundation, G0 repository governance} -> S22 enterprise context/policy -> S23 external trust + ingress membrane -> {S24 provider assist, S25 connector fabric} -> S26 epistemic revision -> S27 enterprise authority/delegation -> S28 material transactions -> S29 world outcome reconciliation -> {S30 native/multi-surface, S31 enterprise audit} -> S32 release/data lifecycle -> S33 fleet/software supply -> E0 enterprise assurance`

C0/G0/E0 are non-runtime gates. S24/S25 are commutable siblings. Future IDs are planning identifiers only until constitutionally registered.

## Product polish rule

Cosmetics are not a separate authority-bearing faculty. C0 aligns README, Surface metadata and visible product narrative and establishes the design-system/a11y regression foundation. Every later runtime slice must deliberately define loading, empty, blocked, error, recovery and success states on the canonical Surface Contract. E0 reruns cross-surface visual consistency, content-truth and accessibility evidence.

## Iteration modes

- `DEVELOP`: materialize the next minimum executable semantic slice.
- `ANTI_ENTROPY_REVIEW`: reconcile repository/product/bundle truth and re-falsify the frontier.
- `HANDOFF`: freeze exact SHA/PR/check state, open ignorance, evidence and next prerequisites.

No mode implies asynchronous work. Each iteration ends with semantic commits and exact PR/CI truth.
