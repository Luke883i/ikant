import copy,tempfile,unittest
from ikant.host_adapter import ReferenceCliHostAdapter
from ikant.host_capabilities import build_manifest,validate_manifest,CAPABILITIES
from ikant.host_conformance import run_conformance,validate_conformance_receipt,REQUIRED_VECTORS
from ikant.host_negotiation import negotiate_host,PROFILE_REQUIRED_CAPABILITIES,certify_host
from ikant.host_sdk import HostRuntimeBinding
from ikant.transport import validate_transport_attestation

class HostManifestTests(unittest.TestCase):
 def setUp(self):self.a=ReferenceCliHostAdapter();self.m=self.a.manifest()
 def test_manifest_valid(self):self.assertTrue(validate_manifest(self.m)[0])
 def test_manifest_is_declaration_only(self):self.assertTrue(self.m.declared_only);self.assertFalse(self.m.actor_authenticated);self.assertEqual(self.m.execution_authority,0)
 def test_wildcard_capability_rejected(self):
  with self.assertRaises(ValueError):build_manifest(adapter_id='x',adapter_version='1',config_fingerprint='c',capabilities=['human.+'])
 def test_unknown_capability_rejected(self):
  with self.assertRaises(ValueError):build_manifest(adapter_id='x',adapter_version='1',config_fingerprint='c',capabilities=['host.magic'])
 def test_manifest_tamper_rejected(self):
  x=self.m.__dict__.copy();x['actor_authenticated']=True;self.assertFalse(validate_manifest(x)[0])

class AdapterProbeTests(unittest.TestCase):
 def setUp(self):self.a=ReferenceCliHostAdapter()
 def test_exact_write(self):self.assertTrue(self.a.probe_human('normal')['accepted'])
 def test_partial_write_rejected(self):self.assertFalse(self.a.probe_human('partial')['accepted'])
 def test_flush_failure_rejected(self):self.assertFalse(self.a.probe_human('flush_fail')['accepted'])
 def test_machine_file_only(self):self.assertTrue(self.a.probe_machine('file')['accepted'])
 def test_machine_aliases_rejected(self):
  for x in ('stdout','stderr','-','/dev/stdout','/dev/stderr',''):self.assertFalse(self.a.probe_machine(x)['accepted'])
 def test_revalidation_exact(self):self.assertTrue(self.a.probe_revalidation(False)['accepted'])
 def test_revalidation_drift_rejected(self):self.assertFalse(self.a.probe_revalidation(True)['accepted'])
 def test_revalidation_zero_authority(self):
  r=self.a.probe_revalidation(False)['receipt'];self.assertFalse(r['grants_runtime_execution_authority']);self.assertFalse(r['executes_action'])
 def test_legacy_attestation_compatible(self):self.assertTrue(self.a.probe_legacy_attestation()['accepted'])

class ConformanceTests(unittest.TestCase):
 def setUp(self):self.a=ReferenceCliHostAdapter();self.m=self.a.manifest();self.r=run_conformance(self.a)
 def test_reference_passes(self):self.assertEqual(self.r['overall_status'],'PASS')
 def test_all_vectors_present(self):self.assertEqual({x['id'] for x in self.r['vectors']},set(sum((list(x) for x in REQUIRED_VECTORS.values()),[]))|{'MACHINE_FILE_ONLY','MANIFEST_INTEGRITY','CONFIG_BOUND'})
 def test_receipt_valid(self):self.assertTrue(validate_conformance_receipt(self.r,self.m)[0])
 def test_not_authentication(self):self.assertFalse(self.r['actor_authenticated']);self.assertFalse(self.r['production_transport_attested']);self.assertTrue(self.r['digest_is_integrity_not_authentication'])
 def test_no_authority(self):self.assertEqual(self.r['epistemic_authority'],0);self.assertEqual(self.r['execution_authority'],0)
 def test_adapter_drift_rejected(self):
  m=ReferenceCliHostAdapter(config_tag='other').manifest();self.assertFalse(validate_conformance_receipt(self.r,m)[0])
 def test_receipt_digest_tamper_rejected(self):
  x=copy.deepcopy(self.r);x['actor_authenticated']=True;self.assertFalse(validate_conformance_receipt(x,self.m)[0])
 def test_vector_failure_recomputes_profile(self):
  x=copy.deepcopy(self.r);next(v for v in x['vectors'] if v['id']=='HUMAN_EXACT_WRITE')['status']='FAIL';self.assertFalse(validate_conformance_receipt(x,self.m)[0])
 def test_declaration_alone_not_conforming(self):self.assertEqual(negotiate_host('HUMAN_EGRESS',self.m,{} )['status'],'NON_CONFORMING')

 def test_declared_capabilities_cannot_mask_failed_probe(self):
  class Broken(ReferenceCliHostAdapter):
   def probe_human(self,mode='normal'):
    if mode=='normal':return {'accepted':False,'error':'broken'}
    return super().probe_human(mode)
  a=Broken();r=run_conformance(a);self.assertEqual(r['profiles']['HUMAN_EGRESS'],'FAIL');self.assertEqual(negotiate_host('HUMAN_EGRESS',a.manifest(),r)['status'],'NON_CONFORMING')

