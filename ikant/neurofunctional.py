from __future__ import annotations
from dataclasses import asdict, dataclass
from .model import Layer, CONCENTRIC_ORDER

@dataclass(frozen=True)
class NeuroFunctionalCluster:
    id: str
    ring: Layer
    label: str
    anatomical_anchors: tuple[str, ...]
    runtime_role: str
    scientific_status: str
    evidence_anchors: tuple[str, ...]
    falsifier: str

CLUSTERS = (
    NeuroFunctionalCluster(
        "NF-SENSORY-ASSOCIATION", Layer.SIGNAL, "sensory-association field",
        ("thalamic sensory relay", "primary sensory cortices", "posterior association cortex"),
        "Represent attributable observations and low-level feature-bearing inputs before coarse graining.",
        "functional_analogue_not_region_simulation", ("PMID:26832438",),
        "The ring is falsified as a sensory analogue if higher-level inference can create new external evidence here.",
    ),
    NeuroFunctionalCluster(
        "NF-SALIENCE-INTEROCEPTION", Layer.SALIENCE_HOMEOSTASIS, "salience and body-state gate",
        ("anterior insula", "dorsal anterior cingulate", "subcortical arousal systems"),
        "Allocate bounded availability using salience, arousal, self/social relevance and homeostatic normalization.",
        "functional_analogue_not_region_simulation", ("PMID:17329432", "PMID:14730305", "PMID:29301874"),
        "The ring is falsified if relevance or arousal changes factual evidence rather than availability.",
    ),
    NeuroFunctionalCluster(
        "NF-MEMORY-CONSOLIDATION", Layer.MEMORY, "episodic-semantic consolidation",
        ("hippocampal formation", "medial temporal lobe", "distributed association cortex"),
        "Separate recurrence, retrieval and consolidation from independent corroboration; preserve temporal traces.",
        "functional_analogue_not_region_simulation", ("PMID:24305832", "PMID:34911768", "PMID:37066263"),
        "The ring is falsified if repetition alone increases evidential support.",
    ),
    NeuroFunctionalCluster(
        "NF-EXECUTIVE-CONTROL", Layer.PREDICTIVE_CONTROL, "executive predictive control",
        ("dorsolateral prefrontal cortex", "frontoparietal control network", "basal-ganglia gating loops"),
        "Represent goals, predictions, candidate actions, inhibition and task switching under explicit authority.",
        "functional_analogue_not_region_simulation", ("PMID:29239622",),
        "The ring is falsified if inferred goals acquire material authority without an attributable directive.",
    ),
    NeuroFunctionalCluster(
        "NF-METACOGNITIVE-MONITOR", Layer.METACOGNITION, "metacognitive monitor",
        ("anterior prefrontal cortex", "dorsal anterior cingulate", "frontoparietal monitoring systems"),
        "Track confidence, prediction error, contradiction, calibration, horizon pressure and epistemic debt.",
        "functional_analogue_not_region_simulation", ("PMID:29519851",),
        "The ring is falsified if known conflict or uncertainty is silently erased during abstraction.",
    ),
    NeuroFunctionalCluster(
        "NF-SELF-NARRATIVE", Layer.REFLECTIVE_SELF, "self-narrative and social model",
        ("medial prefrontal cortex", "posterior cingulate/precuneus", "temporoparietal junction"),
        "Maintain bounded temporal continuity of commitments, agency attribution and self-in-context summaries.",
        "functional_analogue_not_region_simulation", ("PMID:26365506", "PMID:20378581"),
        "The ring is falsified if it invents hidden user traits or treats its self-model as external evidence.",
    ),
    NeuroFunctionalCluster(
        "NF-PSYCHODYNAMIC-HYPOTHESIS", Layer.PSYCHODYNAMIC_HYPOTHESIS, "psychodynamic tension hypothesis",
        (),
        "Offer low-authority, retractable descriptions of unresolved conflict or defensive-like patterns.",
        "interpretive_hypothesis_namespace", (),
        "The construct must be withdrawn if it resists counterevidence, exceeds its ceiling or is treated as diagnosis/anatomy.",
    ),
    NeuroFunctionalCluster(
        "NF-ARCHETYPAL-COMPRESSION", Layer.ARCHETYPAL_HYPOTHESIS, "archetypal symbolic compression",
        (),
        "Represent recurring symbolic motifs as optional low-authority compression labels, never factual proof.",
        "interpretive_hypothesis_namespace", (),
        "The construct is falsified operationally if symbolic recurrence authorizes action or raises evidence.",
    ),
    NeuroFunctionalCluster(
        "NF-KANT-ORACLE", Layer.KANT_ORACLE, "synthetic Kant regulative center",
        (),
        "Integrate closure, contradiction, uncertainty, autonomy, human impact and self-continuity into a regulative disposition.",
        "synthetic_normative_kernel", (),
        "The kernel fails if it self-authorizes material action, creates factual evidence or becomes immune to explicit runtime tests.",
    ),
)

