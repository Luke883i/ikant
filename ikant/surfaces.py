from __future__ import annotations
import html, json, re, zipfile
from pathlib import Path
from .model import CONCENTRIC_ORDER
from .neurofunctional import manifest as neuro_manifest, coupling_manifest, neuroscience_coverage_manifest

_WORD_RE = re.compile(r"\b[\w'’]+\b", re.UNICODE)
_LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


def build_surface_a_contract(cognitive_turn: dict) -> dict:
    cycle = cognitive_turn["cycle"]
    crc = cognitive_turn["crc"]
    proto = cognitive_turn["proto_self"]
    central = cognitive_turn["central_oracle"]
    sem = cycle.get("semantic_slice", {})
    by_id = {r["id"]: r for r in sem.get("nodes", [])}
    projection = cognitive_turn.get("central_projection") or cycle.get("output_projection", {})
    assertable = [by_id[x]["text"] for x in projection.get("assertable_node_ids", []) if x in by_id and by_id[x].get("kind") != "intention"]
    tentative = [by_id[x]["text"] for x in projection.get("tentative_node_ids", []) if x in by_id and by_id[x].get("kind") != "intention"]
    interpretive = [by_id[x]["text"] for x in projection.get("interpretive_hypothesis_node_ids", []) if x in by_id]
    conflicts = projection.get("must_surface_conflicts", [])
    mode = central.get("regulative_mode", "REFLECTIVE_SYNTHESIS")
    base_caution = float(cycle.get("output_policy", {}).get("epistemic_caution", 0.0))
    critique = float(central.get("critique_pressure", 0.0))
    caution = max(base_caution, critique)
    target = 65 if caution < .30 else (105 if caution < .60 else 160)
    stance = "direct and settled" if caution < .30 else ("careful and plain" if caution < .60 else "cautious and explicit about uncertainty")
    return {
        "schema": "ikant-surface-a-contract/v0.2",
        "format": {
            "min_words": 5,
            "max_words": 500,
            "target_words": target,
            "max_paragraphs": 4,
            "preferred_paragraphs": 1 if target <= 105 else 2,
            "headings": False,
            "lists": False,
            "tables": False,
            "code_blocks": False,
            "style": "simple natural colloquial humanistic-formal prose",
            "stance": stance,
            "avoid_meta_language": True,
            "language": "match the human user's language",
        },
        "content": {
            "assertable": assertable[:8],
            "tentative": tentative[:6],
            "interpretive_hypotheses": interpretive[:2],
            "interpretive_macro_candidates": projection.get("interpretive_macro_candidates", [])[:2],
            "conflicts": conflicts[:4],
            "authorized_directives": projection.get("authorized_directives", [])[:4],
            "central_dispositions": central.get("dispositions", [])[:4],
        },
        "regulation": {
            "mode": mode,
            "epistemic_caution": round(caution, 6),
            "base_epistemic_caution": round(base_caution, 6),
            "central_critique_pressure": round(critique, 6),
            "crc_basic": crc.get("roa_alignment", {}).get("crc_basic", False),
            "horizon_exceeded": crc.get("horizon_exceeded", False),
            "proto_self_index": proto.get("proto_self_index", 0.0),
            "must_abstain_or_review": mode in {"HORIZON_BLOCK", "PRACTICAL_BLOCK", "PRACTICAL_REVIEW"} or crc.get("horizon_exceeded", False),
            "derived_history_is_not_external_evidence": True,
            "post_crc_downgrade_count": len(projection.get("downgrades", [])),
            "material_action": projection.get("material_action", cycle.get("output_policy", {}).get("material_action")),
        },
        "host_instruction": "Write only the natural-language reply. Use ordinary sentences, no headings, bullets, numbered lists, tables or code blocks. Do not mention the internal machinery unless the human asks. Let certainty, brevity, conflict surfacing and action restraint follow the central regulative state. Draft, validate with validate_surface_a, repair until valid, record the validated speech act with emit-surface-a/record_surface_a, then send it.",
    }


