import json, unittest
from pathlib import Path
from types import SimpleNamespace
from ikant.model import Node,NodeKind,Layer,Relation,RelationKind
from ikant.temporal_memory import classify_node,temporal_available,set_temporal_state,materialize_temporal_memory
from ikant.commitments import register_commitment,supersede_commitment,retract_commitment,commitment_projection
from ikant.dependency_invalidation import invalidate_source
from ikant.temporal_replay import replay_temporal_events,validate_temporal_replay,temporal_events
from ikant.temporal_core import finalize_temporal_core,ingest_temporal_turn
from ikant.model import node_to_dict

class RT:
    def __init__(self):
        self.nodes={};self.relations={};self.runtime={'session_id':'S','temporal_memory':{}};self.graph={'seq':0};self.events_mem=[];self.durable=False
    def _save(self,n):self.nodes[n.id]=n
    def _write_runtime(self):pass
    def _persist(self):pass
    def _event(self,op,subject,payload):
        self.graph['seq']+=1;e={'seq':self.graph['seq'],'op':op,'subject':subject,'payload':payload};self.events_mem.append(e);return e['seq']

def n(i,kind,text,source='user',e=.7):return Node(i,NodeKind(kind),Layer.MEMORY,text,.7,e,source)

class TemporalV14(unittest.TestCase):
    def test_classes_do_not_change_evidence(self):
        rt=RT();rt.nodes={'O':n('O','observation','event'),'C':n('C','claim','fact'),'G':n('G','goal','ship'),'P':n('P','pattern','motif','runtime_derived')}
        before={k:v.evidence for k,v in rt.nodes.items()};out=materialize_temporal_memory(rt)
        self.assertEqual(before,{k:v.evidence for k,v in rt.nodes.items()});self.assertEqual(classify_node(rt.nodes['G']),'commitment');self.assertEqual(classify_node(rt.nodes['P']),'interpretive');self.assertEqual(out['summary']['epistemic_authority'],0)
    def test_supersession_makes_old_unavailable_and_new_current(self):
        rt=RT();rt.nodes={'A':n('A','constraint','use api v1'),'B':n('B','constraint','use api v2')}
        register_commitment(rt,'A');supersede_commitment(rt,'A','B',reason='version migration')
        self.assertFalse(temporal_available(rt.nodes['A']));self.assertTrue(temporal_available(rt.nodes['B']))
        p=commitment_projection(rt);self.assertEqual(p['active_node_ids'],['B']);self.assertEqual(rt.nodes['A'].evidence,.7)
    def test_cannot_resupersede_nonactive_commitment(self):
        rt=RT();rt.nodes={'A':n('A','goal','a'),'B':n('B','goal','b'),'C':n('C','goal','c')};supersede_commitment(rt,'A','B',reason='r1')
        with self.assertRaises(ValueError):supersede_commitment(rt,'A','C',reason='r2')
    def test_partial_source_revocation_preserves_claim(self):
        rt=RT();rt.nodes={'A':n('A','claim','build passed','document')}
        graph={'sources':{'S1':{'id':'S1','external':True,'provenance_key':'ci:a'},'S2':{'id':'S2','external':True,'provenance_key':'ci:b'}},'claims':{'A':{'source_ids':['S1','S2'],'observation_ids':['O1','O2']}},'observations':{'O1':{'source_id':'S1','independent':True},'O2':{'source_id':'S2','independent':True}}}
        out=invalidate_source(rt,'ci:a',reason='source withdrawn',provenance_graph=graph)
        self.assertEqual(out['suppressed_node_ids'],[]);self.assertEqual(out['preserved_node_ids'],['A']);self.assertTrue(temporal_available(rt.nodes['A']));self.assertEqual(rt.nodes['A'].evidence,.7)
    def test_last_independent_source_revocation_suppresses_claim_and_derived_chain(self):
        rt=RT();rt.nodes={'A':n('A','claim','build passed','document'),'D':n('D','summary','derived result','runtime_derived'),'E':n('E','pattern','derived pattern','runtime_derived')}
        rt.relations={'R1':Relation('R1','A','D',RelationKind.SUPPORTS,.8),'R2':Relation('R2','D','E',RelationKind.ABSTRACTS,.8)}
        graph={'sources':{'S1':{'id':'S1','external':True,'provenance_key':'ci:a'}},'claims':{'A':{'source_ids':['S1'],'observation_ids':['O1']},'D':{'source_ids':[],'observation_ids':[]},'E':{'source_ids':[],'observation_ids':[]}},'observations':{'O1':{'source_id':'S1','independent':True}}}
        before={k:v.evidence for k,v in rt.nodes.items()};out=invalidate_source(rt,'S1',reason='bad artifact',provenance_graph=graph)
        self.assertEqual(set(out['suppressed_node_ids']),{'A','D','E'});self.assertEqual(rt.nodes['A'].metadata['temporal_state'],'SOURCE_REVOKED');self.assertEqual(rt.nodes['D'].metadata['temporal_state'],'DEPENDENCY_INVALIDATED');self.assertEqual(before,{k:v.evidence for k,v in rt.nodes.items()})
    def test_replay_matches_source_invalidation_states(self):
        rt=RT();rt.nodes={'A':n('A','claim','build passed','document'),'D':n('D','summary','derived result','runtime_derived')}
        rt.relations={'R1':Relation('R1','A','D',RelationKind.SUPPORTS,.8)}
        graph={'sources':{'S1':{'id':'S1','external':True,'provenance_key':'ci:a'}},'claims':{'A':{'source_ids':['S1'],'observation_ids':['O1']},'D':{'source_ids':[],'observation_ids':[]}},'observations':{'O1':{'source_id':'S1','independent':True}}}
        invalidate_source(rt,'S1',reason='bad artifact',provenance_graph=graph)
        r=validate_temporal_replay(rt);self.assertTrue(r['ok'],r['mismatches'])

    def test_nonindependent_external_binding_does_not_preserve_claim(self):
        rt=RT();rt.nodes={'A':n('A','claim','build passed','document')}
        graph={'sources':{'S1':{'id':'S1','external':True,'provenance_key':'ci:a'},'S2':{'id':'S2','external':True,'provenance_key':'mirror:a'}},'claims':{'A':{'source_ids':['S1','S2'],'observation_ids':['O1','O2']}},'observations':{'O1':{'source_id':'S1','independent':True},'O2':{'source_id':'S2','independent':False}}}
        invalidate_source(rt,'S1',reason='source withdrawn',provenance_graph=graph)
        self.assertFalse(temporal_available(rt.nodes['A']));self.assertEqual(rt.nodes['A'].metadata['temporal_state'],'SOURCE_REVOKED')

    def test_external_target_is_not_transitively_suppressed(self):
        rt=RT();rt.nodes={'A':n('A','claim','source A','document'),'B':n('B','claim','source B','repository')};rt.relations={'R':Relation('R','A','B',RelationKind.SUPPORTS,.8)}
        graph={'sources':{'S1':{'id':'S1','external':True,'provenance_key':'x'},'S2':{'id':'S2','external':True,'provenance_key':'y'}},'claims':{'A':{'source_ids':['S1'],'observation_ids':['O1']},'B':{'source_ids':['S2'],'observation_ids':['O2']}},'observations':{'O1':{'source_id':'S1','independent':True},'O2':{'source_id':'S2','independent':True}}}
        invalidate_source(rt,'x',reason='bad',provenance_graph=graph);self.assertTrue(temporal_available(rt.nodes['B']))
    def test_replay_matches_commitment_state(self):
        rt=RT();rt.nodes={'A':n('A','goal','old'),'B':n('B','goal','new')};supersede_commitment(rt,'A','B',reason='explicit revision')
        r=validate_temporal_replay(rt);self.assertTrue(r['ok'],r['mismatches']);self.assertEqual(r['state']['nodes']['A']['commitment_status'],'SUPERSEDED')
    def test_replay_detects_tamper(self):
        rt=RT();rt.nodes={'A':n('A','goal','old')};register_commitment(rt,'A');rt.nodes['A'].metadata['commitment_status']='RETRACTED'
        self.assertFalse(validate_temporal_replay(rt)['ok'])
    def test_failed_resupersession_has_no_event_side_effect(self):
        rt=RT();rt.nodes={'A':n('A','goal','a'),'B':n('B','goal','b'),'C':n('C','goal','c')};supersede_commitment(rt,'A','B',reason='r1');before=len(rt.events_mem)
        with self.assertRaises(ValueError):supersede_commitment(rt,'A','C',reason='r2')
        self.assertEqual(before,len(rt.events_mem));self.assertNotIn('commitment_id',rt.nodes['C'].metadata)
    def test_temporal_control_events_do_not_enter_cognitive_event_stream(self):
        rt=RT();rt.nodes={'A':n('A','goal','x')};register_commitment(rt,'A');self.assertEqual(rt.events_mem,[]);self.assertGreater(len(temporal_events(rt)),0)
    def test_temporal_journal_hash_tamper_fails_closed(self):
        rt=RT();rt.nodes={'A':n('A','goal','x')};register_commitment(rt,'A');rt._ikant_temporal_events_mem[0]['payload']['status']='RETRACTED'
        r=validate_temporal_replay(rt);self.assertFalse(r['ok']);self.assertTrue(any('journal:' in x for x in r['mismatches']))
    def test_unjournaled_temporal_state_is_detected(self):
        rt=RT();rt.nodes={'A':n('A','claim','x')};rt.nodes['A'].metadata['temporal_state']='FORGOTTEN';rt.nodes['A'].active=False
        self.assertFalse(validate_temporal_replay(rt)['ok'])

    def test_temporal_api_cannot_revive_non_temporal_retraction(self):
        rt=RT();rt.nodes={'A':n('A','claim','fact')};rt.nodes['A'].active=False
        with self.assertRaises(ValueError):set_temporal_state(rt,'A','ACTIVE',reason='bad revive')
        self.assertFalse(rt.nodes['A'].active)

    def test_finalize_fails_closed_on_replay_divergence(self):
        rt=RT();rt.nodes={'A':n('A','goal','old')};register_commitment(rt,'A');rt.nodes['A'].metadata['commitment_status']='RETRACTED'
        with self.assertRaises(RuntimeError):finalize_temporal_core(rt)

    def test_retraction_is_not_evidence_mutation(self):
        rt=RT();rt.nodes={'A':n('A','goal','old')};register_commitment(rt,'A');before=rt.nodes['A'].evidence;retract_commitment(rt,'A',reason='cancelled');self.assertEqual(before,rt.nodes['A'].evidence);self.assertFalse(temporal_available(rt.nodes['A']))
    def test_turn_integration_requires_explicit_supersession(self):
        rt=RT();old=n('G1','goal','old goal');new=n('G2','goal','new goal');intent=n('I','intention','revise');rt.nodes={x.id:x for x in (old,new,intent)};register_commitment(rt,'G1')
        record=node_to_dict(new);atom={'kind':'goal','metadata':{'commitment_scope':'work','supersedes_node_id':'G1','supersession_reason':'explicit revision'}}
        ingest_temporal_turn(rt,intent,[record],[atom]);self.assertFalse(temporal_available(old));self.assertTrue(temporal_available(new));self.assertEqual(new.metadata['supersedes'],'G1')
    def test_new_commitment_does_not_guess_supersession(self):
        rt=RT();a=n('G1','goal','old goal');b=n('G2','goal','new goal');intent=n('I','intention','add');rt.nodes={x.id:x for x in (a,b,intent)};register_commitment(rt,'G1')
        ingest_temporal_turn(rt,intent,[node_to_dict(b)],[{'kind':'goal','metadata':{}}]);p=commitment_projection(rt);self.assertEqual(set(p['active_node_ids']),{'G1','G2'})

    def test_finalize_core_zero_authority(self):
        rt=RT();rt.nodes={'A':n('A','claim','fact','document')};out=finalize_temporal_core(rt);self.assertEqual(out['memory']['epistemic_authority'],0);self.assertEqual(out['replay']['epistemic_authority'],0);self.assertTrue(out['boundaries']['history_is_not_evidence'])

if __name__=='__main__':unittest.main()
