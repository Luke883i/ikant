# v0.9 Definition of Done

A v0.9 candidate is releasable only when all local invariants and all hosted receipts are green on the same current PR merge head.

## Local / semantic DoD

- successful initialize creates a session-bound dashboard egress lock;
- a normal frame transitions `DASHBOARD_LOCKED -> FRAME_PENDING -> DASHBOARD_LOCKED`;
- a second frame cannot seal while one frame is pending;
- the human-visible candidate must byte-match the sealed dashboard SHA-256;
- prefix, suffix, markdown wrapper, mutated or stale frame fails closed;
- Surface A remains inside dashboard and same-cycle Surface B JSON+DOCX remains required;
- terminal ANSI/control/bidi/prompt spoof is sanitized at rendering;
- exact `EXIT IKANT` alone enters the release path; variants remain ordinary intents;
- exact exit frame transitions to RELEASED; resume requires runtime integrity and a new epoch;
- acceptance receipt is bound to the exact digest presented before checkout materialization;
- changed checkout contract, missing handoff digest or tampered receipt blocks probe/initialize;
- completed unaccounted host/model-exposed orientation acquisition becomes BREACHED;
- incidental unexposed provider overfetch remains quarantined rather than evidence;
- dashboard/egress state never modifies epistemic evidence or material-action authority;
- package, runtime version, contract and manifest versions agree at v0.9 candidate.

## Saturation metrics

- dashboard state-model: seeds 1, 883 and 2026 each pass 100,000 scenarios plus 10,000 independent no-novelty tail;
- all 22 egress scenario families observed;
- zero human-egress invariant violations;
- zero false EXIT transitions;
- zero novel tail signatures;
- durable guard: at least 2,000 normal frames plus final EXIT survive periodic reopen;
- admission bounded-orientation maturity: seeds 1,17,97,883,2026 each pass 80,000 + 1,000 tail;
- every defined v0.9 mutation is killed.

## Global hosted DoD

On the same current PR merge head:

- `HOSTED_CI: PASS`;
- `CHAT_UX_CI: PASS`;
- `PSYCHE_V05_CI: PASS`;
- `INCARNATE_EGRESS_CI: PASS`;
- `ADMISSION_V09_CI: PASS`;
- `DASHBOARD_V09_CI: PASS`;
- full unittest regression PASS;
- PR is mergeable and branch has no unresolved base drift.

The engineering-confidence target is >95% for the declared software invariants. It is not a probability of consciousness, neuroscientific fidelity or impossibility of an out-of-band hostile host.
