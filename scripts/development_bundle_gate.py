from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'IKANT_DEVELOPMENT_BUNDLE.json'
CONTRACT = ROOT / 'PRODUCT_CONTRACT.json'
SCHEMA = 'ikant-development-continuity-bundle/v1-test'
REQUIRED_SLICE_KEYS = {
    'id', 'name', 'foundation_links', 'expected_runtime', 'user_experience',
    'technology_supply_chain', 'dod', 'success_metrics', 'checklist',
    'ui_ux_prototype', 'prerequisites',
}
REQUIRED_DOD = {'local', 'intermediate', 'final'}
REQUIRED_MODES = {'DEVELOP', 'ANTI_ENTROPY_REVIEW', 'HANDOFF'}
BLOCKING_SEVERITIES = {'CRITICAL', 'HIGH'}


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def sha(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _open_blocking(findings: list[dict]) -> list[dict]:
    return [
        row for row in findings
        if isinstance(row, dict)
        and row.get('status') == 'OPEN'
        and row.get('severity') in BLOCKING_SEVERITIES
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--require-ready', action='store_true', help='require that the nominated candidate may start development')
    ap.add_argument('--require-complete', action='store_true', help='require that all HIGH/CRITICAL objectives owned by the candidate are closed')
    args = ap.parse_args()
    errors: list[str] = []

    try:
        bundle = json.loads(BUNDLE.read_text(encoding='utf-8'))
    except Exception as exc:
        raise SystemExit('development bundle unreadable: ' + str(exc))
    try:
        contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    except Exception as exc:
        raise SystemExit('product contract unreadable: ' + str(exc))

    if bundle.get('schema') != SCHEMA:
        errors.append('bundle schema drift')
    baseline = bundle.get('baseline') if isinstance(bundle.get('baseline'), dict) else {}
    if baseline.get('product_contract_current_slice') != contract.get('constitutional_convergence'):
        errors.append('bundle/product current-slice drift')
    if baseline.get('product_contract_version') != contract.get('contract_version'):
        errors.append('bundle/product contract-version drift')

    roadmap = bundle.get('roadmap') if isinstance(bundle.get('roadmap'), list) else []
    ids: list[str] = []
    for row in roadmap:
        if not isinstance(row, dict) or not REQUIRED_SLICE_KEYS.issubset(row):
            errors.append('roadmap slice shape drift')
            continue
        sid = str(row.get('id') or '')
        ids.append(sid)
        dod = row.get('dod') if isinstance(row.get('dod'), dict) else {}
        if set(dod) != REQUIRED_DOD:
            errors.append(f'{sid} DoD shape drift')
    if len(ids) != len(set(ids)) or not ids:
        errors.append('roadmap identity drift')

    candidate = str(baseline.get('candidate_slice') or '')
    if not candidate or candidate not in ids:
        errors.append('candidate slice missing from roadmap')

    dag = bundle.get('dependency_dag') if isinstance(bundle.get('dependency_dag'), dict) else {}
    edges = dag.get('causal_edges') if isinstance(dag.get('causal_edges'), list) else []
    for edge in edges:
        if not isinstance(edge, list) or len(edge) != 2 or edge[0] not in ids or edge[1] not in ids:
            errors.append('dependency DAG edge drift')
            break

    protocol = bundle.get('iteration_protocol') if isinstance(bundle.get('iteration_protocol'), dict) else {}
    modes = set((protocol.get('modes') or {}).keys()) if isinstance(protocol.get('modes'), dict) else set()
    if modes != REQUIRED_MODES:
        errors.append('iteration modes drift')
    end_choices = protocol.get('end_of_iteration_choices')
    if not isinstance(end_choices, list) or set(end_choices) != REQUIRED_MODES:
        errors.append('end-of-iteration choice drift')

    findings = bundle.get('audit_findings') if isinstance(bundle.get('audit_findings'), list) else []
    open_blocking = _open_blocking(findings)
    candidate_objectives = [row for row in open_blocking if row.get('owner_slice') == candidate]
    candidate_entry_blockers = [
        row for row in open_blocking
        if row.get('owner_slice') != candidate
        and candidate in (row.get('blocks_slices') if isinstance(row.get('blocks_slices'), list) else [])
    ]
    future_open_risks = [
        row for row in open_blocking
        if row not in candidate_objectives and row not in candidate_entry_blockers
    ]

    campaigns = bundle.get('modeled_campaigns') if isinstance(bundle.get('modeled_campaigns'), list) else []
    for row in campaigns:
        if (
            row.get('cases') != 10_000_000
            or row.get('tail') != 100_000
            or row.get('coverage_complete') is not True
            or row.get('tail_new_signatures') != 0
        ):
            errors.append('modeled campaign receipt drift')

    status = 'PASS' if not errors else 'FAIL'
    ready_to_develop = not errors and not candidate_entry_blockers
    candidate_complete = not errors and not candidate_objectives
    out = {
        'schema': 'ikant-development-continuity-gate/v2-test',
        'status': status,
        'candidate_slice': candidate,
        'ready_to_develop_candidate': ready_to_develop,
        'candidate_complete': candidate_complete,
        'ready_to_advance': ready_to_develop,
        'bundle_sha256': sha(bundle),
        'baseline_main_sha': baseline.get('main_sha'),
        'product_contract_current_slice': contract.get('constitutional_convergence'),
        'roadmap': ids,
        'candidate_entry_blockers': [x.get('id') for x in candidate_entry_blockers],
        'candidate_open_objectives': [x.get('id') for x in candidate_objectives],
        'future_open_risks': [x.get('id') for x in future_open_risks],
        'errors': errors,
        'model_receipts_are_not_runtime_oracles': True,
    }
    print(json.dumps(out, sort_keys=True))
    if errors:
        return 2
    if args.require_ready and not ready_to_develop:
        return 3
    if args.require_complete and not candidate_complete:
        return 4
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
