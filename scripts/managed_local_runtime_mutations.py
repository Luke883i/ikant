from __future__ import annotations
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.component_manifest import load_manifest,validate_manifest
from ikant.engine_supervisor import build_server_command
FAMILIES=('engine_latest','engine_http','engine_sha','engine_tag_drift','engine_size_bound','model_main','model_http','model_sha','model_revision','model_size_bound','remote_host','fixed_port','api_key_inline','webui','agent','tools','browser_transport','model_authority','component_authority','runtime_authority','epistemic_authority','execution_authority','command_remote_host','command_no_key_file','command_webui','command_agent','loader_env');BASE=load_manifest(ROOT/'MODEL_RUNTIME.json')
def kill(f):
 m=copy.deepcopy(BASE)
 if f=='engine_latest':m['engine']['release_tag']='latest'
 elif f=='engine_http':next(iter(m['engine']['artifacts'].values()))['url']='http://example.test/x'
 elif f=='engine_sha':next(iter(m['engine']['artifacts'].values()))['sha256']='0'
 elif f=='engine_tag_drift':next(iter(m['engine']['artifacts'].values()))['url']=next(iter(m['engine']['artifacts'].values()))['url'].replace('/b10344/','/b1/')
 elif f=='engine_size_bound':next(iter(m['engine']['artifacts'].values()))['max_size_bytes']=0
 elif f=='model_main':m['model']['url']=m['model']['url'].replace(m['model']['revision'],'main')
 elif f=='model_http':m['model']['url']='http://example.test/model.gguf'
 elif f=='model_sha':m['model']['sha256']='0'
 elif f=='model_revision':m['model']['revision']='main'
 elif f=='model_size_bound':m['model']['max_size_bytes']=0
 elif f=='remote_host':m['engine']['server_contract']['host']='0.0.0.0'
 elif f=='fixed_port':m['engine']['server_contract']['ephemeral_port']=False
 elif f=='api_key_inline':m['engine']['server_contract']['api_key_file']=False
 elif f=='webui':m['engine']['server_contract']['webui_enabled']=True
 elif f=='agent':m['engine']['server_contract']['agent_mode_enabled']=True
 elif f=='tools':m['engine']['server_contract']['builtin_tools_enabled']=True
 elif f=='browser_transport':m['engine']['server_contract']['browser_model_transport']=True
 elif f=='model_authority':m['authority']['model_output_is_authority']=True
 elif f=='component_authority':m['authority']['component_presence_is_authority']=True
 elif f=='runtime_authority':m['authority']['runtime_readiness_is_authority']=True
 elif f=='epistemic_authority':m['authority']['epistemic_authority']=1.0
 elif f=='execution_authority':m['authority']['execution_authority']=1.0
 elif f=='loader_env':
  from ikant.engine_supervisor import scrubbed_environment
  env=scrubbed_environment({'PATH':'/bin','LD_PRELOAD':'/evil','LD_LIBRARY_PATH':'/evil','DYLD_LIBRARY_PATH':'/evil'});return not any(k in env for k in ('LD_PRELOAD','LD_LIBRARY_PATH','DYLD_LIBRARY_PATH'))
 elif f.startswith('command_'):
  cmd=build_server_command('/engine','/model',32123,'/state/key')
  if f=='command_remote_host':cmd[cmd.index('--host')+1]='0.0.0.0'
  elif f=='command_no_key_file':cmd=cmd[:cmd.index('--api-key-file')]
  elif f=='command_webui':cmd.append('--webui')
  elif f=='command_agent':cmd.append('--agent')
  return not (cmd[cmd.index('--host')+1]=='127.0.0.1' and '--api-key-file' in cmd and '--no-webui' in cmd and '--webui' not in cmd and '--agent' not in cmd)
 else:return False
 return bool(validate_manifest(m))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mutations',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();cached={f:kill(f) for f in FAMILIES};survivors=[f for f,v in cached.items() if not v];covered={FAMILIES[i%len(FAMILIES)] for i in range(a.mutations)};tail_new={FAMILIES[(a.mutations+i)%len(FAMILIES)] for i in range(a.tail)}-covered;status='PASS' if not survivors and not tail_new and len(covered)==len(FAMILIES) else 'FAIL';print(json.dumps({'schema':'ikant-managed-local-runtime-mutations/v0.23-test','status':status,'mutations':a.mutations,'tail':a.tail,'seed':a.seed,'families':len(FAMILIES),'covered':len(covered),'survivors':survivors,'tail_new_families':sorted(tail_new)},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
