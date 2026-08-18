from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.validation import source_fingerprint

CORE_SEEDS=(1,17,97,883,2026)
COGNITIVE_SEEDS=(17,883,2026)
AUX_SEEDS=(1,97,883)
SURFACE_SEEDS=(1,883)

def load(path):return json.loads(Path(path).read_text())
def require(cond,msg,errors):
    if not cond:errors.append(msg)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dir',required=True);ap.add_argument('--output');a=ap.parse_args();d=Path(a.dir);fp=source_fingerprint();errors=[];receipts={}
    def grab(name):
        p=d/name;require(p.exists(),f'missing receipt {name}',errors)
        if not p.exists():return {}
        try:x=load(p)
        except Exception as e:errors.append(f'invalid JSON {name}: {e}');return {}
        receipts[name]=x;require(x.get('source_fingerprint')==fp,f'stale fingerprint {name}',errors);return x
    unit=grab('unit.json');require(unit.get('status')=='PASS' and unit.get('schema')=='ikant-unit-receipt/v0.2','unit receipt failed',errors)
    static=grab('static-883.json');require(static.get('status')=='PASS' and static.get('cases')==10000 and static.get('novelty_tail')==1000 and static.get('seed')==883,'static profile mismatch',errors)
    tuning=grab('tuning.json');require(bool(tuning.get('hard_invariants_passed')) and bool(tuning.get('near_best')) and tuning.get('candidate_count')==135,'tuning receipt failed',errors)
    dialogue=grab('dialogue.json');require(dialogue.get('status')=='PASS' and dialogue.get('all_responses_zero_evidence') and dialogue.get('all_surface_b'),'dialogue smoke failed',errors)
    for seed in SURFACE_SEEDS:
        x=grab(f'surface-a-{seed}.json');require(x.get('status')=='PASS' and x.get('cases')==10000 and x.get('seed')==seed,'surface A profile mismatch '+str(seed),errors)
    for seed in CORE_SEEDS:
        x=grab(f'dynamic-{seed}.json');require(x.get('status')=='PASS' and x.get('seed')==seed and x.get('operations')==10000 and x.get('novelty_tail')==1000,'dynamic profile mismatch '+str(seed),errors);require(float(x.get('max_mean_activation_ceiling_fraction_sampled',1))<=.5 and float(x.get('max_activation_saturation_share_85_sampled',1))<=.05,'dynamic saturation '+str(seed),errors)
        x=grab(f'crc-{seed}.json');require(x.get('status')=='PASS' and x.get('seed')==seed and x.get('cases')==10000,'CRC profile mismatch '+str(seed),errors);require(.12<=float(x.get('mean_collapse',0))<=.72 and .70<=float(x.get('mean_rir_proxy',0))<=1,'CRC envelope '+str(seed),errors)
    for seed in COGNITIVE_SEEDS:
        x=grab(f'cognitive-{seed}.json');require(x.get('status')=='PASS' and x.get('seed')==seed and x.get('turns')==500 and x.get('novelty_tail')==100,'cognitive profile mismatch '+str(seed),errors);require(bool(x.get('sentinel_evidence_unchanged')) and bool(x.get('response_evidence_zero')) and bool(x.get('response_cycle_window_bounded')) and int(x.get('surface_a_emission_events',0))==500 and float(x.get('max_mean_activation_ceiling_fraction',1))<.70,'cognitive invariant '+str(seed),errors)
    for seed in AUX_SEEDS:
        x=grab(f'edge-{seed}.json');require(x.get('status')=='PASS' and x.get('cases')==10000 and x.get('seed')==seed,'edge profile mismatch '+str(seed),errors)
        x=grab(f'central-{seed}.json');require(x.get('status')=='PASS' and x.get('cases')==10000 and x.get('seed')==seed and x.get('all_modes_reached'),'central profile mismatch '+str(seed),errors)
    out={'schema':'ikant-isolated-full-validation/v0.2','status':'PASS' if not errors else 'FAIL','source_fingerprint':fp,'profiles':{'unit':1,'static':1,'tuning':1,'dialogue':1,'surface_a_seeds':list(SURFACE_SEEDS),'dynamic_seeds':list(CORE_SEEDS),'crc_seeds':list(CORE_SEEDS),'cognitive_seeds':list(COGNITIVE_SEEDS),'edge_seeds':list(AUX_SEEDS),'central_seeds':list(AUX_SEEDS)},'receipt_count':len(receipts),'errors':errors,'release_candidate':not errors,'claim_boundary':'engineering validation of the local cognitive runtime; not neuroscientific validation or evidence of consciousness'}
    text=json.dumps(out,indent=2,sort_keys=True)+'\n';print(text,end='')
    if a.output:Path(a.output).write_text(text)
    return 0 if not errors else 1
if __name__=='__main__':raise SystemExit(main())