BY_RING = {c.ring: c for c in CLUSTERS}


@dataclass(frozen=True)
class FunctionalCoupling:
    source: Layer
    target: Layer
    kind: str
    runtime_effect: str
    scientific_status: str = "functional_analogue_not_connectome_claim"

FUNCTIONAL_COUPLINGS = (
    FunctionalCoupling(Layer.SIGNAL, Layer.SALIENCE_HOMEOSTASIS, "bottom_up_gating", "Attributable inputs compete for bounded availability."),
    FunctionalCoupling(Layer.SALIENCE_HOMEOSTASIS, Layer.MEMORY, "priority_to_encoding", "Available material receives retrieval/consolidation priority without gaining evidence."),
    FunctionalCoupling(Layer.MEMORY, Layer.PREDICTIVE_CONTROL, "history_to_prediction", "Retrieved history shapes predictions and candidate control states."),
    FunctionalCoupling(Layer.PREDICTIVE_CONTROL, Layer.METACOGNITION, "prediction_to_monitoring", "Prediction error and authorization state become monitorable second-order state."),
    FunctionalCoupling(Layer.METACOGNITION, Layer.REFLECTIVE_SELF, "monitoring_to_self_model", "Confidence, conflict and debt constrain continuity claims about the local self-model."),
    FunctionalCoupling(Layer.REFLECTIVE_SELF, Layer.PSYCHODYNAMIC_HYPOTHESIS, "self_conflict_to_hypothesis", "Unresolved self/context tensions may create bounded interpretive hypotheses."),
    FunctionalCoupling(Layer.PSYCHODYNAMIC_HYPOTHESIS, Layer.ARCHETYPAL_HYPOTHESIS, "pattern_coarse_graining", "Repeated low-authority tensions may be compressed into optional symbolic motifs."),
    FunctionalCoupling(Layer.ARCHETYPAL_HYPOTHESIS, Layer.KANT_ORACLE, "symbolic_to_regulative_context", "Symbolic material may affect caution only inside strict interpretive ceilings."),
    FunctionalCoupling(Layer.KANT_ORACLE, Layer.METACOGNITION, "reentrant_critique", "Central critique raises revisit/verification priority without creating evidence."),
    FunctionalCoupling(Layer.KANT_ORACLE, Layer.PREDICTIVE_CONTROL, "reentrant_inhibition", "Autonomy and human-impact checks inhibit unauthorized material action."),
    FunctionalCoupling(Layer.KANT_ORACLE, Layer.SALIENCE_HOMEOSTASIS, "reentrant_attention", "Regulative state changes what is foregrounded on the next cycle."),
)

def coupling_manifest() -> list[dict]:
    return [{**asdict(c), "source": c.source.value, "target": c.target.value} for c in FUNCTIONAL_COUPLINGS]

def validate_cluster_map() -> tuple[bool, list[str]]:
    errors = []
    if set(BY_RING) != set(CONCENTRIC_ORDER):
        errors.append("every concentric ring must have exactly one functional cluster")
    expected_bottom_up={(CONCENTRIC_ORDER[i],CONCENTRIC_ORDER[i+1]) for i in range(len(CONCENTRIC_ORDER)-1)}
    actual_bottom_up={(c.source,c.target) for c in FUNCTIONAL_COUPLINGS if c.source != Layer.KANT_ORACLE}
    if not expected_bottom_up <= actual_bottom_up:
        errors.append("every adjacent concentric ring requires a declared bottom-up functional coupling")
    if not any(c.source==Layer.KANT_ORACLE and c.target==Layer.SALIENCE_HOMEOSTASIS for c in FUNCTIONAL_COUPLINGS):
        errors.append("Kant center requires an explicit reentrant attentional coupling")
    for c in CLUSTERS:
        if c.ring in {Layer.PSYCHODYNAMIC_HYPOTHESIS, Layer.ARCHETYPAL_HYPOTHESIS, Layer.KANT_ORACLE} and c.anatomical_anchors:
            errors.append(f"{c.id} must not claim an anatomical anchor")
        if c.ring not in {Layer.PSYCHODYNAMIC_HYPOTHESIS, Layer.ARCHETYPAL_HYPOTHESIS, Layer.KANT_ORACLE} and not c.anatomical_anchors:
            errors.append(f"{c.id} requires declared functional anatomical anchors")
        if not c.falsifier.strip():
            errors.append(f"{c.id} falsifier missing")
    return not errors, errors

