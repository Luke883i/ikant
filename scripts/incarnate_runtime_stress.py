from __future__ import annotations
import argparse,json,tempfile,time
from pathlib import Path
from ikant.chat_session import ChatController
from ikant.dashboard_v05 import persist_dashboard
from ikant.host import emit_conforming_surface_a
from ikant.host_v05 import conforming_turn
from ikant.incarnate import validate_incarnate_dashboard
from ikant.model import Layer,NodeKind
from tests.helpers import active_runtime

def main():
    p=argparse.ArgumentParser();p.add_argument('--turns',type=int,default=60);a=p.parse_args();started=time.monotonic()
    with tempfile.TemporaryDirectory() as td:
        rt=active_runtime(Path(td),durable=True);sentinel=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='incarnate runtime sentinel',confidence=.8,evidence=.37,source_mode='document');before=sentinel.evidence;controller=ChatController(rt,turn_fn=conforming_turn,emit_fn=emit_conforming_surface_a,dashboard_fn=persist_dashboard)
        for i in range(a.turns):
            identity=i%17==0;intent='ciao, chi sei?' if identity else f'valuta il turno incarnate {i} con prudenza';out=controller.begin(intent,engine_label='GPT-E2E-RUNTIME');pending=json.loads((rt.state_dir/'dashboard.json').read_text(encoding='utf-8'));assert pending['incarnate']['state']=='PENDING';assert validate_incarnate_dashboard(pending)[0]
            text='Sono iKant, con motore GPT-E2E-RUNTIME. Mantengo questa sessione locale verificabile e senza uscire dal dashboard.' if identity else f'Procederei con prudenza nel turno {i}, mantenendo distinti fatti, limiti e inferenze della sessione locale.';rec=controller.close(out['cycle']['cycle_id'],text,intention_node_id=out['intention_node_id'],user_seq=out['chat']['user_seq']);ready=rec['dashboard'];assert ready['incarnate']['state']=='READY';assert validate_incarnate_dashboard(ready)[0];assert ready['incarnate']['surface_b']['bound'];assert Path(ready['incarnate']['surface_b']['docx']['path']).exists();assert rt.nodes[rec['response_id']].evidence==0;assert rt.nodes[sentinel.id].evidence==before;assert rt.integrity()['ok']
        refresh=persist_dashboard(rt);assert refresh['incarnate']['state']=='READY';assert validate_incarnate_dashboard(refresh)[0];receipt=controller.log.verify();rt.close()
    print(json.dumps({'schema':'ikant-incarnate-runtime-stress/v0.7-test','status':'PASS','turns':a.turns,'records':receipt['records'],'sentinel_evidence_unchanged':True,'elapsed_s':round(time.monotonic()-started,3)},sort_keys=True))

if __name__=='__main__':main()
