from __future__ import annotations

import re
from typing import Any

AUTHORITY_SCHEMA = "ikant-authority-capabilities/v0.15-test"
_CAP = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,79}$")
TRUSTED_AUTHORITY_SOURCES = {"user", "repository"}
CURRENT_TEMPORAL_STATES = {None, "ACTIVE"}


def normalize_capability(value: object) -> str:
    cap = str(value).strip().casefold()
    if not _CAP.fullmatch(cap):
        raise ValueError(f"invalid capability: {value!r}")
    return cap


def _kind(node: Any) -> str:
    raw = getattr(node, "kind", "")
    return str(getattr(raw, "value", raw))


def _metadata(node: Any) -> dict[str, Any]:
    return dict(getattr(node, "metadata", {}) or {})


def current_capability_grants(runtime: Any, governing_commitment_ids: list[str] | tuple[str, ...]) -> dict[str, list[str]]:
    """Return exact capability grants from explicitly linked, current user/repository commitments.

    Capability grants are control-plane authority. They never alter node evidence or factual confidence.
    No wildcard, prefix, role or inferred capability expansion is supported.
    """
    grants: dict[str, list[str]] = {}
    for node_id in dict.fromkeys(str(x) for x in governing_commitment_ids):
        node = getattr(runtime, "nodes", {}).get(node_id)
        if node is None or not bool(getattr(node, "active", False)):
            continue
        if _kind(node) not in {"goal", "constraint"}:
            continue
        if str(getattr(node, "source_mode", "")) not in TRUSTED_AUTHORITY_SOURCES:
            continue
        meta = _metadata(node)
        if meta.get("temporal_state") not in CURRENT_TEMPORAL_STATES:
            continue
        for raw in meta.get("grants_capabilities", []) or []:
            cap = normalize_capability(raw)
            grants.setdefault(cap, []).append(node_id)
    return {cap: sorted(set(ids)) for cap, ids in sorted(grants.items())}


def resolve_authority(
    runtime: Any,
    *,
    governing_commitment_ids: list[str] | tuple[str, ...],
    required_capabilities: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    governing = [str(x) for x in dict.fromkeys(governing_commitment_ids)]
    required = sorted({normalize_capability(x) for x in required_capabilities})
    grants = current_capability_grants(runtime, governing)
    valid_governing = []
    for nid in governing:
        node = getattr(runtime, "nodes", {}).get(nid)
        if node is None or not bool(getattr(node, "active", False)):
            continue
        if _kind(node) not in {"goal", "constraint"}:
            continue
        if str(getattr(node, "source_mode", "")) not in TRUSTED_AUTHORITY_SOURCES:
            continue
        if _metadata(node).get("temporal_state") not in CURRENT_TEMPORAL_STATES:
            continue
        valid_governing.append(nid)
    valid_governing = sorted(set(valid_governing))

    missing = [cap for cap in required if cap not in grants]
    return {
        "schema": AUTHORITY_SCHEMA,
        "governing_commitment_ids": governing,
        "valid_governing_commitment_ids": valid_governing,
        "required_capabilities": required,
        "granted_capabilities": sorted(grants),
        "grant_sources": grants,
        "missing_capabilities": missing,
        "explicit_attribution": bool(valid_governing),
        "authority_satisfied": bool(valid_governing) and not missing,
        "epistemic_authority": 0.0,
        "boundaries": {
            "evidence_never_implies_authority": True,
            "approval_never_grants_capability": True,
            "capabilities_are_exact_no_wildcards": True,
            "derived_or_stale_commitments_cannot_grant_authority": True,
        },
    }
