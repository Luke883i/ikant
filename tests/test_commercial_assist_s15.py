import json,unittest
from ikant.commercial_assist import CommercialAssistConfig,build_request,call_abstract
class Response:
 def __init__(self,p):self.raw=json.dumps(p).encode()
 def __enter__(self):return self
 def __exit__(self,*a):return False
 def read(self,n):return self.raw[:n]
class CommercialAssistS15Tests(unittest.TestCase):
 def test_provider_hosts_are_pinned_and_openai_storage_disabled(self):
  rows={'openai':'https://api.openai.com/v1/responses','anthropic':'https://api.anthropic.com/v1/messages','deepseek':'https://api.deepseek.com/chat/completions'}
  for provider,url in rows.items():
   req=build_request('op=COMPARE; keys=latency,architecture',CommercialAssistConfig(provider,'model','secret'));self.assertEqual(req.full_url,url)
   if provider=='openai':self.assertFalse(json.loads(req.data)['store'])
 def test_only_typed_abstract_capsules_cross_transport_boundary(self):
  c=CommercialAssistConfig('openai','m','k')
  for task in ('Confronta due architetture pubbliche','op=CREATE; keys=file','op=COMPARE; keys=valid,contains space'):
   with self.assertRaises(Exception):build_request(task,c)
 def test_secrets_paths_and_emails_fail_closed(self):
  c=CommercialAssistConfig('openai','m','k')
  for task in ('sk-ABCDEF1234567890','/home/user/private.txt','me@example.com'):
   with self.assertRaises(Exception):build_request(task,c)
 def test_tool_output_and_transport_failure_degrade_local(self):
  c=CommercialAssistConfig('anthropic','m','k');out=call_abstract('op=ANALYZE; keys=a,b',c,opener=lambda req,timeout:Response({'content':[{'type':'tool_use','name':'x'}]}));self.assertEqual(out['status'],'UNAVAILABLE');self.assertTrue(out['local_fallback_required']);self.assertEqual(out['execution_authority'],0.0)
  fail=call_abstract('op=ANALYZE; keys=a,b',c,opener=lambda *a,**k:(_ for _ in ()).throw(TimeoutError()));self.assertEqual(fail['status'],'UNAVAILABLE')
 def test_valid_remote_result_stays_zero_authority(self):
  c=CommercialAssistConfig('openai','m','k');out=call_abstract('op=COMPARE; keys=a,b',c,opener=lambda req,timeout:Response({'output':[{'type':'message','content':[{'type':'output_text','text':'finding'}]}]}));self.assertEqual(out['status'],'AVAILABLE');self.assertEqual(out['text'],'finding');self.assertEqual(out['epistemic_authority'],0.0)
if __name__=='__main__':unittest.main()
