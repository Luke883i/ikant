from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from .model import Node, clamp01
@dataclass(frozen=True)
class DynamicsParameters:
    activation_decay:float=.25; stability_decay_protection:float=.55; recurrence_activation_gain:float=.035; recurrence_stability_gain:float=.01; recurrence_novelty_retention:float=.84; retrieval_activation_gain:float=.19; retrieval_stability_gain_immediate:float=.012; retrieval_stability_gain_spaced:float=.055; retrieval_novelty_retention:float=.90; prediction_error_decay:float=.22; prediction_error_activation_gain:float=.18; negative_feedback_destabilization:float=.14; positive_feedback_consolidation:float=.045; homeostatic_target:float=.34; homeostatic_gain:float=.60; salience_epistemic_weight:float=.66; salience_activation_weight:float=.14; salience_stability_weight:float=.07; salience_novelty_weight:float=.05; salience_prediction_error_weight:float=.08; lexical_overlap_per_token:float=.035; lexical_overlap_cap:float=.18; directive_epistemic_weight:float=.78; corroboration_gain:float=.35; oracle_retroaction_gain:float=.08; interpretive_inhibition:float=.16; unauthorized_action_inhibition:float=.20; modulatory_salience_cap:float=.06; slice_max_runtime_derived_share:float=.25; slice_max_interpretive_share:float=.25; slice_max_kernel_principles:int=1; pattern_miss_retract_threshold:int=3; max_active_summaries:int=16; max_inactive_derived_nodes:int=64; compression_trend_alpha:float=.28; compression_interval_cycles:int=8; compression_event_window:int=512; emergent_recurrence_threshold:int=5; emergent_revision_threshold:int=3; emergent_coactivation_threshold:int=4
    def validate(self):
        ints={"slice_max_kernel_principles","pattern_miss_retract_threshold","max_active_summaries","max_inactive_derived_nodes","compression_interval_cycles","compression_event_window","emergent_recurrence_threshold","emergent_revision_threshold","emergent_coactivation_threshold"}
        for k,v in asdict(self).items():
            if k not in ints and (not math.isfinite(float(v)) or not 0<=float(v)<=1): raise ValueError(f"{k} must be in [0,1]")
        if self.compression_event_window<16 or self.compression_interval_cycles<1 or min(self.emergent_recurrence_threshold,self.emergent_revision_threshold,self.emergent_coactivation_threshold)<2: raise ValueError("invalid dynamic count parameter")
DEFAULT_DYNAMICS=DynamicsParameters(); DEFAULT_DYNAMICS.validate()
def decay(n,p=DEFAULT_DYNAMICS):
    n.activation=clamp01(n.activation*(1-p.activation_decay*(1-p.stability_decay_protection*n.stability))); n.prediction_error=clamp01(n.prediction_error*(1-p.prediction_error_decay))
def recur(n,p=DEFAULT_DYNAMICS):
    n.activation=min(n.activation_ceiling,clamp01(n.activation+p.recurrence_activation_gain*(1-n.activation))); n.stability=clamp01(n.stability+p.recurrence_stability_gain*(1-n.stability)); n.novelty=clamp01(n.novelty*p.recurrence_novelty_retention)
def retrieve(n,relevance,cycle,p=DEFAULT_DYNAMICS):
    relevance=clamp01(relevance); n.activation=min(n.activation_ceiling,clamp01(n.activation+p.retrieval_activation_gain*relevance*(1-n.activation))); gap=cycle-int(n.metadata.get("last_retrieved_cycle",-9999)); gain=p.retrieval_stability_gain_spaced if gap>=2 else p.retrieval_stability_gain_immediate; n.stability=clamp01(n.stability+gain*relevance*(1-n.stability)); n.novelty=clamp01(n.novelty*p.retrieval_novelty_retention); n.metadata["last_retrieved_cycle"]=cycle
def feedback(n,error,valence,p=DEFAULT_DYNAMICS):
    error=clamp01(error); valence=float(valence)
    if not -1<=valence<=1: raise ValueError("valence")
    n.prediction_error=max(n.prediction_error,error); n.activation=min(n.activation_ceiling,clamp01(n.activation+p.prediction_error_activation_gain*error*(1-n.activation)))
    if valence<0: n.stability=clamp01(n.stability*(1-p.negative_feedback_destabilization*abs(valence)*error))
    elif valence>0: n.stability=clamp01(n.stability+p.positive_feedback_consolidation*valence*(1-error)*(1-n.stability))
def homeostasis(nodes,p=DEFAULT_DYNAMICS):
    xs=[n for n in nodes if n.active and n.activation>0]
    if not xs:return 1.
    mean=sum(n.activation for n in xs)/len(xs)
    if mean<=p.homeostatic_target:return 1.
    scale=clamp01(1-p.homeostatic_gain*(1-p.homeostatic_target/mean))
    for n in xs:n.activation=min(n.activation_ceiling,n.activation*scale)
    return scale
def salience(n,epi,overlap,p=DEFAULT_DYNAMICS):
    lexical=min(p.lexical_overlap_cap,max(0,overlap)*p.lexical_overlap_per_token)
    m=n.modulators; m.validate(); mod=p.modulatory_salience_cap*(.15*(m.valence+1)/2+.2*m.arousal+.1*m.interoceptive_relevance+.15*m.self_relevance+.15*m.social_relevance+.15*m.agency_relevance+.1*m.temporal_horizon)
    return clamp01(p.salience_epistemic_weight*epi+p.salience_activation_weight*n.activation+p.salience_stability_weight*n.stability+p.salience_novelty_weight*n.novelty+p.salience_prediction_error_weight*n.prediction_error+lexical+mod)