def validate_surface_a(text: str) -> tuple[bool, list[str]]:
    errors = []
    words = _WORD_RE.findall(text)
    if not 5 <= len(words) <= 500:
        errors.append(f"word count {len(words)} outside 5..500")
    lines = text.splitlines()
    if any(line.lstrip().startswith("#") for line in lines):
        errors.append("headings forbidden")
    if any(_LIST_RE.match(line) for line in lines):
        errors.append("lists forbidden")
    if any("|" in line and line.count("|") >= 2 for line in lines):
        errors.append("tables forbidden")
    if "```" in text:
        errors.append("code blocks forbidden")
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if len(paragraphs) > 4:
        errors.append("too many paragraphs")
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if any(len(_WORD_RE.findall(s)) > 55 for s in sentences):
        errors.append("sentence too long for simple conversational surface")
    return not errors, errors


def build_surface_b_snapshot(cognitive_turn: dict) -> dict:
    cycle = cognitive_turn["cycle"]
    crc = cognitive_turn["crc"]
    central = cognitive_turn.get("central_oracle", {})
    backlog = []
    debt = crc.get("diagnostics", {}).get("epistemic_debt_open_count", 0)
    conflicts = cycle.get("output_projection", {}).get("must_surface_conflicts", [])
    if crc.get("horizon_exceeded"): backlog.append("Resolve the epistemic-horizon mismatch before treating the turn as closed.")
    if debt: backlog.append(f"Discharge {debt} open epistemic-debt macrostate(s) with attributable evidence or retraction.")
    if conflicts: backlog.append(f"Resolve or explicitly preserve {len(conflicts)} surfaced conflict(s).")
    if central.get("regulative_mode") in {"PRACTICAL_BLOCK", "PRACTICAL_REVIEW"}: backlog.append("Obtain the required human practical review before material action.")
    backlog.extend(central.get("dispositions", [])[:4])
    return {
        "schema": "ikant-surface-b-snapshot/v0.2",
        "cycle_id": cycle.get("cycle_id"),
        "session_id": cognitive_turn.get("session_id"),
        "intent_sha256": cycle.get("semantic_slice", {}).get("intent_sha256"),
        "reticulum": {
            "rings": [r.value for r in CONCENTRIC_ORDER],
            "neurofunctional_clusters": neuro_manifest(),
            "functional_couplings": coupling_manifest(),
            "neuroscience_coverage": neuroscience_coverage_manifest(),
            "neurofunctional_state": crc.get("neurofunctional_state", {}),
            "levels": crc.get("levels", []),
            "transmissions": crc.get("transmissions", []),
            "ring_states": crc.get("ring_states", {}),
            "diagnostics": crc.get("diagnostics", {}),
            "roa_alignment": crc.get("roa_alignment", {}),
            "horizon": crc.get("horizon", {}),
        },
        "dynamic_state": {
            "proto_self": cognitive_turn.get("proto_self", {}),
            "central_oracle": cognitive_turn.get("central_oracle", {}),
            "central_projection": cognitive_turn.get("central_projection", {}),
            "workspace": cognitive_turn.get("workspace", {}),
            "intention_node_id": cognitive_turn.get("intention_node_id"),
            "mined_atoms": cognitive_turn.get("mined_atoms", []),
            "output_policy": cycle.get("output_policy", {}),
            "surface_a_contract": cognitive_turn.get("surface_a_contract", {}),
            "runtime_backlog": list(dict.fromkeys(backlog)),
        },
        "audit": {
            "recent_events": cognitive_turn.get("recent_events", [])[-40:],
            "compression": cognitive_turn.get("compression", {}),
            "model_boundary": {
                "brain_simulation": False,
                "consciousness_claim": False,
                "functional_proto_self": True,
                "freud_jung_are_bounded_hypotheses": True,
                "kant_is_synthetic_regulative_kernel": True,
            },
        },
    }


