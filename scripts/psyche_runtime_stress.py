from __future__ import annotations
import argparse,json,random,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.admission import issue_receipt,save_receipt,probe,save_probe
from ikant.chat_session import ChatController
from ikant.host import emit_conforming_surface_a
from ikant.host_v05 import conforming_turn
from ikant.dashboard_v05 import persist_dashboard
from ikant.model import Layer,NodeKind
from ikant.runtime import Runtime
from ikant.psyche import validate_functional_psyche
def make_runtime(base:Path):
 root=base/'repo';root.mkdir();(root/'ikant').mkdir();(root/'ikant'/'runtime.py').write_text('# fixture');contract='fixture';(root/'IKANT_ACCESS_CONTRACT.md').write_text(contract);s=root/'.ikant';save_receipt(s,issue_receipt(contract,'I ACCEPT'));save_probe(s,probe(root,s,contract));return Runtime.initialize(s,contract,durable=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--turns',type=int,default=300);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);start=time.monotonic()
 with tempfile.TemporaryDirectory() as td:
  rt=make_runtime(Path(td));sentinel=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text='durable psyche sentinel evidence',confidence=.8,evidence=.39,source_mode='document');ev=sentinel.evidence;controller=ChatController(rt,turn_fn=conforming_turn,emit_fn=emit_conforming_surface_a,dashboard_fn=persist_dashboard);labels=set();maturity=set();max_tension=0.;max_collapse=0.
  for i in range(a.turns):
   out=controller.begin(f'Valuta scenario {i%53} con vincolo {rng.randrange(11)} e mantieni separati fatti e ipotesi.',engine_label='v0.5-stress-engine');p=out['functional_psyche'];ok,errors=validate_functional_psyche(p);assert ok,errors;labels.add(p['affective_field']['label']);maturity.add(p['epistemic_accumulation']['maturity_mode']);max_tension=max(max_tension,p['affective_field']['tension']);max_collapse=max(max_collapse,p['collapse_emergence']['summary']['max_collapse']);rec=controller.close(out['cycle']['cycle_id'],'Mantengo distinto ciò che è attribuibile dalle inferenze interne e rivedo il giudizio se emergono conflitti o prove migliori.',intention_node_id=out['intention_node_id'],user_seq=out['chat']['user_seq']);assert rec['evidence']==0;assert rt.nodes[sentinel.id].evidence==ev;assert not out['workspace']['evidence_modified']
  integrity=rt.integrity();chat=controller.log.verify();assert integrity['ok'] and chat['ok'];state=Path(rt.state_dir);assert (state/'psyche.json').exists() and (state/'dashboard.json').exists();rt.close();reopened=Runtime(Path(td)/'repo'/'.ikant');assert reopened.integrity()['ok'];reopened.close()
 print(json.dumps({'schema':'ikant-psyche-runtime-stress/v0.5-test','status':'PASS','turns':a.turns,'seed':a.seed,'affective_labels':sorted(labels),'maturity_modes':sorted(maturity),'max_tension':round(max_tension,6),'max_collapse':round(max_collapse,6),'sentinel_evidence_unchanged':True,'durable_reopen':True,'elapsed_s':round(time.monotonic()-start,3)},sort_keys=True))
if __name__=='__main__':main()