def manifest() -> list[dict]:
    return [
        {
            **asdict(c),
            "ring": c.ring.value,
            "anatomical_anchors": list(c.anatomical_anchors),
            "evidence_anchors": list(c.evidence_anchors),
        }
        for c in CLUSTERS
    ]

@dataclass(frozen=True)
class ClusterControlProfile:
    ring: Layer
    inertia: float
    gain_bias: float
    precision_weight: float
    error_sensitivity: float
    inhibitory_bias: float
    plasticity_weight: float

CONTROL_PROFILES = {
    Layer.SIGNAL: ClusterControlProfile(Layer.SIGNAL,.25,.10,.60,.20,.08,.25),
    Layer.SALIENCE_HOMEOSTASIS: ClusterControlProfile(Layer.SALIENCE_HOMEOSTASIS,.35,.16,.30,.30,.18,.20),
    Layer.MEMORY: ClusterControlProfile(Layer.MEMORY,.48,.10,.35,.30,.10,.55),
    Layer.PREDICTIVE_CONTROL: ClusterControlProfile(Layer.PREDICTIVE_CONTROL,.35,.12,.45,.45,.22,.25),
    Layer.METACOGNITION: ClusterControlProfile(Layer.METACOGNITION,.30,.08,.52,.58,.15,.30),
    Layer.REFLECTIVE_SELF: ClusterControlProfile(Layer.REFLECTIVE_SELF,.58,.08,.38,.25,.12,.18),
    Layer.PSYCHODYNAMIC_HYPOTHESIS: ClusterControlProfile(Layer.PSYCHODYNAMIC_HYPOTHESIS,.40,-.12,.22,.40,.38,.15),
    Layer.ARCHETYPAL_HYPOTHESIS: ClusterControlProfile(Layer.ARCHETYPAL_HYPOTHESIS,.52,-.16,.18,.30,.45,.10),
    Layer.KANT_ORACLE: ClusterControlProfile(Layer.KANT_ORACLE,.62,.05,.50,.45,.28,.08),
}


def _avg(rows, key, default=0.0):
    vals=[float(r.get(key,default)) for r in rows]
    return sum(vals)/len(vals) if vals else 0.0


def _mod_avg(rows, key):
    vals=[]
    for r in rows:
        vals.append(float((r.get('modulators') or {}).get(key,0.0)))
    return sum(vals)/len(vals) if vals else 0.0


def derive_cluster_control(ring: Layer, frames: list[dict], previous: dict | None = None) -> dict:
    """Derive a bounded functional control state from runtime observables.

    This is an engineering analogue. Anatomical anchors motivate the variables but are never
    interpreted as measured regional activity.
    """
    from .model import clamp01
    p=CONTROL_PROFILES[ring]; previous=previous or {}
    activation=_avg(frames,'activation'); epistemic=_avg(frames,'epistemic'); stability=_avg(frames,'stability'); novelty=_avg(frames,'novelty'); pe=_avg(frames,'prediction_error')
    arousal=_mod_avg(frames,'arousal'); self_rel=_mod_avg(frames,'self_relevance'); social=_mod_avg(frames,'social_relevance'); agency=_mod_avg(frames,'agency_relevance')
    grounded=sum(1 for r in frames if any(s in {'user','repository','document','live'} for s in r.get('source_modes',[])))/max(1,len(frames))
    conflict=sum(1 for r in frames if 'conflict' in set(r.get('kinds',[])))/max(1,len(frames))
    raw_gain=clamp01(p.gain_bias + .30*activation + .24*epistemic + .12*novelty + .10*arousal + .08*self_rel + .08*social + .08*agency)
    raw_precision=clamp01(p.precision_weight*epistemic + (1-p.precision_weight)*grounded - p.error_sensitivity*.30*pe)
    raw_inhibition=clamp01(p.inhibitory_bias + .36*conflict + .28*pe + .18*(1-grounded) + .18*(1-epistemic))
    raw_plasticity=clamp01(p.plasticity_weight*novelty + (1-p.plasticity_weight)*pe)
    raw_persistence=clamp01(.72*stability + .28*(1-novelty))
    def smooth(name, value):
        prev=float(previous.get(name,value)); return clamp01(p.inertia*prev+(1-p.inertia)*value)
    state={
        'cluster_id': BY_RING[ring].id,
        'ring': ring.value,
        'gain': round(smooth('gain',raw_gain),6),
        'precision': round(smooth('precision',raw_precision),6),
        'inhibition': round(smooth('inhibition',raw_inhibition),6),
        'plasticity': round(smooth('plasticity',raw_plasticity),6),
        'persistence': round(smooth('persistence',raw_persistence),6),
        'prediction_error': round(pe,6),
        'grounding_ratio': round(grounded,6),
        'conflict_pressure': round(conflict,6),
        'input_count': len(frames),
        'scientific_status': 'functional_control_proxy_not_neural_measurement',
    }
    state['control_index']=round(clamp01(.30*state['gain']+.28*state['precision']+.20*state['persistence']+.12*state['plasticity']+.10*(1-state['inhibition'])),6)
    return state


