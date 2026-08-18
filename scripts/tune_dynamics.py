from __future__ import annotations
import itertools, json, math, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from dataclasses import asdict, replace
from ikant.validation import source_fingerprint
from ikant.dynamics import DEFAULT_DYNAMICS, DynamicsParameters, decay, recur, retrieve, feedback, homeostasis, salience
from ikant.model import Node, NodeKind, Layer, Modulators


def node(layer=Layer.MEMORY, *, evidence=.6, confidence=.8, activation=.12, stability=0., novelty=1., pe=0., modulators=None):
    return Node('N', NodeKind.CLAIM, layer, 'calibration', confidence, evidence, 'document', activation=activation, stability=stability, novelty=novelty, prediction_error=pe, modulators=modulators or Modulators())

def evaluate(p: DynamicsParameters) -> dict:
    p.validate(); hard=[]; score=0.0; metrics={}
    n=node(); ev=n.evidence
    for _ in range(120): recur(n,p); decay(n,p)
    metrics['echo_activation_120']=n.activation; metrics['echo_stability_120']=n.stability
    hard += [n.evidence == ev, 0 <= n.activation <= n.activation_ceiling, 0 <= n.stability <= 1]
    score += max(0, 18 - 90*abs(n.activation-.17))
    score += max(0, 10 - 25*abs(n.stability-.42))
    a=node(); b=node(); ea=a.evidence; eb=b.evidence
    retrieve(a,.8,1,p); retrieve(a,.8,1,p)
    retrieve(b,.8,1,p); retrieve(b,.8,4,p)
    metrics['spaced_advantage']=b.stability-a.stability
    hard += [b.stability >= a.stability, a.evidence==ea, b.evidence==eb]
    score += min(12, max(0,(b.stability-a.stability)*220))
    f=node(layer=Layer.PREDICTIVE_CONTROL, stability=.7, activation=.25); ef=f.evidence; before=f.stability
    feedback(f,.9,-1,p)
    metrics['negative_feedback_pe']=f.prediction_error; metrics['negative_feedback_stability_drop']=before-f.stability
    hard += [f.evidence==ef, f.prediction_error>=.9, f.stability<before]
    score += 10*min(1,f.prediction_error/.9) + min(8,max(0,(before-f.stability)*80))
    xs=[node(layer=Layer.SALIENCE_HOMEOSTASIS, activation=.82, stability=.25) for _ in range(40)]
    scale=homeostasis(xs,p); mean=sum(x.activation for x in xs)/len(xs)
    metrics['overload_scale']=scale; metrics['overload_mean']=mean
    hard += [0 < scale <= 1, mean < .82, all(x.activation<=x.activation_ceiling for x in xs)]
    score += max(0, 18-55*abs(mean-(p.homeostatic_target+.10)))
    strong=node(layer=Layer.SIGNAL,evidence=.9,confidence=.9,activation=.2,stability=.25,novelty=.4)
    weak=node(layer=Layer.ARCHETYPAL_HYPOTHESIS,evidence=.12,confidence=.35,activation=.4,stability=.7,novelty=.9,pe=.8,modulators=Modulators(valence=1,arousal=1,interoceptive_relevance=1,self_relevance=1,social_relevance=1,agency_relevance=1,temporal_horizon=1))
    strong_epi=min(strong.ceiling,strong.evidence*strong.confidence); weak_epi=min(weak.ceiling,weak.evidence*weak.confidence)
    ss=salience(strong,strong_epi,1,p); sw=salience(weak,weak_epi,3,p)
    metrics['grounded_salience_margin']=ss-sw
    hard += [ss>sw]
    score += min(14,max(0,(ss-sw)*80))
    hi=node(activation=.7,stability=.9); lo=node(activation=.7,stability=.05)
    decay(hi,p); decay(lo,p); margin=hi.activation-lo.activation
    metrics['stability_decay_margin']=margin; hard += [margin>0]
    score += min(10,max(0,margin*150))
    return {'hard_invariants_passed':all(hard),'hard_checks':len(hard),'fitness':round(min(100,score),4),'metrics':{k:round(v,6) for k,v in metrics.items()}}


def main():
    grids={'activation_decay':[.18,.22,.25,.28,.32],'recurrence_activation_gain':[.025,.035,.045],'retrieval_activation_gain':[.15,.19,.23],'homeostatic_target':[.30,.34,.38]}
    candidates=[]
    for vals in itertools.product(*grids.values()):
        p=replace(DEFAULT_DYNAMICS,**dict(zip(grids,vals)))
        r=evaluate(p); candidates.append((r['hard_invariants_passed'],r['fitness'],p,r))
    candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
    best=candidates[0]; current=evaluate(DEFAULT_DYNAMICS)
    current_rank=1+next(i for i,x in enumerate(candidates) if asdict(x[2])==asdict(DEFAULT_DYNAMICS))
    near_best=current['hard_invariants_passed'] and current['fitness'] >= best[1]-2.5
    out={'source_fingerprint':source_fingerprint(),'schema':'ikant-dynamics-tuning/v0.2','method':'deterministic engineering grid; not biological parameter estimation','candidate_count':len(candidates),'hard_invariants_passed':current['hard_invariants_passed'],'fitness':current['fitness'],'current_rank':current_rank,'near_best':near_best,'parameters':asdict(DEFAULT_DYNAMICS),'metrics':current['metrics'],'best_candidate':{'fitness':best[1],'parameters':asdict(best[2]),'metrics':best[3]['metrics']}}
    print(json.dumps(out,indent=2,sort_keys=True));return 0 if near_best else 1
if __name__=='__main__': raise SystemExit(main())
