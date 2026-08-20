import os,tempfile,unittest
from ikant.native_snapshot import canonical_native_path,sensitive_path
from ikant.native_actions import build_native_action,validate_native_action,required_entitlements,bound_native_resource
from ikant.native_driver import InMemoryNativeAdapter,PosixWorkspaceAdapter,NativeDriverError
from ikant.native_agency import NativeAgency,NativeAgencyError

def envelope(cap='native.fs.read'):
 return {'session_id':'S','cycle_id':'C','intent_sha256':'I','handoff_id':'H','idempotency_key':'K','action_fingerprint':'A','action_ledger_sha256':'AL','plan_ledger_sha256':'PL','plan_id':'P','step_id':'T','handoff_kind':'HOST','handoff_state':'HOST_REVALIDATION_REQUIRED','action_status':'HOST_EXECUTION_ELIGIBLE','execution_eligible':False,'execution_authority':0.0,'required_capabilities':[cap]}
class FakeAgency:
 def __init__(self):self.consumed=[]
 def consume_lease(self,lid,reason=''):
  if lid in self.consumed:raise PermissionError('replay')
  self.consumed.append(lid);return {'lease_id':lid,'status':'CONSUMED'}
class FakeHost:
 def __init__(self):self.calls=0
 def revalidate_execution(self,e,l):self.calls+=1;return {'host_revalidation':{'ok':True}}
def lease(a,e):return {'lease_id':'L','status':'PENDING','entitlements':[{'capability':c,'resource':r} for c,r in required_entitlements(a,e)]}

class PathTests(unittest.TestCase):
 def test_canonical_path(self):
  self.assertEqual(canonical_native_path('dir/file.txt'),'dir/file.txt')
  for bad in ('','/etc/passwd','../x','a/../x','a\\b','C:/x','a//b','a/./b','a\x00b'):
   with self.subTest(bad=bad),self.assertRaises(ValueError):canonical_native_path(bad)
 def test_sensitive_path(self):
  for p in ('.env','dir/.secret','credentials.json','x/id_rsa','x/token-store.txt','x/a.pem'):self.assertTrue(sensitive_path(p),p)
  self.assertFalse(sensitive_path('docs/readme.txt'))

class ActionTests(unittest.TestCase):
 def setUp(self):self.d=InMemoryNativeAdapter(files={'docs/a.txt':'hello'})
 def test_read_action(self):
  s=self.d.snapshot('docs/a.txt');a=build_native_action(s,verb='read_file');self.assertTrue(validate_native_action(a,s)[0]);self.assertEqual(a['capability'],'native.fs.read')
 def test_create_action_exact_content_digest(self):
  s=self.d.snapshot('docs/new.txt');a=build_native_action(s,verb='create_file',text='new');self.assertTrue(validate_native_action(a,s)[0]);m={**a,'text':'other'};self.assertFalse(validate_native_action(m,s)[0])
 def test_existing_create_rejected(self):
  s=self.d.snapshot('docs/a.txt')
  with self.assertRaises(ValueError):build_native_action(s,verb='create_file',text='x')
 def test_missing_read_rejected(self):
  s=self.d.snapshot('docs/new.txt')
  with self.assertRaises(ValueError):build_native_action(s,verb='read_file')
 def test_binary_nul_create_rejected(self):
  s=self.d.snapshot('docs/new.txt')
  with self.assertRaises(ValueError):build_native_action(s,verb='create_file',text='a\x00b')
 def test_large_create_rejected(self):
  s=self.d.snapshot('docs/new.txt')
  with self.assertRaises(ValueError):build_native_action(s,verb='create_file',text='x'*(16*1024+1))
 def test_bound_entitlement_changes_with_handoff(self):
  s=self.d.snapshot('docs/a.txt');a=build_native_action(s,verb='read_file');e=envelope();r=bound_native_resource(a,e);e2={**e,'handoff_id':'H2'};self.assertNotEqual(r,bound_native_resource(a,e2))
 def test_capability_drift_rejected(self):
  s=self.d.snapshot('docs/a.txt');a=build_native_action(s,verb='read_file')
  with self.assertRaises(ValueError):required_entitlements(a,envelope('native.fs.create'))

