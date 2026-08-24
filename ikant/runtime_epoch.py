from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .foundation import load_experiment_config
from .store import acquire_writer_lock, append_jsonl, atomic_json_write, read_json

RUNTIME_EPOCH_SCHEMA = "ikant-runtime-provenance-epoch/v1-test"
RUNTIME_EPOCH_EVENT_SCHEMA = "ikant-runtime-provenance-epoch-event/v1-test"
RUNTIME_EPOCH_LEDGER_SCHEMA = "ikant-runtime-provenance-epoch-ledger/v1-test"


class RuntimeEpochError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = read_json(path, {})
    except Exception as exc:
        raise RuntimeEpochError(f"runtime epoch dependency unreadable: {path.name}") from exc
    return value if isinstance(value, dict) else {}


def _product_descriptor(root: Path) -> dict[str, Any]:
    path = root / "PRODUCT_CONTRACT.json"
    raw = _json_object(path)
    if not raw or not isinstance(raw.get("slices"), list):
        raise RuntimeEpochError("PRODUCT_CONTRACT unavailable for runtime epoch")
    return {
        "schema": str(raw.get("schema") or ""),
        "product_version": str(raw.get("product_version") or ""),
        "contract_version": str(raw.get("contract_version") or ""),
        "constitutional_convergence": str(raw.get("constitutional_convergence") or ""),
        "semantic_sha256": _sha(raw),
    }


def _surface_descriptor(surface_contract_sha256: str | None) -> dict[str, Any]:
    digest = str(surface_contract_sha256 or "").strip()
    if not digest:
        # Delayed import avoids making the Surface Contract and epoch modules import-time cyclic.
        from .surface_contract import surface_manifest
        digest = str(surface_manifest().get("semantic_contract_sha256") or "")
    if len(digest) != 64:
        raise RuntimeEpochError("Surface Contract digest unavailable for runtime epoch")
    return {"semantic_contract_sha256": digest}


def _model_descriptor(root: Path, *, require_verified: bool) -> dict[str, Any]:
    raw = _json_object(root / ".ikant" / "model-runtime.json")
    binding = str(raw.get("binding_sha256") or "")
    engine = raw.get("engine") if isinstance(raw.get("engine"), dict) else {}
    model = raw.get("model") if isinstance(raw.get("model"), dict) else {}
    complete = bool(
        len(binding) == 64
        and raw.get("manifest_sha256")
        and all(engine.get(k) for k in ("id", "version", "platform", "artifact_sha256"))
        and all(model.get(k) for k in ("id", "revision", "sha256"))
    )
    verified = False
    if complete:
        from .managed_runtime import _binding_digest
        candidate = {
            "manifest_sha256": raw["manifest_sha256"],
            "engine": {k: engine[k] for k in ("id", "version", "platform", "artifact_sha256")},
            "model": {k: model[k] for k in ("id", "revision", "sha256")},
        }
        verified = _binding_digest(candidate) == binding
        if not verified:
            raise RuntimeEpochError("managed runtime binding digest mismatch")
    if require_verified and not verified:
        raise RuntimeEpochError("verified managed runtime binding required for runtime epoch")
    return {
        "binding_sha256": binding or None,
        "binding_verified": verified,
        "manifest_sha256": str(raw.get("manifest_sha256") or "") or None,
        "engine": {
            "id": str(engine.get("id") or "") or None,
            "version": str(engine.get("version") or "") or None,
            "platform": str(engine.get("platform") or "") or None,
            "artifact_sha256": str(engine.get("artifact_sha256") or "") or None,
        },
        "model": {
            "id": str(model.get("id") or "") or None,
            "revision": str(model.get("revision") or "") or None,
            "sha256": str(model.get("sha256") or "") or None,
        },
        # Process liveness is observable but intentionally excluded from epoch material identity.
        "live_status": str(raw.get("status") or "UNKNOWN")[:48],
    }


