from __future__ import annotations
import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Iterable
from .model import Layer, NodeKind, CONCENTRIC_ORDER, clamp01
from .neurofunctional import derive_cluster_control, functional_state_summary

RING_INDEX = {r: i for i, r in enumerate(CONCENTRIC_ORDER)}
SUPPORTED_SOURCE_MODES = {"user", "repository", "document", "live", "cache", "demo", "inference", "runtime_derived"}
SUPPORTED_ANSWER_TYPES = {"assertable", "tentative", "abstain", "human_review", "proposal"}

@dataclass(frozen=True)
class EpistemicHorizon:
    id: str = "H-DEFAULT-V02"
    allowed_source_modes: tuple[str, ...] = tuple(sorted(SUPPORTED_SOURCE_MODES))
    allowed_answer_types: tuple[str, ...] = tuple(sorted(SUPPORTED_ANSWER_TYPES))
    required_answer_type: str = "proposal"
    max_ring: str = Layer.KANT_ORACLE.value
    material_action_requires_human: bool = True
    description: str = "Local conversational reasoning under attributable sources, bounded abstraction and human-controlled material action."

    def validate(self) -> list[str]:
        errors = []
        if self.required_answer_type not in self.allowed_answer_types:
            errors.append("required answer type outside horizon")
        if self.max_ring not in {r.value for r in CONCENTRIC_ORDER}:
            errors.append("max_ring outside reticulum")
        if not set(self.allowed_source_modes) <= SUPPORTED_SOURCE_MODES:
            errors.append("unsupported source mode declared by horizon")
        return errors

@dataclass(frozen=True)
class LevelSpec:
    ring: Layer
    state_space: str
    rule_set: tuple[str, ...]
    turing_like_formalism: bool = False

@dataclass(frozen=True)
class TransmissionSpec:
    source: Layer
    target: Layer
    mode: str
    rule_id: str
    introduced_properties: tuple[str, ...]

@dataclass
class MacroState:
    id: str
    ring: Layer
    bucket: str
    support_ids: list[str]
    input_count: int
    mean_epistemic: float
    mean_activation: float
    mean_stability: float
    mean_novelty: float
    mean_prediction_error: float
    source_modes: list[str]
    node_kinds: list[str]
    lexical_signature: list[str]
    properties: dict = field(default_factory=dict)

    def record(self) -> dict:
        d = asdict(self)
        d["ring"] = self.ring.value
        return d

LEVELS = (
    LevelSpec(Layer.SIGNAL, "attributable observations and feature-bearing claims", ("source attribution", "evidence boundary", "feature extraction")),
    LevelSpec(Layer.SALIENCE_HOMEOSTASIS, "bounded availability states", ("salience allocation", "gain modulation", "homeostatic normalization")),
    LevelSpec(Layer.MEMORY, "retrievable temporal traces", ("recurrence", "retrieval", "consolidation", "revision")),
    LevelSpec(Layer.PREDICTIVE_CONTROL, "goals, predictions, constraints and candidate actions", ("authorization", "prediction", "selection", "inhibition"), True),
    LevelSpec(Layer.METACOGNITION, "confidence, conflict, calibration and horizon state", ("uncertainty monitoring", "conflict preservation", "debt accounting")),
    LevelSpec(Layer.REFLECTIVE_SELF, "temporally linked commitments and agency states", ("self-continuity", "agency binding", "social context")),
    LevelSpec(Layer.PSYCHODYNAMIC_HYPOTHESIS, "low-authority conflict/tension hypotheses", ("tension detection", "counterevidence requirement")),
    LevelSpec(Layer.ARCHETYPAL_HYPOTHESIS, "low-authority recurring symbolic compression", ("recurrence compression", "symbolic label bounding")),
    LevelSpec(Layer.KANT_ORACLE, "regulative judgments and action constraints", ("grounding", "non-contradiction", "judgment", "autonomy", "persons-as-ends")),
)

