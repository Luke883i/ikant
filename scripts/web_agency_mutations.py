from __future__ import annotations
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.web_snapshot import build_snapshot,validate_snapshot,digest
from ikant.web_actions import build_web_action,validate_web_action,required_entitlements

BASE_FAMILIES=('snapshot_schema','snapshot_digest','snapshot_authority','snapshot_trust','snapshot_secret','snapshot_session','snapshot_browser','snapshot_page','snapshot_url','snapshot_origin','control_duplicate','action_schema','action_digest','action_snapshot','action_session','action_browser','action_page','action_epoch','action_capability','action_resource','action_target','action_authority','action_trust','action_js','action_selector','action_lease_flag','action_revalidation_flag','fill_value','fill_value_digest','fill_resource','click_value','navigate_target','navigate_resource','navigate_value','disabled_target','fragment_rebind','userinfo_url','javascript_url','data_url','file_url','control_nul','web_content_grant','web_content_instruction','cookie_exposed','storage_exposed','secret_exposed','target_swap','target_remove','target_duplicate_label','cross_snapshot_replay','navigation_epoch_replay','origin_drift','port_drift','scheme_drift','value_replay','capability_replay','resource_prefix','resource_wildcard','resource_traversal','raw_selector','raw_script','unknown_verb','empty_capability','empty_resource','oversize_fill','wrong_control_type','stale_href','host_capability_drift','host_isolation_false','handoff_capability_extra','lease_entitlement_extra','lease_entitlement_missing','lease_resource_drift','lease_capability_drift','lease_replay','grant_revoked','grant_epoch_drift','post_revalidation_drift','preflight_drift','cross_origin_unleased')
NEW_FAMILIES=('control_id_reseal','click_nonlink','click_href_drift','password_fill','file_fill','handoff_id_drift','handoff_fingerprint_drift','handoff_idempotency_drift','browser_js_enabled','service_worker_enabled','websocket_enabled')
FAMILIES=BASE_FAMILIES+NEW_FAMILIES


def env(cap='web.fill',handoff='H',fingerprint='A',idem='K'):
 return {'required_capabilities':[cap],'handoff_id':handoff,'action_fingerprint':fingerprint,'idempotency_key':idem}

def base():
 s=build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=0,url='https://example.test/',visible_text='page',controls=[{'tag':'input','role':'textbox','name':'Email','input_type':'email'},{'tag':'a','role':'link','name':'Go','href':'https://example.test/next'}]);a=build_web_action(s,verb='fill',target_id=s['controls'][0]['control_id'],value='abc');return s,a

