from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path

from ikant.human_frame import build_actor_binding,build_human_frame,issue_interaction_receipt,validate_human_frame,validate_interaction_receipt
from ikant.agency_kernel import AgencyKernel,AgencyAuthorityError,AgencyIntegrityError
from ikant.agency_host import AgencyHostBinding

SECRET=b'x'*32

def envelope(**overrides):
    base={'session_id':'S','cycle_id':'C1','intent_sha256':'I','handoff_id':'H','idempotency_key':'K','action_fingerprint':'AF','action_ledger_sha256':'AL','plan_ledger_sha256':'PL','plan_id':'P','step_id':'ST','handoff_state':'HOST_REVALIDATION_REQUIRED','handoff_kind':'HOST','required_capabilities':['browser.read'],'execution_eligible':False,'execution_authority':0.0}
    base.update(overrides);return base

class FakeHost:
    def revalidate_execution(self,e):return {'schema':'fake-host','handoff_id':e['handoff_id'],'execution_authority':0.0,'executes_action':False}

class AgencyKernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.binding=build_actor_binding(session_id='S',channel_id='ui',secret=SECRET);self.k=AgencyKernel(self.root,session_id='S',binding=self.binding,interaction_secret=SECRET)
    def tearDown(self):self.tmp.cleanup()
    def grant(self,max_uses=1,expires_at=None,ents=(('browser.read','https:example.test/page'),)):
        frame=build_human_frame(session_id='S',actor_binding_id=self.binding.binding_id,frame_seq=1,purpose='CAPABILITY_GRANT',title='Grant',body='Allow exact access',entitlements=ents,max_uses=max_uses,expires_at=expires_at,nonce='f1')
        rec=issue_interaction_receipt(frame,binding=self.binding,decision='APPROVE',secret=SECRET,interaction_nonce='i1')
        return self.k.issue_grant(frame,rec,now=10),frame,rec
    def test_frame_presentation_zero_authority(self):
        frame=build_human_frame(session_id='S',actor_binding_id=self.binding.binding_id,frame_seq=1,purpose='CAPABILITY_GRANT',title='Grant',body='x',entitlements=[('browser.read','https:example.test/page')],nonce='f')
        self.assertEqual(frame['authority_effect'],'NONE');self.assertEqual(frame['execution_authority'],0.0);self.assertTrue(validate_human_frame(frame)[0])
    def test_receipt_exact_frame_and_channel_bound(self):
        frame=build_human_frame(session_id='S',actor_binding_id=self.binding.binding_id,frame_seq=1,purpose='CAPABILITY_GRANT',title='Grant',body='x',entitlements=[('browser.read','https:example.test/page')],nonce='f')
        rec=issue_interaction_receipt(frame,binding=self.binding,decision='APPROVE',secret=SECRET,interaction_nonce='i')
        self.assertTrue(validate_interaction_receipt(frame,rec,binding=self.binding,secret=SECRET)[0])
        bad=dict(frame);bad['body']='different'
        self.assertFalse(validate_interaction_receipt(bad,rec,binding=self.binding,secret=SECRET)[0])
    def test_grant_requires_explicit_approval(self):
        frame=build_human_frame(session_id='S',actor_binding_id=self.binding.binding_id,frame_seq=1,purpose='CAPABILITY_GRANT',title='Grant',body='x',entitlements=[('browser.read','https:example.test/page')],nonce='f')
        rec=issue_interaction_receipt(frame,binding=self.binding,decision='DENY',secret=SECRET,interaction_nonce='i')
        with self.assertRaises(AgencyAuthorityError):self.k.issue_grant(frame,rec,now=10)
    def test_grant_idempotent(self):
        g,f,r=self.grant(max_uses=2);g2=self.k.issue_grant(f,r,now=11)
        self.assertEqual(g['grant_id'],g2['grant_id']);self.assertEqual(self.k.state().events,1)
    def test_exact_resource_no_prefix_or_wildcard(self):
        self.grant()
        with self.assertRaises(AgencyAuthorityError):self.k.issue_lease(envelope(),[('browser.read','https:example.test/page/child')],now=11)
        with self.assertRaises(ValueError):build_human_frame(session_id='S',actor_binding_id=self.binding.binding_id,frame_seq=2,purpose='CAPABILITY_GRANT',title='g',body='x',entitlements=[('browser.*','https:example.test/page')])
    def test_lease_exact_handoff_and_one_shot(self):
        self.grant();e=envelope();lease=self.k.issue_lease(e,[('browser.read','https:example.test/page')],now=11)
        self.assertTrue(self.k.validate_lease(lease,e,now=12)[0])
        bad=dict(e);bad['action_fingerprint']='OTHER';self.assertFalse(self.k.validate_lease(lease,bad,now=12)[0])
        used=self.k.consume_lease(lease['lease_id'],now=13);self.assertEqual(used['status'],'CONSUMED');self.assertFalse(self.k.validate_lease(lease,e,now=14)[0])
    def test_pending_lease_reserves_max_use(self):
        self.grant(max_uses=1);self.k.issue_lease(envelope(),[('browser.read','https:example.test/page')],now=11)
        e2=envelope(handoff_id='H2',idempotency_key='K2',step_id='ST2')
        with self.assertRaises(AgencyAuthorityError):self.k.issue_lease(e2,[('browser.read','https:example.test/page')],now=12)
    def test_concurrent_last_use_cannot_oversubscribe(self):
        from concurrent.futures import ThreadPoolExecutor
        self.grant(max_uses=1)
        e1=envelope(handoff_id='H1',idempotency_key='K1',step_id='ST1');e2=envelope(handoff_id='H2',idempotency_key='K2',step_id='ST2')
        def attempt(e):
            k=AgencyKernel(self.root,session_id='S',binding=self.binding,interaction_secret=SECRET)
            try:return ('OK',k.issue_lease(e,[('browser.read','https:example.test/page')],now=11)['lease_id'])
            except (AgencyAuthorityError,RuntimeError) as exc:return ('BLOCK',str(exc))
        with ThreadPoolExecutor(max_workers=2) as ex:r=list(ex.map(attempt,(e1,e2)))
        self.assertEqual([x[0] for x in r].count('OK'),1,r);self.assertEqual([x[0] for x in r].count('BLOCK'),1,r)
    def test_cancel_releases_reservation(self):
        self.grant(max_uses=1);l=self.k.issue_lease(envelope(),[('browser.read','https:example.test/page')],now=11);self.k.cancel_lease(l['lease_id'],now=12)
        e2=envelope(handoff_id='H2',idempotency_key='K2',step_id='ST2');l2=self.k.issue_lease(e2,[('browser.read','https:example.test/page')],now=13);self.assertEqual(l2['status'],'PENDING')
    def test_revocation_invalidates_pending_lease(self):
        g,_,_=self.grant(max_uses=2);e=envelope();l=self.k.issue_lease(e,[('browser.read','https:example.test/page')],now=11)
        frame=build_human_frame(session_id='S',actor_binding_id=self.binding.binding_id,frame_seq=2,purpose='CAPABILITY_REVOKE',title='Revoke',body='revoke',subject_id=g['grant_id'],nonce='f2')
        rec=issue_interaction_receipt(frame,binding=self.binding,decision='REVOKE',secret=SECRET,interaction_nonce='i2');self.k.revoke_grant(g['grant_id'],frame,rec,now=12)
        self.assertFalse(self.k.validate_lease(l,e,now=13)[0]);self.assertFalse(self.k.pending_outbox(now=13)[0]['currently_valid'])
    def test_grant_and_lease_expiry(self):
        self.grant(expires_at=20);l=self.k.issue_lease(envelope(),[('browser.read','https:example.test/page')],now=11);self.assertFalse(self.k.validate_lease(l,envelope(),now=20)[0])
    def test_capabilities_must_exactly_match_handoff(self):
        self.grant(ents=(('browser.read','https:example.test/page'),('browser.write','https:example.test/page')))
        with self.assertRaises(AgencyAuthorityError):self.k.issue_lease(envelope(),[('browser.read','https:example.test/page'),('browser.write','https:example.test/page')],now=11)
    def test_multi_grant_composition(self):
        self.grant(max_uses=2,ents=(('browser.read','https:example.test/page'),))
        frame=build_human_frame(session_id='S',actor_binding_id=self.binding.binding_id,frame_seq=2,purpose='CAPABILITY_GRANT',title='Grant',body='write',entitlements=[('browser.write','https:example.test/page')],max_uses=2,nonce='f2')
        rec=issue_interaction_receipt(frame,binding=self.binding,decision='APPROVE',secret=SECRET,interaction_nonce='i2');self.k.issue_grant(frame,rec,now=10)
        e=envelope(required_capabilities=['browser.read','browser.write']);l=self.k.issue_lease(e,[('browser.read','https:example.test/page'),('browser.write','https:example.test/page')],now=11);self.assertEqual(len(l['grant_refs']),2)
    def test_journal_tamper_fail_closed(self):
        self.grant();p=self.root/'agency-events.jsonl';rows=p.read_text().splitlines();r=json.loads(rows[0]);r['payload']['max_uses']=99;rows[0]=json.dumps(r);p.write_text('\n'.join(rows)+'\n')
        with self.assertRaises(AgencyIntegrityError):self.k.verify()
    def test_recovery_never_auto_executes(self):
        self.grant();l=self.k.issue_lease(envelope(),[('browser.read','https:example.test/page')],now=11);out=self.k.pending_outbox(now=12)
        self.assertEqual(out[0]['lease_id'],l['lease_id']);self.assertTrue(out[0]['recovery_requires_explicit_host_revalidation']);self.assertEqual(self.k.state().leases[l['lease_id']]['status'],'PENDING')
    def test_host_binding_is_conjunctive_and_zero_authority(self):
        self.grant();e=envelope();l=self.k.issue_lease(e,[('browser.read','https:example.test/page')],now=11);bundle=AgencyHostBinding(FakeHost(),self.k).revalidate_execution(e,l,now=12)
        self.assertTrue(bundle['agency_lease_valid']);self.assertFalse(bundle['execution_performed']);self.assertEqual(bundle['execution_authority'],0.0)

if __name__=='__main__':unittest.main()
