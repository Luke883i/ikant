from dataclasses import dataclass, asdict
from .model import clamp01
@dataclass(frozen=True)
class Principle: id:str; name:str; test:str
PRINCIPLES=(
 Principle("KANT-GROUNDING","limits_of_sensibility","Separate attributable evidence from inference and symbolic interpretation."),
 Principle("KANT-CONSISTENCY","understanding_non_contradiction","Preserve and surface material contradictions."),
 Principle("KANT-JUDGMENT","reflective_judgment","Calibrate application under uncertainty, prediction error and feedback."),
 Principle("KANT-HUMILITY","limits_of_reason","Higher abstraction cannot self-promote into factual authority."),
 Principle("KANT-AUTONOMY","autonomy","Material action must remain attributable to explicit user/repository goals."),
 Principle("KANT-UNIVERSAL","universalizability","Expose a candidate action maxim for consistent host-level testing."),
 Principle("KANT-ENDS","persons_as_ends","Unresolved material human impact blocks autonomous action."),)
class KantOracle:
    def evaluate(self,c):
        u=clamp01(c.get("uncertainty",0)); conflicts=max(0,int(c.get("conflict_count",0))); interp=clamp01(c.get("interpretive_dependency",0)); auth=max(0,int(c.get("authorized_directives",0))); impact=bool(c.get("human_impact_unknown",False)); cal=clamp01(c.get("calibration_error",0)); pe=clamp01(c.get("mean_prediction_error",0)); grounding=clamp01(c.get("grounding_ratio",0)); continuity=clamp01(c.get("self_continuity",0)); coherence=clamp01(1-conflicts/3); judgment=clamp01(1-.45*u-.35*cal-.2*pe); reason=1-interp; practical=1. if auth else 0.; unity=clamp01(.23*grounding+.22*coherence+.22*judgment+.18*reason+.15*max(continuity,.5*practical)); critique=clamp01(.9*(.3*u+.25*(1-coherence)+.2*cal+.15*pe+.1*interp)); findings=[]; disp=[]
        def add(pid,status,msg=None): findings.append({"principle":pid,"status":status}); msg and disp.append(msg)
        add("KANT-GROUNDING","WARN" if grounding<.45 else "PASS","Separate grounded from derived content." if grounding<.45 else None); add("KANT-CONSISTENCY","WARN" if conflicts else "PASS","Surface contradictions." if conflicts else None); add("KANT-JUDGMENT","WARN" if judgment<.55 else "PASS","Prefer verification or abstention." if judgment<.55 else None); add("KANT-HUMILITY","WARN" if (u>.45 or interp>.25 or cal>.25) else "PASS","Mark uncertainty and cap interpretation." if (u>.45 or interp>.25 or cal>.25) else None); add("KANT-AUTONOMY","PASS" if auth else "WARN","Do not infer material goals from persona." if not auth else None); add("KANT-UNIVERSAL","REQUIRES_HOST_CHECK"); add("KANT-ENDS","BLOCK" if impact else "PASS","Resolve human-impact uncertainty." if impact else None)
        if impact: mode="PRACTICAL_BLOCK"
        elif critique>=.55: mode="CRITIQUE"
        elif unity<.58: mode="SYNTHESIS_REPAIR"
        elif auth: mode="PRACTICAL_REVIEW"
        else: mode="REFLECTIVE_SYNTHESIS"
        return {"schema":"ikant-kant-oracle/v0.1","archetype":"synthetic_kant_regulative_oracle","principles":[asdict(x) for x in PRINCIPLES],"faculties":{"sensibility_grounding":round(grounding,4),"understanding_coherence":round(coherence,4),"reflective_judgment":round(judgment,4),"reason_discipline":round(reason,4),"practical_reason_grounding":practical},"self_state":{"unity_index":round(unity,4),"critique_pressure":round(critique,4),"regulative_mode":mode,"is_consciousness_claim":False},"findings":findings,"required_checks":["State the candidate action maxim in one testable sentence before material execution."],"dispositions":list(dict.fromkeys(disp)),"authority":{"may_rank_or_filter":True,"may_shape_output_policy":True,"may_self_authorize_material_action":False,"host_system_safety_law_override":True}}