TRANSMISSIONS = tuple(
    TransmissionSpec(
        CONCENTRIC_ORDER[i], CONCENTRIC_ORDER[i + 1], "non_injective_coarse_graining",
        f"tau-{CONCENTRIC_ORDER[i].value}-to-{CONCENTRIC_ORDER[i+1].value}-v02",
        {
            Layer.SALIENCE_HOMEOSTASIS: ("priority_class",),
            Layer.MEMORY: ("consolidation_class",),
            Layer.PREDICTIVE_CONTROL: ("control_role",),
            Layer.METACOGNITION: ("monitor_state", "epistemic_debt_open"),
            Layer.REFLECTIVE_SELF: ("self_relation",),
            Layer.PSYCHODYNAMIC_HYPOTHESIS: ("tension_pressure", "freudian_structural_hypothesis"),
            Layer.ARCHETYPAL_HYPOTHESIS: ("recurring_motif_pressure", "jungian_archetype_candidate"),
            Layer.KANT_ORACLE: ("regulative_context", "synthetic_kant_archetype_state"),
        }[CONCENTRIC_ORDER[i + 1]],
    )
    for i in range(len(CONCENTRIC_ORDER) - 1)
)


def _tokens(text: str) -> list[str]:
    clean = "".join(c.casefold() if c.isalnum() else " " for c in text)
    return [x for x in clean.split() if len(x) > 3]


def _mean(items: Iterable[float]) -> float:
    xs = list(items)
    return sum(xs) / len(xs) if xs else 0.0


def _frame_from_node(row: dict) -> dict:
    return {
        "support_ids": [row["id"]],
        "texts": [row.get("text", "")],
        "kinds": [row.get("kind", "claim")],
        "source_modes": [row.get("source_mode", "inference")],
        "epistemic": float(row.get("epistemic_score", 0.0)),
        "activation": float(row.get("activation", 0.0)),
        "stability": float(row.get("stability", 0.0)),
        "novelty": float(row.get("novelty", 0.0)),
        "prediction_error": float(row.get("prediction_error", 0.0)),
        "properties": {},
        "modulators": dict(row.get("modulators") or {}),
    }


def _frame_from_macro(m: MacroState) -> dict:
    return {
        "support_ids": list(m.support_ids),
        "texts": list(m.lexical_signature),
        "kinds": list(m.node_kinds),
        "source_modes": list(m.source_modes),
        "epistemic": m.mean_epistemic,
        "activation": m.mean_activation,
        "stability": m.mean_stability,
        "novelty": m.mean_novelty,
        "prediction_error": m.mean_prediction_error,
        "properties": dict(m.properties),
        "modulators": {},
    }


