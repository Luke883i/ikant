from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import re
import unicodedata
from typing import Any, Callable

from .provenance import materialize_provenance, provenance_quality

HYBRID_RETRIEVAL_SCHEMA = "ikant-hybrid-memory-retrieval/v0.13-test"
_TOKEN = re.compile(r"[a-z0-9]+")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(_TOKEN.findall(text))


def _tokens(text: str) -> set[str]:
    return {x for x in _norm(text).split() if len(x) > 2}


def _grams(text: str, n: int = 3) -> set[str]:
    s = _norm(text).replace(" ", "_")
    return {s[i:i+n] for i in range(max(0, len(s) - n + 1))}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)


@dataclass(frozen=True)
class HybridRetrievalConfig:
    lexical_weight: float = 0.28
    semantic_proxy_weight: float = 0.22
    provenance_weight: float = 0.18
    temporal_weight: float = 0.12
    graph_weight: float = 0.12
    conflict_weight: float = 0.08
    activation_gain: float = 0.08
    max_candidates: int = 24

    def validate(self) -> None:
        weights = [self.lexical_weight, self.semantic_proxy_weight, self.provenance_weight, self.temporal_weight, self.graph_weight, self.conflict_weight]
        if any(not math.isfinite(x) or x < 0 for x in weights): raise ValueError("hybrid retrieval weights")
        if not 0.99 <= sum(weights) <= 1.01: raise ValueError("hybrid retrieval weights must sum to 1")
        if not 0 <= self.activation_gain <= 0.25: raise ValueError("activation gain")
        if self.max_candidates < 1: raise ValueError("max candidates")


DEFAULT_HYBRID_RETRIEVAL = HybridRetrievalConfig(); DEFAULT_HYBRID_RETRIEVAL.validate()


def _relation_neighborhood(runtime: Any, seeds: set[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for relation in getattr(runtime, "relations", {}).values():
        source = str(getattr(relation, "source", "")); target = str(getattr(relation, "target", "")); weight = float(getattr(relation, "weight", 0.0))
        if source in seeds: out[target] = max(out.get(target, 0.0), weight)
        if target in seeds: out[source] = max(out.get(source, 0.0), weight)
    return out


def rank_hybrid_memory(runtime: Any, intent: str, *, limit: int = 12, config: HybridRetrievalConfig = DEFAULT_HYBRID_RETRIEVAL, semantic_similarity: Callable[[str, str], float] | None = None) -> list[dict[str, Any]]:
    config.validate(); materialize_provenance(runtime); qtok = _tokens(intent); qgrams = _grams(intent); lexical: dict[str, float] = {}; semantic: dict[str, float] = {}
    for nid, node in runtime.nodes.items():
        if not getattr(node, "active", True): continue
        lexical[nid] = _jaccard(qtok, _tokens(getattr(node, "text", "")))
        semantic[nid] = max(0.0, min(1.0, float(semantic_similarity(intent, getattr(node, "text", ""))))) if semantic_similarity else _jaccard(qgrams, _grams(getattr(node, "text", "")))
    seeds = {nid for nid in lexical if max(lexical[nid], semantic[nid]) >= 0.18}; graph = _relation_neighborhood(runtime, seeds); conflict_nodes: set[str] = set()
    for relation in getattr(runtime, "relations", {}).values():
        kind = str(getattr(getattr(relation, "kind", None), "value", getattr(relation, "kind", "")))
        if kind in {"contradicts", "falsifies", "inhibits"}: conflict_nodes.update({str(getattr(relation, "source", "")), str(getattr(relation, "target", ""))})
    rows = []; cycle_index = int(runtime.runtime.get("cycle_count", 0))
    for nid, node in runtime.nodes.items():
        if not getattr(node, "active", True): continue
        meta = dict(getattr(node, "metadata", {}) or {}); last = int(meta.get("last_retrieved_cycle", cycle_index)); recency = 1.0 / (1.0 + max(0, cycle_index - last)); temporal = 0.55 * float(getattr(node, "stability", 0.0)) + 0.45 * recency; pqual = provenance_quality(runtime, nid)
        components = {"lexical": lexical.get(nid, 0.0), "semantic_proxy": semantic.get(nid, 0.0), "provenance": pqual, "temporal": temporal, "graph": graph.get(nid, 0.0), "conflict": 1.0 if nid in conflict_nodes else 0.0}
        score = config.lexical_weight * components["lexical"] + config.semantic_proxy_weight * components["semantic_proxy"] + config.provenance_weight * components["provenance"] + config.temporal_weight * components["temporal"] + config.graph_weight * components["graph"] + config.conflict_weight * components["conflict"]
        rows.append({"node_id": nid, "score": round(score, 6), "components": {k: round(v, 6) for k, v in components.items()}})
    rows.sort(key=lambda x: (-x["score"], x["node_id"])); return rows[:max(limit, min(config.max_candidates, limit * 2))]


def apply_hybrid_retrieval(runtime: Any, intent: str, *, limit: int = 12, config: HybridRetrievalConfig = DEFAULT_HYBRID_RETRIEVAL) -> dict[str, Any]:
    ranked = rank_hybrid_memory(runtime, intent, limit=limit, config=config); evidence_before = {nid: float(node.evidence) for nid, node in runtime.nodes.items()}; applied = []
    for row in ranked[:limit]:
        node = runtime.nodes.get(row["node_id"])
        if node is None or not getattr(node, "active", True): continue
        before = float(node.activation); ceiling = float(getattr(node, "activation_ceiling", 1.0)); delta = config.activation_gain * float(row["score"]) * max(0.0, 1.0 - before); node.activation = min(ceiling, max(0.0, before + delta))
        if hasattr(runtime, "_save"): runtime._save(node)
        if node.activation != before: applied.append({"node_id": node.id, "before": round(before, 6), "after": round(node.activation, 6), "score": row["score"]})
    evidence_after = {nid: float(node.evidence) for nid, node in runtime.nodes.items()}
    if evidence_before != evidence_after: raise RuntimeError("hybrid retrieval modified evidence")
    trace = {"schema": HYBRID_RETRIEVAL_SCHEMA, "intent_sha256": hashlib.sha256(intent.encode("utf-8")).hexdigest(), "config": asdict(config), "ranked": ranked, "applied": applied, "evidence_modified": False, "semantic_component": "character_ngram_proxy_or_host_adapter", "authority": "AVAILABILITY_ONLY"}
    runtime.runtime.setdefault("epistemic_core", {})["last_hybrid_retrieval"] = {"schema": HYBRID_RETRIEVAL_SCHEMA, "candidate_count": len(ranked), "applied_count": len(applied), "top_node_ids": [x["node_id"] for x in ranked[:6]], "evidence_modified": False}
    if hasattr(runtime, "_write_runtime"): runtime._write_runtime()
    return trace
