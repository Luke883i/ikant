from __future__ import annotations
import argparse,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.psyche import derive_functional_psyche
from ikant.self_regulation import regulate_central_with_psyche
from tests.test_psyche_v05 import fixture
RANK={'REFLECTIVE_SYNTHESIS':0,'PRACTICAL_REVIEW':1,'SYNTHESIS_REPAIR':2,'CRITIQUE':3,'PRACTICAL_BLOCK':4,'HORIZON_BLOCK':5};MODES=tuple(RANK)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);start=time.monotonic();escalations=0;signatures=set()
 for i in range(a.cases):
  base=rng.choice(MODES);crc,cy,proto,rt=fixture(conflict=rng.randrange(5),debt=rng.randrange(6),pe=rng.random(),grounding=rng.random(),closure=rng.random()>.18);cy={**cy,'cycle_id':f'REG-{a.seed}-{i}'};p=derive_functional_psyche(crc,cy,proto,runtime_state=rt);central={'regulative_mode':base,'unity_index':rng.random(),'critique_pressure':rng.random(),'dispositions':[],'authority':{'may_create_external_evidence':False,'may_self_authorize_material_action':False}};out=regulate_central_with_psyche(central,p);result=out['regulative_mode'];assert RANK[result]>=RANK[base];assert out['critique_pressure']>=central['critique_pressure']-1e-12;reg=out['functional_psyche_regulation'];assert reg['monotone_caution_only'] and not reg['evidence_modified'];assert not out['authority']['may_create_external_evidence'] and not out['authority']['may_self_authorize_material_action'];escalations+=int(RANK[result]>RANK[base]);signatures.add((base,result,p['affective_field']['label'],p['epistemic_accumulation']['maturity_mode']))
 print(json.dumps({'schema':'ikant-self-regulation-stress/v0.5-test','status':'PASS','cases':a.cases,'seed':a.seed,'signatures':len(signatures),'escalations':escalations,'mode_relaxations':0,'evidence_authority_escalations':0,'elapsed_s':round(time.monotonic()-start,3)},sort_keys=True))
if __name__=='__main__':main()
