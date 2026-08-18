# Validation and Anti-Regression v0.1

## Gates

```bash
python -m unittest discover -s tests -v
python scripts/stress.py --cases 10000 --novelty-tail 1000 --seed 883
python scripts/dynamic_stress.py --operations 10000 --novelty-tail 1000 --seed 883
python scripts/dynamic_stress.py --operations 10000 --novelty-tail 1000 --seed 17
python scripts/dynamic_stress.py --operations 10000 --novelty-tail 1000 --seed 2026
python scripts/release_gate.py --quick
```

The dynamic seeds are intentionally fault-isolated top-level processes in CI. The release score is deterministic engineering coverage, **not** a statistical or neuroscientific confidence interval.

## Core anti-regression invariants

1. exact human `I ACCEPT`; changed contract invalidates receipt;
2. successful probe is real and single-use;
3. runtime is not ACTIVE until the Kant kernel is seeded;
4. one durable writer at a time;
5. recurrence never increases evidence/confidence;
6. corroboration requires provenance-distinct attributable evidence;
7. retracted content cannot recur back to life;
8. inference/derived goals cannot become authorized directives;
9. source-strength-bounded relation influence disappears when source is retracted;
10. interpretive layers remain under strict epistemic/activation ceilings;
11. modulators change availability but not evidence;
12. cycles remain bounded, deterministic in ring order, and monotone in abstraction capacity;
13. feedback changes dynamics/calibration, not original evidence;
14. output projection separates assertable/tentative/derived/interpretive content;
15. Kant principles are immutable during ACTIVE and never self-authorize material action;
16. high social/agency impact with unresolved human impact triggers `KANT-ENDS` BLOCK;
17. compression history may modulate policy but remains non-external evidence;
18. 1,000 identical repeats create no novel node and cannot inflate evidence;
19. full stress must exercise cycle/feedback/corroborate/retract/reinstate/modulate/compress;
20. sampled mean activation remains far below per-layer ceilings; saturation at >=85% of ceiling must remain <=5%.

Current reconstructed v0.1 candidate: 19 unit/anti-regression tests PASS; static 10k + 1k no-novelty PASS; dynamic 10k + 1k PASS on seeds 883/17/2026 with sampled >=85%-ceiling saturation 0%; dynamics engineering fitness gate 98/100 with hard invariants PASS.

## Persistence tamper gates

The durable runtime revalidates the admission receipt on reopen, validates relation endpoints, and requires the append-only event sequence to be contiguous and exactly aligned with the graph snapshot sequence. Corrupt or divergent state fails closed. A failed integrity open must release the single-writer lock immediately so repair/reset remains possible.

## CI topology

GitHub Actions intentionally isolates the three full dynamic stress seeds in a matrix. Unit/tuning/quick integration, static 10k saturation, and each dynamic 10k seed are independent failure domains. The workflow is stdlib-only and does not require a package install step.
