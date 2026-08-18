from __future__ import annotations
from .model import clamp01


def converge_kant_oracle(base_oracle: dict, crc: dict, proto_self: dict) -> dict:
    base_state = base_oracle.get("self_state", {})
    base_unity = float(base_state.get("unity_index", 0.0))
    base_critique = float(base_state.get("critique_pressure", 0.0))
    closure = crc.get("roa_alignment", {})
    diag = crc.get("diagnostics", {})
    crc_basic = bool(closure.get("crc_basic"))
    horizon_exceeded = bool(crc.get("horizon_exceeded"))
    debt = clamp01(diag.get("epistemic_debt_open_count", 0) / 4)
    collapse = clamp01(diag.get("mean_coefficient_of_collapse", 0.0))
    integration = clamp01(proto_self.get("cross_ring_integration", 0.0))
    continuity = clamp01(proto_self.get("temporal_continuity", 0.0))
    meta = clamp01(proto_self.get("metacognitive_access", 0.0))
    functional_self = clamp01(proto_self.get("proto_self_index", 0.0))
    functional_coherence = clamp01(diag.get("functional_coherence", 0.0))
    reentrant_capacity = clamp01(diag.get("reentrant_capacity", 0.0))
    interpretive_pressure = max(clamp01(diag.get("psychodynamic_interpretive_pressure",0.0)),clamp01(diag.get("archetypal_interpretive_pressure",0.0)))

    closure_factor = 1.0 if crc_basic else .35
    unity = clamp01(.36 * base_unity + .16 * integration + .12 * continuity + .10 * meta + .12 * functional_coherence + .06 * reentrant_capacity + .08 * closure_factor)
    critique = clamp01(.42 * base_critique + .18 * debt + .13 * collapse + .15 * (1 - closure_factor) + .08 * (1-functional_coherence) + .04 * interpretive_pressure)

    apperception=clamp01(.34*functional_self+.24*integration+.18*continuity+.14*meta+.10*functional_coherence)

    if horizon_exceeded or not crc_basic:
        mode = "HORIZON_BLOCK"
    elif any(f.get("status") == "BLOCK" for f in base_oracle.get("findings", [])):
        mode = "PRACTICAL_BLOCK"
    elif critique >= .58:
        mode = "CRITIQUE"
    elif unity < .56 or functional_self < .42:
        mode = "SYNTHESIS_REPAIR"
    elif base_state.get("regulative_mode") == "PRACTICAL_REVIEW":
        mode = "PRACTICAL_REVIEW"
    else:
        mode = "REFLECTIVE_SYNTHESIS"

    dispositions = list(base_oracle.get("dispositions", []))
    if debt > .25: dispositions.append("Keep unsupported abstractions tentative and discharge epistemic debt before reuse.")
    if collapse > .70: dispositions.append("Compression is aggressive; surface lost distinctions that could change the answer.")
    if functional_self < .42: dispositions.append("Prefer reconstruction from grounded state over narrative continuity.")
    if horizon_exceeded: dispositions.append("The current question exceeds the declared epistemic horizon; abstain or request admissible evidence/scope.")
    return {
        "schema": "ikant-central-oracle/v0.2",
        "archetype": "synthetic_kant_regulative_oracle",
        "regulative_mode": mode,
        "unity_index": round(unity, 6),
        "critique_pressure": round(critique, 6),
        "functional_proto_self_index": round(functional_self, 6),
        "transcendental_apperception_proxy": round(apperception, 6),
        "integrated_faculties": {
            "sensibility_grounding": base_oracle.get("faculties",{}).get("sensibility_grounding",0.0),
            "understanding_coherence": base_oracle.get("faculties",{}).get("understanding_coherence",0.0),
            "reflective_judgment": base_oracle.get("faculties",{}).get("reflective_judgment",0.0),
            "reason_discipline": base_oracle.get("faculties",{}).get("reason_discipline",0.0),
            "practical_reason_grounding": base_oracle.get("faculties",{}).get("practical_reason_grounding",0.0),
            "transcendental_apperception_proxy": round(apperception,6),
        },
        "crc_basic": crc_basic,
        "crc_strong_candidate": bool(closure.get("crc_strong_candidate")),
        "horizon_exceeded": horizon_exceeded,
        "mean_collapse": round(collapse, 6),
        "epistemic_debt_pressure": round(debt, 6),
        "neurofunctional_coherence": round(functional_coherence, 6),
        "reentrant_capacity": round(reentrant_capacity, 6),
        "bounded_interpretive_pressure": round(interpretive_pressure, 6),
        "base_oracle": base_oracle,
        "dispositions": list(dict.fromkeys(dispositions)),
        "authority": {
            "may_shape_surface_a": True,
            "may_drive_activation_retroaction": True,
            "may_create_external_evidence": False,
            "may_self_authorize_material_action": False,
        },
        "claim_boundary": "Functional regulative integration and apperception proxies, not consciousness, a soul, moral agency or a historical reconstruction of Kant's mind.",
    }


