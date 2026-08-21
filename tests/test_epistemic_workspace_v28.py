from __future__ import annotations
import json,tempfile,threading,unittest
from pathlib import Path
from ikant.epistemic_workspace import EpistemicWorkspaceCoordinator,EpistemicWorkspaceError,EpistemicWorkspaceReader
from ikant.epistemic_projection import EPISTEMIC_INDEX_SCHEMA,EPISTEMIC_WORKSPACE_SCHEMA,MAX_HISTORY,MAX_OBJECTS,MAX_SNAPSHOT_BYTES
from scripts.epistemic_workspace_edges import run as run_epistemic_edges
ROOT=Path(__file__).resolve().parents[1]
FRAME={'runtime_session_id':'SES-S10','epoch':2,'frame_seq':7,'frame_sha256':'a'*64};CYCLE='CYC-S10-1'

def snapshot(cycle=CYCLE,session='SES-S10',objects=1):
 return {'cycle_id':cycle,'session_id':session,'intent_sha256':'b'*64,'reticulum':{'rings':['signal','memory','kant_oracle'],'ring_states':{'signal':{'activation':.7},'memory':{'activation':.4}},'transmissions':[{}],'diagnostics':{'epistemic_debt_open_count':1,'mean_coefficient_of_collapse':.2,'reticular_irreducibility_proxy':.8}},'dynamic_state':{'proto_self':{'proto_self_index':.5},'central_oracle':{'regulative_mode':'REFLECTIVE_SYNTHESIS'},'central_projection':{'must_surface_conflicts':['conflict x'],'interpretive_macro_candidates':['hypothesis y']},'mined_atoms':[{'id':f'n{i}','kind':'claim','text':f'claim {i}','source_mode':'user','confidence':.8,'evidence':.9} for i in range(objects)],'runtime_backlog':['resolve debt']},'audit':{'recent_events':[{'seq':1,'type':'COGNITIVE_COMPILE','cycle_id':cycle,'payload':{'cycle_id':cycle,'secret':'hidden','phase':'COMPILE'}}]}}

def make_root(objects=1):
 td=tempfile.TemporaryDirectory();root=Path(td.name);state=root/'.ikant';(state/'cognitive').mkdir(parents=True);(state/'artifacts').mkdir();(state/'runtime.json').write_text(json.dumps({'status':'ACTIVE','session_id':'SES-S10','cognitive':{'last_surface_a_cycle_id':CYCLE}}),encoding='utf-8');(state/'cognitive'/f'{CYCLE}.json').write_text(json.dumps(snapshot(objects=objects)),encoding='utf-8');(state/'artifacts'/f'CRC_SNAPSHOT_{CYCLE}.docx').write_bytes(b'PK\x03\x04fake');return td,root

class FakeShell:
 def __init__(self):self._lock=threading.RLock();self._pending=None;self._last_acked_frame=dict(FRAME)
 def _require_bound(self,s,sh,c):
  if (s,sh,c)!=('SES-S10','shell-1234567890123456','client-1234567890123456'):raise PermissionError('writer mismatch')
class FakeDelegate:
 def __init__(self):self.web_shell=FakeShell()
 def _active_session_id(self):return 'SES-S10'
class FakeBase:
 def __init__(self,root):self.root=root;self.delegate=FakeDelegate()
 def _delegate_or_raise(self):return self.delegate
 def product_status(self):return {'ok':True}

