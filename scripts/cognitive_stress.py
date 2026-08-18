from __future__ import annotations
import argparse,json,random,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.validation import source_fingerprint
from ikant.cognitive import compile_cognitive_turn, record_surface_a
from ikant.model import NodeKind,Layer
from tests.helpers import active_runtime

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--turns',type=int,default=1200);ap.add_argument('--novelty-tail',type=int,default=300);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);t=time.monotonic()
    with tempfile.TemporaryDirectory() as td:
        rt=active_runtime(Path(td),durable=False);sentinel=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='sentinel external evidence',confidence=.8,evidence=.37,source_mode='document');ev=sentinel.evidence;max_proto=0.;max_mean=0.;modes={}
        for i in range(a.turns):
            intent=f"evaluate local option {i%113} under constraint {rng.randrange(17)}"
            out=compile_cognitive_turn(rt,intent,export_docx=False);p=out['proto_self']['proto_self_index'];max_proto=max(max_proto,p);m=out['central_oracle']['regulative_mode'];modes[m]=modes.get(m,0)+1
            emission=record_surface_a(rt,out['cycle']['cycle_id'],f'Procedo con cautela sul caso {i%43}, mantenendo verificabili i limiti e senza trasformare inferenze interne in nuove prove.',intention_node_id=out.get('intention_node_id'));assert emission['evidence']==0
            xs=[n.activation/n.activation_ceiling for n in rt.nodes.values() if n.active and n.activation_ceiling>0];max_mean=max(max_mean,sum(xs)/len(xs) if xs else 0)
            assert out['crc']['roa_alignment']['crc_basic'];assert 0<=p<=1;assert out['workspace']['evidence_modified'] is False;assert all(n.activation<=n.activation_ceiling+1e-12 for n in rt.nodes.values())
            assert out['crc']['diagnostics']['neurofunctional_state_is_neural_measurement'] is False
            for state in out['crc']['neurofunctional_state'].values():
                for key in ('gain','precision','inhibition','plasticity','persistence','control_index'): assert 0<=state[key]<=1
        repeated='evaluate repeated stable intention';first=None
        for _ in range(a.novelty_tail):
            out=compile_cognitive_turn(rt,repeated,export_docx=False);first=first or next(n for n in rt.nodes.values() if n.kind==NodeKind.INTENTION and n.text==repeated).evidence
        same=next(n for n in rt.nodes.values() if n.kind==NodeKind.INTENTION and n.text==repeated)
        assert same.evidence==first==1.0;assert rt.nodes[sentinel.id].evidence==ev;assert max_mean<.70
        responses=[n for n in rt.nodes.values() if n.kind==NodeKind.RESPONSE];assert responses and all(n.evidence==0 for n in responses);assert all(len(n.metadata.get('response_cycles',[]))<=32 for n in responses)
        emission_events=sum(1 for e in rt.events_mem if e.get('op')=='SURFACE_A_EMIT');assert emission_events==a.turns
        result={'source_fingerprint':source_fingerprint(),'schema':'ikant-cognitive-stress/v0.2','status':'PASS','turns':a.turns,'novelty_tail':a.novelty_tail,'seed':a.seed,'nodes':len(rt.nodes),'cycles':rt.runtime['cycle_count'],'max_proto_self_index':round(max_proto,6),'max_mean_activation_ceiling_fraction':round(max_mean,6),'modes':modes,'sentinel_evidence_unchanged':True,'surface_a_emission_events':emission_events,'unique_response_nodes':len(responses),'response_cycle_window_bounded':True,'response_evidence_zero':True,'elapsed_s':round(time.monotonic()-t,3)};print(json.dumps(result,sort_keys=True));rt.close()
if __name__=='__main__':main()
