from __future__ import annotations
import copy
from typing import Any
from .model import clamp01

REGULATION_SCHEMA='ikant-psyche-central-regulation/v0.5-test'
_MODE_RANK={'REFLECTIVE_SYNTHESIS':0,'PRACTICAL_REVIEW':1,'SYNTHESIS_REPAIR':2,'CRITIQUE':3,'PRACTICAL_BLOCK':4,'HORIZON_BLOCK':5}
def _more_cautious(base:str,candidate:str)->str:return candidate if _MODE_RANK.get(candidate,2)>_MODE_RANK.get(base,2) else base

def regulate_central_with_psyche(central:dict[str,Any],psyche:dict[str,Any])->dict[str,Any]:
 out=copy.deepcopy(central);affect=psyche.get('affective_field') or {};accum=psyche.get('epistemic_accumulation') or {};traces=accum.get('traces') or {};selfk=psyche.get('self_knowledge') or {};tension=clamp01(float(affect.get('tension',0)));trust=clamp01(float(affect.get('synthesis_trust',0)));control=clamp01(float(affect.get('control',0)));revision=clamp01(float(traces.get('revision',0)));debt=clamp01(float(traces.get('epistemic_debt',0)));stability=clamp01(float(accum.get('adaptive_stability',0)));self_conf=clamp01(float(selfk.get('self_model_confidence',0)));base_critique=clamp01(float(out.get('critique_pressure',0)));base_unity=clamp01(float(out.get('unity_index',0)));critique=clamp01(base_critique+.10*tension+.06*revision+.04*debt+.04*(1-trust));unity=clamp01(base_unity+.05*(stability-.5)+.03*(control-.5)-.06*tension);mode=str(out.get('regulative_mode','REFLECTIVE_SYNTHESIS'));candidate=mode
 if mode not in {'HORIZON_BLOCK','PRACTICAL_BLOCK'}:
  if tension>=.74 or revision>=.62 or critique>=.68:candidate='CRITIQUE'
  elif unity<.50 or self_conf<.42 or trust<.38:candidate='SYNTHESIS_REPAIR'
 mode=_more_cautious(mode,candidate);dispositions=list(out.get('dispositions',[]))
 if tension>=.52:dispositions.append('Treat internal tension as a reason to preserve distinctions, not as external evidence.')
 if revision>=.45:dispositions.append('Recent history is revision-heavy; prefer reversible synthesis and explicit verification.')
 if trust<.42:dispositions.append('Current synthesis trust is low; state uncertainty in first person and avoid premature closure.')
 if float(affect.get('curiosity',0))>=.58 and float(affect.get('grounding_ratio',0))<.55:dispositions.append('Curiosity is high while grounding is incomplete; seek attributable evidence rather than inventing completion.')
 out['regulative_mode']=mode;out['unity_index']=round(unity,6);out['critique_pressure']=round(critique,6);out['dispositions']=list(dict.fromkeys(dispositions));out['functional_psyche_regulation']={'schema':REGULATION_SCHEMA,'base_mode':central.get('regulative_mode'),'result_mode':mode,'base_unity':round(base_unity,6),'result_unity':round(unity,6),'base_critique':round(base_critique,6),'result_critique':round(critique,6),'affective_label':affect.get('label'),'tension':round(tension,6),'synthesis_trust':round(trust,6),'adaptive_stability':round(stability,6),'maturity_mode':accum.get('maturity_mode'),'monotone_caution_only':True,'evidence_modified':False,'retroaction_route':'functional_psyche -> central_regulation -> workspace_activation'};return out

def finalize_psyche(psyche:dict[str,Any],central:dict[str,Any])->dict[str,Any]:
 out=copy.deepcopy(psyche);out.setdefault('faculties',{}).setdefault('thinking_self',{})['regulative_mode']=central.get('regulative_mode');out['faculties']['thinking_self']['critique_pressure']=central.get('critique_pressure');out.setdefault('self_knowledge',{})['central_mode']=central.get('regulative_mode');out['self_knowledge']['current_critique_pressure']=central.get('critique_pressure');return out