_RING_LABELS = {
    "signal": "R0 signal",
    "salience_homeostasis": "R1 salience",
    "memory": "R2 memory",
    "predictive_control": "R3 control",
    "metacognition": "R4 metacognition",
    "reflective_self": "R5 reflective self",
    "psychodynamic_hypothesis": "R6 psychodynamic",
    "archetypal_hypothesis": "R7 archetypal",
    "kant_oracle": "R8 iKant oracle",
}
_STATUS_LABELS = {
    "functional_analogue_not_region_simulation": "functional analogue",
    "interpretive_hypothesis_namespace": "interpretive hypothesis",
    "synthetic_normative_kernel": "synthetic normative kernel",
    "functional_analogue_not_connectome_claim": "functional coupling",
}

def _display_ring(value: object) -> str:
    return _RING_LABELS.get(str(value), str(value).replace("_", " "))

def _display_status(value: object) -> str:
    return _STATUS_LABELS.get(str(value), str(value).replace("_", " "))

def _pretty(value: object) -> str:
    return str(value).replace("_", " ")


def _xml_text(text: object) -> str:
    return html.escape(str(text), quote=False)


def _p(text: object, *, style: str | None = None) -> str:
    ppr = f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""
    return f"<w:p>{ppr}<w:r><w:t xml:space=\"preserve\">{_xml_text(text)}</w:t></w:r></w:p>"