class DriverTests(unittest.TestCase):
 def test_inmemory_drift_blocks(self):
  d=InMemoryNativeAdapter(files={'a.txt':'x'});s=d.snapshot('a.txt');a=build_native_action(s,verb='read_file');p=d.preflight(a);d.files['a.txt']='y';d.generation+=1
  with self.assertRaises(NativeDriverError):d.commit(p)
 @unittest.skipUnless(os.name=='posix' and hasattr(os,'O_NOFOLLOW'),'POSIX only')
 def test_posix_read_create_and_symlink_block(self):
  with tempfile.TemporaryDirectory() as td:
   os.mkdir(os.path.join(td,'docs'))
   with open(os.path.join(td,'docs','a.txt'),'w') as f:f.write('hello')
   d=PosixWorkspaceAdapter(session_id='S',workspace_root=td);s=d.snapshot('docs/a.txt');a=build_native_action(s,verb='read_file');o=d.commit(d.preflight(a));self.assertEqual(o['text'],'hello')
   s2=d.snapshot('docs/new.txt');c=build_native_action(s2,verb='create_file',text='new');d.commit(d.preflight(c))
   with open(os.path.join(td,'docs','new.txt')) as f:self.assertEqual(f.read(),'new')
   os.symlink('/etc/passwd',os.path.join(td,'docs','link'))
   with self.assertRaises((ValueError,NativeDriverError)):d.snapshot('docs/link')
 @unittest.skipUnless(os.name=='posix' and hasattr(os,'O_NOFOLLOW'),'POSIX only')
 def test_posix_parent_symlink_block(self):
  with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as other:
   os.symlink(other,os.path.join(td,'escape'));d=PosixWorkspaceAdapter(session_id='S',workspace_root=td)
   with self.assertRaises(OSError):d.snapshot('escape/x.txt')
 @unittest.skipUnless(os.name=='posix' and hasattr(os,'O_NOFOLLOW'),'POSIX only')
 def test_posix_toctou_leaf_swap_blocks_read(self):
  with tempfile.TemporaryDirectory() as td:
   for name,text in (('a.txt','one'),('b.txt','two')):
    with open(os.path.join(td,name),'w') as f:f.write(text)
   d=PosixWorkspaceAdapter(session_id='S',workspace_root=td);s=d.snapshot('a.txt');a=build_native_action(s,verb='read_file');p=d.preflight(a);os.replace(os.path.join(td,'b.txt'),os.path.join(td,'a.txt'))
   with self.assertRaises(NativeDriverError):d.commit(p)
 @unittest.skipUnless(os.name=='posix' and hasattr(os,'O_NOFOLLOW'),'POSIX only')
 def test_posix_create_no_clobber_race(self):
  with tempfile.TemporaryDirectory() as td:
   d=PosixWorkspaceAdapter(session_id='S',workspace_root=td);s=d.snapshot('new.txt');a=build_native_action(s,verb='create_file',text='ikant');p=d.preflight(a)
   with open(os.path.join(td,'new.txt'),'w') as f:f.write('external')
   with self.assertRaises(NativeDriverError):d.commit(p)
   with open(os.path.join(td,'new.txt')) as f:self.assertEqual(f.read(),'external')
 def test_filesystem_root_rejected(self):
  if os.name=='posix':
   with self.assertRaises(NativeDriverError):PosixWorkspaceAdapter(session_id='S',workspace_root='/')

class AgencyTests(unittest.TestCase):
 def make(self):
  d=InMemoryNativeAdapter(files={'docs/a.txt':'hello'});ag=FakeAgency();h=FakeHost();return d,ag,h,NativeAgency(driver=d,agency_kernel=ag,agency_host_binding=h)
 def test_read_executes_after_revalidation_and_consume(self):
  d,ag,h,n=self.make();s=n.observe('docs/a.txt');a=build_native_action(s,verb='read_file');e=envelope();l=lease(a,e);o=n.execute(a,e,l);self.assertEqual(o['native_outcome']['text'],'hello');self.assertEqual(ag.consumed,['L']);self.assertEqual(h.calls,1);self.assertTrue(o['native_content_is_untrusted_observation'])
 def test_create_executes_exact_content(self):
  d,ag,h,n=self.make();s=n.observe('docs/new.txt');a=build_native_action(s,verb='create_file',text='new');e=envelope('native.fs.create');l=lease(a,e);n.execute(a,e,l);self.assertEqual(d.files['docs/new.txt'],'new')
 def test_extra_lease_scope_rejected(self):
  d,ag,h,n=self.make();s=n.observe('docs/a.txt');a=build_native_action(s,verb='read_file');e=envelope();l=lease(a,e);l['entitlements'].append({'capability':'native.fs.create','resource':'native-action:x'})
  with self.assertRaises(NativeAgencyError):n.execute(a,e,l)
  self.assertEqual(ag.consumed,[])
 def test_stale_target_rejected_without_consume(self):
  d,ag,h,n=self.make();s=n.observe('docs/a.txt');a=build_native_action(s,verb='read_file');e=envelope();l=lease(a,e);d.files['docs/a.txt']='changed';d.generation+=1
  with self.assertRaises(NativeAgencyError):n.execute(a,e,l)
  self.assertEqual(ag.consumed,[])
 def test_security_profile_drift_rejected(self):
  d,ag,h,n=self.make();s=n.observe('docs/a.txt');a=build_native_action(s,verb='read_file');e=envelope();l=lease(a,e);d.security_profile['symlink_safe']=False
  with self.assertRaises(NativeAgencyError):n.execute(a,e,l)
 def test_handoff_drift_rejected(self):
  d,ag,h,n=self.make();s=n.observe('docs/a.txt');a=build_native_action(s,verb='read_file');e=envelope();l=lease(a,e);e['idempotency_key']='OTHER'
  with self.assertRaises(NativeAgencyError):n.execute(a,e,l)

