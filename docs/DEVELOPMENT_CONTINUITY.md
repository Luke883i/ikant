# iKant Development Continuity Bundle

## Purpose

`IKANT_DEVELOPMENT_BUNDLE.json` is the machine-readable continuity and anti-entropy contract for AI-assisted repository development. A fresh chat session must be able to reconstruct the engineering frontier from repository state rather than from conversational memory.

The bundle is control-plane state. Its simulations, hashes, CI receipts and design decisions are not world evidence and do not replace runtime/browser/OS/provider oracles.

## Start of every development iteration

After the admission/rights boundary in `AGENTS.md` permits repository study:

1. fetch current `main`, current open/draft PRs and exact `PRODUCT_CONTRACT.json`;
2. read `AGENTS.md`, `PRODUCT_CONTRACT.json`, `IKANT_DEVELOPMENT_BUNDLE.json`, then the code/tests/docs owned by the current candidate slice;
3. run `python scripts/development_bundle_gate.py`;
4. if baseline, Product Contract or high/critical findings changed, enter `ANTI_ENTROPY_REVIEW` before adding capability;
5. choose the smallest roadmap slice whose prerequisites and concrete technological supply chain can actually be exercised.

`python scripts/development_bundle_gate.py --require-ready` is a stricter advancement gate: it fails while any HIGH/CRITICAL bundle blocker remains open.

## Three iteration modes

### DEVELOP

Materialize the next minimal semantic runtime slice. Use atomic commits, independent oracles, exact-head CI and a draft PR until the declared DoD is materially green.

### ANTI_ENTROPY_REVIEW

Re-audit `main` and the current PR, rerun the declared model campaigns, challenge assumptions, supply-chain claims, roadmap ordering and UI/UX semantics, then update the bundle before feature work.

### HANDOFF

Freeze current engineering truth into the bundle: exact SHA/PR/check state, open ignorance, decision/falsification logs and next prerequisites. The next chat starts from files, not from remembered prose.

## Evidence hierarchy

Use separate labels for:

- modeled coverage: mutation/scenario/design-space vocabulary only;
- unit/property tests: executable local logic;
- integration HTTP tests: real local transport and concurrency;
- real browser tests: Chromium DOM/event-loop/cache/controller behavior;
- real OS/native tests: installed host, permissions, process lifecycle and platform behavior;
- real provider tests: effective network origin, credential boundary and actual provider schemas;
- repository governance: exact CI receipts plus materially enforced branch/ruleset checks.

A stronger label may never be inferred from a weaker one.

## Current roadmap after S16 audit

The original post-S16 three-slice proposal is intentionally superseded by:

`S16bis Foundation Enforcement & Development Continuity -> S17 Runtime Identity & Provenance Epoch -> S18 Memory Governance -> S19 Temporal Task Governance -> S20 Reactive Intent / Plan Reconciliation -> S21 Hybrid Abstract Assist Opt-in`.

The full foundation links, expected runtime behavior, end-user interaction, technological supply chain, local/intermediate/final DoD, metrics, checklists and UI/UX prototypes are canonical in `IKANT_DEVELOPMENT_BUNDLE.json`.

## End of every iteration

Update the required logs in the bundle/backlog, separate modeled results from physical-boundary receipts, create semantic commits, open/update the exact-head draft PR, run the bundle gate and report `ready_to_advance` truthfully.

The final human choice must be presented as exactly three semantic options:

- `DEVELOP` — continue with the next eligible slice;
- `ANTI_ENTROPY_REVIEW` — re-audit, stress and reconverge the bundle/product;
- `HANDOFF` — freeze/update the bundle for continuation in a fresh chat session.

No option implies that work continues asynchronously. A new iteration starts only from a new user instruction.
