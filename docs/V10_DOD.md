# iKant v0.10 Definition of Done

Local DoD:
- 22+ targeted unit/host tests green.
- 5 independent seeds x (100,000 scenarios + 10,000 no-novelty), zero novel tail signatures.
- 2,000 durable frames with repeated process reopen/crash recovery plus release.
- mutation kills for pre-delivery ACK, missing replay artifact, journal tamper, snapshot drift, unsafe frame bytes, legacy pending migration and release mismatch.
- package/contract/manifest version coherence.

Hosted DoD:
- repository-wide CI PASS.
- inherited chat v0.4, psyche v0.5, incarnate v0.7, admission v0.9 and dashboard v0.9 gates PASS.
- new `DASHBOARD_V10_CI` PASS on the same merge head: unit, 5x100k+10k saturation, durable recovery, mutation kill and full regression.

Merge recommendation is PASS only when every applicable receipt is green on the same merge head.
