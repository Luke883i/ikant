from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ikant.component_manifest import ComponentManifestError,platform_key
from ikant.engine_supervisor import EngineSupervisorError,build_server_command
FAMILIES=('port_1','port_65535','port_0_reject','port_65536_reject','darwin_arm64','linux_amd64','windows_reject','argv_spaces','key_path_spaces','repeat_determinism')
def check(f):
 if f=='port_1':return build_server_command('/e','/m',1,'/k')[6]=='1'
 if f=='port_65535':return build_server_command('/e','/m',65535,'/k')[6]=='65535'
 if f in {'port_0_reject','port_65536_reject'}:
  try:build_server_command('/e','/m',0 if f=='port_0_reject' else 65536,'/k');return False
  except EngineSupervisorError:return True
 if f=='darwin_arm64':return platform_key('Darwin','arm64')=='darwin-arm64'
 if f=='linux_amd64':return platform_key('Linux','amd64')=='linux-x86_64'
 if f=='windows_reject':
  try:platform_key('Windows','AMD64');return False
  except ComponentManifestError:return True
 if f=='argv_spaces':return build_server_command('/engine dir/s','/model dir/m',2,'/k')[0]=='/engine dir/s'
 if f=='key_path_spaces':return '/state dir/key' in build_server_command('/e','/m',2,'/state dir/key')
 if f=='repeat_determinism':return build_server_command('/e','/m',3,'/k')==build_server_command('/e','/m',3,'/k')
 return False
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();cached={f:check(f) for f in FAMILIES};failures=[f for f,v in cached.items() if not v];covered={FAMILIES[i%len(FAMILIES)] for i in range(a.cases)};tail_new={FAMILIES[(a.cases+i)%len(FAMILIES)] for i in range(a.tail)}-covered;status='PASS' if not failures and not tail_new and len(covered)==len(FAMILIES) else 'FAIL';print(json.dumps({'schema':'ikant-managed-local-runtime-edges/v0.23-test','status':status,'cases':a.cases,'tail':a.tail,'seed':a.seed,'families':len(FAMILIES),'failures':failures,'tail_new_families':sorted(tail_new)},sort_keys=True));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