class EpistemicWorkspaceV28Tests(unittest.TestCase):
 def test_reader_projects_bounded_read_only_surface_b(self):
  td,root=make_root();self.addCleanup(td.cleanup);r=EpistemicWorkspaceReader(root);idx=r.index(frame_binding=FRAME);self.assertEqual(idx['schema'],EPISTEMIC_INDEX_SCHEMA);self.assertEqual(idx['history_limit'],MAX_HISTORY);self.assertTrue(idx['read_only']);self.assertEqual(idx['epistemic_authority'],0.0);c=r.cycle(CYCLE,frame_binding=FRAME);self.assertEqual(c['schema'],EPISTEMIC_WORKSPACE_SCHEMA);self.assertEqual(len(c['graph']['nodes']),3);self.assertTrue(any(x['kind']=='conflict' for x in c['objects']));self.assertNotIn('secret',json.dumps(c['events']));self.assertIn('phase',json.dumps(c['events']));self.assertTrue(c['projection_is_not_source_snapshot']);self.assertTrue(c['presentation_is_not_evidence']);self.assertTrue(c['presentation_is_not_authorization'])
 def test_history_and_object_cardinality_are_bounded(self):
  td,root=make_root(objects=MAX_OBJECTS+40);self.addCleanup(td.cleanup);state=root/'.ikant'
  for i in range(MAX_HISTORY+20):
   cid=f'CYC-H-{i:03d}';(state/'cognitive'/f'{cid}.json').write_text(json.dumps(snapshot(cid,objects=0)),encoding='utf-8')
  r=EpistemicWorkspaceReader(root);self.assertLessEqual(len(r.index(frame_binding=FRAME)['cycles']),MAX_HISTORY);self.assertEqual(len(r.cycle(CYCLE,frame_binding=FRAME)['objects']),MAX_OBJECTS)
 def test_session_drift_traversal_and_oversize_fail_closed(self):
  td,root=make_root();self.addCleanup(td.cleanup);r=EpistemicWorkspaceReader(root);bad=dict(FRAME);bad['runtime_session_id']='OTHER'
  with self.assertRaises(EpistemicWorkspaceError):r.index(frame_binding=bad)
  with self.assertRaises(EpistemicWorkspaceError):r.cycle('../runtime',frame_binding=FRAME)
  p=root/'.ikant'/'cognitive'/f'{CYCLE}.json';p.write_bytes(b'{' + b'x'*MAX_SNAPSHOT_BYTES + b'}')
  with self.assertRaises(EpistemicWorkspaceError):r.cycle(CYCLE,frame_binding=FRAME)
 def test_docx_download_requires_same_session_cycle_json_companion(self):
  td,root=make_root();self.addCleanup(td.cleanup);r=EpistemicWorkspaceReader(root);meta,raw,_=r.artifact(CYCLE,'DOCX',frame_binding=FRAME);self.assertTrue(meta['read_only']);self.assertEqual(raw,b'PK\x03\x04fake');p=root/'.ikant'/'cognitive'/f'{CYCLE}.json';bad=snapshot(session='OTHER');p.write_text(json.dumps(bad),encoding='utf-8')
  with self.assertRaises(EpistemicWorkspaceError):r.artifact(CYCLE,'DOCX',frame_binding=FRAME)
 def test_coordinator_requires_exact_last_ack_single_writer_and_no_pending_frame(self):
  td,root=make_root();self.addCleanup(td.cleanup);base=FakeBase(root);c=EpistemicWorkspaceCoordinator(base);self.assertEqual(c.epistemic_index('shell-1234567890123456','client-1234567890123456',FRAME)['current_cycle_id'],CYCLE);bad=dict(FRAME);bad['frame_seq']=8
  with self.assertRaises(EpistemicWorkspaceError):c.epistemic_index('shell-1234567890123456','client-1234567890123456',bad)
  with self.assertRaises(PermissionError):c.epistemic_index('wrong-shell-1234567890','client-1234567890123456',FRAME)
  base.delegate.web_shell._pending={'seq':8}
  with self.assertRaises(EpistemicWorkspaceError):c.epistemic_index('shell-1234567890123456','client-1234567890123456',FRAME)
 def test_edge_oracle_converges_at_registered_boundary_scales(self):
  for seed in (17,883,2026):
   short=run_epistemic_edges(100000,10000,seed);self.assertEqual(short['violations'],0);self.assertEqual(short['families_covered'],40);self.assertEqual(short['tail_novelty'],0)
  long_tail=run_epistemic_edges(100000,100000,883);self.assertEqual(long_tail['tail_novelty'],0);self.assertEqual(long_tail['signatures'],440)
 def test_static_ui_and_http_preserve_s9_semantic_surface(self):
  js=(ROOT/'ikant/web/epistemic.js').read_text(encoding='utf-8');css=(ROOT/'ikant/web/epistemic.css').read_text(encoding='utf-8');http=(ROOT/'ikant/epistemic_http.py').read_text(encoding='utf-8');app=(ROOT/'ikant/local_app.py').read_text(encoding='utf-8');index=(ROOT/'ikant/web/index.html').read_text(encoding='utf-8');sw=(ROOT/'ikant/web/sw.js').read_text(encoding='utf-8');bootstrap_path=ROOT/'ikant/bootstrap_http.py';bootstrap=bootstrap_path.read_text(encoding='utf-8') if bootstrap_path.is_file() else ''
  self.assertEqual(index.count('id="dashboard"'),1);self.assertNotIn('dashboard',js);self.assertIn('/api/v4/epistemic/index',http);self.assertIn('/api/v4/epistemic/artifact',http);self.assertIn('make_handler',http);self.assertNotIn('do_POST',http);self.assertIn('Graph',js);self.assertIn('List',js);self.assertIn("event.code==='Space'",js);self.assertIn('bindingHeaders',js);self.assertNotIn('https://',js+css);self.assertIn('prefers-reduced-motion:reduce',css);self.assertIn('EpistemicWorkspaceCoordinator',app);self.assertTrue('epistemic_http' in app or ('bootstrap_http' in app and 'make_epistemic_handler' in bootstrap and '.epistemic_http' in bootstrap));self.assertIn('const CACHE=',sw);self.assertIn('keys.filter(k=>k!==CACHE)',sw)
if __name__=='__main__':unittest.main()
