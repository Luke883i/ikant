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
 def test_trend_modulates_policy(self):
  with tempfile.TemporaryDirectory() as td:
   rt=active_runtime(Path(td));n=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.MEMORY,text='revision target',confidence=.8,evidence=.7,source_mode='user');base=rt.concentric_cycle('revision target')['output_policy']['epistemic_caution']
   for i in range(5):
    x=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.MEMORY,text=f'temp {i}',confidence=.5,evidence=.5,source_mode='user');rt.retract_node(x.id,reason='revision');rt.compress_history()
   after=rt.concentric_cycle('revision target')['output_policy']['epistemic_caution'];self.assertGreaterEqual(after,base);self.assertEqual(rt.nodes[n.id].evidence,.7)
