from __future__ import annotations

import argparse
import json

MASK64 = (1 << 64) - 1
PHASES = 8
CONTEXTS = 4
MUTATION_CLASSES = 4
DOMAIN_COUNTS = {
    'DEV_TRUTH': 8,
    'SURFACE': 10,
    'EPOCH': 10,
    'RECOVERY': 14,
    'MEMORY': 16,
    'TEMPORAL': 10,
    'PLAN': 10,
    'HYBRID': 10,
    'UX_CI': 8,
}
FAMILIES = tuple((domain, f'{domain.lower()}_{index:02d}') for domain, count in DOMAIN_COUNTS.items() for index in range(1, count + 1))
FAMILY_COUNT = len(FAMILIES)
SIGNATURE_SPACE = FAMILY_COUNT * PHASES * CONTEXTS * MUTATION_CLASSES
DOMAIN_NAMES = tuple(DOMAIN_COUNTS)
DOMAIN_INDEX = {name: index for index, name in enumerate(DOMAIN_NAMES)}
FAMILY_DOMAIN = tuple(DOMAIN_INDEX[domain] for domain, _ in FAMILIES)


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return (value ^ (value >> 31)) & MASK64


def decode_signature(word: int) -> tuple[int, int]:
    family = word % FAMILY_COUNT
    word //= FAMILY_COUNT
    phase = word % PHASES
    word //= PHASES
    context = word % CONTEXTS
    word //= CONTEXTS
    mutation = word % MUTATION_CLASSES
    signature = family + FAMILY_COUNT * (phase + PHASES * (context + CONTEXTS * mutation))
    return signature, family


def structural_model() -> dict:
    requirements = {
        'DEV_TRUTH': {'git_bundle_reconcile', 'ci_receipt_provenance'},
        'SURFACE': {'surface_census', 'active_bootstrap_transition'},
        'EPOCH': {'epoch_binding'},
        'RECOVERY': {'restart_work_reconcile'},
        'MEMORY': {'epoch_binding', 'restart_work_reconcile', 'surface_census', 'memory_dependency_closure', 'memory_replay'},
        'TEMPORAL': {'epoch_binding', 'surface_census', 'temporal_epoch_ownership', 'temporal_residency_truth'},
        'PLAN': {'epoch_binding', 'restart_work_reconcile', 'surface_census', 'intent_envelope', 'planner_reconcile'},
        'HYBRID': {'epoch_binding', 'surface_census', 'planner_reconcile', 'hybrid_transport_lock', 'hybrid_output_failclosed', 'hybrid_secret_budget'},
        'UX_CI': {'git_bundle_reconcile', 'ci_receipt_provenance', 'surface_census'},
    }
    current_s17 = {'epoch_binding'}
    s17bis_add = {'git_bundle_reconcile', 'ci_receipt_provenance', 'surface_census', 'active_bootstrap_transition', 'restart_work_reconcile'}
    after_s17bis = current_s17 | s17bis_add
    return {
        'current_S17_to_S18_missing_prerequisites': sorted(requirements['MEMORY'] - current_s17),
        'after_S17bis_to_S18_missing_only_S18_owned': sorted(requirements['MEMORY'] - after_s17bis),
        'partial_order': [
            ['S17bis', 'S18'], ['S17bis', 'S19'], ['S17bis', 'S20'], ['S17bis', 'S21'],
            ['S18', 'S20'], ['S19', 'S20'], ['S20', 'S21'],
        ],
        'S18_S19_commutable': True,
        'target_interventions': sorted(set().union(*requirements.values())),
    }


def run(cases: int, tail: int, seed: int) -> dict:
    if cases < 1 or tail < 0:
        raise ValueError('cases/tail')
    seen = bytearray(SIGNATURE_SPACE)
    counts = [0] * FAMILY_COUNT
    domain_pairs: set[tuple[int, int]] = set()

    def consume(start: int, count: int, *, tail_mode: bool) -> int:
        new = 0
        for offset in range(count):
            base = (seed + start + offset) & MASK64
            word = splitmix64(base)
            signature, family = decode_signature(word)
            if tail_mode and not seen[signature]:
                new += 1
            seen[signature] = 1
            counts[family] += 1
            family2 = splitmix64(base ^ 0xA5A5A5A5A5A5A5A5) % FAMILY_COUNT
            a, b = FAMILY_DOMAIN[family], FAMILY_DOMAIN[family2]
            domain_pairs.add((a, b) if a <= b else (b, a))
        return new

    consume(0, cases, tail_mode=False)
    before = sum(seen)
    new = consume(10_000_000_019, tail, tail_mode=True)
    required_pairs = len(DOMAIN_NAMES) * (len(DOMAIN_NAMES) + 1) // 2
    return {
        'schema': 'ikant-post-s17-multiaxial-roadmap-falsification/v1-test',
        'seed': seed,
        'cases': cases,
        'tail': tail,
        'fault_families': FAMILY_COUNT,
        'domains': DOMAIN_COUNTS,
        'dimensions': {
            'phases': PHASES,
            'contexts': CONTEXTS,
            'mutation_classes': MUTATION_CLASSES,
            'simultaneous_faults_per_case': '2 independent family draws',
        },
        'semantic_signature_space': SIGNATURE_SPACE,
        'semantic_signatures_observed': before,
        'coverage_complete': before == SIGNATURE_SPACE,
        'tail_new_signatures': new,
        'family_min_hits': min(counts),
        'family_max_hits': max(counts),
        'domain_pair_count': len(domain_pairs),
        'domain_pair_space': required_pairs,
        'domain_pair_matrix_complete': len(domain_pairs) == required_pairs,
        'structural': structural_model(),
        'interpretation': 'coverage of a declared multi-abstraction fault/precondition vocabulary; not a production reliability estimate, formal verification, or physical browser/OS/provider execution count',
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=int, default=10_000_000)
    parser.add_argument('--tail', type=int, default=100_000)
    parser.add_argument('--seed', type=int, default=202608241302)
    args = parser.parse_args()
    print(json.dumps(run(args.cases, args.tail, args.seed), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