def _table(rows: list[list[object]], widths: list[int] | None = None) -> str:
    if not rows:
        return ""
    widths = widths or [3000] * len(rows[0])
    grid = "".join(f"<w:gridCol w:w=\"{w}\"/>" for w in widths)
    out = ["<w:tbl><w:tblPr><w:tblStyle w:val=\"TableGrid\"/><w:tblW w:w=\"0\" w:type=\"auto\"/></w:tblPr><w:tblGrid>", grid, "</w:tblGrid>"]
    for ridx, row in enumerate(rows):
        out.append("<w:tr>")
        for i, cell in enumerate(row):
            style = "TableHead" if ridx == 0 else "TableText"
            out.append(f"<w:tc><w:tcPr><w:tcW w:w=\"{widths[min(i,len(widths)-1)]}\" w:type=\"dxa\"/></w:tcPr>{_p(cell, style=style)}</w:tc>")
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def export_surface_b_docx(snapshot: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = []
    body += [_p("iKant CRC Runtime Snapshot", style="Title"), _p(f"Cycle {snapshot.get('cycle_id')} | Session {snapshot.get('session_id')}")]
    body += [_p("Purpose", style="Heading1"), _p("This document is the auditable Surface B photograph of one cognitive iteration. It records externalized CRC state and telemetry; it is not a private chain-of-thought transcript and it is not evidence of biological consciousness.")]

    ret = snapshot["reticulum"]
    body += [_p("Concentric reticulum", style="Heading1")]
    body.append(_table([["Ring", "Functional analogue", "Scientific status", "Runtime role"]] + [
        [_display_ring(c["ring"]), c["label"], _display_status(c["scientific_status"]), c["runtime_role"]] for c in ret["neurofunctional_clusters"]
    ], [1500, 2100, 1800, 4200]))
    body += [_p("Neurofunctional anchors and recurrent couplings", style="Heading1")]
    anchor_rows = [["Ring", "Functional anatomical/network anchors", "Evidence anchors"]]
    for c in ret["neurofunctional_clusters"]:
        anchor_rows.append([_display_ring(c["ring"]), ", ".join(c.get("anatomical_anchors", [])) or "none by design", ", ".join(c.get("evidence_anchors", [])) or "interpretive/normative; no anatomical claim"])
    body.append(_table(anchor_rows, [1700, 4700, 2200]))
    coupling_rows = [["Coupling", "Type", "Runtime effect"]]
    for c in ret.get("functional_couplings", []):
        coupling_rows.append([f"{_display_ring(c['source'])} → {_display_ring(c['target'])}", _pretty(c["kind"]), c["runtime_effect"]])
    body.append(_table(coupling_rows, [2800, 2000, 3800]))

    body += [_p("Neuroscience coverage horizon", style="Heading1")]
    cov=ret.get("neuroscience_coverage", [])
    body.append(_table([["Domain","Status","Runtime binding"]]+[[_pretty(x.get("domain")),_pretty(x.get("status")),x.get("runtime_binding")] for x in cov],[2600,1900,4100]))

    body += [_p("Dynamic neurofunctional control state", style="Heading1")]
    nf_state=ret.get("neurofunctional_state", {})
    if nf_state:
        body.append(_table([["Ring","Gain","Precision","Inhibition","Plasticity","Persistence","Control"]] + [[_display_ring(r),v.get("gain"),v.get("precision"),v.get("inhibition"),v.get("plasticity"),v.get("persistence"),v.get("control_index")] for r,v in nf_state.items()], [1900,950,950,950,950,950,950]))
    else:
        body.append(_p("No dynamic neurofunctional state was supplied."))

    body += [_p("CRC telemetry", style="Heading1")]
    roa = ret.get("roa_alignment", {}); diag = ret.get("diagnostics", {})
    body.append(_table([
        ["IOA", roa.get("ioa")], ["Epistemic closure", roa.get("epistemic_closure")], ["TC witness", roa.get("turing_computability_witness")],
        ["CRC-basic", roa.get("crc_basic")], ["CRC-strong candidate", roa.get("crc_strong_candidate")],
        ["Mean collapse coefficient", diag.get("mean_coefficient_of_collapse")], ["Emergence index proxy", diag.get("emergence_index_proxy")],
        ["Reticular irreducibility proxy", diag.get("reticular_irreducibility_proxy")], ["Functional coherence", diag.get("functional_coherence")],
        ["Reentrant capacity", diag.get("reentrant_capacity")], ["Open epistemic debt states", diag.get("epistemic_debt_open_count")],
    ], [3000, 5600]))

    body += [_p("Ring-by-ring transmission", style="Heading1")]
    tx_rows = [["Transmission", "Inputs", "Outputs", "Collapse", "Introduced properties"]]
    for t in ret.get("transmissions", []):
        tx_rows.append([f"{_display_ring(t['source'])} → {_display_ring(t['target'])}", t["input_count"], t["output_count"], t["coefficient_of_collapse"], ", ".join(_pretty(x) for x in t.get("introduced_properties", []))])
    body.append(_table(tx_rows, [2400, 900, 900, 1100, 4300]))

    body += [_p("Dynamic proto-self and central oracle", style="Heading1")]
    dyn = snapshot["dynamic_state"]; proto = dyn.get("proto_self", {}); central = dyn.get("central_oracle", {})
    body.append(_table([
        ["Proto-self index", proto.get("proto_self_index")], ["Integration mode", proto.get("integration_mode")], ["Global availability", proto.get("global_availability")],
        ["Cross-ring integration", proto.get("cross_ring_integration")], ["Temporal continuity", proto.get("temporal_continuity")],
        ["Metacognitive access", proto.get("metacognitive_access")], ["Self-model continuity", proto.get("self_model_continuity")],
        ["Agency binding", proto.get("agency_binding")], ["Neurofunctional coherence", proto.get("neurofunctional_coherence")],
        ["Reentrant capacity", proto.get("reentrant_capacity")], ["Central mode", central.get("regulative_mode")],
        ["Central unity", central.get("unity_index")], ["Apperception proxy", central.get("transcendental_apperception_proxy")], ["Central critique pressure", central.get("critique_pressure")],
    ], [3200, 5400]))

    body += [_p("Workspace action and retroaction", style="Heading1")]
    ws = dyn.get("workspace", {})
    body.append(_p(f"Broadcast mode: {ws.get('regulative_mode')}; boosts: {len(ws.get('activation_boosts', []))}; interpretive inhibition: {ws.get('interpretive_inhibition')}; evidence modified: {ws.get('evidence_modified')}"))
    if ws.get("activation_boosts"):
        body.append(_table([["Node", "Activation delta", "Reason"]] + [[b["node_id"], b["activation_delta"], b["reason"]] for b in ws["activation_boosts"][:12]], [3100, 1600, 3900]))

    body += [_p("Post-CRC response projection", style="Heading1")]
    cp=dyn.get("central_projection", {})
    body.append(_table([["Mode",cp.get("mode")],["Assertable nodes",len(cp.get("assertable_node_ids",[]))],["Tentative nodes",len(cp.get("tentative_node_ids",[]))],["Downgrades",len(cp.get("downgrades",[]))],["Material action",cp.get("material_action")],["Post-CRC",cp.get("projection_is_post_crc")]], [3000,5600]))
    if cp.get("downgrades"):
        body.append(_table([["Node","Downgrade reason"]]+[[x.get("node_id"),_pretty(x.get("reason"))] for x in cp.get("downgrades",[])[:12]],[3200,5400]))

    body += [_p("Surface A contract", style="Heading1")]
    contract = dyn.get("surface_a_contract", {})
    body.append(_p(json.dumps(contract.get("regulation", {}), ensure_ascii=False, sort_keys=True)))
    body.append(_p("Surface A must be 5 to 500 words of simple natural prose with no headings, lists, tables or code blocks. The host must use assertable/tentative/conflict partitions and the central regulative state when writing the conversational reply."))

    body += [_p("Surface A emission", style="Heading1")]
    emission=dyn.get("surface_a_emission")
    if emission:
        body.append(_table([["Validated",emission.get("validated")],["Response node",emission.get("response_id")],["Word count",emission.get("word_count")],["Evidence",emission.get("evidence")]], [3000,5600]))
        body.append(_p(emission.get("text","")))
    else:
        body.append(_p("Surface A had not yet been emitted when this snapshot was taken."))

    body += [_p("Runtime convergence backlog", style="Heading1")]
    backlog = dyn.get("runtime_backlog", [])
    if backlog:
        for i, item in enumerate(backlog, 1): body.append(_p(f"{i}. {item}"))
    else:
        body.append(_p("No unresolved convergence item was generated for this iteration."))

    body += [_p("Recent persistent events", style="Heading1")]
    events = snapshot.get("audit", {}).get("recent_events", [])
    if events:
        body.append(_table([["Seq", "Operation", "Subject"]] + [[e.get("seq"), e.get("op"), e.get("subject")] for e in events[-30:]], [900, 2300, 5400]))
    else:
        body.append(_p("No event records were supplied to this snapshot."))

    body += [_p("Boundary", style="Heading1"), _p("The neurofunctional mapping is a falsifiable software analogy constrained by neuroscience. Psychodynamic and archetypal rings are interpretive namespaces without anatomical localization. The Kant oracle is a synthetic normative kernel. The proto-self index measures functional integration of the local runtime; it is not a probability or proof of consciousness.")]

    sect = '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="850" w:bottom="1134" w:left="850"/></w:sectPr>'
    document = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + "".join(body) + sect + '</w:body></w:document>'
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="19"/></w:rPr><w:pPr><w:spacing w:after="100"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="34"/></w:rPr><w:pPr><w:spacing w:after="220"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="25"/></w:rPr><w:pPr><w:spacing w:before="220" w:after="100"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:rPr><w:sz w:val="16"/></w:rPr><w:pPr><w:spacing w:after="0"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="TableHead"><w:name w:val="Table Head"/><w:basedOn w:val="TableText"/><w:rPr><w:b/><w:sz w:val="16"/></w:rPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/><w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/><w:insideH w:val="single" w:sz="4"/><w:insideV w:val="single" w:sz="4"/></w:tblBorders></w:tblPr></w:style>
</w:styles>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    docrels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", docrels)
    return path
