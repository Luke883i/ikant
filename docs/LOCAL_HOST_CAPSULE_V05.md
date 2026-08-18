# Local host capsule v0.5

The minimal host infrastructure remains Python 3.11+ and the repository checkout. Node.js is intentionally not required in v0.5: a second runtime would duplicate state, add a dependency/supply-chain boundary and offer no epistemic capability that the existing JSON/TXT/DOCX surfaces need.

A conforming ChatGPT-like host uses `python -m ikant` and persists only under `.ikant/`. The operational capsule is:

- admission/probe/runtime receipts;
- graph and append-only event log;
- cognitive snapshots and Surface B artifacts;
- hash-chained visible chat transcript;
- `psyche.json` operational self snapshot;
- `dashboard.json` machine projection and `dashboard.txt` DOS-shell projection.

Canonical interaction is `turn -> draft Surface A from both contracts -> emit-surface-a`. `python -m ikant self` exposes the bounded self model. `python -m ikant dashboard` renders the humanistic neuro-proto projection. `python -m ikant integrity` checks runtime, chat and psyche consistency.

A host must not create a parallel hidden database, store private chain-of-thought, scrape DOCX prose back into factual evidence, or use dashboard values to self-authorize action. Optional UI layers may read the persisted JSON/TXT projections but must remain stateless clients.
