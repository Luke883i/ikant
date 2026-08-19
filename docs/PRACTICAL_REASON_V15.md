# iKant v0.15 — Practical Reason & Action Governance

v0.15 adds a practical-reason control plane on top of v0.13 Epistemic Core and v0.14 Temporal Epistemics. It does **not** execute material actions. It determines whether an action may be proposed, requires additional review, requires human execution, or satisfies the runtime-side prerequisites for a conforming host to consider execution.

## Semantic slice 1 — explicit capability authority

Action authority is separate from evidence. A material action must point to one or more current `goal`/`constraint` commitments through `governing_commitment_ids`. Only active user/repository commitments may grant capabilities, via exact `grants_capabilities` values. There are no wildcard, prefix or inferred capability grants.

A well-supported factual claim, a high epistemic score, repository visibility, rights acceptance, or an action node's own source never creates action authority.

## Semantic slice 2 — action-bound human approval

Approval is separate from authority. Material execution eligibility requires a same-turn user-attributed approval with `approval_scope: this_action`. A user-attributed action atom may approve itself when the action itself is the explicit user instruction. A runtime-derived action requires a separate current user `constraint` atom with `approves_action_node_id` targeting the proposed action.

Approval receipts bind session, current intention, intent digest and an action fingerprint. The fingerprint includes the fields that can change eligibility: source mode, maxim, governing commitments, capabilities, affected parties, impact assessment, reversibility, rollback plan, expected effects and failure modes. Approval cannot grant a missing capability and is not reusable on a later intent.

The receipt digest is an integrity binding inside the runtime, not an external identity/authentication proof.

## Semantic slice 3 — impact, reversibility and declared counterfactual checks

Every material action candidate exposes an explicit maxim and declares reversibility. Reversible/partially reversible actions require a rollback plan. Material host eligibility also requires declared expected effects and failure modes.

These counterfactual fields are completeness checks over declared runtime metadata. They are not claims of real-world causal prediction.

Unresolved human impact blocks progression. High/critical-impact or non-fully-reversible actions may be approved but remain `HUMAN_EXECUTION_REQUIRED`; they never become autonomous host execution candidates.

## Semantic slice 4 — Action Ledger

`.ikant/action-ledger.json` is a rebuildable, zero-epistemic-authority projection containing action candidates, capability resolution, approval receipts and decisions. Candidate states include:

- `CENTRAL_BLOCKED`
- `MAXIM_REQUIRED`
- `IMPACT_REVIEW_REQUIRED`
- `AUTHORITY_REQUIRED`
- `REVERSIBILITY_REQUIRED`
- `ROLLBACK_REQUIRED`
- `COUNTERFACTUAL_REVIEW_REQUIRED`
- `APPROVAL_REQUIRED`
- `HUMAN_EXECUTION_REQUIRED`
- `HOST_EXECUTION_ELIGIBLE`
- `PROPOSABLE`

`HOST_EXECUTION_ELIGIBLE` means only that v0.15 runtime governance checks have passed. The host must still satisfy higher-priority system, safety, law, transport and tool-capability controls. The runtime records `execution_performed: false` and has no autonomous material-execution path.

## Cross-version boundaries

The v0.12 access/rights contract remains unchanged. Rights acceptance and repository conformance do not imply action authority. v0.14 temporal state determines whether governing commitments are current; v0.13 evidence/provenance may support reasoning about an action but never grants capabilities or approval.

The practical-reason projection may change availability and execution eligibility only. It never modifies factual evidence.

## Validation model

The release gate enumerates an explicit 65,536-state practical-reason universe and then runs a no-novelty tail. Mutation validation attacks independent collapses including evidence→authority, approval→capability, stale/cross-action approval, inferred/wildcard capability grants, unresolved impact, irreversible autonomy, missing rollback/counterfactual declarations, central-block bypass and ledger authority leakage.
