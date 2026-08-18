from __future__ import annotations
import hashlib, math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

class Layer(str, Enum):
    SIGNAL="signal"; SALIENCE_HOMEOSTASIS="salience_homeostasis"; MEMORY="memory"; PREDICTIVE_CONTROL="predictive_control"; METACOGNITION="metacognition"; REFLECTIVE_SELF="reflective_self"; PSYCHODYNAMIC_HYPOTHESIS="psychodynamic_hypothesis"; ARCHETYPAL_HYPOTHESIS="archetypal_hypothesis"; KANT_ORACLE="kant_oracle"; META_EPISTEMIC="meta_epistemic"
CONCENTRIC_ORDER=(Layer.SIGNAL,Layer.SALIENCE_HOMEOSTASIS,Layer.MEMORY,Layer.PREDICTIVE_CONTROL,Layer.METACOGNITION,Layer.REFLECTIVE_SELF,Layer.PSYCHODYNAMIC_HYPOTHESIS,Layer.ARCHETYPAL_HYPOTHESIS,Layer.KANT_ORACLE)
class NodeKind(str, Enum):
    OBSERVATION="observation"; INTENTION="intention"; RESPONSE="response"; CLAIM="claim"; GOAL="goal"; CONSTRAINT="constraint"; MEMORY="memory"; HYPOTHESIS="hypothesis"; SELF_MODEL="self_model"; ACTION="action"; PREDICTION="prediction"; CONFLICT="conflict"; PRINCIPLE="principle"; SUMMARY="summary"; PATTERN="pattern"
class RelationKind(str, Enum):
    SUPPORTS="supports"; CONTRADICTS="contradicts"; ACTIVATES="activates"; INHIBITS="inhibits"; ABSTRACTS="abstracts"; ASSOCIATES="associates"; RETROACTS="retroacts"; FALSIFIES="falsifies"; PRECEDES="precedes"
EPI={Layer.SIGNAL:.80,Layer.SALIENCE_HOMEOSTASIS:.72,Layer.MEMORY:.78,Layer.PREDICTIVE_CONTROL:.80,Layer.METACOGNITION:.85,Layer.REFLECTIVE_SELF:.68,Layer.PSYCHODYNAMIC_HYPOTHESIS:.22,Layer.ARCHETYPAL_HYPOTHESIS:.18,Layer.KANT_ORACLE:.60,Layer.META_EPISTEMIC:.90}
ACT={Layer.SIGNAL:.92,Layer.SALIENCE_HOMEOSTASIS:.88,Layer.MEMORY:.86,Layer.PREDICTIVE_CONTROL:.90,Layer.METACOGNITION:.86,Layer.REFLECTIVE_SELF:.76,Layer.PSYCHODYNAMIC_HYPOTHESIS:.46,Layer.ARCHETYPAL_HYPOTHESIS:.40,Layer.KANT_ORACLE:.74,Layer.META_EPISTEMIC:.90}
def finite(v:float)->float:
    v=float(v)
    if not math.isfinite(v): raise ValueError("value must be finite")
    return v
def clamp01(v:float)->float: return min(1.,max(0.,finite(v)))
@dataclass
class Modulators:
    valence:float=0.; arousal:float=0.; interoceptive_relevance:float=0.; self_relevance:float=0.; social_relevance:float=0.; agency_relevance:float=0.; temporal_horizon:float=0.
    def validate(self):
        if not -1<=finite(self.valence)<=1: raise ValueError("valence must be in [-1,1]")
        for k,v in asdict(self).items():
            if k!="valence" and not 0<=finite(v)<=1: raise ValueError(f"{k} must be in [0,1]")
@dataclass
class Node:
    id:str; kind:NodeKind; layer:Layer; text:str; confidence:float; evidence:float; source_mode:str; recurrence:int=1; activation:float=.12; stability:float=0.; novelty:float=1.; prediction_error:float=0.; active:bool=True; modulators:Modulators=field(default_factory=Modulators); metadata:dict[str,Any]=field(default_factory=dict)
    @property
    def ceiling(self): return EPI[self.layer]
    @property
    def activation_ceiling(self): return ACT[self.layer]
@dataclass
class Relation:
    id:str; source:str; target:str; kind:RelationKind; weight:float; active:bool=True
def content_id(kind,layer,text): return "N-"+hashlib.sha256(f"{kind.value}|{layer.value}|{' '.join(text.casefold().split())}".encode()).hexdigest()[:16]
def relation_id(source,target,kind): return "R-"+hashlib.sha256(f"{source}|{target}|{kind.value}".encode()).hexdigest()[:16]
def node_to_dict(n):
    d=asdict(n); d["kind"]=n.kind.value; d["layer"]=n.layer.value; return d
def node_from_dict(d):
    m=d.get("modulators",{})
    return Node(d["id"],NodeKind(d["kind"]),Layer(d["layer"]),d["text"],clamp01(d["confidence"]),clamp01(d["evidence"]),d["source_mode"],int(d.get("recurrence",1)),clamp01(d.get("activation",.12)),clamp01(d.get("stability",0)),clamp01(d.get("novelty",1)),clamp01(d.get("prediction_error",0)),bool(d.get("active",True)),Modulators(**m),dict(d.get("metadata",{})))
def relation_to_dict(r): return {"id":r.id,"source":r.source,"target":r.target,"kind":r.kind.value,"weight":r.weight,"active":r.active}
def relation_from_dict(d): return Relation(d["id"],d["source"],d["target"],RelationKind(d["kind"]),clamp01(d["weight"]),bool(d.get("active",True)))
