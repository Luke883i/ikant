import tempfile,unittest
from pathlib import Path
from ikant.model import *
from tests.helpers import active_runtime
class Compression(unittest.TestCase):
 def test_compression_is_derived_not_directive(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));
   for _ in range(8):rt.ingest(kind=NodeKind.GOAL,layer=Layer.MEMORY,text='repeat motif',confidence=.8,evidence=.7,source_mode='user')
   r=rt.compress_history();self.assertEqual(rt.nodes[r['summary_node_id']].source_mode,'runtime_derived');self.assertFalse(any(d['source_mode']=='runtime_derived' for d in rt.slice('repeat motif',limit=20)['directives']))
 def test_emergent_process_pattern_retracts_without_reobservation(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td))
   for _ in range(10):rt.ingest(kind=NodeKind.GOAL,layer=Layer.MEMORY,text='stable echo process',confidence=.7,evidence=.6,source_mode='user')
   first=rt.compress_history();self.assertIn('echo_recurrence',first['motifs']);pid=first['pattern_node_ids'][0];self.assertTrue(rt.nodes[pid].active);pe=rt.nodes[pid].evidence
   for i in range(rt.params.pattern_miss_retract_threshold):
    rt.ingest(kind=NodeKind.OBSERVATION,layer=Layer.SIGNAL,text=f'fresh calm observation {i}',confidence=.7,evidence=.6,source_mode='document');rt.compress_history()
   self.assertFalse(rt.nodes[pid].active);self.assertEqual(rt.nodes[pid].evidence,pe)
 def test_derived_working_set_is_bounded_and_archived(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td))
   for i in range(90):
    rt.ingest(kind=NodeKind.OBSERVATION,layer=Layer.SIGNAL,text=f'bounded compression observation {i}',confidence=.7,evidence=.6,source_mode='document');rt.compress_history()
   active=[n for n in rt.nodes.values() if n.active and n.metadata.get('compression_owned') and n.metadata.get('derivation_kind')=='summary']
   inactive=[n for n in rt.nodes.values() if not n.active and n.metadata.get('compression_owned')]
   self.assertLessEqual(len(active),rt.params.max_active_summaries);self.assertLessEqual(len(inactive),rt.params.max_inactive_derived_nodes);self.assertTrue(rt.derived_archive_mem)
 def test_trend_modulates_policy(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));n=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.MEMORY,text='revision target',confidence=.8,evidence=.7,source_mode='user');base=rt.concentric_cycle('revision target')['output_policy']['epistemic_caution']
   for i in range(5):
    x=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.MEMORY,text=f'temp {i}',confidence=.5,evidence=.5,source_mode='user');rt.retract_node(x.id,reason='revision');rt.compress_history()
   after=rt.concentric_cycle('revision target')['output_policy']['epistemic_caution'];self.assertGreaterEqual(after,base);self.assertEqual(rt.nodes[n.id].evidence,.7)
