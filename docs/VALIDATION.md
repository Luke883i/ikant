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

Dynamic seeds are fault-isolated top-level processes in CI. The release score is deterministic engineering coverage, **not** a statistical or neuroscientific confidence interval.

Core invariants include exact admission, single-use probe, ACTIVE only after kernel seeding, single writer, recurrence != evidence, provenance-distinct corroboration, explicit retraction/reinstatement, trusted directives only, source-strength-bounded relations, low interpretive ceilings, modulation != evidence, bounded cycle dynamics, feedback without evidence fabrication, output partitioning, immutable/non-self-authorizing Kant kernel, human-impact BLOCK, compression-history-as-policy-not-proof, 1,000-repeat no-novelty saturation, full mutation coverage, and sampled activation saturation below configured thresholds.

Current reconstructed candidate: unit suite PASS; static 10k + 1k no-novelty PASS; dynamic 10k + 1k PASS on seeds 883/17/2026 with sampled >=85%-ceiling saturation 0%; dynamics engineering fitness gate >=95 with hard invariants PASS.