def epoch_material(
    root: str | Path,
    *,
    surface_contract_sha256: str | None = None,
    require_managed_binding: bool = False,
) -> dict[str, Any]:
    base = Path(root).resolve()
    runtime = _json_object(base / ".ikant" / "runtime.json")
    session = str(runtime.get("session_id") or "").strip()
    if not session:
        raise RuntimeEpochError("runtime session required for runtime epoch")
    config = load_experiment_config(base)
    model = _model_descriptor(base, require_verified=require_managed_binding)
    material = {
        "runtime_session_id": session,
        "admission_contract_sha256": str(runtime.get("contract_sha256") or "") or None,
        "product": _product_descriptor(base),
        "surface_contract": _surface_descriptor(surface_contract_sha256),
        "generation_config": {
            "revision": int(config.get("revision") or 0),
            "sha256": _sha(config),
        },
        "managed_component": {
            "binding_sha256": model["binding_sha256"],
            "binding_verified": model["binding_verified"],
            "manifest_sha256": model["manifest_sha256"],
            "engine": model["engine"],
            "model": model["model"],
        },
    }
    return {"material": material, "material_sha256": _sha(material), "live_status": model["live_status"]}


def _ledger_path(root: Path) -> Path:
    return root / ".ikant" / "runtime-epochs.jsonl"


def _current_path(root: Path) -> Path:
    return root / ".ikant" / "runtime-epoch.json"


