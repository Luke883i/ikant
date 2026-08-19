# iKant v0.14-test

iKant is a repository-local epistemic control runtime for conforming AI session-chat hosts. v0.14 keeps the v0.13 Epistemic Core and adds **temporal epistemics**: typed memory classes, explicit commitment continuity, dependency-aware source invalidation, and deterministic replay of temporal control state.

The runtime distinguishes **episodic**, **semantic**, **commitment**, **interpretive**, and **kernel** memory. Classification and lifecycle metadata have zero epistemic authority: they may change availability and currentness, never factual evidence. Supersession is explicit rather than inferred; an old goal or constraint becomes non-current only through a typed transition such as `supersedes_node_id`, retraction, forgetting, source revocation, or dependency invalidation.

Source invalidation is provenance-aware. Revoking one source does not suppress a claim while another independent unrevoked external source remains. When the last external support is revoked, the directly affected node becomes unavailable and invalidation propagates only into dependent derived runtime state, not into unrelated external claims.

Temporal transitions are recorded in a dedicated `.ikant/temporal-events.jsonl` hash-chained journal. This control journal is intentionally separate from the cognitive event stream so memory bookkeeping cannot dilute compression/revision metrics or lower epistemic caution. A divergence between temporal metadata and deterministic replay fails closed before a new cognitive turn is acquired.

The v0.12 rights/access contract remains unchanged. v0.14 evolves the admitted runtime product; it does not silently broaden owner authorization or turn memory/control state into evidence. Human egress remains dashboard-only after ACTIVE, machine telemetry remains file-only, and the v0.11 transport invariants remain intact.

Canonical execution remains `python -m ikant`. See `docs/TEMPORAL_EPISTEMICS_V14.md`, `docs/EPISTEMIC_CORE_V13.md`, `IKANT_ACCESS_CONTRACT.md`, and `RIGHTS.md`.
