from __future__ import annotations
from pathlib import Path
import json
from .crc import EpistemicHorizon, evaluate_reticulum
from .central import converge_kant_oracle, project_surface_content
from .proto_self import derive_proto_self, workspace_plan
from .surfaces import build_surface_a_contract, build_surface_b_snapshot, export_surface_b_docx, validate_surface_a
from .model import Layer, NodeKind, RelationKind, clamp01, node_to_dict
from .store import atomic_json_write



ALLOWED_MINED_KINDS={NodeKind.OBSERVATION,NodeKind.CLAIM,NodeKind.GOAL,NodeKind.CONSTRAINT,NodeKind.MEMORY,NodeKind.HYPOTHESIS,NodeKind.SELF_MODEL,NodeKind.ACTION,NodeKind.PREDICTION,NodeKind.CONFLICT}
ALLOWED_MINED_SOURCES={'user','repository','document','live','cache','demo','inference','runtime_derived'}

def apply_intention_atoms(runtime, atoms: list[dict] | None) -> list[dict]:
    records=[]
    for idx,atom in enumerate(atoms or []):
        kind=NodeKind(atom['kind']);layer=Layer(atom['layer']);source=str(atom['source_mode'])
        if kind not in ALLOWED_MINED_KINDS:raise ValueError(f'mined atom kind not allowed: {kind.value}')
        if source not in ALLOWED_MINED_SOURCES:raise ValueError(f'mined atom source not allowed: {source}')
        evidence=float(atom.get('evidence',0));confidence=float(atom.get('confidence',.5))
        if source in {'inference','runtime_derived','demo','cache'} and evidence>.25:raise ValueError('derived/inferred intention atoms cannot claim strong external evidence')
        if layer in {Layer.PSYCHODYNAMIC_HYPOTHESIS,Layer.ARCHETYPAL_HYPOTHESIS} and evidence>.20:raise ValueError('interpretive intention atoms exceed v0.2 evidence allowance')
        n=runtime.ingest(kind=kind,layer=layer,text=str(atom['text']),confidence=confidence,evidence=evidence,source_mode=source,metadata={**dict(atom.get('metadata') or {}),'mined_from_intention':True,'atom_index':idx})
        records.append(node_to_dict(n))
    return records

def record_surface_a(runtime, cycle_id: str, text: str, *, intention_node_id: str | None = None) -> dict:
    ok,errors=validate_surface_a(text)
    if not ok:raise ValueError('Surface A validation failed: '+'; '.join(errors))
    n=runtime.ingest(kind=NodeKind.RESPONSE,layer=Layer.MEMORY,text=text,confidence=1.0,evidence=0.0,source_mode='runtime_derived',metadata={'speech_act_not_evidence':True,'surface_a_validated':True,'response_cycles':[cycle_id]})
    cycles=list(n.metadata.get('response_cycles',[]))
    if cycle_id not in cycles:cycles.append(cycle_id)
    cycles=cycles[-32:]
    n.metadata.update({'speech_act_not_evidence':True,'surface_a_validated':True,'response_cycles':cycles,'response_cycle_window':32,'response_emission_count':n.recurrence,'last_cycle_id':cycle_id});runtime._save(n)
    if intention_node_id and intention_node_id in runtime.nodes:runtime.relate(intention_node_id,n.id,RelationKind.PRECEDES,1.0)
    runtime.runtime.setdefault('cognitive',{})['last_surface_a_response_id']=n.id;runtime.runtime['cognitive']['last_surface_a_cycle_id']=cycle_id;runtime._write_runtime();runtime._event('SURFACE_A_EMIT',cycle_id,{'response_id':n.id,'word_count':len(text.split()),'validated':True})
    receipt={'schema':'ikant-surface-a-emission/v0.2','cycle_id':cycle_id,'response_id':n.id,'validated':True,'evidence':n.evidence,'speech_act_not_evidence':True,'word_count':len(text.split())}
    snap_path=runtime.runtime.get('cognitive',{}).get('last_snapshot')
    if snap_path and Path(snap_path).exists():
        snap=json.loads(Path(snap_path).read_text(encoding='utf-8'))
        if snap.get('cycle_id')==cycle_id:
            snap.setdefault('dynamic_state',{})['surface_a_emission']={**receipt,'text':text}
            snap.setdefault('audit',{})['recent_events']=_recent_events(runtime)
            atomic_json_write(Path(snap_path),snap)
            docx=runtime.runtime.get('cognitive',{}).get('last_surface_b_docx')
            if docx:export_surface_b_docx(snap,docx);receipt['surface_b_docx']=docx
            receipt['surface_b_json']=snap_path
    return receipt

def _apply_workspace(runtime, plan: dict) -> dict:
    evidence_before = {nid: n.evidence for nid, n in runtime.nodes.items()}
    applied = []
    for item in plan.get("activation_boosts", []):
        n = runtime.nodes.get(item["node_id"])
        if not n or not n.active:
            continue
        before = n.activation
        n.activation = min(n.activation_ceiling, clamp01(n.activation + item["activation_delta"]))
        if n.activation != before:
            runtime._save(n)
            applied.append({"node_id": n.id, "before": round(before, 6), "after": round(n.activation, 6), "kind": "broadcast"})
    inhibition = float(plan.get("interpretive_inhibition", 0.0))
    for n in runtime.nodes.values():
        if not n.active or n.layer not in {Layer.PSYCHODYNAMIC_HYPOTHESIS, Layer.ARCHETYPAL_HYPOTHESIS}:
            continue
        before = n.activation
        n.activation = max(0.0, n.activation * (1 - inhibition))
        if n.activation != before:
            runtime._save(n)
            applied.append({"node_id": n.id, "before": round(before, 6), "after": round(n.activation, 6), "kind": "interpretive_inhibition"})
    evidence_after = {nid: n.evidence for nid, n in runtime.nodes.items()}
    if evidence_before != evidence_after:
        raise RuntimeError("workspace retroaction modified evidence")
    return {**plan, "applied": applied, "evidence_modified": False}


