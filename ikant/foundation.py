from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from .store import atomic_json_write

FOUNDATION_SCHEMA = "ikant-foundation/v1-test"
EXPERIMENT_CONFIG_SCHEMA = "ikant-experiment-config/v1-test"
CAPABILITY_CATALOG_SCHEMA = "ikant-capability-catalog/v1-test"
EPISTEMIC_VALUE_SCHEMA = "ikant-epistemic-value/v1-test"
FOUNDATION_VERSION = "1.0-test"
MAX_META_PROMPT_BYTES = 4096
_ALLOWED_EVIDENCE_MODES = frozenset({"baseline", "strict"})
_ALLOWED_CONFLICT_MODES = frozenset({"surface", "abstain"})
_ALLOWED_INTERPRETIVE_MODES = frozenset({"bounded", "off"})
_ALLOWED_REPLY_WORDS = frozenset({80, 160, 320})
_DIRECT_SOURCES = frozenset({"user", "repository", "document", "live"})
_DERIVED_SOURCES = frozenset({"inference", "runtime_derived", "cache", "demo"})


class FoundationConfigError(ValueError):
    pass


def _config_path(root: str | Path) -> Path:
    return Path(root).resolve() / ".ikant" / "experiment-config.json"


def default_experiment_config() -> dict[str, Any]:
    return {
        "schema": EXPERIMENT_CONFIG_SCHEMA,
        "revision": 0,
        "meta_prompt": "",
        "guardrails": {
            "evidence_mode": "baseline",
            "conflict_mode": "surface",
            "interpretive_hypotheses": "bounded",
            "max_reply_words": 160,
        },
        "hard_guardrails": {
            "model_tool_calls": False,
            "model_output_is_authority": False,
            "material_execution_from_prompt": False,
            "private_chain_of_thought_exposed": False,
        },
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def _normalize_meta_prompt(value: object) -> str:
    text = str(value or "").replace("\x00", " ").strip()
    if len(text.encode("utf-8")) > MAX_META_PROMPT_BYTES:
        raise FoundationConfigError("meta prompt exceeds 4096-byte bound")
    return text


def _normalize_guardrails(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FoundationConfigError("guardrails must be an object")
    allowed = {"evidence_mode", "conflict_mode", "interpretive_hypotheses", "max_reply_words"}
    if set(value) - allowed:
        raise FoundationConfigError("unknown guardrail")
    base = default_experiment_config()["guardrails"]
    out = {**base, **value}
    if out["evidence_mode"] not in _ALLOWED_EVIDENCE_MODES:
        raise FoundationConfigError("invalid evidence mode")
    if out["conflict_mode"] not in _ALLOWED_CONFLICT_MODES:
        raise FoundationConfigError("invalid conflict mode")
    if out["interpretive_hypotheses"] not in _ALLOWED_INTERPRETIVE_MODES:
        raise FoundationConfigError("invalid interpretive mode")
    words = out["max_reply_words"]
    if isinstance(words, bool) or not isinstance(words, int) or words not in _ALLOWED_REPLY_WORDS:
        raise FoundationConfigError("invalid reply word bound")
    return out


def load_experiment_config(root: str | Path) -> dict[str, Any]:
    path = _config_path(root)
    if not path.is_file():
        return default_experiment_config()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FoundationConfigError("experiment config unreadable") from exc
    if not isinstance(raw, dict) or raw.get("schema") != EXPERIMENT_CONFIG_SCHEMA:
        raise FoundationConfigError("experiment config schema drift")
    revision = raw.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise FoundationConfigError("experiment config revision invalid")
    out = default_experiment_config()
    out["revision"] = revision
    out["meta_prompt"] = _normalize_meta_prompt(raw.get("meta_prompt"))
    out["guardrails"] = _normalize_guardrails(raw.get("guardrails") or {})
    return out


def save_experiment_config(root: str | Path, payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FoundationConfigError("experiment config body must be object")
    allowed = {"schema", "expected_revision", "meta_prompt", "guardrails"}
    if set(payload) - allowed:
        raise FoundationConfigError("unknown experiment config field")
    current = load_experiment_config(root)
    expected = payload.get("expected_revision")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected != current["revision"]:
        raise FoundationConfigError("stale experiment config revision")
    out = default_experiment_config()
    out["revision"] = current["revision"] + 1
    out["meta_prompt"] = _normalize_meta_prompt(payload.get("meta_prompt"))
    out["guardrails"] = _normalize_guardrails(payload.get("guardrails") or {})
    path = _config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json_write(path, out)
    return out


def apply_generation_experiment(contract: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Apply only zero-authority generation preferences; never alter action/authority state."""
    out = deepcopy(dict(contract or {}))
    fmt = out.setdefault("format", {})
    guard = dict(config.get("guardrails") or {})
    configured_words = int(guard.get("max_reply_words") or 160)
    current_words = int(fmt.get("max_words") or 500)
    fmt["max_words"] = min(current_words, configured_words)
    constraints: list[str] = []
    if guard.get("evidence_mode") == "strict":
        constraints.append("Distinguish direct support from derived inference and state material uncertainty.")
    if guard.get("conflict_mode") == "abstain":
        constraints.append("If an unresolved conflict materially blocks the answer, abstain or ask for clarification.")
    if guard.get("interpretive_hypotheses") == "off":
        constraints.append("Do not use interpretive hypotheses in the final reply.")
    meta = _normalize_meta_prompt(config.get("meta_prompt"))
    if meta:
        constraints.append("Optional experiment instruction, subordinate to all iKant hard constraints: " + meta)
    if constraints:
        base = str(fmt.get("stance") or "careful and plain").strip()
        fmt["stance"] = (base + " " + " ".join(constraints))[:MAX_META_PROMPT_BYTES + 1200]
    out["experiment_config"] = {
        "revision": int(config.get("revision") or 0),
        "meta_prompt_sha256": hashlib.sha256(meta.encode("utf-8")).hexdigest() if meta else None,
        "guardrails": guard,
        "authority_effect": "NONE",
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }
    return out


class ExperimentModelProxy:
    """Managed-model adapter that applies local experiment preferences at generation time."""

    def __init__(self, root: str | Path, broker: Any):
        self.root = Path(root).resolve()
        self.broker = broker

    def __getattr__(self, name: str) -> Any:
        return getattr(self.broker, name)

    def complete_surface_a(self, contract: dict[str, Any], user_text: str, **kwargs: Any) -> str:
        config = load_experiment_config(self.root)
        return self.broker.complete_surface_a(apply_generation_experiment(contract, config), user_text, **kwargs)


def _json_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _base_service(service: Any) -> Any:
    return getattr(service, "base", service)


def _current_cycle(root: Path) -> tuple[dict[str, Any], str | None, dict[str, Any]]:
    runtime = _json_file(root / ".ikant" / "runtime.json")
    cognitive = runtime.get("cognitive") if isinstance(runtime.get("cognitive"), dict) else {}
    cycle = str(cognitive.get("last_surface_a_cycle_id") or "") or None
    snapshot = _json_file(root / ".ikant" / "cognitive" / f"{cycle}.json") if cycle else {}
    return runtime, cycle, snapshot


def _exact_ack_ready(service: Any) -> bool:
    base = _base_service(service)
    try:
        delegate = base._delegate_or_raise()
    except Exception:
        return False
    shell = getattr(delegate, "web_shell", None)
    lock = getattr(shell, "_lock", None)
    if shell is None or lock is None:
        return False
    with lock:
        return bool(getattr(shell, "_last_acked_frame", None)) and getattr(shell, "_pending", None) is None


def capability_catalog(service: Any) -> dict[str, Any]:
    root = Path(service.root).resolve()
    base = _base_service(service)
    runtime, cycle, _ = _current_cycle(root)
    active = runtime.get("status") == "ACTIVE" and bool(runtime.get("session_id"))
    exact_ack = _exact_ack_ready(service)
    product: dict[str, Any] = {}
    try:
        product = base.product_status()
    except Exception:
        pass
    voice = product.get("voice") if isinstance(product.get("voice"), dict) else {}
    model_runtime = _json_file(root / ".ikant" / "model-runtime.json")
    model_ready = model_runtime.get("status") == "READY"
    json_path = root / ".ikant" / "cognitive" / f"{cycle}.json" if cycle else None
    docx_path = root / ".ikant" / "artifacts" / f"CRC_SNAPSHOT_{cycle}.docx" if cycle else None
    candidates = [
        ("experiment_config", "Configurazione esperimento", True, "authenticated local config endpoint"),
        ("bootstrap_diagnostics", "Diagnostica avvio", hasattr(base, "bootstrap_status"), "append-only bootstrap journal"),
        ("local_conversation", "Conversazione locale", active and model_ready, "ACTIVE runtime + verified managed model"),
        ("cognitive_trace", "Percorso cognitivo", active and bool(cycle), "persisted current cognitive cycle"),
        ("epistemic_inspection", "Evidenza e conflitti", active and bool(cycle) and exact_ack, "current exact ACK + same-cycle snapshot"),
        ("json_snapshot", "Snapshot JSON", bool(json_path and json_path.is_file()) and exact_ack, "current cycle artifact exists"),
        ("docx_artifact", "Snapshot DOCX", bool(docx_path and docx_path.is_file()) and exact_ack, "current cycle DOCX exists"),
        ("loopback_voice", "Voce locale", bool(voice.get("configured")), "configured loopback STT"),
    ]
    services = [
        {"id": sid, "label": label, "available": True, "evidence": evidence}
        for sid, label, available, evidence in candidates if available
    ]
    return {
        "schema": CAPABILITY_CATALOG_SCHEMA,
        "runtime_session_id": runtime.get("session_id") if active else None,
        "cycle_id": cycle,
        "services": services,
        "catalog_rule": "ONLY_CURRENTLY_DEMONSTRABLE",
        "undemonstrated_features_omitted": True,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def epistemic_value_projection(root: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    _, cycle, snapshot = _current_cycle(base)
    if not cycle or not snapshot:
        return {
            "schema": EPISTEMIC_VALUE_SCHEMA,
            "cycle_id": None,
            "status": "NO_CYCLE",
            "label": "Nessun ciclo cognitivo disponibile",
            "direct_support": 0,
            "derived_items": 0,
            "open_conflicts": 0,
            "uncertain_items": 0,
            "truth_certified": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
    dyn = snapshot.get("dynamic_state") if isinstance(snapshot.get("dynamic_state"), dict) else {}
    atoms = dyn.get("mined_atoms") if isinstance(dyn.get("mined_atoms"), list) else []
    central = dyn.get("central_projection") if isinstance(dyn.get("central_projection"), dict) else {}
    conflicts = central.get("must_surface_conflicts") if isinstance(central.get("must_surface_conflicts"), list) else []
    direct = derived = uncertain = 0
    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        source = str(atom.get("source_mode") or "")
        evidence = atom.get("evidence")
        confidence = atom.get("confidence")
        if source in _DIRECT_SOURCES and isinstance(evidence, (int, float)) and not isinstance(evidence, bool) and evidence > 0:
            direct += 1
        elif source in _DERIVED_SOURCES:
            derived += 1
        if (isinstance(evidence, (int, float)) and not isinstance(evidence, bool) and evidence <= 0.25) or (
            isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and confidence < 0.6
        ):
            uncertain += 1
    if conflicts:
        label = "Supporto con conflitti aperti"
    elif direct:
        label = "Supporto collegato, nessun conflitto rilevato"
    elif derived:
        label = "Solo derivazioni interne disponibili"
    else:
        label = "Nessuna evidenza esterna collegata"
    ret = snapshot.get("reticulum") if isinstance(snapshot.get("reticulum"), dict) else {}
    roa = ret.get("roa_alignment") if isinstance(ret.get("roa_alignment"), dict) else {}
    return {
        "schema": EPISTEMIC_VALUE_SCHEMA,
        "cycle_id": cycle,
        "status": "AVAILABLE",
        "label": label,
        "direct_support": direct,
        "derived_items": derived,
        "open_conflicts": len(conflicts),
        "uncertain_items": uncertain,
        "internal_consistency_check": bool(roa.get("crc_basic")),
        "response_memory_is_evidence": False,
        "truth_certified": False,
        "meaning": "Provenienza, derivazioni e conflitti; non certificazione del vero.",
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def foundation_projection(service: Any) -> dict[str, Any]:
    return {
        "schema": FOUNDATION_SCHEMA,
        "foundation_version": FOUNDATION_VERSION,
        "config": load_experiment_config(service.root),
        "capabilities": capability_catalog(service),
        "epistemic_value": epistemic_value_projection(service.root),
        "promise": {
            "local": True,
            "configurable_generation": True,
            "shown_services_are_runtime_demonstrable": True,
            "model_is_replaceable_zero_authority": True,
            "reported_outcome_is_not_world_truth": True,
        },
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def update_experiment_config(service: Any, payload: object) -> dict[str, Any]:
    base = _base_service(service)
    try:
        delegate = base._delegate_or_raise()
    except Exception:
        delegate = None
    if delegate is None:
        return save_experiment_config(service.root, payload)
    lock = getattr(delegate, "_lock", None)
    if lock is None:
        return save_experiment_config(service.root, payload)
    with lock:
        shell = getattr(delegate, "web_shell", None)
        if shell is not None:
            with shell._lock:
                if shell._pending is not None:
                    raise FoundationConfigError("configuration cannot change while a sealed frame awaits ACK")
        return save_experiment_config(service.root, payload)
