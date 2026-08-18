from __future__ import annotations
import argparse,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.crc import EpistemicHorizon,evaluate_reticulum
from ikant.validation import source_fingerprint


def row(i=0,**kw):
    x={'id':f'N{i}','layer':'signal','kind':'observation','epistemic_score':.72,'activation':.2,'stability':.25,'novelty':.7,'prediction_error':.1,'source_mode':'document','text':f'grounded observation {i}','modulators':{}}
    x.update(kw);return x

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=10000);ap.add_argument('--seed',type=int,default=1);a=ap.parse_args();rng=random.Random(a.seed);t=time.monotonic();counts={}
    for i in range(a.cases):
        kind=rng.randrange(9);counts[kind]=counts.get(kind,0)+1
        if kind==0:
            out=evaluate_reticulum({'nodes':[row(i,layer='unknown')],'directives':[]});assert not out['roa_alignment']['crc_basic'] and 'unregistered ring:unknown' in out['ioa_errors']
        elif kind==1:
            h=EpistemicHorizon(allowed_source_modes=('document',));out=evaluate_reticulum({'nodes':[row(i,source_mode='user')],'directives':[]},horizon=h);assert out['horizon_exceeded'] and not out['roa_alignment']['epistemic_closure']
        elif kind==2:
            bad=rng.choice([float('nan'),float('inf'),-0.01,1.01]);out=evaluate_reticulum({'nodes':[row(i,activation=bad)],'directives':[]});assert not out['roa_alignment']['crc_basic'] and any(e.startswith('invalid numeric:activation') for e in out['ioa_errors'])
        elif kind==3:
            out=evaluate_reticulum({'nodes':[row(i,id='D',text='a'),row(i+1,id='D',text='b')],'directives':[]});assert not out['roa_alignment']['crc_basic'] and 'divergent duplicate id:D' in out['ioa_errors']
        elif kind==4:
            out=evaluate_reticulum({'nodes':[row(i,kind='alien')],'directives':[]});assert not out['roa_alignment']['crc_basic']
        elif kind==5:
            out=evaluate_reticulum({'nodes':[row(i,source_mode='alien')],'directives':[]});assert not out['roa_alignment']['crc_basic']
        elif kind==6:
            out=evaluate_reticulum({'nodes':[],'directives':[]});assert not out['roa_alignment']['crc_basic'] and not out['roa_alignment']['representational_path_complete']
        elif kind==7:
            h=EpistemicHorizon(required_answer_type='forbidden');out=evaluate_reticulum({'nodes':[row(i)],'directives':[]},horizon=h);assert out['horizon_exceeded'] and not out['roa_alignment']['crc_basic']
        else:
            prev={'salience_homeostasis':{'gain':rng.random(),'precision':rng.random(),'inhibition':rng.random(),'plasticity':rng.random(),'persistence':rng.random()}}
            out=evaluate_reticulum({'nodes':[row(i)],'directives':[]},previous_neurofunctional_state=prev);assert out['roa_alignment']['crc_basic']
            for state in out['neurofunctional_state'].values():
                for key in ('gain','precision','inhibition','plasticity','persistence','control_index'):assert 0<=state[key]<=1
    result={'schema':'ikant-edge-stress/v0.2','status':'PASS','cases':a.cases,'seed':a.seed,'case_distribution':counts,'source_fingerprint':source_fingerprint(),'elapsed_s':round(time.monotonic()-t,3),'claim_boundary':'adversarial engineering robustness; not biological validation'}
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