def _bucket(target: Layer, f: dict, control: dict | None = None) -> tuple[str, dict]:
    epi = f["epistemic"]; act = f["activation"]; stab = f["stability"]; nov = f["novelty"]; pe = f["prediction_error"]
    kinds = set(f["kinds"]); props = {}; control = control or {}
    gain=float(control.get("gain",.5)); inhibition=float(control.get("inhibition",.25)); plasticity=float(control.get("plasticity",.5)); persistence=float(control.get("persistence",.5)); precision=float(control.get("precision",.5))
    if target == Layer.SALIENCE_HOMEOSTASIS:
        threshold = .42 + .08*inhibition - .06*gain
        priority = "foreground" if (.55 * epi + .30 * act + .15 * pe) >= threshold else "background"
        props["functional_threshold"] = round(threshold,6)
        props["priority_class"] = priority
        return priority, props
    if target == Layer.MEMORY:
        consolidation_threshold = .49 - .10*persistence
        labile_threshold = .40 - .08*plasticity
        cls = "consolidated" if stab >= consolidation_threshold and nov <= .55 else ("labile" if pe >= labile_threshold else "recent")
        props.update({"consolidation_threshold":round(consolidation_threshold,6),"labile_threshold":round(labile_threshold,6)})
        props["consolidation_class"] = cls
        return cls, props
    if target == Layer.PREDICTIVE_CONTROL:
        if kinds & {NodeKind.GOAL.value, NodeKind.CONSTRAINT.value}: role = "directive"
        elif NodeKind.INTENTION.value in kinds: role = "expressed_intention"
        elif kinds & {NodeKind.ACTION.value, NodeKind.PREDICTION.value}: role = "inhibited_prospective" if inhibition >= .58 else "prospective"
        else: role = "world_model"
        props["control_role"] = role
        return role, props
    if target == Layer.METACOGNITION:
        revision_threshold = .52 - .18*max(precision,gain)
        if NodeKind.CONFLICT.value in kinds or pe >= revision_threshold: state = "revision_required"
        elif epi < .35: state = "uncertain"
        else: state = "coherent"
        debt = all(s in {"inference", "runtime_derived", "demo", "cache"} for s in f["source_modes"])
        props.update({"monitor_state": state, "epistemic_debt_open": debt, "revision_threshold":round(revision_threshold,6)})
        return f"{state}:{'debt' if debt else 'grounded'}", props
    if target == Layer.REFLECTIVE_SELF:
        if kinds & {NodeKind.SELF_MODEL.value}: relation = "explicit_self"
        elif kinds & {NodeKind.GOAL.value, NodeKind.ACTION.value}: relation = "agentic_commitment"
        else: relation = "world_in_context"
        props["self_relation"] = relation
        return relation, props
    if target == Layer.PSYCHODYNAMIC_HYPOTHESIS:
        pressure = "elevated" if inhibition < .72 and (NodeKind.CONFLICT.value in kinds or pe >= .50) else "low"
        if pressure == "elevated" and kinds & {NodeKind.GOAL.value,NodeKind.ACTION.value,NodeKind.PREDICTION.value}: structural="drive_control_conflict"
        elif pressure == "elevated" and NodeKind.CONSTRAINT.value in kinds: structural="normative_constraint_pressure"
        elif pressure == "elevated": structural="unresolved_tension"
        elif kinds & {NodeKind.SELF_MODEL.value,NodeKind.GOAL.value,NodeKind.CONSTRAINT.value}: structural="ego_mediation_candidate"
        else: structural="no_structural_candidate"
        props.update({"tension_pressure":pressure,"freudian_structural_hypothesis":structural,"historical_model_status":"interpretive_not_neuroscientific"})
        return f"{pressure}:{structural}", props
    if target == Layer.ARCHETYPAL_HYPOTHESIS:
        recurring = "recurring" if inhibition < .68 and stab >= (.50-.08*persistence) and nov <= .35 else "non_recurring"
        lineage=f.get("properties",{}).get("property_lineage",{}) if isinstance(f.get("properties",{}),dict) else {}
        freud=str(f.get("properties",{}).get("freudian_structural_hypothesis",""))
        prior_self=set(lineage.get("self_relation",[]))
        if recurring != "recurring": candidate="none"
        elif freud in {"drive_control_conflict","unresolved_tension"}: candidate="shadow_candidate"
        elif "explicit_self" in prior_self or NodeKind.SELF_MODEL.value in kinds: candidate="self_candidate"
        elif kinds & {NodeKind.GOAL.value,NodeKind.ACTION.value}: candidate="hero_candidate"
        elif "world_in_context" in prior_self: candidate="persona_candidate"
        else: candidate="symbolic_recurrence_candidate"
        props.update({"recurring_motif_pressure":recurring,"jungian_archetype_candidate":candidate,"historical_model_status":"jung_inspired_interpretive_label"})
        return f"{recurring}:{candidate}", props
    if target == Layer.KANT_ORACLE:
        review_threshold=.38-.08*gain
        props["regulative_context"] = "review" if pe >= review_threshold or epi < (.44-.08*precision) else "synthesis"
        props["synthetic_kant_archetype_state"] = "critical_review" if props["regulative_context"]=="review" else "reflective_synthesis"
        props["review_threshold"] = round(review_threshold,6)
        return props["regulative_context"], props
    return "default", props


