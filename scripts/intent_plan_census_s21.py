from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IKANT = ROOT / "ikant"


def _calls(path: Path, symbol: str) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
        if name == symbol:
            lines.append(int(getattr(node, "lineno", 0)))
    return lines


def main() -> int:
    planner_calls: dict[str, list[int]] = {}
    handoff_calls: dict[str, list[int]] = {}
    reactive_execution_refs: list[str] = []
    for path in sorted(IKANT.glob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        pc = _calls(path, "finalize_planning")
        if pc:
            planner_calls[rel] = pc
        hc = _calls(path, "build_execution_ledger")
        if hc:
            handoff_calls[rel] = hc
        if path.name in {"execution_handoff.py", "execution_protocol.py", "web_agency.py", "native_agency.py", "host_adapter.py"}:
            text = path.read_text(encoding="utf-8")
            for forbidden in ("command_plan", "compile_command(", "build_graph("):
                if forbidden in text:
                    reactive_execution_refs.append(f"{rel}:{forbidden}")

    errors: list[str] = []
    if set(planner_calls) != {"ikant/practical_reason.py"}:
        errors.append("canonical planner call-site drift: " + json.dumps(planner_calls, sort_keys=True))
    if set(handoff_calls) != {"ikant/execution_protocol.py"}:
        errors.append("execution-ledger call-site drift: " + json.dumps(handoff_calls, sort_keys=True))
    if reactive_execution_refs:
        errors.append("reactive bypass reference: " + ", ".join(reactive_execution_refs))

    receipt = {
        "schema": "ikant-s21-planner-census/v1-test",
        "ok": not errors,
        "canonical_planner_entrypoint": "ikant.planning.finalize_planning",
        "planner_call_sites": planner_calls,
        "execution_ledger_call_sites": handoff_calls,
        "reactive_execution_refs": reactive_execution_refs,
        "planner_count": 1 if set(planner_calls) == {"ikant/practical_reason.py"} else len(planner_calls),
        "errors": errors,
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
