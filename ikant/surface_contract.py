from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from .foundation import FOUNDATION_SCHEMA, FOUNDATION_VERSION, foundation_projection, load_experiment_config
from .public_v1 import public_projection
from .store import atomic_json_write, read_json

SURFACE_CONTRACT_SCHEMA = "ikant-surface-contract/v1-test"
SURFACE_MANIFEST_SCHEMA = "ikant-surface-manifest/v1-test"
CONFIG_EFFECT_SCHEMA = "ikant-config-effect-receipt/v1-test"
ASSET_REVISION = "v030-s16-surface-contract-1"

_CACHE_LOCK = threading.RLock()
_STABLE_CACHE: dict[tuple[str, str], dict[str, Any]] = {}

_ABSTRACTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "admission_lifecycle",
        "readable": True,
        "mutable": True,
        "writer": "canonical_admission_endpoints",
        "effect_scope": "admission_state_only",
        "authority_effect": "BOUNDED_BY_EXISTING_GOVERNANCE",
    },
    {
        "id": "conversation_turn",
        "readable": True,
        "mutable": True,
        "writer": "advanced_web_shell_single_writer",
        "effect_scope": "sealed_surface_a_turn",
        "authority_effect": "NONE",
    },
    {
        "id": "generation_config",
        "readable": True,
        "mutable": True,
        "writer": "revision_compare_and_swap",
        "effect_scope": "generation_only",
        "authority_effect": "NONE",
    },
    {
        "id": "cognitive_trace",
        "readable": True,
        "mutable": False,
        "writer": None,
        "effect_scope": "derived_cycle_projection",
        "authority_effect": "NONE",
    },
    {
        "id": "epistemic_workspace",
        "readable": True,
        "mutable": False,
        "writer": None,
        "effect_scope": "exact_ack_read_only_projection",
        "authority_effect": "NONE",
    },
    {
        "id": "capability_catalog",
        "readable": True,
        "mutable": False,
        "writer": None,
        "effect_scope": "currently_demonstrable_services_only",
        "authority_effect": "NONE",
    },
    {
        "id": "runtime_systems",
        "readable": True,
        "mutable": False,
        "writer": None,
        "effect_scope": "recognized_persisted_inspection_only",
        "authority_effect": "NONE",
    },
    {
        "id": "enduser_identity_audit",
        "readable": True,
        "mutable": False,
        "writer": None,
        "effect_scope": "session_cycle_integrity_projection",
        "authority_effect": "NONE",
    },
    {
        "id": "reactive_work",
        "readable": True,
        "mutable": False,
        "writer": None,
        "effect_scope": "derived_cognitive_moment_projection",
        "authority_effect": "NONE",
    },
    {
        "id": "artifacts",
        "readable": True,
        "mutable": False,
        "writer": None,
        "effect_scope": "bounded_same_cycle_read_download",
        "authority_effect": "NONE",
    },
    {
        "id": "bootstrap_diagnostics",
        "readable": True,
        "mutable": False,
        "writer": None,
        "effect_scope": "append_only_diagnostics_projection",
        "authority_effect": "NONE",
    },
    {
        "id": "voice_candidate",
        "readable": True,
        "mutable": True,
        "writer": "current_shell_candidate_only",
        "effect_scope": "transcript_candidate_never_auto_submit",
        "authority_effect": "NONE",
    },
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def surface_manifest() -> dict[str, Any]:
    abstractions = [deepcopy(x) | {"surfaces": ["webapp", "floating_pwa_profile"]} for x in _ABSTRACTIONS]
    semantic_material = {
        "schema": SURFACE_MANIFEST_SCHEMA,
        "abstractions": abstractions,
        "single_runtime": True,
        "presentation_profiles_are_not_separate_runtimes": True,
        "undeclared_controls_forbidden": True,
        "future_capabilities_omitted": True,
    }
    semantic_sha = _sha(semantic_material)
    return {
        **semantic_material,
        "semantic_contract_sha256": semantic_sha,
        "asset_revision": ASSET_REVISION,
        "surface_profiles": [
            {
                "id": "webapp",
                "semantic_contract_sha256": semantic_sha,
                "authority_effect": "NONE",
                "layout_only": False,
            },
            {
                "id": "floating_pwa_profile",
                "semantic_contract_sha256": semantic_sha,
                "authority_effect": "NONE",
                "layout_only": True,
                "native_os_overlay_claimed": False,
            },
        ],
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def _runtime(root: Path) -> dict[str, Any]:
    value = read_json(root / ".ikant" / "runtime.json", {})
    return value if isinstance(value, dict) else {}


def _config_sha(config: dict[str, Any]) -> str:
    return _sha(config)


def _effect_path(root: Path) -> Path:
    return root / ".ikant" / "surface-config-effect.json"


def record_config_effect(root: str | Path, *, config: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    """Persist a zero-authority receipt binding the config observed at canonical TURN intake to its sealed cycle.

    The canonical shell and delegate lock already serialize TURN against config mutation. This receipt is
    derivative evidence of that binding; failure to write it may degrade observability but never the frame.
    """
    base = Path(root).resolve()
    runtime = _runtime(base)
    session = str(runtime.get("session_id") or "")
    receipt = frame.get("receipt") if isinstance(frame, dict) else None
    cycle = str(receipt.get("cycle_id") or "") if isinstance(receipt, dict) else ""
    if not session or not cycle:
        raise ValueError("config effect receipt requires active session and sealed cycle")
    generation = frame.get("generation") if isinstance(frame.get("generation"), dict) else None
    if not generation:
        cognitive = runtime.get("cognitive") if isinstance(runtime.get("cognitive"), dict) else {}
        candidate = cognitive.get("last_surface_a_generation") if isinstance(cognitive.get("last_surface_a_generation"), dict) else {}
        if str(candidate.get("cycle_id") or "") == cycle:
            generation = candidate
    generation = generation if isinstance(generation, dict) else {}
    source = str(generation.get("source") or "UNKNOWN")
    model_contract_attempted = source in {"MODEL", "OPERATIONAL_FALLBACK"}
    final_surface_effect_confirmed = source == "MODEL"
    payload = {
        "schema": CONFIG_EFFECT_SCHEMA,
        "runtime_session_id": session,
        "cycle_id": cycle,
        "config_revision": int(config.get("revision") or 0),
        "config_sha256": _config_sha(config),
        "generation_source": source,
        "model_contract_attempted": model_contract_attempted,
        "final_surface_effect_confirmed": final_surface_effect_confirmed,
        "binding_basis": "CANONICAL_TURN_SERIALIZATION",
        "effect_scope": "GENERATION_ONLY",
        "receipt_is_not_authority": True,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    payload["receipt_sha256"] = _sha(payload)
    atomic_json_write(_effect_path(base), payload)
    return payload


def config_effect_projection(root: str | Path, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    base = Path(root).resolve()
    runtime = _runtime(base)
    session = str(runtime.get("session_id") or "") or None
    cognitive = runtime.get("cognitive") if isinstance(runtime.get("cognitive"), dict) else {}
    cycle = str(cognitive.get("last_surface_a_cycle_id") or "") or None
    current = config if isinstance(config, dict) else load_experiment_config(base)
    current_revision = int(current.get("revision") or 0)
    raw = read_json(_effect_path(base), {})
    if not isinstance(raw, dict) or raw.get("schema") != CONFIG_EFFECT_SCHEMA:
        status = "NO_CYCLE" if not cycle else "UNATTESTED_CYCLE"
        return {
            "schema": CONFIG_EFFECT_SCHEMA,
            "status": status,
            "runtime_session_id": session,
            "cycle_id": cycle,
            "current_config_revision": current_revision,
            "cycle_config_revision": None,
            "final_surface_effect_confirmed": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
    receipt = deepcopy(raw)
    valid_sha = str(receipt.pop("receipt_sha256", "")) == _sha(receipt)
    receipt["receipt_sha256"] = raw.get("receipt_sha256")
    same_session = session is not None and receipt.get("runtime_session_id") == session
    same_cycle = cycle is not None and receipt.get("cycle_id") == cycle
    cycle_revision = receipt.get("config_revision") if isinstance(receipt.get("config_revision"), int) else None
    if not valid_sha:
        status = "RECEIPT_INTEGRITY_BLOCKED"
    elif not same_session or not same_cycle:
        status = "STALE_BINDING"
    elif receipt.get("generation_source") == "MODEL" and receipt.get("final_surface_effect_confirmed") is True:
        status = "CONFIRMED_CURRENT" if cycle_revision == current_revision else "CONFIRMED_CYCLE_CONFIG_NOW_CHANGED"
    elif receipt.get("generation_source") == "OPERATIONAL_FALLBACK":
        status = "MODEL_CONFIG_ATTEMPTED_FINAL_FALLBACK"
    else:
        status = "BYPASSED_NON_MODEL_ROUTE"
    return {
        **receipt,
        "status": status,
        "current_config_revision": current_revision,
        "cycle_config_revision": cycle_revision,
        "same_session": same_session,
        "same_cycle": same_cycle,
        "integrity_verified": valid_sha,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def _state_stamp(root: Path) -> dict[str, Any]:
    runtime = _runtime(root)
    cognitive = runtime.get("cognitive") if isinstance(runtime.get("cognitive"), dict) else {}
    config = load_experiment_config(root)
    transcript = root / ".ikant" / "chat" / "transcript.jsonl"
    try:
        stat = transcript.stat()
        transcript_stamp = [stat.st_size, stat.st_mtime_ns]
    except OSError:
        transcript_stamp = [0, 0]
    return {
        "runtime_session_id": str(runtime.get("session_id") or "") or None,
        "runtime_status": str(runtime.get("status") or "") or None,
        "cycle_id": str(cognitive.get("last_surface_a_cycle_id") or "") or None,
        "config_revision": int(config.get("revision") or 0),
        "transcript_stamp": transcript_stamp,
    }


def _safe_product(service: Any) -> dict[str, Any]:
    try:
        out = service.product_status()
    except Exception:
        return {}
    return out if isinstance(out, dict) else {}


def _snapshot_token(snapshot: dict[str, Any]) -> str:
    material = deepcopy(snapshot)
    material.pop("snapshot_sha256", None)
    return _sha(material)


def _work_identity(work: dict[str, Any] | None) -> dict[str, Any]:
    value = work if isinstance(work, dict) else {}
    return {
        "work_id": value.get("work_id"),
        "phase": value.get("phase"),
        "active": bool(value.get("active")),
        "terminal": bool(value.get("terminal")),
        "cycle_id": value.get("cycle_id"),
    }


def _build_stable(service: Any, *, work: dict[str, Any] | None) -> dict[str, Any]:
    root = Path(service.root).resolve()
    manifest = surface_manifest()
    public: dict[str, Any] = {}
    foundation: dict[str, Any] = {}
    consistency = "STABLE"
    before = after = _state_stamp(root)
    for attempt in range(2):
        before = _state_stamp(root)
        foundation = foundation_projection(service)
        public = public_projection(service)
        after = _state_stamp(root)
        if before == after:
            consistency = "STABLE" if attempt == 0 else "STABLE_AFTER_RETRY"
            break
        consistency = "DRIFT_AFTER_RETRY"
    config = foundation.get("config") if isinstance(foundation.get("config"), dict) else load_experiment_config(root)
    effect = config_effect_projection(root, config=config)
    product = _safe_product(service)
    vector = {
        **after,
        "conversation_last_sha256": ((public.get("conversation") or {}).get("last_sha256") if isinstance(public.get("conversation"), dict) else None),
        "product_stage": product.get("stage"),
        "product_attempt": product.get("attempt"),
        "work": _work_identity(work),
    }
    snapshot = {
        "schema": SURFACE_CONTRACT_SCHEMA,
        "version": "S16",
        "asset_revision": ASSET_REVISION,
        "snapshot_mode": "STABLE",
        "consistency": consistency,
        "semantic_contract_sha256": manifest["semantic_contract_sha256"],
        "revision_vector": vector,
        "manifest": manifest,
        "product": product,
        "foundation": foundation,
        "public": public,
        "work": deepcopy(work) if isinstance(work, dict) else {},
        "config_effect": effect,
        "presentation_is_authority": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    snapshot["snapshot_sha256"] = _snapshot_token(snapshot)
    session = str(after.get("runtime_session_id") or "")
    if session and consistency != "DRIFT_AFTER_RETRY":
        with _CACHE_LOCK:
            _STABLE_CACHE[(str(root), session)] = deepcopy(snapshot)
    return snapshot


def _running_overlay(service: Any, work: dict[str, Any]) -> dict[str, Any]:
    root = Path(service.root).resolve()
    stamp = _state_stamp(root)
    session = str(stamp.get("runtime_session_id") or "")
    manifest = surface_manifest()
    with _CACHE_LOCK:
        cached = deepcopy(_STABLE_CACHE.get((str(root), session))) if session else None
    if cached is None:
        config = load_experiment_config(root)
        snapshot = {
            "schema": SURFACE_CONTRACT_SCHEMA,
            "version": "S16",
            "asset_revision": ASSET_REVISION,
            "snapshot_mode": "WORK_OVERLAY",
            "consistency": "NONBLOCKING_NO_STABLE_BASE",
            "semantic_contract_sha256": manifest["semantic_contract_sha256"],
            "revision_vector": {**stamp, "work": _work_identity(work)},
            "manifest": manifest,
            "product": {},
            "foundation": {"schema": FOUNDATION_SCHEMA, "foundation_version": FOUNDATION_VERSION, "config": config},
            "public": None,
            "work": deepcopy(work),
            "config_effect": config_effect_projection(root, config=config),
            "presentation_is_authority": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
        snapshot["snapshot_sha256"] = _snapshot_token(snapshot)
        return snapshot
    base_sha = cached.get("snapshot_sha256")
    cached["snapshot_mode"] = "WORK_OVERLAY"
    cached["consistency"] = "NONBLOCKING_OVER_STABLE_BASE"
    cached["base_snapshot_sha256"] = base_sha
    cached["work"] = deepcopy(work)
    vector = dict(cached.get("revision_vector") or {})
    vector.update(stamp)
    vector["work"] = _work_identity(work)
    cached["revision_vector"] = vector
    cached["snapshot_sha256"] = _snapshot_token(cached)
    return cached


def surface_snapshot(service: Any, *, work: dict[str, Any] | None = None) -> dict[str, Any]:
    current = work if isinstance(work, dict) else {}
    if current.get("active") is True and current.get("phase") == "RUNNING":
        return _running_overlay(service, current)
    return _build_stable(service, work=current)
