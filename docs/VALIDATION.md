# Validation and Anti-Regression v0.2

The validation suite is an engineering challenge system, not a statistical confidence interval, neuroscientific validation or evidence of consciousness.

Core v0.1 invariants remain mandatory: exact human acceptance; real single-use probe; no ACTIVE before kernel seeding; single durable writer; recurrence never increases evidence; corroboration requires distinct attributable provenance; retracted content cannot recur back to life; derived goals cannot become authorized directives; interpretive ceilings remain strict; modulation changes availability, not evidence; feedback changes dynamics, not original evidence; Kant principles cannot self-authorize material action; compression remains non-external evidence; no-novelty repeats create no new node or evidence; durable state fails closed on tamper/divergence.

v0.2 adds explicit CRC and conversational invariants. Every adjacent ring must have a declared transmission. Coarse-graining may only preserve or reduce state cardinality and cannot invent support IDs. Neurofunctional control state must be causally effective in transmission thresholds while remaining explicitly non-neural measurement. Freud/Jung transforms must stay interpretive-only. The proto-self must remain bounded and explicitly non-consciousness-claiming. Central convergence may only downgrade/withhold content relative to the prior epistemic partition. Surface A must satisfy 5–500 words and no heading/list/table/code constraints. Emitted responses must have evidence zero and every emission occurrence must remain audit-visible. Derived memory must remain bounded and non-self-feeding.

`scripts/tune_dynamics.py` performs a deterministic 135-candidate engineering grid and requires checked-in defaults to pass all hard invariants and remain in the near-best envelope. The score is computed, not a constant, and is not biological parameter fitting.

The quick gate is `python scripts/release_gate.py --quick`. Full validation is fault-isolated: unit, tuning, static, Surface A, dynamic, CRC and cognitive profiles produce separate source-fingerprint-bound receipts. `scripts/aggregate_validation.py` rejects missing, stale, wrong-seed, wrong-scale or threshold-failing receipts. `release_gate.py` refuses a full PASS without those isolated receipts.

Hosted CI runs unit/tuning/quick, static 10k+1k, Surface A 10k, dynamic 10k+1k on seeds 883/17/2026, CRC 10k on the same seeds, and cognitive 500-turn+100-tail runs on the same seeds. The PR bot final receipt is the hosted delivery witness.