class NegotiationTests(unittest.TestCase):
 def setUp(self):self.a=ReferenceCliHostAdapter();self.m=self.a.manifest();self.r=run_conformance(self.a)
 def test_all_profiles_conform(self):
  for p in PROFILE_REQUIRED_CAPABILITIES:self.assertEqual(negotiate_host(p,self.m,self.r)['status'],'CONFORMING')
 def test_unknown_profile_fails(self):self.assertEqual(negotiate_host('MAGIC',self.m,self.r)['status'],'NON_CONFORMING')
 def test_missing_declared_capability_fails(self):
  req=sorted(PROFILE_REQUIRED_CAPABILITIES['HUMAN_EGRESS']);caps=[x for x in CAPABILITIES if x!=req[0]];m=build_manifest(adapter_id=self.m.adapter_id,adapter_version=self.m.adapter_version,config_fingerprint=self.m.config_fingerprint,capabilities=caps);self.assertEqual(negotiate_host('HUMAN_EGRESS',m,self.r)['status'],'NON_CONFORMING')
 def test_failed_required_vector_fails(self):
  x=copy.deepcopy(self.r);next(v for v in x['vectors'] if v['id']=='HUMAN_EXACT_WRITE')['status']='FAIL';
  # reseal intentionally omitted: invalid receipt must fail closed
  self.assertEqual(negotiate_host('HUMAN_EGRESS',self.m,x)['status'],'NON_CONFORMING')
 def test_nonrequired_vector_failure_profile_scoped(self):
  x=copy.deepcopy(self.r);next(v for v in x['vectors'] if v['id']=='EXEC_REVALIDATION_BIND')['status']='FAIL';
  # recompute profile and digest to create internally valid degraded receipt
  x['profiles']['EXECUTION_HANDOFF']='FAIL';x['overall_status']='FAIL';from ikant.host_capabilities import digest;x.pop('sha256',None);x['sha256']=digest(x)
  self.assertEqual(negotiate_host('HUMAN_EGRESS',self.m,x)['status'],'CONFORMING');self.assertEqual(negotiate_host('EXECUTION_HANDOFF',self.m,x)['status'],'NON_CONFORMING')

 def test_certification_persists_zero_authority_projection(self):
  with tempfile.TemporaryDirectory() as td:
   out=certify_host(self.a,profiles=['BREACH_RESUME'],persist_path=td+'/host-conformance.json');self.assertEqual(out['status'],'CONFORMING');self.assertTrue(__import__('pathlib').Path(out['path']).exists());self.assertFalse(out['actor_authenticated']);self.assertFalse(out['production_transport_attested'])
 def test_negotiation_never_grants_authority(self):
  n=negotiate_host('BREACH_RESUME',self.m,self.r);self.assertFalse(n['grants_runtime_authority']);self.assertEqual(n['execution_authority'],0);self.assertFalse(n['actor_authenticated'])

if __name__=='__main__':unittest.main()

class HostSdkTests(unittest.TestCase):
 def test_binding_status_zero_authority(self):
  b=HostRuntimeBinding(ReferenceCliHostAdapter());s=b.status();self.assertEqual(s['status'],'CONFORMING');self.assertEqual(s['execution_authority'],0);self.assertFalse(s['actor_authenticated']);self.assertFalse(s['production_transport_attested'])
 def test_resume_attestation_requires_profile_and_is_legacy_valid(self):
  b=HostRuntimeBinding(ReferenceCliHostAdapter());att=b.legacy_resume_attestation();self.assertTrue(validate_transport_attestation(att)[0])
 def test_revalidation_requires_profile_and_exact_binding(self):
  a=ReferenceCliHostAdapter();b=HostRuntimeBinding(a);env=a.sample_handoff();r=b.revalidate_execution(env);self.assertTrue(a.probe_revalidation(False)['accepted']);self.assertEqual(r['handoff_id'],env['handoff_id'])
 def test_broken_adapter_cannot_materialize_resume_attestation(self):
  class Broken(ReferenceCliHostAdapter):
   def probe_human(self,mode='normal'):
    if mode=='normal':return {'accepted':False}
    return super().probe_human(mode)
  b=HostRuntimeBinding(Broken())
  with self.assertRaises(PermissionError):b.legacy_resume_attestation()
