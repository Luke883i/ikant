# Enterprise-Candidate Workbook v1 — RTA handoff

This document binds the session artifact `iKant_Enterprise_Candidate_Workbook_v1.xlsx` to repository truth and records its falsification. The workbook binary is not repository truth; Git, Product Contract, exact CI and physical oracles outrank it.

## Live repository baseline

- `main` = `c46db91c968edbf2203a27de9f0f17de46c38108`, merged PR57 / S21.
- `PRODUCT_CONTRACT.json` = S21, contract `0.22.0`.
- package = `0.29.0a1`.
- main branch protection/required checks remain externally unenforced.

C0 in PR58 reconciles the stale post-PR57 bundle, README and canonical Surface metadata without advancing the Product Contract or adding execution/epistemic authority.

## RTA campaign

Master seed was drawn from session system entropy and captured for replay: `1085021672383838793`.

Two independent bounded campaigns are recorded in `backlog/rta/rta_200k_receipt.json`:

- 100,000 AS-IS main mutations + 1,000 no-novelty tail;
- 100,000 workbook-lattice mutations (188,718 operator applications) + 1,000 no-novelty tail.

Both tails produced zero new semantic signatures. These are fault-model/design-space coverage statements, **not** production reliability, formal verification or physical execution counts.

## AS-IS result

The strongest current bounded areas are admission/egress, causal TURN, memory/task governance, runtime recovery/provenance and the single S21 planner path. Survivors concentrate in product-truth drift, visual/a11y polish, repository governance and software-supply reproducibility.

The audit therefore rejects two bad shortcuts: a UI facelift cannot substitute for runtime proof, and green runtime tests cannot substitute for an accurate product surface or enforced repository governance.

## Workbook v1 falsified

The original 14-runtime-slice / 2-gate proposal does not survive RTA unchanged:

1. **S35 is not a runtime faculty.** The workbook types it `Runtime`, while its own decision log says it adds no capability. It becomes final gate **E0 — Enterprise Assurance & E2E Convergence**.
2. **Ingress quarantine is too late.** Original S26 follows S24 provider/S25 connector activation. Untrusted provider/connector responses and events must cross a trust/ingress membrane before entering cognition. Original S26 is absorbed into S23.
3. **Product truth and polish are too late/implicit.** C0 expands into a zero-authority Product Truth & Surface Foundation: README/Surface/version truth, design-system coherence and the contract for future visual/a11y oracles.

## Converged minimum lattice

Non-runtime gates:

`C0 Product Truth & Surface Foundation` · `G0 Repository Governance` · `E0 Enterprise Assurance`

Proposed runtime chain:

`S22 Enterprise Context & Policy Foundation`
`→ S23 External Trust & Ingress Membrane`
`→ {S24 Hybrid Provider Assist & Provenance, S25 Connector Capability Fabric & Revocation}`
`→ S26 Epistemic Revision & Conflict`
`→ S27 Enterprise Authority & Delegation`
`→ S28 Material Transaction Orchestration`
`→ S29 World Outcome Reconciliation & Compensation`
`→ {S30 Native Residency & Multi-Surface Convergence, S31 Enterprise Audit & Incident Projection}`
`→ S32 Release & Data Lifecycle`
`→ S33 Fleet & Software Supply Governance`
`→ E0 Enterprise Assurance & E2E Convergence`

This is **12 proposed runtime slices + 3 non-runtime gates**. C0/G0 and S24/S25 are commutable siblings at their respective frontier.

## Cosmetics and polish

Polish is deliberately not a constitutional runtime slice because presentation does not create authority. C0 establishes the product-truth/design-system foundation. Every future runtime slice must define intentional loading, empty, blocked, error, recovery and success states on the canonical Surface Contract and preserve keyboard/focus/contrast behavior. E0 performs the final cross-surface content-truth, visual-consistency and accessibility assurance.

The current CSS already has a useful token/responsive/reduced-motion base; the open debt is coherence and browser-grade visual/a11y regression evidence, not the total absence of styling.

## Next boundary

S22 is the next runtime candidate but is **not ready**: G0 branch/ruleset enforcement is still open and S22 enterprise context/policy is unimplemented. No S22+ capability, standards compliance, production reliability or enterprise readiness is claimed by PR58.
