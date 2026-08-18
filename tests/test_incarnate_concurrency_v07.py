import threading
import time
import unittest
from unittest.mock import patch
from ikant import host_v05

class IncarnateConcurrencyV07Tests(unittest.TestCase):
    def test_concurrent_turns_serialize_to_one_pending_cycle(self):
        class RT:
            def __init__(self):self.runtime={'status':'ACTIVE','session_id':'SES-C','cognitive':{},'host':{}}
            def require_active(self):
                if self.runtime['status']!='ACTIVE':raise PermissionError
            def _write_runtime(self):pass
            def _event(self,*a,**k):pass
        rt=RT();barrier=threading.Barrier(3);success=[];errors=[];compile_calls=[]
        def fake_compile(runtime,intent,**kw):
            compile_calls.append(intent);time.sleep(.03);return {'cycle':{'cycle_id':'CYC-'+intent},'surface_b_snapshot':{},'surface_b_json':None,'surface_b_docx':None}
        def worker(name):
            barrier.wait()
            try:success.append(host_v05.conforming_turn(rt,name,engine_label='GPT-C'))
            except Exception as exc:errors.append(exc)
        with patch.object(host_v05,'_bind_engine',return_value='GPT-C'),patch.object(host_v05,'compile_cognitive_turn',side_effect=fake_compile),patch.object(host_v05,'build_interaction_contract',return_value={'schema':'x','profile':{'kind':'simple'}}):
            ts=[threading.Thread(target=worker,args=(x,)) for x in ('A','B')]
            [t.start() for t in ts];barrier.wait();[t.join() for t in ts]
        self.assertEqual(len(success),1);self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],RuntimeError);self.assertEqual(len(compile_calls),1);self.assertTrue(rt.runtime['cognitive'].get('pending_surface_a_cycle_id'))

    def test_concurrent_surface_a_close_allows_exactly_one(self):
        class RT:
            def __init__(self):self.runtime={'status':'ACTIVE','session_id':'SES-C','cognitive':{'pending_surface_a_cycle_id':'CYC-1'}}
        rt=RT();barrier=threading.Barrier(3);success=[];errors=[]
        def fake_emit(runtime,cycle_id,text,intention_node_id=None):
            if runtime.runtime['cognitive'].get('pending_surface_a_cycle_id')!=cycle_id:raise PermissionError('not pending')
            time.sleep(.03);runtime.runtime['cognitive'].pop('pending_surface_a_cycle_id',None);return {'response_id':'R1'}
        def worker():
            barrier.wait()
            try:success.append(host_v05.emit_incarnate_surface_a(rt,'CYC-1','valid text'))
            except Exception as exc:errors.append(exc)
        with patch.object(host_v05,'_emit_conforming_surface_a',side_effect=fake_emit):
            ts=[threading.Thread(target=worker) for _ in range(2)];[t.start() for t in ts];barrier.wait();[t.join() for t in ts]
        self.assertEqual(len(success),1);self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],PermissionError)

if __name__=='__main__':unittest.main()