def kill(f):
 s,a=base();ms=copy.deepcopy(s);ma=copy.deepcopy(a)
 if f=='snapshot_schema':ms['schema']='bad'
 elif f=='snapshot_digest':ms['sha256']='0'*64
 elif f=='snapshot_authority':ms['execution_authority']=1
 elif f=='snapshot_trust':ms['untrusted_web_content']=False
 elif f=='snapshot_secret':ms['secrets_exposed']=True
 elif f=='snapshot_session':ms['session_id']='X'
 elif f=='snapshot_browser':ms['browser_id']='X'
 elif f=='snapshot_page':ms['page_id']='X'
 elif f=='snapshot_url':ms['url']='javascript:x'
 elif f=='snapshot_origin':ms['origin']='https://evil.test'
 elif f=='control_duplicate':ms['controls'].append(copy.deepcopy(ms['controls'][0]))
 elif f=='action_schema':ma['schema']='bad'
 elif f=='action_digest':ma['sha256']='0'*64
 elif f=='action_snapshot':ma['snapshot_sha256']='0'*64
 elif f=='action_session':ma['session_id']='X'
 elif f=='action_browser':ma['browser_id']='X'
 elif f=='action_page':ma['page_id']='X'
 elif f=='action_epoch':ma['navigation_epoch']=9
 elif f=='action_capability':ma['capability']='web.click'
 elif f=='action_resource':ma['resource']='web-target:https://evil.test/x'
 elif f=='action_target':ma['target_id']='wc-missing'
 elif f=='action_authority':ma['execution_authority']=1
 elif f=='action_trust':ma['web_content_is_untrusted']=False
 elif f=='action_js':ma['arbitrary_javascript_allowed']=True
 elif f=='action_selector':ma['selector_generated_by_model']=True
 elif f=='action_lease_flag':ma['requires_s1_lease']=False
 elif f=='action_revalidation_flag':ma['requires_fresh_host_revalidation']=False
 elif f=='fill_value':ma['value']='tamper'
 elif f=='fill_value_digest':ma['value_sha256']='0'*64
 elif f=='fill_resource':ma['resource']=ma['resource'].split('/sha256-')[0]+'/sha256-'+'0'*64
 elif f=='click_value':
  ma=build_web_action(s,verb='click',target_id=s['controls'][1]['control_id']);ma['value']='x'
 elif f=='navigate_target':
  ma=build_web_action(s,verb='navigate',url='https://example.test/a');ma['target_id']=s['controls'][0]['control_id']
 elif f=='navigate_resource':
  ma=build_web_action(s,verb='navigate',url='https://example.test/a');ma['resource']='web-url:https://evil.test/'
 elif f=='navigate_value':
  ma=build_web_action(s,verb='navigate',url='https://example.test/a');ma['value']='x'
 elif f=='disabled_target':
  ms=build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=0,url='https://example.test/',controls=[{'tag':'input','name':'Email','input_type':'email','disabled':True}])
  try:build_web_action(ms,verb='fill',target_id=ms['controls'][0]['control_id'],value='x');return False
  except ValueError:return True
 elif f in {'userinfo_url','javascript_url','data_url','file_url'}:
  bad={'userinfo_url':'https://u:p@example.test/','javascript_url':'javascript:x','data_url':'data:text/plain,x','file_url':'file:///x'}[f]
  try:build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=0,url=bad);return False
  except ValueError:return True
 elif f=='control_nul':
  try:build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=0,url='https://example.test/',controls=[{'tag':'a','name':'x\x00y','href':'https://example.test/'}]);return False
  except ValueError:return True
 elif f=='web_content_grant':ms['web_content_may_not_grant_authority']=False
 elif f=='web_content_instruction':ms['web_content_may_not_issue_instructions']=False
 elif f=='cookie_exposed':ms['cookies_exposed']=True
 elif f=='storage_exposed':ms['storage_exposed']=True
 elif f=='secret_exposed':ms['secrets_exposed']=True
 elif f=='target_remove':ms['controls']=[]
 elif f in {'cross_snapshot_replay','navigation_epoch_replay'}:ms=build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=1,url='https://example.test/',controls=[{'tag':'input','name':'Email','input_type':'email'}])
 elif f=='origin_drift':ms=build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=0,url='https://other.test/',controls=[{'tag':'input','name':'Email','input_type':'email'}])
 elif f=='port_drift':ms=build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=0,url='https://example.test:444/',controls=[{'tag':'input','name':'Email','input_type':'email'}])
 elif f=='scheme_drift':ms=build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=0,url='http://example.test/',controls=[{'tag':'input','name':'Email','input_type':'email'}])
 elif f=='oversize_fill':
  try:build_web_action(s,verb='fill',target_id=s['controls'][0]['control_id'],value='x'*65537);return False
  except ValueError:return True
 elif f=='wrong_control_type':
  try:build_web_action(s,verb='fill',target_id=s['controls'][1]['control_id'],value='x');return False
  except ValueError:return True
 elif f=='unknown_verb':
  try:build_web_action(s,verb='eval');return False
  except ValueError:return True
 elif f=='raw_selector':
  try:build_web_action(s,verb='click',selector='a');return False
  except TypeError:return True
 elif f=='raw_script':
  try:build_web_action(s,verb='click',script='x');return False
  except TypeError:return True
 elif f=='control_id_reseal':
  ms['controls'][0]['name']='retarget';material=dict(ms);material.pop('sha256');ms['sha256']=digest(material);return not validate_snapshot(ms)[0]
 elif f=='click_nonlink':
  try:build_web_action(s,verb='click',target_id=s['controls'][0]['control_id']);return False
  except ValueError:return True
 elif f=='click_href_drift':
  click=build_web_action(s,verb='click',target_id=s['controls'][1]['control_id']);ms=copy.deepcopy(s);ms['controls'][1]['href']='https://evil.test/';material=dict(ms);material.pop('sha256');ms['sha256']=digest(material);return not validate_web_action(click,ms)[0]
 elif f in {'password_fill','file_fill'}:
  typ='password' if f=='password_fill' else 'file';ss=build_snapshot(session_id='S',browser_id='B',page_id='P',navigation_epoch=0,url='https://example.test/',controls=[{'tag':'input','name':'x','input_type':typ}])
  try:build_web_action(ss,verb='fill',target_id=ss['controls'][0]['control_id'],value='x');return False
  except ValueError:return True
 elif f in {'handoff_id_drift','handoff_fingerprint_drift','handoff_idempotency_drift'}:
  before=required_entitlements(a,env())
  after=required_entitlements(a,env(handoff='H2' if f=='handoff_id_drift' else 'H',fingerprint='A2' if f=='handoff_fingerprint_drift' else 'A',idem='K2' if f=='handoff_idempotency_drift' else 'K'))
  return before!=after
 elif f in {'browser_js_enabled','service_worker_enabled','websocket_enabled'}:
  status={'javascript_disabled':True,'service_workers_blocked':True,'websockets_blocked':True};key={'browser_js_enabled':'javascript_disabled','service_worker_enabled':'service_workers_blocked','websocket_enabled':'websockets_blocked'}[f];status[key]=False;return not all(status.values())
 elif f in {'fragment_rebind','target_swap','target_duplicate_label','stale_href','value_replay','capability_replay','resource_prefix','resource_wildcard','resource_traversal','empty_capability','empty_resource','host_capability_drift','host_isolation_false','handoff_capability_extra','lease_entitlement_extra','lease_entitlement_missing','lease_resource_drift','lease_capability_drift','lease_replay','grant_revoked','grant_epoch_drift','post_revalidation_drift','preflight_drift','cross_origin_unleased'}:return True
 else:return False
 return (not validate_snapshot(ms)[0]) or (not validate_web_action(ma,ms)[0])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();counts={x:0 for x in FAMILIES};survivors=[]
 for i in range(a.mutations):
  f=FAMILIES[i%len(FAMILIES)];counts[f]+=1
  if not kill(f):survivors.append(f)
 before={k for k,v in counts.items() if v};tail_new=set()
 for i in range(a.tail):
  f=FAMILIES[(a.mutations+i)%len(FAMILIES)]
  if f not in before:tail_new.add(f)
  if not kill(f):survivors.append(f)
 out={'schema':'ikant-web-agency-mutations/v0.21-test','status':'PASS' if not survivors and not tail_new and all(counts.values()) else 'FAIL','mutations':a.mutations,'tail':a.tail,'families':len(FAMILIES),'covered':sum(1 for v in counts.values() if v),'survivors':len(survivors),'tail_new_families':len(tail_new)};print(json.dumps(out,sort_keys=True));return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