class RepositoryIntegrationTests(unittest.TestCase):
 def test_runtime_refuses_before_active_without_touching_workspace(self):
  try:from ikant.native_runtime import build_native_agency_runtime
  except ImportError as exc:self.skipTest(str(exc))
  with self.assertRaises(PermissionError):
   build_native_agency_runtime(state_dir='/tmp/unused',session_id='S',actor_binding=None,interaction_secret=b'',workspace_root='/definitely/not/existing/ikant-s4',active=False)
 def test_real_s1_grant_lease_host_revalidation_and_receipt(self):
  try:
   from ikant.human_frame import build_actor_binding,issue_interaction_receipt
   from ikant.agency_kernel import AgencyKernel
   from ikant.agency_host import AgencyHostBinding
   from ikant.host_sdk import HostRuntimeBinding
   from ikant.execution_receipts import validate_execution_receipt
   from ikant.native_authorization import build_native_grant_frame
   from ikant.native_host import NativeExecutionHostAdapter
  except ImportError as exc:self.skipTest(str(exc))
  with tempfile.TemporaryDirectory() as td:
   secret=b's'*32;binding=build_actor_binding(session_id='S',channel_id='local-native',secret=secret);kernel=AgencyKernel(td,session_id='S',binding=binding,interaction_secret=secret);driver=InMemoryNativeAdapter(session_id='S',files={'docs/a.txt':'hello'});snap=driver.snapshot('docs/a.txt');action=build_native_action(snap,verb='read_file');env=envelope('native.fs.read');frame=build_native_grant_frame(snap,action,env,actor_binding_id=binding.binding_id,frame_seq=1);interaction=issue_interaction_receipt(frame,binding=binding,decision='APPROVE',secret=secret);grant=kernel.issue_grant(frame,interaction);self.assertEqual(grant['max_uses'],1);lo=kernel.issue_lease(env,required_entitlements(action,env));host=HostRuntimeBinding(NativeExecutionHostAdapter(driver_kind=type(driver).__name__,security_profile=driver.security_profile));agency=NativeAgency(driver=driver,agency_kernel=kernel,agency_host_binding=AgencyHostBinding(host,kernel));out=agency.execute(action,env,lo);self.assertEqual(out['native_outcome']['text'],'hello');self.assertEqual(kernel.state().leases[lo['lease_id']]['status'],'CONSUMED');ok,errors=validate_execution_receipt(env,out['execution_receipt'],revalidation_receipt=out['host_revalidation']);self.assertTrue(ok,errors)
 def test_create_grant_displays_exact_content(self):
  try:
   from ikant.human_frame import build_actor_binding
   from ikant.native_authorization import build_native_grant_frame
  except ImportError as exc:self.skipTest(str(exc))
  binding=build_actor_binding(session_id='S',channel_id='local-native',secret=b'x'*32);driver=InMemoryNativeAdapter(session_id='S');snap=driver.snapshot('docs/new.txt');action=build_native_action(snap,verb='create_file',text='alpha\nbeta');env=envelope('native.fs.create');frame=build_native_grant_frame(snap,action,env,actor_binding_id=binding.binding_id,frame_seq=1);self.assertEqual(frame['max_uses'],1);self.assertIn('alpha\nbeta',frame['body']);self.assertEqual(frame['handoff_id'],'H');self.assertEqual(frame['requested_entitlements'],[{'capability':c,'resource':r} for c,r in required_entitlements(action,env)])
 def test_native_host_rejects_weakened_security_profile(self):
  try:from ikant.native_host import NativeExecutionHostAdapter
  except ImportError as exc:self.skipTest(str(exc))
  d=InMemoryNativeAdapter();profile=dict(d.security_profile);profile['symlink_safe']=False;r=NativeExecutionHostAdapter(driver_kind='memory',security_profile=profile).revalidate(envelope('native.fs.read'));self.assertFalse(r['system_safety_law_checked']);self.assertFalse(r['tool_capability_checked'])

if __name__=='__main__':unittest.main()
