import json
import tempfile
import unittest
from pathlib import Path

from ikant.incarnate import bind_dashboard, validate_incarnate_dashboard


class Node:
    def __init__(self,text,cycle):
        self.text=text
        self.metadata={'surface_a_validated':True,'last_cycle_id':cycle}


class RT:
    def __init__(self,root):
        self.root=Path(root)
        self.state_dir=self.root/'.ikant';self.state_dir.mkdir(parents=True,exist_ok=True)
        self.runtime={'status':'ACTIVE','session_id':'SES-I','cognitive':{}}
        self.nodes={}


def pair(rt,cycle,*,docx=True,json_file=True,snapshot_cycle=None,session='SES-I'):
    c=rt.runtime['cognitive'];jp=rt.state_dir/'cognitive'/f'{cycle}.json';dp=rt.state_dir/'artifacts'/f'{cycle}.docx';jp.parent.mkdir(parents=True,exist_ok=True);dp.parent.mkdir(parents=True,exist_ok=True)
    if json_file:jp.write_text(json.dumps({'cycle_id':snapshot_cycle or cycle,'session_id':session}),encoding='utf-8')
    if docx:dp.write_bytes(b'PK-test-docx')
    c['last_snapshot']=str(jp);c['last_surface_b_docx']=str(dp)


class IncarnateV07Tests(unittest.TestCase):
    def test_pending_dashboard_has_bound_b_but_no_validated_a(self):
        with tempfile.TemporaryDirectory() as td:
            rt=RT(td);cycle='CYC-1';pair(rt,cycle);rt.runtime['cognitive']['pending_surface_a_cycle_id']=cycle;d={'overall':'STABLE','contract':{},'surface_b':{}}
            bind_dashboard(rt,d,cycle_id=cycle);self.assertEqual(d['incarnate']['state'],'PENDING');self.assertTrue(d['incarnate']['surface_b']['bound']);self.assertIsNone(d['incarnate']['surface_a']['text']);self.assertTrue(validate_incarnate_dashboard(d)[0])
    def test_validated_a_requires_same_cycle_json_and_docx(self):
        with tempfile.TemporaryDirectory() as td:
            rt=RT(td);pair(rt,'CYC-2',snapshot_cycle='CYC-stale');d={'overall':'STABLE','contract':{},'surface_b':{}}
            bind_dashboard(rt,d,surface_a_text='Surface A validata dentro dashboard.',cycle_id='CYC-2',surface_a_validated=True);self.assertEqual(d['incarnate']['state'],'BLOCKED');self.assertIn('surface_b_cycle_mismatch',d['incarnate']['errors'])
    def test_refresh_recovers_last_validated_surface_a(self):
        with tempfile.TemporaryDirectory() as td:
            rt=RT(td);cycle='CYC-3';pair(rt,cycle);node=Node('Risposta persistita e validata nel dashboard.',cycle);rt.nodes['R1']=node;rt.runtime['cognitive'].update({'last_surface_a_response_id':'R1','last_surface_a_cycle_id':cycle});d={'overall':'STABLE','contract':{},'surface_b':{}}
            bind_dashboard(rt,d);self.assertEqual(d['incarnate']['state'],'READY');self.assertEqual(d['incarnate']['surface_a']['text'],node.text);self.assertTrue(d['incarnate']['surface_b']['bound']);self.assertTrue(validate_incarnate_dashboard(d)[0])
    def test_missing_docx_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            rt=RT(td);cycle='CYC-4';pair(rt,cycle,docx=False);d={'overall':'STABLE','contract':{},'surface_b':{}}
            bind_dashboard(rt,d,surface_a_text='Risposta valida ma senza artefatto B.',cycle_id=cycle,surface_a_validated=True);self.assertEqual(d['overall'],'BLOCKED');self.assertIn('surface_b_docx_missing',d['incarnate']['errors'])
    def test_unvalidated_text_is_never_renderable_a(self):
        with tempfile.TemporaryDirectory() as td:
            rt=RT(td);cycle='CYC-5';pair(rt,cycle);d={'overall':'STABLE','contract':{},'surface_b':{}}
            bind_dashboard(rt,d,surface_a_text='Candidate text must not leak.',cycle_id=cycle,surface_a_validated=False);self.assertEqual(d['incarnate']['state'],'BLOCKED');self.assertIsNone(d['incarnate']['surface_a']['text']);self.assertIn('surface_a_text_not_validated',d['incarnate']['errors'])

if __name__=='__main__':unittest.main()