def project_surface_content(cycle: dict, crc: dict, central: dict) -> dict:
    """Compile the post-CRC content partition consumed by Surface A."""
    sem=cycle.get('semantic_slice',{});by={r.get('id'):r for r in sem.get('nodes',[])};legacy=cycle.get('output_projection',{})
    debt=set();revision=set()
    for state in crc.get('ring_states',{}).get('metacognition',[]):
        props=state.get('properties',{})
        if props.get('epistemic_debt_open'):debt.update(state.get('support_ids',[]))
        if props.get('monitor_state')=='revision_required':revision.update(state.get('support_ids',[]))
    mode=central.get('regulative_mode','REFLECTIVE_SYNTHESIS');blocked=mode in {'HORIZON_BLOCK','PRACTICAL_BLOCK'}
    action_kinds={'action','goal','constraint','prediction'};assertable=[];tentative=[];downgrades=[]
    threshold=float(cycle.get('output_policy',{}).get('claim_threshold',.5))
    for nid in legacy.get('assertable_node_ids',[]):
        row=by.get(nid)
        if not row or row.get('kind') in {'intention','response'}:continue
        reason=None
        if nid in debt:reason='epistemic_debt'
        elif nid in revision:reason='revision_required'
        elif blocked and row.get('kind') in action_kinds:reason='central_material_block'
        elif float(row.get('epistemic_score',0))<threshold:reason='post_crc_threshold'
        if reason:tentative.append(nid);downgrades.append({'node_id':nid,'reason':reason})
        else:assertable.append(nid)
    for nid in legacy.get('tentative_node_ids',[]):
        row=by.get(nid)
        if row and row.get('kind') not in {'intention','response'} and nid not in assertable and nid not in tentative:tentative.append(nid)
    # Strong central critique can only downgrade, never upgrade unsupported content.
    if mode in {'CRITIQUE','SYNTHESIS_REPAIR'}:
        for nid in list(assertable):
            row=by[nid]
            if float(row.get('epistemic_score',0))<min(.75,threshold+.12):
                assertable.remove(nid);tentative.append(nid);downgrades.append({'node_id':nid,'reason':'central_critique'})
    interp=[nid for nid in legacy.get('interpretive_hypothesis_node_ids',[]) if nid in by and by[nid].get('kind') not in {'intention','response'}]
    budget=0 if mode in {'HORIZON_BLOCK','PRACTICAL_BLOCK'} else (1 if float(central.get('critique_pressure',0))>=.5 else 2)
    interp=interp[:budget]
    macro=[]
    for ring,key in [('psychodynamic_hypothesis','freudian_structural_hypothesis'),('archetypal_hypothesis','jungian_archetype_candidate')]:
        for state in crc.get('ring_states',{}).get(ring,[]):
            value=state.get('properties',{}).get(key)
            if value and value not in {'none','no_structural_candidate'}:macro.append({'ring':ring,'type':key,'value':value,'support_ids':state.get('support_ids',[]),'authority':'interpretive_only'})
    return {
        'schema':'ikant-central-surface-projection/v0.2','mode':mode,'assertable_node_ids':assertable,'tentative_node_ids':tentative,
        'interpretive_hypothesis_node_ids':interp,'interpretive_macro_candidates':macro[:4],
        'authorized_directives':legacy.get('authorized_directives',[]) if not blocked else [],'withheld_directives':legacy.get('authorized_directives',[]) if blocked else [],
        'must_surface_conflicts':legacy.get('must_surface_conflicts',[]),'downgrades':downgrades,
        'material_action':'BLOCK' if blocked else cycle.get('output_policy',{}).get('material_action','PROPOSE_ONLY'),
        'projection_is_post_crc':True,
    }
