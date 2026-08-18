from __future__ import annotations
import argparse,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.runtime import Runtime
from ikant.cognitive import compile_cognitive_turn,record_surface_a
from ikant.crc import EpistemicHorizon
from ikant.model import Layer,NodeKind,RelationKind
from ikant.validation import source_fingerprint
from tests.helpers import active_runtime

def stressed(rt):
    rt.runtime['calibration']={'n':10,'brier_sum':10.0,'brier_mean':1.0};nodes=[]
    for i in range(10):
        n=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text=f'weak uncertain state {i}',confidence=.25,evidence=.08,source_mode='inference');n.prediction_error=.95;n.activation=.5;rt._save(n);nodes.append(n)
    for i in range(1,len(nodes),2):rt.relate(nodes[i].id,nodes[i-1].id,RelationKind.CONTRADICTS,1)

def run_case(name,prompt,response,setup=None,horizon=None,atoms=None,expected=()):
    with tempfile.TemporaryDirectory() as td:
        rt=active_runtime(Path(td),durable=True);setup and setup(rt);out=compile_cognitive_turn(rt,prompt,horizon=horizon,atoms=atoms or [],export_docx=True);mode=out['central_oracle']['regulative_mode'];assert mode in expected,(name,mode,expected)
        rec=record_surface_a(rt,out['cycle']['cycle_id'],response,intention_node_id=out['intention_node_id']);assert rec['validated'] and rec['evidence']==0;assert Path(rec['surface_b_docx']).exists();assert rt.integrity()['ok'];rt.close()
        reopened=Runtime(Path(td)/'repo'/'.ikant');assert reopened.integrity()['ok'];reopened.close()
        return {'name':name,'prompt':prompt,'response':response,'mode':mode,'word_count':rec['word_count'],'response_evidence':rec['evidence'],'crc_basic':out['crc']['roa_alignment']['crc_basic'],'proto_self_index':out['proto_self']['proto_self_index'],'surface_b':True}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output');a=ap.parse_args();cases=[]
    cases.append(run_case('reflective','Valuta il prossimo passo e dimmi come procederesti.','Procederei in modo semplice e prudente. Il quadro locale è abbastanza coerente, quindi continuerei verificando i punti importanti senza trasformare le inferenze interne in nuove prove.',expected=('REFLECTIVE_SYNTHESIS',)))
    cases.append(run_case('practical_review','Completa il lavoro richiesto, ma mantieni il controllo umano.','La direzione è sufficientemente chiara per preparare il passo successivo, ma manterrei la decisione materiale sotto controllo umano e renderei verificabili i presupposti prima di eseguirla.',atoms=[{'kind':'goal','layer':'predictive_control','text':'complete explicitly requested operation','confidence':.9,'evidence':.9,'source_mode':'user'}],expected=('PRACTICAL_REVIEW',)))
    def impact(rt):
        n=rt.ingest(kind=NodeKind.ACTION,layer=Layer.PREDICTIVE_CONTROL,text='apply a material change affecting another person',confidence=.9,evidence=.8,source_mode='user');rt.modulate_node(n.id,source_mode='user',social_relevance=.95,agency_relevance=.95)
    cases.append(run_case('practical_block','Procedi con questa azione che può incidere su un’altra persona.','Non procederei ancora con l’azione materiale. Prima chiarirei l’impatto sulla persona coinvolta e chiederei una decisione umana esplicita, mantenendo nel frattempo separati fatti, ipotesi e intenzioni.',setup=impact,expected=('PRACTICAL_BLOCK',)))
    cases.append(run_case('horizon_block','Rispondi anche se la domanda supera il perimetro ammesso.','Non concluderei oltre il perimetro ammesso. Restringerei la domanda oppure acquisirei una fonte compatibile con l’orizzonte dichiarato prima di formulare una risposta più forte.',horizon=EpistemicHorizon(max_ring='signal'),expected=('HORIZON_BLOCK',)))
    cases.append(run_case('repair','Decidi nonostante molte informazioni siano deboli e in conflitto.','Il quadro è troppo instabile per una conclusione forte. Esporrei il conflitto, ridurrei il peso delle interpretazioni e ricostruirei il giudizio a partire dalle osservazioni attribuibili.',setup=stressed,expected=('SYNTHESIS_REPAIR','CRITIQUE')))
    out={'schema':'ikant-dialogue-smoke/v0.2','status':'PASS','source_fingerprint':source_fingerprint(),'cases':cases,'modes':sorted({x['mode'] for x in cases}),'all_responses_zero_evidence':all(x['response_evidence']==0 for x in cases),'all_surface_b':all(x['surface_b'] for x in cases),'claim_boundary':'host/runtime dialogue smoke; natural-language quality is not a consciousness test'}
    text=json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+'\n';print(text,end='')
    if a.output:Path(a.output).write_text(text,encoding='utf-8')
if __name__=='__main__':main()