def _aggregate(ring: Layer, bucket: str, frames: list[dict], props: dict) -> MacroState:
    support = sorted({nid for f in frames for nid in f["support_ids"]})
    lineage = defaultdict(set)
    for f in frames:
        for k,v in (f.get("properties") or {}).items():
            if k == "property_lineage" and isinstance(v, dict):
                for lk,lv in v.items():
                    for item in (lv if isinstance(lv,list) else [lv]): lineage[lk].add(str(item))
            elif isinstance(v,(str,int,float,bool)):
                lineage[k].add(str(v))
    merged_props=dict(props)
    if lineage: merged_props["property_lineage"]={k:sorted(v) for k,v in sorted(lineage.items())}
    kinds = sorted({k for f in frames for k in f["kinds"]})
    sources = sorted({s for f in frames for s in f["source_modes"]})
    toks = Counter(t for f in frames for text in f["texts"] for t in _tokens(text))
    signature = [t for t, _ in sorted(toks.items(), key=lambda kv: (-kv[1], kv[0]))[:6]]
    digest = hashlib.sha256(f"{ring.value}|{bucket}|{'|'.join(support)}".encode()).hexdigest()[:16]
    return MacroState(
        id="M-" + digest,
        ring=ring,
        bucket=bucket,
        support_ids=support,
        input_count=len(frames),
        mean_epistemic=round(_mean(f["epistemic"] for f in frames), 6),
        mean_activation=round(_mean(f["activation"] for f in frames), 6),
        mean_stability=round(_mean(f["stability"] for f in frames), 6),
        mean_novelty=round(_mean(f["novelty"] for f in frames), 6),
        mean_prediction_error=round(_mean(f["prediction_error"] for f in frames), 6),
        source_modes=sources,
        node_kinds=kinds,
        lexical_signature=signature,
        properties=merged_props,
    )


def _compress(target: Layer, frames: list[dict], control: dict | None = None) -> list[MacroState]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    properties: dict[str, dict] = {}
    for f in frames:
        key, props = _bucket(target, f, control)
        grouped[key].append(f)
        properties[key] = props
    return [_aggregate(target, key, grouped[key], properties[key]) for key in sorted(grouped)]


def _collapse_coefficient(input_count: int, output_count: int) -> float:
    if input_count <= 0:
        return 0.0
    return round(clamp01(1.0 - output_count / input_count), 6)


def _row_validation_errors(row: object, *, horizon: EpistemicHorizon | None = None) -> list[str]:
    if not isinstance(row, dict):
        return ["row:not_object"]
    errors=[]
    rid=row.get("id")
    if not isinstance(rid,str) or not rid.strip(): errors.append("row:missing_id")
    try: Layer(row.get("layer"))
    except Exception: errors.append(f"unregistered ring:{row.get('layer')}")
    if row.get("kind") not in {k.value for k in NodeKind}: errors.append(f"unregistered kind:{row.get('kind')}")
    source=row.get("source_mode")
    if source not in SUPPORTED_SOURCE_MODES: errors.append(f"unregistered source:{source}")
    if horizon is not None and source in SUPPORTED_SOURCE_MODES and source not in set(horizon.allowed_source_modes): errors.append(f"source outside horizon:{source}")
    for key in ("epistemic_score","activation","stability","novelty","prediction_error"):
        try: value=float(row.get(key,0.0))
        except (TypeError,ValueError): errors.append(f"invalid numeric:{key}");continue
        if not math.isfinite(value) or not 0<=value<=1: errors.append(f"invalid numeric:{key}")
    return errors

def _native_rows(semantic_slice: dict, *, horizon: EpistemicHorizon | None = None) -> dict[Layer, list[dict]]:
    out = {r: [] for r in CONCENTRIC_ORDER}
    for row in semantic_slice.get("nodes", []):
        if _row_validation_errors(row,horizon=horizon): continue
        layer=Layer(row.get("layer"))
        if layer in out: out[layer].append(row)
    return out


