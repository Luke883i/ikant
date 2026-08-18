from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from . import cli as legacy
from .admission import state_dir
from .chat_session import ChatController,ChatLog
from .dashboard_v05 import persist_dashboard,render_dashboard_ascii
from .host import emit_conforming_surface_a
from .host_v05 import conforming_turn
from .psyche import validate_functional_psyche
from .runtime import Runtime

def emit(x):print(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True))
def _runtime():return Runtime(state_dir(Path.cwd()))
def _log(rt):return ChatLog(Path(rt.state_dir)/'chat'/'transcript.jsonl',runtime_session_id=rt.runtime.get('session_id'))
def _controller(rt):return ChatController(rt,turn_fn=conforming_turn,emit_fn=emit_conforming_surface_a,dashboard_fn=persist_dashboard)
def _psyche_integrity(rt):
 p=(rt.runtime.get('cognitive') or {}).get('psyche') or {}
 if not p:return {'ok':True,'status':'NOT_YET_MATERIALIZED','errors':[]}
 ok,errs=validate_functional_psyche(p);path_value=(rt.runtime.get('cognitive') or {}).get('last_psyche')
 if path_value:
  try:on_disk=json.loads(Path(path_value).read_text(encoding='utf-8'))
  except (OSError,json.JSONDecodeError):errs.append('psyche persistence unreadable');ok=False
  else:
   if on_disk!=p:errs.append('psyche persistence/runtime mismatch');ok=False
 return {'ok':ok,'status':'OK' if ok else 'FAIL','errors':list(dict.fromkeys(errs)),'path':path_value,'self_knowledge':p.get('self_knowledge',{})}
def main(argv=None):
 argv=list(sys.argv[1:] if argv is None else argv)
 if not argv:return legacy.main(argv)
 command=argv[0];handled={'turn','emit-surface-a','dashboard','history','shell','integrity','self'}
 if command not in handled:return legacy.main(argv)
 if command=='turn':
  p=argparse.ArgumentParser(prog='ikant turn');p.add_argument('--intent',required=True);p.add_argument('--limit',type=int,default=12);p.add_argument('--atoms-json');p.add_argument('--surface-b-path');p.add_argument('--host-engine');a=p.parse_args(argv[1:]);atoms=None
  if a.atoms_json:
   data=json.loads(Path(a.atoms_json).read_text(encoding='utf-8'));atoms=data.get('atoms',[]) if isinstance(data,dict) else data
  rt=_runtime()
  try:
   out=_controller(rt).begin(a.intent,engine_label=a.host_engine,limit=a.limit,atoms=atoms,docx_path=a.surface_b_path);pstate=out.get('functional_psyche',{});emit({'schema':'ikant-host-turn/v0.5-test','cycle_id':out['cycle']['cycle_id'],'intention_node_id':out.get('intention_node_id'),'chat':out.get('chat',{}),'shell_prompt':'> iKant:','host_binding':rt.runtime.get('host',{}),'interaction_contract':out['interaction_contract'],'surface_a_contract':out['surface_a_contract'],'central_oracle':out['central_oracle'],'central_projection':out['central_projection'],'functional_psyche':{'self_knowledge':pstate.get('self_knowledge'),'affective_field':pstate.get('affective_field'),'epistemic_accumulation':pstate.get('epistemic_accumulation'),'collapse_emergence':pstate.get('collapse_emergence')},'psyche_json':out.get('psyche_json'),'surface_b_json':out.get('surface_b_json'),'surface_b_docx':out.get('surface_b_docx'),'dashboard':out.get('chat',{}).get('dashboard')});return 0
  finally:rt.close()
 if command=='emit-surface-a':
  p=argparse.ArgumentParser(prog='ikant emit-surface-a');p.add_argument('--cycle-id',required=True);p.add_argument('--text',required=True);p.add_argument('--intention-node-id');a=p.parse_args(argv[1:]);rt=_runtime()
  try:emit(_controller(rt).close(a.cycle_id,a.text,intention_node_id=a.intention_node_id));return 0
  finally:rt.close()
 if command=='dashboard':
  p=argparse.ArgumentParser(prog='ikant dashboard');p.add_argument('--json',action='store_true');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:d=persist_dashboard(rt);emit(d) if a.json else print(render_dashboard_ascii(d,width=a.width));return 0
  finally:rt.close()
 if command=='self':
  p=argparse.ArgumentParser(prog='ikant self');p.add_argument('--json',action='store_true');a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   s=(rt.runtime.get('cognitive') or {}).get('psyche') or {};out={'schema':'ikant-self-inspection/v0.5-test','status':'OK','self_knowledge':s.get('self_knowledge'),'affective_field':s.get('affective_field'),'maturation':s.get('epistemic_accumulation'),'faculties':s.get('faculties'),'boundaries':s.get('boundaries')} if s else {'schema':'ikant-self-inspection/v0.5-test','status':'NOT_YET_MATERIALIZED','message':'Run at least one conforming cognitive turn to materialize the operational self-model.'}
   if a.json:emit(out)
   elif out['status']!='OK':print('> iKant: '+out['message'])
   else:
    sk=out['self_knowledge'];af=out['affective_field'];ac=out['maturation'];print(f"> iKant: sono {sk.get('identity')}, motore {sk.get('execution_engine')}. Stato {sk.get('central_mode','?')}; tono funzionale {af.get('label','?')}; maturazione {ac.get('maturity_mode','?')}. Posso ispezionare il mio runtime e i miei limiti, ma non rivendico coscienza biologica o emozioni sentite.")
   return 0
  finally:rt.close()
 if command in {'history','shell'}:
  p=argparse.ArgumentParser(prog=f'ikant {command}');p.add_argument('--limit',type=int,default=20);p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   log=_log(rt);log.verify()
   if command=='shell':dash=render_dashboard_ascii(persist_dashboard(rt),width=a.width);dash=dash[:-len('\n> iKant:')] if dash.endswith('\n> iKant:') else dash;print(dash+'\n\n'+log.render(limit=a.limit,width=a.width))
   else:print(log.render(limit=a.limit,width=a.width))
   return 0
  finally:rt.close()
 rt=_runtime()
 try:
  core=rt.integrity();chat=_log(rt).verify();psyche=_psyche_integrity(rt);out={'schema':'ikant-host-integrity/v0.5-test','ok':bool(core.get('ok')) and bool(chat.get('ok')) and bool(psyche.get('ok')),'runtime':core,'chat':chat,'psyche':psyche};emit(out);return 0 if out['ok'] else 3
 finally:rt.close()