def functional_state_summary(states: dict[str, dict]) -> dict:
    from .model import clamp01
    rows=list(states.values())
    if not rows:return {'mean_control_index':0.0,'functional_coherence':0.0,'reentrant_capacity':0.0,'is_neural_measurement':False}
    xs=[float(r.get('control_index',0)) for r in rows]
    mean=sum(xs)/len(xs); variance=sum((x-mean)**2 for x in xs)/len(xs)
    coherence=clamp01(1-(variance**.5)/.5)
    needed=[states.get(x.value,{}) for x in (Layer.SALIENCE_HOMEOSTASIS,Layer.PREDICTIVE_CONTROL,Layer.METACOGNITION)]
    reentrant=min((float(r.get('control_index',0)) for r in needed),default=0.0)
    return {'mean_control_index':round(mean,6),'functional_coherence':round(coherence,6),'reentrant_capacity':round(reentrant,6),'is_neural_measurement':False}

@dataclass(frozen=True)
class NeuroscienceCoverage:
    domain: str
    status: str
    runtime_binding: str
    biological_claim: str
    evidence_anchors: tuple[str, ...] = ()

NEUROSCIENCE_COVERAGE = (
    NeuroscienceCoverage('sensory_and_association','active_ring','R0 attributable input and feature-bearing boundary','functional analogue only',('PMID:26832438',)),
    NeuroscienceCoverage('attention_salience_arousal_interoception','active_ring_and_modulators','R1 gating plus arousal/interoceptive/self/social relevance modulators','functional analogue only',('PMID:17329432','PMID:14730305','PMID:29301874')),
    NeuroscienceCoverage('episodic_semantic_memory_and_consolidation','active_ring','R2 recurrence/retrieval/consolidation and persistent event/compression memory','functional analogue only',('PMID:24305832','PMID:34911768','PMID:37066263')),
    NeuroscienceCoverage('executive_frontoparietal_control','active_ring','R3 prediction, directive authority, inhibition and candidate action','functional analogue only',('PMID:29239622','PMID:30113310')),
    NeuroscienceCoverage('metacognition_conflict_monitoring','active_ring','R4 confidence, prediction error, contradiction and epistemic debt','functional analogue only',('PMID:29519851',)),
    NeuroscienceCoverage('self_social_agency','active_ring','R5 continuity, agency binding and self-in-context state','functional analogue only',('PMID:26365506','PMID:20378581')),
    NeuroscienceCoverage('language_and_distributed_semantics','host_boundary','Host language model generates/understands natural language; local CRC stores lexical signatures and constrains Surface A','not a local cortical language simulation',('PMID:27121839','PMID:37577530')),
    NeuroscienceCoverage('affect_reward_valuation','bounded_modulator','valence/arousal/social/agency relevance may change availability but never evidence','no synthetic emotion or reward-system claim',('PMID:29301874',)),
    NeuroscienceCoverage('sensorimotor_action','host_boundary','Material action stays outside local CRC and requires host/tool authorization','no motor-system simulation',()),
    NeuroscienceCoverage('cerebellar_timing_and_motor_prediction','inactive_v02','No dedicated local dynamical equivalent in v0.2','explicitly out of active scope',()),
    NeuroscienceCoverage('autonomic_endocrine_and_homeostatic_physiology','inactive_v02','Homeostasis is computational activation normalization only','no bodily physiology claim',()),
    NeuroscienceCoverage('sleep_offline_replay','partial_analogue','Compression/retrieval provide bounded offline-like consolidation mechanics without sleep-state simulation','computational analogy only',('PMID:24305832',)),
    NeuroscienceCoverage('developmental_learning_aging','inactive_v02','No developmental trajectory or age model','requires separate longitudinal evidence',()),
    NeuroscienceCoverage('clinical_lesion_pharmacological','inactive_v02','No diagnosis, disorder, lesion or drug-response model','requires separate clinical validation and governance',()),
    NeuroscienceCoverage('cellular_molecular_genetic_glial','inactive_v02','No neurons, neurotransmitters, genes or glia are simulated','outside abstraction horizon',()),
)

def neuroscience_coverage_manifest() -> list[dict]:
    return [{**asdict(x),'evidence_anchors':list(x.evidence_anchors)} for x in NEUROSCIENCE_COVERAGE]