def evaluate_reticulum(semantic_slice: dict, *, horizon: EpistemicHorizon | None = None, previous_neurofunctional_state: dict | None = None) -> dict:
    horizon = horizon or EpistemicHorizon()
    horizon_errors = horizon.validate()
    all_rows = semantic_slice.get("nodes", [])
    ioa_errors=[]; seen_ids={}
    for row in all_rows:
        ioa_errors.extend(_row_validation_errors(row,horizon=horizon))
        if isinstance(row,dict) and isinstance(row.get("id"),str) and row.get("id"):
            rid=row["id"]; signature=(row.get("layer"),row.get("kind"),row.get("source_mode"),row.get("text"))
            if rid in seen_ids and seen_ids[rid]!=signature: ioa_errors.append(f"divergent duplicate id:{rid}")
            seen_ids[rid]=signature
    native = _native_rows(semantic_slice,horizon=horizon)
    ring_states: dict[Layer, list[MacroState]] = {}
    transmissions = []
    carried: list[MacroState] = []
    native_seen: set[str] = set()
    previous_neurofunctional_state = previous_neurofunctional_state or {}
    neurofunctional_state: dict[str, dict] = {}

    for idx, ring in enumerate(CONCENTRIC_ORDER):
        frames = [_frame_from_macro(m) for m in carried]
        for row in native[ring]:
            native_seen.add(row["id"])
            frames.append(_frame_from_node(row))
        if idx == 0 and not frames:
            boundary = [r for r in semantic_slice.get("nodes", []) if isinstance(r,dict) and not _row_validation_errors(r,horizon=horizon) and r.get("source_mode") in {"user", "repository", "document", "live"} and r.get("kind") != NodeKind.PRINCIPLE.value]
            frames.extend(_frame_from_node(r) for r in boundary)
        control = derive_cluster_control(ring, frames, previous_neurofunctional_state.get(ring.value))
        neurofunctional_state[ring.value] = control
        if idx == 0:
            ring_states[ring] = [_aggregate(ring, "boundary", [f], {"functional_control_index":control["control_index"]}) for f in frames]
        else:
            source = CONCENTRIC_ORDER[idx - 1]
            outputs = _compress(ring, frames, control) if frames else []
            transmissions.append({
                "source": source.value,
                "target": ring.value,
                "rule_id": TRANSMISSIONS[idx - 1].rule_id,
                "mode": TRANSMISSIONS[idx - 1].mode,
                "input_count": len(frames),
                "output_count": len(outputs),
                "coefficient_of_collapse": _collapse_coefficient(len(frames), len(outputs)),
                "introduced_properties": list(TRANSMISSIONS[idx - 1].introduced_properties),
                "functional_control": {k:control[k] for k in ("cluster_id","gain","precision","inhibition","plasticity","persistence","control_index")},
            })
            ring_states[ring] = outputs
        carried = ring_states[ring]

    ioa_errors=sorted(set(ioa_errors))
    ioa = not ioa_errors
    horizon_source_errors=[e for e in ioa_errors if e.startswith("source outside horizon:")]
    valid_layer_indices=[]
    for row in all_rows:
        if not isinstance(row,dict): continue
        try: valid_layer_indices.append(RING_INDEX[Layer(row.get("layer"))])
        except Exception: continue
    max_allowed=RING_INDEX.get(Layer(horizon.max_ring),-1) if not horizon_errors else -1
    horizon_exceeded = bool(horizon_errors or horizon_source_errors) or (bool(valid_layer_indices) and max_allowed < max(valid_layer_indices))
    ec = not horizon_errors and not horizon_source_errors and horizon.required_answer_type in SUPPORTED_ANSWER_TYPES
    tc = len(TRANSMISSIONS) == len(CONCENTRIC_ORDER) - 1 and any(l.turing_like_formalism for l in LEVELS)

    introduced_total = 0; introduced_active = 0
    for t in transmissions:
        introduced_total += len(t["introduced_properties"])
        states = ring_states[Layer(t["target"])]
        for p in t["introduced_properties"]:
            if any(s.properties.get(p) not in (None, False, "low", "non_recurring") for s in states): introduced_active += 1
    ie_proxy = round(introduced_active / introduced_total, 6) if introduced_total else 0.0
    counts = [len(ring_states[r]) for r in CONCENTRIC_ORDER]
    total_vertices = sum(counts)
    intermediate = [c for c in counts[1:-1] if c > 0]
    min_cut_proxy = min(intermediate) if intermediate else 0
    rir_proxy = round(clamp01(1 - (min_cut_proxy / total_vertices if total_vertices else 0)), 6)
    collapse_mean = round(_mean(t["coefficient_of_collapse"] for t in transmissions), 6)
    functional_summary = functional_state_summary(neurofunctional_state)
    psych_states=ring_states.get(Layer.PSYCHODYNAMIC_HYPOTHESIS,[])
    arch_states=ring_states.get(Layer.ARCHETYPAL_HYPOTHESIS,[])
    psych_pressure=round(sum(1 for x in psych_states if x.properties.get("tension_pressure")=="elevated")/max(1,len(psych_states)),6)
    archetype_pressure=round(sum(1 for x in arch_states if x.properties.get("jungian_archetype_candidate") not in {None,"none"})/max(1,len(arch_states)),6)
    debt_states = [s.id for states in ring_states.values() for s in states if s.properties.get("epistemic_debt_open")]
    representational_path = bool(ring_states.get(Layer.SIGNAL)) and bool(ring_states.get(Layer.KANT_ORACLE))
    crc_basic = ioa and ec and tc and representational_path and not horizon_exceeded
    crc_strong_candidate = crc_basic and not debt_states and bool(ring_states[Layer.KANT_ORACLE])

    return {
        "schema": "ikant-crc-reticulum/v0.2",
        "roa_alignment": {
            "levels_are_state_rule_pairs": True,
            "transmissions_explicit": True,
            "epistemic_horizon_declared": True,
            "ioa": ioa,
            "epistemic_closure": ec,
            "turing_computability_witness": tc,
            "turing_like_level": Layer.PREDICTIVE_CONTROL.value,
            "representational_path_complete": representational_path,
            "crc_basic": crc_basic,
            "crc_strong_candidate": crc_strong_candidate,
            "claim_boundary": "Operational CRC witness, not proof of ontological closure or consciousness.",
        },
        "horizon": asdict(horizon),
        "horizon_exceeded": horizon_exceeded,
        "ioa_errors": sorted(set(ioa_errors)),
        "horizon_errors": horizon_errors,
        "levels": [{**asdict(l), "ring": l.ring.value, "rule_set": list(l.rule_set)} for l in LEVELS],
        "ring_states": {r.value: [s.record() for s in ring_states[r]] for r in CONCENTRIC_ORDER},
        "transmissions": transmissions,
        "neurofunctional_state": neurofunctional_state,
        "diagnostics": {
            "mean_coefficient_of_collapse": collapse_mean,
            "emergence_index_proxy": ie_proxy,
            "reticular_irreducibility_proxy": rir_proxy,
            "minimum_vertex_cut_proxy": min_cut_proxy,
            "causal_vertex_count": total_vertices,
            "epistemic_debt_open_count": len(debt_states),
            "epistemic_debt_state_ids": debt_states,
            "functional_coherence": functional_summary["functional_coherence"],
            "mean_functional_control_index": functional_summary["mean_control_index"],
            "reentrant_capacity": functional_summary["reentrant_capacity"],
            "psychodynamic_interpretive_pressure": psych_pressure,
            "archetypal_interpretive_pressure": archetype_pressure,
            "neurofunctional_state_is_neural_measurement": False,
        },
    }
