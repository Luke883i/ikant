from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from ikant.human_frame import build_actor_binding, build_human_frame, issue_interaction_receipt
from ikant.memory_governance import apply_forget, forget_action_fingerprint, governance_events, preview_forget, reconcile_memory_governance
from ikant.model import Layer, Node, NodeKind, Relation, RelationKind
from ikant.temporal_memory import materialize_temporal_memory, temporal_available
SECRET=b'm'*32;SESSION='SES-S19';BINDING=build_actor_binding(session_id=SESSION,channel_id='web-paired',secret=SECRET)
def node(nid,kind,text,source='runtime_derived',e=.7):return Node(nid,NodeKind(kind),Layer.MEMORY,text,.7,e,source)
class RT:
 def __init__(self,state_dir:Path):self.state_dir=state_dir;self.nodes={};self.relations={};self.runtime={'session_id':SESSION,'temporal_memory':{}};self.graph={'seq':0};self.durable=True
 def _save(self,n):self.nodes[n.id]=n
 def _persist(self):pass
 def _write_runtime(self):(self.state_dir/'runtime.json').write_text(json.dumps(self.runtime),encoding='utf-8')
def authorize(preview,seq=1):
 frame=build_human_frame(session_id=SESSION,actor_binding_id=BINDING.binding_id,frame_seq=seq,purpose='ACTION_CONFIRMATION',title='Dimentica',body='Conferma impatto memoria.',action_fingerprint=forget_action_fingerprint(preview),subject_id=preview['node_id']);return frame,issue_interaction_receipt(frame,binding=BINDING,decision='APPROVE',secret=SECRET)
class MemoryGovernanceS19Tests(unittest.TestCase):
 def test_support_aware_forget_invalidates_only_unsupported_derived_chain(self):
  with tempfile.TemporaryDirectory() as td:
   rt=RT(Path(td));a=node('A','memory','root','user');b=node('B','claim','independent','document');d=node('D','summary','derived');e=node('E','pattern','derived2');rt.nodes={x.id:x for x in (a,b,d,e)};rt.relations={'R1':Relation('R1','A','D',RelationKind.SUPPORTS,.8),'R2':Relation('R2','B','D',RelationKind.SUPPORTS,.8),'R3':Relation('R3','A','E',RelationKind.ABSTRACTS,.8)};before={k:v.evidence for k,v in rt.nodes.items()};p=preview_forget(rt,'A',reason='user forget');self.assertEqual(set(p['suppressed_states']),{'A','E'});self.assertEqual(p['preserved_node_ids'],['D']);f,r=authorize(p);out=apply_forget(rt,p,f,r,binding=BINDING,secret=SECRET);self.assertEqual(out['status'],'COMMITTED');self.assertFalse(temporal_available(a));self.assertFalse(temporal_available(e));self.assertTrue(temporal_available(d));self.assertEqual(before,{k:v.evidence for k,v in rt.nodes.items()})
 def test_preview_binds_only_declared_memory_dependent_tasks(self):
  with tempfile.TemporaryDirectory() as td:
   rt=RT(Path(td));rt.nodes={'A':node('A','memory','root','user')};tasks={'tasks':[{'task_id':'T1','status':'ACTIVE','memory_dependency_ids':['A']},{'task_id':'T2','status':'ACTIVE','memory_dependency_ids':[]}]};p=preview_forget(rt,'A',reason='forget',task_projection=tasks);self.assertEqual(p['dependent_task_ids'],['T1']);self.assertEqual(p['independent_task_ids'],['T2'])
 def test_confirmation_is_exact_and_preview_drift_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   rt=RT(Path(td));rt.nodes={'A':node('A','memory','root','user'),'D':node('D','summary','derived')};p=preview_forget(rt,'A',reason='forget');f,r=authorize(p);rt.relations['R']=Relation('R','A','D',RelationKind.SUPPORTS,.8)
   with self.assertRaises(RuntimeError):apply_forget(rt,p,f,r,binding=BINDING,secret=SECRET)
 def test_governance_journal_reasserts_tombstone_after_restore(self):
  with tempfile.TemporaryDirectory() as td:
   rt=RT(Path(td));rt.nodes={'A':node('A','memory','root','user')};p=preview_forget(rt,'A',reason='forget');f,r=authorize(p);apply_forget(rt,p,f,r,binding=BINDING,secret=SECRET);rt.nodes['A'].metadata['temporal_state']='ACTIVE';rt.nodes['A'].active=True;out=reconcile_memory_governance(rt);self.assertFalse(temporal_available(rt.nodes['A']));self.assertIn('A',out['reconciled_node_ids']);self.assertEqual(len(governance_events(rt)),1)
 def test_forget_tombstone_replays_across_future_session_restore(self):
  with tempfile.TemporaryDirectory() as td:
   rt=RT(Path(td));rt.nodes={'A':node('A','memory','root','user')};p=preview_forget(rt,'A',reason='forget');f,r=authorize(p);apply_forget(rt,p,f,r,binding=BINDING,secret=SECRET);rt.runtime['session_id']='SES-RESTORED';rt.nodes['A'].metadata['temporal_state']='ACTIVE';rt.nodes['A'].active=True;out=reconcile_memory_governance(rt);self.assertFalse(temporal_available(rt.nodes['A']));self.assertIn('A',out['reconciled_node_ids'])
 def test_temporal_memory_projection_excludes_forgotten_after_commit(self):
  with tempfile.TemporaryDirectory() as td:
   rt=RT(Path(td));rt.nodes={'A':node('A','memory','secret','user')};p=preview_forget(rt,'A',reason='forget');f,r=authorize(p);apply_forget(rt,p,f,r,binding=BINDING,secret=SECRET);m=materialize_temporal_memory(rt);self.assertFalse(m['records']['A']['available']);self.assertEqual(m['records']['A']['state'],'FORGOTTEN')
if __name__=='__main__':unittest.main()