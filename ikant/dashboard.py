from __future__ import annotations

import hashlib
import io
import json
import math
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

DASHBOARD_SCHEMA = "ikant-enduser-dashboard/v0.4-test"
DOCX_INDEX_SCHEMA = "ikant-docx-backlog-index/v0.4-test"
DOCX_CACHE_SCHEMA = "ikant-docx-backlog-cache/v0.4-test"
_MAX_DOCS = 64
_MAX_DOCX_BYTES = 20 * 1024 * 1024
_MAX_XML_BYTES = 5 * 1024 * 1024
_MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
_SIGNAL_TERMS = {
    "decision": ("decision", "decisione"),
    "conflict": ("conflict", "conflitto"),
    "validation": ("validation", "validazione", "test"),
    "risk": ("risk", "rischio"),
    "strategy": ("strategy", "strategia"),
    "backlog": ("backlog", "todo", "next"),
}


def _clamp01(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return max(0.0, min(1.0, number))


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{round(100 * value):d}%"


def _kpi(key: str, label: str, value: Any, display: str, status: str, explanation: str, source: str) -> dict[str, Any]:
    return {"key": key, "label": label, "value": value, "display": display, "status": status, "explanation": explanation, "source": source}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _snapshot_for_runtime(runtime: Any) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    cognitive = runtime.runtime.get("cognitive", {}) if isinstance(runtime.runtime, dict) else {}
    path_value = cognitive.get("last_snapshot")
    if not path_value:
        return {}, ["surface_b_snapshot_missing"]
    path = Path(path_value)
    snapshot = _read_json(path)
    if snapshot is None:
        return {}, ["surface_b_snapshot_unreadable"]
    if snapshot.get("session_id") not in {None, runtime.runtime.get("session_id")}:
        warnings.append("surface_b_session_binding_mismatch")
    return snapshot, warnings


def _safe_docx_text_payload(payload: bytes) -> tuple[str | None, str | None]:
    if len(payload) > _MAX_DOCX_BYTES:
        return None, "docx_too_large"
    bio = io.BytesIO(payload)
    if not zipfile.is_zipfile(bio):
        return None, "invalid_docx_zip"
    bio.seek(0)
    try:
        with zipfile.ZipFile(bio) as archive:
            infos = archive.infolist()
            if sum(max(0, i.file_size) for i in infos) > _MAX_UNCOMPRESSED_BYTES:
                return None, "docx_uncompressed_limit"
            try:
                info = archive.getinfo("word/document.xml")
            except KeyError:
                return None, "document_xml_missing"
            if info.file_size > _MAX_XML_BYTES:
                return None, "document_xml_too_large"
            data = archive.read(info)
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return None, "docx_read_failed"
    upper = data[:4096].upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        return None, "docx_xml_doctype_forbidden"
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None, "document_xml_malformed"
    texts: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            texts.append(node.text)
    return " ".join(texts)[:20000], None


def index_docx_backlog(paths: list[str | Path], *, cache_path: str | Path | None = None) -> dict[str, Any]:
    candidates: list[Path] = []
    for value in paths:
        path = Path(value)
        if path.is_dir():
            candidates.extend(sorted(path.glob("*.docx")))
        elif path.suffix.casefold() == ".docx":
            candidates.append(path)
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
        if len(unique) >= _MAX_DOCS:
            break
    cache_file = Path(cache_path) if cache_path else None
    cache = _read_json(cache_file) if cache_file and cache_file.exists() else None
    cached_files = cache.get("files", {}) if isinstance(cache, dict) and cache.get("schema") == DOCX_CACHE_SCHEMA else {}
    new_cache: dict[str, Any] = {}
    docs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    aggregate = {key: 0 for key in _SIGNAL_TERMS}
    hits = misses = 0
    for path in unique:
        if path.is_symlink():
            errors.append({"path": str(path), "error": "docx_symlink_forbidden"})
            continue
        try:
            payload = path.read_bytes()
        except OSError:
            errors.append({"path": str(path), "error": "read_failed"})
            continue
        if len(payload) > _MAX_DOCX_BYTES:
            errors.append({"path": str(path), "error": "docx_too_large"})
            continue
        digest = hashlib.sha256(payload).hexdigest()
        key = str(path.resolve())
        cached = cached_files.get(key, {})
        if cached.get("sha256") == digest and isinstance(cached.get("signals"), dict):
            signals = {name: int(cached["signals"].get(name, 0) or 0) for name in _SIGNAL_TERMS}
            hits += 1
        else:
            text, error = _safe_docx_text_payload(payload)
            if error:
                errors.append({"path": str(path), "error": error})
                continue
            assert text is not None
            low = text.casefold()
            signals = {name: sum(low.count(term) for term in terms) for name, terms in _SIGNAL_TERMS.items()}
            misses += 1
        for name, value in signals.items():
            aggregate[name] += value
        row = {"path": str(path), "name": path.name, "bytes": len(payload), "sha256": digest, "signals": signals}
        docs.append(row)
        new_cache[key] = {"sha256": digest, "bytes": len(payload), "signals": signals}
    if cache_file:
        _atomic_json(cache_file, {"schema": DOCX_CACHE_SCHEMA, "files": new_cache, "operational_projection_only": True})
    return {
        "schema": DOCX_INDEX_SCHEMA,
        "documents": docs,
        "document_count": len(docs),
        "errors": errors,
        "signal_counts": aggregate,
        "cache": {"hits": hits, "misses": misses, "content_addressed": True},
        "operational_projection_only": True,
        "may_create_epistemic_evidence": False,
    }


def project_dashboard(runtime: Any, *, backlog_paths: list[str | Path] | None = None) -> dict[str, Any]:
    snapshot, warnings = _snapshot_for_runtime(runtime)
    state = runtime.runtime if isinstance(runtime.runtime, dict) else {}
    cognitive = state.get("cognitive", {})
    dynamic = snapshot.get("dynamic_state", {})
    reticulum = snapshot.get("reticulum", {})
    diag = reticulum.get("diagnostics", {})
    roa = reticulum.get("roa_alignment", {})
    central = dynamic.get("central_oracle", {})
    projection = dynamic.get("central_projection", {})
    proto = dynamic.get("proto_self", {})
    surface = dynamic.get("surface_a_contract", {})
    regulation = surface.get("regulation", {})
    base_oracle = central.get("base_oracle", {})
    grounding = _clamp01(base_oracle.get("faculties", {}).get("sensibility_grounding"))
    caution = _clamp01(regulation.get("epistemic_caution"))
    integration = _clamp01(proto.get("proto_self_index"))
    revision = _clamp01(state.get("compression", {}).get("trend", {}).get("metrics", {}).get("revision_pressure"))
    conflicts = len(projection.get("must_surface_conflicts", []) or [])
    debt = int(diag.get("epistemic_debt_open_count", 0) or 0)
    crc_basic = bool(roa.get("crc_basic")) if snapshot else False
    central_mode = str(central.get("regulative_mode") or "NO_SNAPSHOT")
    pending = bool(cognitive.get("pending_surface_a_cycle_id"))
    runtime_status = str(state.get("status") or "UNKNOWN")
    kpis = [
        _kpi("runtime", "Runtime", runtime_status, runtime_status, "ok" if runtime_status == "ACTIVE" else "block", "Stato del runtime locale inizializzato.", "runtime.status"),
        _kpi("turns", "Turni", int(state.get("cycle_count", 0) or 0), str(int(state.get("cycle_count", 0) or 0)), "ok", "Numero di cicli cognitivi persistiti nella sessione.", "runtime.cycle_count"),
        _kpi("grounding", "Ancoraggio", grounding, _pct(grounding), "ok" if grounding is not None and grounding >= .6 else ("watch" if grounding is not None else "na"), "Quota funzionale di contenuto attribuibile rispetto a derivazioni interne.", "Surface B central oracle"),
        _kpi("caution", "Cautela", caution, _pct(caution), "watch" if caution is not None and caution >= .6 else ("ok" if caution is not None else "na"), "Pressione a qualificare, verificare o astenersi.", "Surface B output regulation"),
        _kpi("conflicts", "Conflitti", conflicts, str(conflicts), "ok" if conflicts == 0 else "watch", "Conflitti espliciti che non devono essere compressi via silenziosamente.", "Surface B central projection"),
        _kpi("debt", "Debito epistemico", debt, str(debt), "ok" if debt == 0 else "watch", "Macrostati che richiedono evidenza, revisione o ritiro.", "Surface B CRC diagnostics"),
        _kpi("integration", "Integrazione runtime", integration, _pct(integration), "ok" if integration is not None and integration >= .5 else ("watch" if integration is not None else "na"), "Coordinamento software persistente tra livelli; non e una misura di coscienza.", "Surface B proto-self"),
        _kpi("closure", "Chiusura CRC", crc_basic, "SI" if crc_basic else "NO", "ok" if crc_basic else "watch", "Il percorso rappresentazionale dichiarato e chiuso entro l'orizzonte corrente.", "Surface B ROA alignment"),
        _kpi("revision", "Pressione revisione", revision, _pct(revision), "watch" if revision is not None and revision >= .45 else ("ok" if revision is not None else "na"), "Tendenza recente a correzioni/revisioni nella memoria derivata.", "runtime compression trend"),
        _kpi("pending", "Risposta pendente", pending, "SI" if pending else "NO", "watch" if pending else "ok", "Indica un turno aperto che deve ancora chiudere Surface A.", "runtime cognitive state"),
    ]
    block = runtime_status != "ACTIVE" or central_mode in {"HORIZON_BLOCK", "PRACTICAL_BLOCK"}
    watch = any(k["status"] == "watch" for k in kpis) or warnings
    overall = "BLOCKED" if block else ("WATCH" if watch else "STABLE")
    root = Path(getattr(runtime, "root", Path(getattr(runtime, "state_dir", ".")).parent))
    state_dir = Path(getattr(runtime, "state_dir", root / ".ikant"))
    if backlog_paths is None:
        backlog_paths = [root / "backlog", state_dir / "artifacts"]
    backlog = index_docx_backlog(backlog_paths, cache_path=state_dir / "dashboard_docx_cache.json")
    return {
        "schema": DASHBOARD_SCHEMA,
        "session_id": state.get("session_id"),
        "overall": overall,
        "central_mode": central_mode,
        "kpis": kpis,
        "warnings": list(dict.fromkeys(warnings)),
        "surface_b": {"available": bool(snapshot), "cycle_id": snapshot.get("cycle_id"), "snapshot_path": cognitive.get("last_snapshot")},
        "backlog": backlog,
        "contract": {
            "derived_view_only": True,
            "may_modify_runtime_evidence": False,
            "may_authorize_material_action": False,
            "contains_private_chain_of_thought": False,
            "consciousness_claim": False,
        },
    }


def render_dashboard_ascii(dashboard: dict[str, Any], *, width: int = 96) -> str:
    if width < 72:
        raise ValueError("dashboard width must be >= 72")
    line = "+" + "-" * (width - 2) + "+"
    out = [line, "|" + " iKant runtime telemetry ".center(width - 2) + "|", line]
    header = f"State {dashboard.get('overall','?')} | mode {dashboard.get('central_mode','?')} | session {str(dashboard.get('session_id') or '-')[:24]}"
    out.append("| " + header[: width - 4].ljust(width - 4) + " |")
    out.append(line)
    kpis = dashboard.get("kpis", [])
    for i in range(0, len(kpis), 2):
        left = kpis[i]
        right = kpis[i + 1] if i + 1 < len(kpis) else {"label": "", "display": "", "status": ""}
        cell_w = (width - 5) // 2
        ltxt = f"{left['label']}: {left['display']} [{left['status']}]"[:cell_w].ljust(cell_w)
        rtxt = f"{right['label']}: {right['display']} [{right['status']}]"[:cell_w].ljust(cell_w)
        out.append(f"| {ltxt} | {rtxt} |")
    out.append(line)
    backlog = dashboard.get("backlog", {})
    summary = f"Backlog DOCX: {backlog.get('document_count',0)} | parse errors: {len(backlog.get('errors',[]))} | projection only: yes"
    out.append("| " + summary[: width - 4].ljust(width - 4) + " |")
    out.extend([line, "> iKant:"])
    return "\n".join(out)


def persist_dashboard(runtime: Any, *, backlog_paths: list[str | Path] | None = None) -> dict[str, Any]:
    dashboard = project_dashboard(runtime, backlog_paths=backlog_paths)
    state_dir = Path(runtime.state_dir)
    json_path = state_dir / "dashboard.json"
    text_path = state_dir / "dashboard.txt"
    _atomic_json(json_path, dashboard)
    tmp_text = text_path.with_suffix(".txt.tmp")
    tmp_text.write_text(render_dashboard_ascii(dashboard) + "\n", encoding="utf-8")
    tmp_text.replace(text_path)
    dashboard["persisted"] = {"json": str(json_path), "text": str(text_path)}
    return dashboard