def verify_epoch_ledger(root: str | Path) -> dict[str, Any]:
    base = Path(root).resolve()
    path = _ledger_path(base)
    rows: list[dict[str, Any]] = []
    if path.exists():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeEpochError(f"runtime epoch ledger malformed at line {lineno}") from exc
            rows.append(row)
    prev = "0" * 64
    for seq, row in enumerate(rows, 1):
        if row.get("schema") != RUNTIME_EPOCH_EVENT_SCHEMA:
            raise RuntimeEpochError("runtime epoch ledger schema drift")
        if row.get("seq") != seq or row.get("ordinal") != seq:
            raise RuntimeEpochError("runtime epoch ledger sequence drift")
        if row.get("prev_sha256") != prev:
            raise RuntimeEpochError("runtime epoch ledger predecessor drift")
        supplied = str(row.get("sha256") or "")
        material = deepcopy(row)
        material.pop("sha256", None)
        if supplied != _sha(material):
            raise RuntimeEpochError("runtime epoch ledger digest mismatch")
        descriptor = row.get("material") if isinstance(row.get("material"), dict) else {}
        if row.get("material_sha256") != _sha(descriptor):
            raise RuntimeEpochError("runtime epoch material digest mismatch")
        expected_id = "EPOCH-" + _sha({
            "ordinal": seq,
            "runtime_session_id": row.get("runtime_session_id"),
            "material_sha256": row.get("material_sha256"),
            "prev_sha256": row.get("prev_sha256"),
        })[:20]
        if row.get("epoch_id") != expected_id:
            raise RuntimeEpochError("runtime epoch id mismatch")
        prev = supplied
    return {
        "schema": RUNTIME_EPOCH_LEDGER_SCHEMA,
        "ok": True,
        "events": len(rows),
        "last_sha256": prev,
        "rows": rows,
        "authenticity_claimed": False,
        "slsa_attestation_claimed": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def _projection(event: dict[str, Any], *, live_status: str) -> dict[str, Any]:
    material = deepcopy(event.get("material") or {})
    component = material.get("managed_component") if isinstance(material.get("managed_component"), dict) else {}
    return {
        "schema": RUNTIME_EPOCH_SCHEMA,
        "status": "CURRENT",
        "epoch_id": event.get("epoch_id"),
        "ordinal": event.get("ordinal"),
        "material_sha256": event.get("material_sha256"),
        "runtime_session_id": event.get("runtime_session_id"),
        "created_at": event.get("at"),
        "product": deepcopy(material.get("product") or {}),
        "surface_contract": deepcopy(material.get("surface_contract") or {}),
        "generation_config": deepcopy(material.get("generation_config") or {}),
        "component": {
            "binding_sha256": component.get("binding_sha256"),
            "binding_verified": component.get("binding_verified") is True,
            "engine": deepcopy(component.get("engine") or {}),
            "model": deepcopy(component.get("model") or {}),
            "live_status": str(live_status or "UNKNOWN")[:48],
            "live_status_in_epoch_identity": False,
        },
        "ledger": {
            "event_seq": event.get("seq"),
            "event_sha256": event.get("sha256"),
            "integrity_verified": True,
            "local_integrity_only": True,
            "authenticity_claimed": False,
            "slsa_attestation_claimed": False,
        },
        "identity_label": "iKant",
        "model_is_identity": False,
        "component_presence_is_authority": False,
        "hash_is_not_actor_authentication": True,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def compact_epoch(epoch: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(epoch, dict) or epoch.get("schema") != RUNTIME_EPOCH_SCHEMA:
        return None
    component = epoch.get("component") if isinstance(epoch.get("component"), dict) else {}
    model = component.get("model") if isinstance(component.get("model"), dict) else {}
    return {
        "schema": RUNTIME_EPOCH_SCHEMA,
        "epoch_id": epoch.get("epoch_id"),
        "ordinal": epoch.get("ordinal"),
        "material_sha256": epoch.get("material_sha256"),
        "runtime_session_id": epoch.get("runtime_session_id"),
        "component_binding_sha256": component.get("binding_sha256"),
        "component_model_id": model.get("id"),
        "component_model_revision": model.get("revision"),
        "model_is_identity": False,
        "epistemic_authority": 0.0,
        "execution_authority": 0.0,
    }


def materialize_runtime_epoch(
    root: str | Path,
    *,
    surface_contract_sha256: str | None = None,
    require_managed_binding: bool = False,
) -> dict[str, Any]:
    base = Path(root).resolve()
    state = base / ".ikant"
    state.mkdir(parents=True, exist_ok=True)
    lock = acquire_writer_lock(state / "runtime-epoch.writer.lock")
    try:
        verified = verify_epoch_ledger(base)
        rows = verified["rows"]
        current_material = epoch_material(
            base,
            surface_contract_sha256=surface_contract_sha256,
            require_managed_binding=require_managed_binding,
        )
        material = current_material["material"]
        material_sha = current_material["material_sha256"]
        live_status = current_material["live_status"]
        last = rows[-1] if rows else None
        if last and last.get("material_sha256") == material_sha:
            out = _projection(last, live_status=live_status)
            atomic_json_write(_current_path(base), out)
            return out
        if last and last.get("runtime_session_id") == material.get("runtime_session_id"):
            previous_material = last.get("material") if isinstance(last.get("material"), dict) else {}
            previous_config = previous_material.get("generation_config") if isinstance(previous_material.get("generation_config"), dict) else {}
            previous_revision = previous_config.get("revision")
            current_revision = (material.get("generation_config") or {}).get("revision")
            if isinstance(previous_revision, int) and isinstance(current_revision, int) and current_revision < previous_revision:
                raise RuntimeEpochError("generation config revision rollback inside runtime session")
        seq = len(rows) + 1
        prev = verified["last_sha256"]
        session = str(material.get("runtime_session_id") or "")
        epoch_id = "EPOCH-" + _sha({
            "ordinal": seq,
            "runtime_session_id": session,
            "material_sha256": material_sha,
            "prev_sha256": prev,
        })[:20]
        event = {
            "schema": RUNTIME_EPOCH_EVENT_SCHEMA,
            "seq": seq,
            "ordinal": seq,
            "at": _now(),
            "epoch_id": epoch_id,
            "runtime_session_id": session,
            "material_sha256": material_sha,
            "material": material,
            "reason": "INITIAL_MATERIAL" if not last else "MATERIAL_CHANGE",
            "prev_sha256": prev,
            "authenticity_claimed": False,
            "slsa_attestation_claimed": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
        event["sha256"] = _sha(event)
        append_jsonl(_ledger_path(base), event)
        out = _projection(event, live_status=live_status)
        atomic_json_write(_current_path(base), out)
        return out
    finally:
        lock.release()


def current_runtime_epoch(
    root: str | Path,
    *,
    surface_contract_sha256: str | None = None,
    require_managed_binding: bool = False,
) -> dict[str, Any]:
    return materialize_runtime_epoch(
        root,
        surface_contract_sha256=surface_contract_sha256,
        require_managed_binding=require_managed_binding,
    )


def known_epoch_ids(root: str | Path) -> set[str]:
    verified = verify_epoch_ledger(root)
    return {str(row.get("epoch_id")) for row in verified["rows"] if row.get("epoch_id")}


def epoch_binding_status(root: str | Path, epoch_id: object, *, current: dict[str, Any] | None = None) -> str:
    candidate = str(epoch_id or "")
    if not candidate:
        return "UNATTESTED"
    live = current if isinstance(current, dict) else current_runtime_epoch(root)
    if candidate == str(live.get("epoch_id") or ""):
        return "CURRENT"
    return "PRIOR_KNOWN" if candidate in known_epoch_ids(root) else "UNKNOWN"
