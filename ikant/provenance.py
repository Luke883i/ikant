from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .store import atomic_json_write

PROVENANCE_SCHEMA = "ikant-provenance-graph/v0.13-test"
EXTERNAL_SOURCE_MODES = {"user", "repository", "document", "live"}
DERIVED_SOURCE_MODES = {"cache", "demo", "inference", "runtime_derived"}


def _digest(*parts: object) -> str:
    material = "|".join(str(x) for x in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceRecord:
    id: str
    source_mode: str
    provenance_key: str
    locator: str | None
    external: bool
    authority: str = "ATTRIBUTION_ONLY"


@dataclass(frozen=True)
class ObservationRecord:
    id: str
    node_id: str
    source_id: str
    acquisition: str
    content_sha256: str
    independent: bool
    creates_evidence: bool = False


def _runtime_core(runtime: Any) -> dict[str, Any]:
    return runtime.runtime.setdefault("epistemic_core", {})


def _state(runtime: Any) -> dict[str, Any]:
    cached = getattr(runtime, '_ikant_provenance_state', None)
    if isinstance(cached, dict):
        return cached
    state = {"sources": {}, "observations": {}, "claims": {}, "derivations": []}
    if getattr(runtime, 'durable', False):
        path = Path(runtime.state_dir) / 'provenance.json'
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                raw = {}
            if raw.get('schema') == PROVENANCE_SCHEMA:
                state = {k: raw.get(k, {} if k != 'derivations' else []) for k in ('sources','observations','claims','derivations')}
    setattr(runtime, '_ikant_provenance_state', state)
    return state


def bind_node_source(
    runtime: Any,
    node_id: str,
    *,
    source_mode: str,
    provenance_key: str | None = None,
    locator: str | None = None,
    acquisition: str = "runtime_observation",
    independent: bool = True,
) -> str:
    """Bind an attributable source observation to a content node without changing evidence.

    Node identity may be content-addressed; provenance is therefore represented separately and
    may contain multiple independent source observations for the same node.
    """
    if source_mode not in EXTERNAL_SOURCE_MODES | DERIVED_SOURCE_MODES:
        raise ValueError(f"unsupported provenance source mode: {source_mode}")
    node = runtime.nodes.get(node_id)
    if node is None:
        raise KeyError(node_id)
    key = str(provenance_key or f"{source_mode}:implicit")
    source_id = "SRC-" + _digest(source_mode, key, locator or "")[:20]
    external = source_mode in EXTERNAL_SOURCE_MODES
    source = SourceRecord(source_id, source_mode, key, locator, external)
    text = str(getattr(node, "text", ""))
    obs_id = "OBS-" + _digest(node_id, source_id, acquisition, hashlib.sha256(text.encode("utf-8")).hexdigest())[:20]
    obs = ObservationRecord(
        obs_id,
        node_id,
        source_id,
        acquisition,
        hashlib.sha256(text.encode("utf-8")).hexdigest(),
        bool(independent),
    )
    state = _state(runtime)
    state["sources"][source_id] = asdict(source)
    state["observations"][obs_id] = asdict(obs)
    claim = state["claims"].setdefault(node_id, {"observation_ids": [], "source_ids": []})
    if obs_id not in claim["observation_ids"]:
        claim["observation_ids"].append(obs_id)
    if source_id not in claim["source_ids"]:
        claim["source_ids"].append(source_id)
    claim["observation_ids"].sort(); claim["source_ids"].sort()
    return obs_id


def _bind_existing_nodes(runtime: Any) -> None:
    state = _state(runtime)
    for node_id, node in runtime.nodes.items():
        mode = str(getattr(node, "source_mode", "runtime_derived"))
        if mode not in EXTERNAL_SOURCE_MODES | DERIVED_SOURCE_MODES:
            mode = "runtime_derived"
        metadata = dict(getattr(node, "metadata", {}) or {})
        locator = metadata.get("source_locator") or metadata.get("path") or metadata.get("url")
        key = metadata.get("provenance_key") or metadata.get("source_id") or f"{mode}:node-origin"
        claim = state.get("claims", {}).get(node_id, {})
        bound_modes = {str(state.get("sources", {}).get(sid, {}).get("source_mode")) for sid in claim.get("source_ids", [])}
        if mode not in bound_modes:
            bind_node_source(runtime, node_id, source_mode=mode, provenance_key=str(key), locator=str(locator) if locator else None, acquisition="node_origin", independent=True)
        for corroboration_key in metadata.get("corroboration_keys", []) or []:
            bind_node_source(runtime, node_id, source_mode=mode if mode in EXTERNAL_SOURCE_MODES else "document", provenance_key=str(corroboration_key), acquisition="corroboration", independent=True)
    derivations = []
    for relation in getattr(runtime, "relations", {}).values():
        derivations.append({
            "id": str(getattr(relation, "id", "")),
            "source": str(getattr(relation, "source", "")),
            "target": str(getattr(relation, "target", "")),
            "kind": str(getattr(getattr(relation, "kind", None), "value", getattr(relation, "kind", ""))),
            "weight": float(getattr(relation, "weight", 0.0)),
            "creates_evidence": False,
        })
    state["derivations"] = sorted(derivations, key=lambda x: (x["source"], x["target"], x["kind"], x["id"]))


def provenance_quality(runtime: Any, node_id: str) -> float:
    """Return a retrieval-only attribution quality proxy in [0,1]."""
    state = _state(runtime)
    claim = state.get("claims", {}).get(node_id, {})
    source_ids = list(claim.get("source_ids", []))
    if not source_ids:
        return 0.0
    rows = [state["sources"].get(s, {}) for s in source_ids]
    external = sum(bool(r.get("external")) for r in rows)
    independent_keys = set()
    for oid in claim.get("observation_ids", []):
        obs = state.get("observations", {}).get(oid, {})
        source = state.get("sources", {}).get(obs.get("source_id"), {})
        if obs.get("independent") is True and source.get("external") is True:
            independent_keys.add(source.get("provenance_key"))
    return round(min(1.0, 0.55 * (external / len(rows)) + 0.45 * min(1.0, len(independent_keys) / 2.0)), 6)


def validate_provenance_graph(graph: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if graph.get("schema") != PROVENANCE_SCHEMA:
        errors.append("provenance schema")
    sources = graph.get("sources") or {}
    observations = graph.get("observations") or {}
    claims = graph.get("claims") or {}
    for sid, row in sources.items():
        if row.get("id") != sid:
            errors.append("source id mismatch")
        mode = row.get("source_mode")
        if mode in DERIVED_SOURCE_MODES and row.get("external") is True:
            errors.append("derived source promoted to external")
        if row.get("authority") != "ATTRIBUTION_ONLY":
            errors.append("source attribution promoted to epistemic authority")
    for oid, row in observations.items():
        if row.get("id") != oid or row.get("source_id") not in sources or row.get("node_id") not in claims:
            errors.append("observation binding")
        if row.get("creates_evidence") is not False:
            errors.append("provenance observation creates evidence")
    for node_id, row in claims.items():
        if any(x not in observations for x in row.get("observation_ids", [])):
            errors.append(f"claim observation missing:{node_id}")
        if any(x not in sources for x in row.get("source_ids", [])):
            errors.append(f"claim source missing:{node_id}")
    return not errors, list(dict.fromkeys(errors))


def materialize_provenance(runtime: Any) -> dict[str, Any]:
    _bind_existing_nodes(runtime)
    state = _state(runtime)
    graph = {
        "schema": PROVENANCE_SCHEMA,
        "runtime_session_id": runtime.runtime.get("session_id"),
        "sources": dict(sorted(state.get("sources", {}).items())),
        "observations": dict(sorted(state.get("observations", {}).items())),
        "claims": dict(sorted(state.get("claims", {}).items())),
        "derivations": list(state.get("derivations", [])),
        "boundary": {
            "provenance_is_attribution_not_external_evidence": True,
            "derived_sources_never_self_promote": True,
            "content_identity_and_source_identity_are_separate": True,
        },
    }
    ok, errors = validate_provenance_graph(graph)
    if not ok:
        raise RuntimeError("provenance validation failed: " + "; ".join(errors))
    raw = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    external_sources = sum(bool(x.get("external")) for x in graph["sources"].values())
    multi_source_claims = sum(len(x.get("source_ids", [])) > 1 for x in graph["claims"].values())
    summary = {
        "schema": "ikant-provenance-summary/v0.13-test",
        "sha256": digest,
        "source_count": len(graph["sources"]),
        "external_source_count": external_sources,
        "observation_count": len(graph["observations"]),
        "claim_count": len(graph["claims"]),
        "multi_source_claim_count": multi_source_claims,
        "epistemic_authority": 0.0,
    }
    core = _runtime_core(runtime); core["provenance"] = summary
    if getattr(runtime, "durable", False):
        path = Path(runtime.state_dir) / "provenance.json"
        atomic_json_write(path, graph)
        summary["path"] = str(path)
    if hasattr(runtime, "_write_runtime"):
        runtime._write_runtime()
    return {"graph": graph, "summary": summary}
