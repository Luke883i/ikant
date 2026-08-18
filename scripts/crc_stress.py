from __future__ import annotations
import argparse, json, random, statistics, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ikant.validation import source_fingerprint
from ikant.crc import evaluate_reticulum
from ikant.model import CONCENTRIC_ORDER, NodeKind

SOURCES=("user","repository","document","live","runtime_derived","inference")
KINDS=tuple(k.value for k in NodeKind)

def build_slice(rng: random.Random, idx: int) -> dict:
    count=rng.randint(8,18); rows=[]
    for j in range(count):
        layer=CONCENTRIC_ORDER[rng.randrange(len(CONCENTRIC_ORDER))]
        source=rng.choice(SOURCES); kind=rng.choice(KINDS)
        rows.append({
          "id":f"N{idx}-{j}","layer":layer.value,"kind":kind,
          "epistemic_score":round(rng.random()*.82,6),"activation":round(rng.random()*.62,6),
          "stability":round(rng.random(),6),"novelty":round(rng.random(),6),"prediction_error":round(rng.random()*.8,6),
          "source_mode":source,"text":f"case {idx} semantic feature {j%7} context {j%3}",
        })
    # Every case has a grounded boundary observation so CRC closure is not a vacuous internal loop.
    rows[0].update({"layer":"signal","kind":"observation","source_mode":"document","epistemic_score":.72,"text":f"grounded boundary observation {idx}"})
    return {"nodes":rows,"directives":[]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args()
    rng=random.Random(a.seed); collapses=[]; rirs=[]; ies=[]; vertex=[]; debt=[]; started=time.monotonic()
    for i in range(a.cases):
        sem=build_slice(rng,i); original={r['id'] for r in sem['nodes']}; out=evaluate_reticulum(sem)
        assert out['roa_alignment']['crc_basic']; assert not out['horizon_exceeded']; assert len(out['transmissions'])==8
        for tx in out['transmissions']:
            assert 0<=tx['coefficient_of_collapse']<=1; assert 0<tx['output_count']<=tx['input_count']
            fc=tx.get('functional_control',{}); assert fc.get('cluster_id')
            for key in ('gain','precision','inhibition','plasticity','persistence','control_index'): assert 0<=fc[key]<=1
        for states in out['ring_states'].values():
            for state in states: assert set(state['support_ids'])<=original
        d=out['diagnostics']; assert d['neurofunctional_state_is_neural_measurement'] is False
        assert 0<=d['functional_coherence']<=1 and 0<=d['reentrant_capacity']<=1
        assert 0<=d['psychodynamic_interpretive_pressure']<=1 and 0<=d['archetypal_interpretive_pressure']<=1
        collapses.append(d['mean_coefficient_of_collapse']);rirs.append(d['reticular_irreducibility_proxy']);ies.append(d['emergence_index_proxy']);vertex.append(d['causal_vertex_count']);debt.append(d['epistemic_debt_open_count'])
    mc=statistics.fmean(collapses); mr=statistics.fmean(rirs)
    # Engineering envelopes calibrated on runtime-sized slices, not biological constants.
    assert .12 <= mc <= .72, mc
    assert .70 <= mr <= 1.0, mr
    result={
      'source_fingerprint':source_fingerprint(),'schema':'ikant-crc-stress/v0.2','status':'PASS','cases':a.cases,'seed':a.seed,
      'mean_collapse':round(mc,6),'collapse_min':min(collapses),'collapse_max':max(collapses),
      'mean_rir_proxy':round(mr,6),'mean_emergence_proxy':round(statistics.fmean(ies),6),
      'mean_vertices':round(statistics.fmean(vertex),3),'mean_open_debt_states':round(statistics.fmean(debt),3),
      'elapsed_s':round(time.monotonic()-started,3),
      'boundary':'operational CRC stress; not neuroscientific validation or consciousness evidence'
    }
    print(json.dumps(result,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
