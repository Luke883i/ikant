# iKant v0.15-test

iKant is a repository-local epistemic and practical control runtime for conforming AI session-chat hosts. v0.15 keeps the v0.13 Epistemic Core and v0.14 Temporal Epistemics, then adds **Practical Reason & Action Governance**: explicit action authority, same-turn action-bound approval, human-impact/reversibility gates, and a zero-authority Action Ledger.

Evidence and permission are deliberately separate. High epistemic support, provenance, repository visibility, rights acceptance or technical conformance never creates material-action authority. A material action must point to current user/repository goals or constraints and satisfy exact declared capabilities; wildcard, prefix, derived and stale capability grants are rejected.

Approval is also separate from authority. A user-attributed action may carry explicit current-turn approval for itself. A runtime-derived proposed action requires a separately user-attributed constraint targeting that action. Approval receipts bind session, current intention, intent digest and the complete governance-relevant action fingerprint; they cannot grant missing capabilities or be replayed on a later intent.

Material action candidates expose an explicit maxim, affected parties, impact assessment, reversibility, rollback, expected effects and failure modes. Unresolved impact, unknown reversibility or incomplete rollback/counterfactual metadata prevents host execution eligibility. Irreversible or high-impact actions remain `HUMAN_EXECUTION_REQUIRED` even after approval.

`.ikant/action-ledger.json` is a rebuildable control projection with epistemic authority `0.0`. `HOST_EXECUTION_ELIGIBLE` means only that v0.15 runtime-side governance prerequisites have passed. iKant v0.15 does not execute material actions; the host must still apply higher-priority system, safety, law, transport and tool-capability controls.

The v0.12 rights/access contract remains unchanged. v0.15 changes the admitted runtime product, not owner authorization for repository access or external legal bases. Human egress remains dashboard-only after ACTIVE and machine telemetry remains file-only.

Canonical execution remains `python -m ikant`. See `docs/PRACTICAL_REASON_V15.md`, `docs/TEMPORAL_EPISTEMICS_V14.md`, `docs/EPISTEMIC_CORE_V13.md`, `IKANT_ACCESS_CONTRACT.md`, and `RIGHTS.md`.