def _recent_events(runtime, limit: int = 40) -> list[dict]:
    rows = []
    path = getattr(runtime, "events_path", None)
    if path is not None and Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines()[-limit * 2:]:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows.extend(list(getattr(runtime, "events_mem", []))[-limit:])
    by_seq = {}
    for event in rows:
        by_seq[event.get("seq", len(by_seq) + 1)] = event
    return [by_seq[k] for k in sorted(by_seq)][-limit:]

def _persist_cognitive_snapshot(runtime, snapshot: dict) -> str | None:
    if not getattr(runtime, "durable", False):
        return None
    cycle_id = snapshot.get("cycle_id") or "UNKNOWN"
    base = Path(getattr(runtime, "state_dir", Path(".ikant"))) / "cognitive"
    path = base / f"{cycle_id}.json"
    atomic_json_write(path, snapshot)
    return str(path)


def compile_cognitive_turn(runtime, intent: str, *, limit: int = 12, horizon: EpistemicHorizon | None = None, atoms: list[dict] | None = None, export_docx: bool = False, docx_path: str | Path | None = None) -> dict:
    runtime.require_active()
    intention_node=None
    if hasattr(runtime, "ingest"):
        prior_response=runtime.runtime.get("cognitive",{}).get("last_surface_a_response_id")
        intention_node=runtime.ingest(kind=NodeKind.INTENTION, layer=Layer.SIGNAL, text=intent, confidence=1.0, evidence=1.0, source_mode="user", metadata={"raw_user_intention": True, "not_factual_claim": True})
        if prior_response in runtime.nodes:runtime.relate(prior_response,intention_node.id,RelationKind.PRECEDES,1.0)
    mined_atoms=apply_intention_atoms(runtime,atoms)
    cycle = runtime.concentric_cycle(intent, limit=limit)
    cognitive_state = runtime.runtime.get("cognitive", {})
    crc = evaluate_reticulum(cycle["semantic_slice"], horizon=horizon, previous_neurofunctional_state=cognitive_state.get("neurofunctional_state", {}))
    previous = cognitive_state.get("proto_self", {})
    proto = derive_proto_self(crc, cycle, previous)
    central = converge_kant_oracle(cycle.get("kant_oracle", {}), crc, proto)
    central_projection=project_surface_content(cycle,crc,central)
    plan = workspace_plan(crc, cycle, proto, gain=getattr(runtime.params, "oracle_retroaction_gain", .06), central=central)
    plan["regulative_mode"] = central["regulative_mode"]
    workspace = _apply_workspace(runtime, plan)

    runtime.runtime.setdefault("cognitive", {})["proto_self"] = proto
    runtime.runtime["cognitive"]["neurofunctional_state"] = crc.get("neurofunctional_state", {})
    runtime.runtime["cognitive"]["last_crc"] = {
        "cycle_id": cycle.get("cycle_id"),
        "crc_basic": crc.get("roa_alignment", {}).get("crc_basic"),
        "collapse": crc.get("diagnostics", {}).get("mean_coefficient_of_collapse"),
        "rir_proxy": crc.get("diagnostics", {}).get("reticular_irreducibility_proxy"),
        "central_mode": central.get("regulative_mode"),
        "proto_self_index": proto.get("proto_self_index"),
    }
    runtime._write_runtime()
    runtime._event("COGNITIVE_COMPILE", cycle.get("cycle_id"), {
        "crc_basic": crc.get("roa_alignment", {}).get("crc_basic"),
        "central_mode": central.get("regulative_mode"),
        "proto_self_index": proto.get("proto_self_index"),
        "workspace_applied": len(workspace.get("applied", [])),
        "mean_collapse": crc.get("diagnostics", {}).get("mean_coefficient_of_collapse"),
    })

    result = {
        "schema": "ikant-cognitive-turn/v0.2",
        "session_id": runtime.runtime.get("session_id"),
        "cycle": cycle,
        "crc": crc,
        "proto_self": proto,
        "central_oracle": central,
        "central_projection": central_projection,
        "workspace": workspace,
        "intention_node_id": intention_node.id if intention_node else None,
        "mined_atoms": mined_atoms,
        "compression": runtime.runtime.get("compression", {}),
        "recent_events": _recent_events(runtime),
    }
    result["surface_a_contract"] = build_surface_a_contract(result)
    snapshot = build_surface_b_snapshot(result)
    result["surface_b_snapshot"] = snapshot
    json_path = _persist_cognitive_snapshot(runtime, snapshot)
    if json_path:
        result["surface_b_json"] = json_path
        runtime.runtime["cognitive"]["last_snapshot"] = json_path
        runtime._write_runtime()

    if export_docx:
        if docx_path is None:
            base = Path(getattr(runtime, "state_dir", Path(".ikant"))) / "artifacts"
            docx_path = base / f"CRC_SNAPSHOT_{cycle.get('cycle_id')}.docx"
        result["surface_b_docx"] = str(export_surface_b_docx(snapshot, docx_path))
        runtime.runtime["cognitive"]["last_surface_b_docx"] = result["surface_b_docx"]
        runtime._write_runtime()
        runtime._event("SURFACE_B_SNAPSHOT", cycle.get("cycle_id"), {"path": result["surface_b_docx"], "json_path": json_path})
    return result
