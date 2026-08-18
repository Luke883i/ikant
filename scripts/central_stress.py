from __future__ import annotations
import argparse,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.central import converge_kant_oracle
from ikant.validation import source_fingerprint

MODES={'HORIZON_BLOCK','PRACTICAL_BLOCK','CRITIQUE','SYNTHESIS_REPAIR','PRACTICAL_REVIEW','REFLECTIVE_SYNTHESIS'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=10000);ap.add_argument('--seed',type=int,default=1);a=ap.parse_args();rng=random.Random(a.seed);t=time.monotonic();dist={m:0 for m in MODES}
    for _ in range(a.cases):
        base_mode=rng.choice(['REFLECTIVE_SYNTHESIS','PRACTICAL_REVIEW'])
        block=rng.random()<.035
        base={'self_state':{'unity_index':rng.random(),'critique_pressure':rng.random(),'regulative_mode':base_mode},'findings':[{'status':'BLOCK'}] if block else [],'faculties':{}}
        crc_basic=rng.random()>.06;horizon=rng.random()<.035
        diag={'epistemic_debt_open_count':rng.randrange(0,5),'mean_coefficient_of_collapse':rng.random(),'functional_coherence':rng.random(),'reentrant_capacity':rng.random(),'psychodynamic_interpretive_pressure':rng.random(),'archetypal_interpretive_pressure':rng.random()}
        crc={'roa_alignment':{'crc_basic':crc_basic,'crc_strong_candidate':False},'horizon_exceeded':horizon,'diagnostics':diag}
        proto={'cross_ring_integration':rng.random(),'temporal_continuity':rng.random(),'metacognitive_access':rng.random(),'proto_self_index':rng.random()}
        out=converge_kant_oracle(base,crc,proto);mode=out['regulative_mode'];assert mode in MODES;dist[mode]+=1
        for key in ('unity_index','critique_pressure','functional_proto_self_index','transcendental_apperception_proxy','epistemic_debt_pressure','mean_collapse','neurofunctional_coherence','reentrant_capacity','bounded_interpretive_pressure'):assert 0<=float(out[key])<=1
        auth=out['authority'];assert auth['may_create_external_evidence'] is False and auth['may_self_authorize_material_action'] is False
        if horizon or not crc_basic:assert mode=='HORIZON_BLOCK'
        elif block:assert mode=='PRACTICAL_BLOCK'
        elif mode=='CRITIQUE':assert out['critique_pressure']>=.58
    assert all(dist[m]>0 for m in MODES),dist
    result={'schema':'ikant-central-stress/v0.2','status':'PASS','cases':a.cases,'seed':a.seed,'mode_distribution':dist,'all_modes_reached':True,'source_fingerprint':source_fingerprint(),'elapsed_s':round(time.monotonic()-t,3),'claim_boundary':'regulative-state engineering stress; not moral agency or consciousness evidence'}
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
