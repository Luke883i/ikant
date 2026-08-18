from __future__ import annotations
import argparse,json,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.admission import issue_receipt,save_receipt,probe,save_probe
from ikant.chat_session import ChatController
from ikant.model import Layer,NodeKind
from ikant.runtime import Runtime
from ikant.validation import source_fingerprint

def make_runtime(base:Path):
    root=base/'repo';root.mkdir();(root/'ikant').mkdir();(root/'ikant'/'runtime.py').write_text('# fixture');contract='fixture';(root/'IKANT_ACCESS_CONTRACT.md').write_text(contract);s=root/'.ikant';save_receipt(s,issue_receipt(contract,'I ACCEPT'));save_probe(s,probe(root,s,contract));return Runtime.initialize(s,contract,durable=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--turns',type=int,default=60);a=ap.parse_args();t=time.monotonic()
    with tempfile.TemporaryDirectory() as td:
        rt=make_runtime(Path(td));sentinel=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='chat stress sentinel',confidence=.8,evidence=.37,source_mode='document');ev=sentinel.evidence;controller=ChatController(rt)
        for i in range(a.turns):
            identity=i%17==0;intent='ciao, chi sei?' if identity else f'valuta il turno chat {i} con prudenza';out=controller.begin(intent,engine_label='GPT-STRESS')
            text='Sono iKant, con motore GPT-STRESS. Mantengo questa sessione verificabile e sintetica.' if identity else f'Procederei con prudenza nel turno {i}, mantenendo distinti fatti, limiti e inferenze della sessione locale.'
            rec=controller.close(out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id'],user_seq=out['chat']['user_seq']);assert rec['interaction_validated'];assert rec['evidence']==0;assert rt.integrity()['ok'];assert rt.nodes[sentinel.id].evidence==ev
        receipt=controller.log.verify();state_dir=rt.state_dir;session=rt.runtime['session_id'];rt.close();reopened=Runtime(state_dir);re_controller=ChatController(reopened);assert re_controller.log.verify()['runtime_session_id']==session;assert reopened.nodes[sentinel.id].evidence==ev;reopened.close()
        print(json.dumps({'schema':'ikant-chat-runtime-stress/v0.4-test','status':'PASS','turns':a.turns,'records':receipt['records'],'sentinel_evidence_unchanged':True,'source_fingerprint':source_fingerprint(),'elapsed_s':round(time.monotonic()-t,3)},sort_keys=True))
if __name__=='__main__':main()
