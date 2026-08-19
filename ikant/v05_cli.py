from __future__ import annotations
import argparse,json,os,sys,textwrap
from pathlib import Path
from . import cli as legacy
from .admission import state_dir,issue_receipt,save_receipt,load_receipt,probe,save_probe,validate_receipt
from .chat_session import ChatController,ChatLog,sanitize_shell_content
from .dashboard_v05 import persist_dashboard,render_dashboard_ascii
from .host_v05 import conforming_turn,emit_incarnate_surface_a
from .psyche import validate_functional_psyche
from .runtime import Runtime
from .session_egress import activate_runtime_egress,existing_runtime_egress,EgressState,EgressViolation
from .session_host import prepare_human_frame,prepare_text_frame,acknowledge_prepared_frame,recover_prepared_frame

def emit(x):print(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True))
def _root():return Path.cwd()
def _contract():return (_root()/'IKANT_ACCESS_CONTRACT.md').read_text(encoding='utf-8')
def _runtime():return Runtime(state_dir(_root()))
def _log(rt):return ChatLog(Path(rt.state_dir)/'chat'/'transcript.jsonl',runtime_session_id=rt.runtime.get('session_id'))
def _controller(rt):return ChatController(rt,turn_fn=conforming_turn,emit_fn=emit_incarnate_surface_a,dashboard_fn=persist_dashboard)
def _machine_channel():return os.environ.get('IKANT_MACHINE_CHANNEL')=='1'
def _active_on_disk():
 try:return json.loads((_root()/'.ikant'/'runtime.json').read_text(encoding='utf-8')).get('status')=='ACTIVE'
 except Exception:return False

def _emit_prepared(rt,prepared):
 text=prepared['text']
 try:
  written=sys.stdout.write(text);sys.stdout.flush()
 except Exception:
  # Deliberately keep FRAME_PENDING/RELEASE_PENDING for exact replay.
  raise
 if written is not None and written!=len(text):
  raise OSError(f'partial human egress write: {written}/{len(text)} characters')
 return acknowledge_prepared_frame(rt,prepared,text)

def _human(rt,dash,*,kind,cycle_id=None,release=False,notice=None,width=96):
 return _emit_prepared(rt,prepare_human_frame(rt,dash,kind=kind,cycle_id=cycle_id,release_after_frame=release,notice=notice,width=width))

def _recover_pending_human_frame_if_any():
 if not _active_on_disk() or _machine_channel():return False
 rt=_runtime()
 try:
  g=existing_runtime_egress(rt)
  if not g or g.state not in {EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING}:return False
  prepared=recover_prepared_frame(rt)
  if not prepared:raise EgressViolation('pending egress state has no recoverable frame')
  _emit_prepared(rt,prepared);return True
 finally:rt.close()

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
def _render_history_inside_dashboard(dashboard,log,*,limit=20,width=96):
 base=render_dashboard_ascii(dashboard,width=width).splitlines();line='+'+'-'*(width-2)+'+';inner=width-4
 if base and base[-1]==line:base.pop()
 base.extend([line,'|'+ ' CHAT PERSISTENTE '.center(width-2)+'|',line]);rows=log.rows()[-max(1,int(limit)):]
 for row in rows:
  prefix='> iKant:' if row.get('role')=='ikant' else '> user:';clean=sanitize_shell_content(row.get('text',''));logical=clean.split('\n') or [''];first=True
  for part in logical:
   chunks=textwrap.wrap(part,width=max(12,inner-len(prefix)-1),replace_whitespace=False,drop_whitespace=False) or ['']
   for chunk in chunks:
    text=f"{prefix if first else ' '*len(prefix)} {chunk}".rstrip();base.append('| '+text[:inner].ljust(inner)+' |');first=False
 base.append(line);return '\n'.join(base)

def main(argv=None):
 argv=list(sys.argv[1:] if argv is None else argv)
 # Crash recovery has precedence over every new human-channel command. The prior
 # sealed frame is replayed byte-for-byte, then the user may retry their command.
 if _recover_pending_human_frame_if_any():return 0
 if not argv:
  if _active_on_disk() and not _machine_channel():
   rt=_runtime()
   try:
    g=existing_runtime_egress(rt)
    if g and g.state==EgressState.RELEASED:return 0
    _human(rt,persist_dashboard(rt),kind='DASHBOARD',notice='Canale iKant ACTIVE: usa EXIT IKANT per tornare all assistente locale.');return 0
   finally:rt.close()
  return legacy.main(argv)
 command=argv[0]
 handled={'accept','probe','initialize','turn','emit-surface-a','dashboard','history','shell','integrity','self','status','exit','resume'}
 if command not in handled:
  if _active_on_disk() and not _machine_channel():
   rt=_runtime()
   try:
    g=existing_runtime_egress(rt) or activate_runtime_egress(rt);g.require_locked();_human(rt,persist_dashboard(rt),kind='COMMAND_BLOCKED',notice=f'Comando {command} disponibile solo sul canale macchina interno.');return 4
   finally:rt.close()
  return legacy.main(argv)
 if command=='accept':
  p=argparse.ArgumentParser(prog='ikant accept');p.add_argument('phrase');p.add_argument('--presented-terms-sha256',required=True);a=p.parse_args(argv[1:]);ct=_contract();r=issue_receipt(ct,a.phrase,presented_terms_sha256=a.presented_terms_sha256);save_receipt(state_dir(_root()),r);emit(r);return 0
 if command=='probe':
  p=argparse.ArgumentParser(prog='ikant probe');p.parse_args(argv[1:]);ct=_contract();ok,errs=validate_receipt(load_receipt(state_dir(_root())),ct)
  if not ok:raise PermissionError('; '.join(errs))
  x=probe(_root(),state_dir(_root()),ct);save_probe(state_dir(_root()),x);emit(x);return 0 if x['overall']=='READY' else 2
 if command=='initialize':
  p=argparse.ArgumentParser(prog='ikant initialize');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=Runtime.initialize(state_dir(_root()),_contract())
  try:
   activate_runtime_egress(rt);_human(rt,persist_dashboard(rt),kind='INITIALIZE',notice='iKant ACTIVE. Da ora il canale umano e bloccato sulla dashboard.',width=a.width);return 0
  finally:rt.close()
 if command=='resume':
  p=argparse.ArgumentParser(prog='ikant resume');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   g=existing_runtime_egress(rt)
   if not g:raise PermissionError('egress state missing; initialize iKant first')
   g.resume(runtime_integrity_ok=bool(rt.integrity().get('ok')));_human(rt,persist_dashboard(rt),kind='RESUME',notice='iKant riattivato: output umano nuovamente vincolato alla dashboard.',width=a.width);return 0
  finally:rt.close()
 if command=='exit':
  p=argparse.ArgumentParser(prog='ikant exit');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   g=existing_runtime_egress(rt) or activate_runtime_egress(rt);g.require_locked();_human(rt,persist_dashboard(rt),kind='EXIT',release=True,notice="Uscita da iKant confermata: dal prossimo turno risponde l'assistente locale. RESUME IKANT per rientrare se il runtime resta integro.",width=a.width);return 0
  finally:rt.close()
 if command=='status':
  p=argparse.ArgumentParser(prog='ikant status');p.add_argument('--json',action='store_true');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   if a.json and _machine_channel():emit(rt.status())
   else:_human(rt,persist_dashboard(rt),kind='STATUS',width=a.width)
   return 0
  finally:rt.close()
 if command=='turn':
  p=argparse.ArgumentParser(prog='ikant turn');p.add_argument('--intent',required=True);p.add_argument('--limit',type=int,default=12);p.add_argument('--atoms-json');p.add_argument('--surface-b-path');p.add_argument('--host-engine');p.add_argument('--json',action='store_true');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);atoms=None
  if a.atoms_json:
   data=json.loads(Path(a.atoms_json).read_text(encoding='utf-8'));atoms=data.get('atoms',[]) if isinstance(data,dict) else data
  rt=_runtime()
  try:
   g=existing_runtime_egress(rt) or activate_runtime_egress(rt);g.require_locked();out=_controller(rt).begin(a.intent,engine_label=a.host_engine,limit=a.limit,atoms=atoms,docx_path=a.surface_b_path);pstate=out.get('functional_psyche',{});dash=persist_dashboard(rt,cycle_id=out['cycle']['cycle_id']);payload={'schema':'ikant-host-turn/v0.10-test','cycle_id':out['cycle']['cycle_id'],'intention_node_id':out.get('intention_node_id'),'chat':out.get('chat',{}),'host_binding':rt.runtime.get('host',{}),'interaction_contract':out['interaction_contract'],'surface_a_contract':out['surface_a_contract'],'central_oracle':out['central_oracle'],'central_projection':out['central_projection'],'functional_psyche':{'self_knowledge':pstate.get('self_knowledge'),'affective_field':pstate.get('affective_field'),'epistemic_accumulation':pstate.get('epistemic_accumulation'),'collapse_emergence':pstate.get('collapse_emergence')},'psyche_json':out.get('psyche_json'),'surface_b_json':out.get('surface_b_json'),'surface_b_docx':out.get('surface_b_docx'),'dashboard':dash.get('persisted',{}),'incarnate':dash.get('incarnate',{})}
   if a.json and _machine_channel():emit(payload)
   else:_human(rt,dash,kind='TURN_PENDING',cycle_id=out['cycle']['cycle_id'],width=a.width)
   return 0
  finally:rt.close()
 if command=='emit-surface-a':
  p=argparse.ArgumentParser(prog='ikant emit-surface-a');p.add_argument('--cycle-id',required=True);p.add_argument('--text',required=True);p.add_argument('--intention-node-id');p.add_argument('--json',action='store_true');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   g=existing_runtime_egress(rt) or activate_runtime_egress(rt);g.require_locked();rec=_controller(rt).close(a.cycle_id,a.text,intention_node_id=a.intention_node_id);dash=persist_dashboard(rt,surface_a_text=a.text,cycle_id=a.cycle_id,surface_a_validated=True);rec['dashboard']=dash
   if a.json and _machine_channel():emit(rec)
   else:_human(rt,dash,kind='TURN',cycle_id=a.cycle_id,width=a.width)
   return 0
  finally:rt.close()
 if command=='dashboard':
  p=argparse.ArgumentParser(prog='ikant dashboard');p.add_argument('--json',action='store_true');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   d=persist_dashboard(rt)
   if a.json and _machine_channel():emit(d)
   else:_human(rt,d,kind='DASHBOARD',width=a.width)
   return 0
  finally:rt.close()
 if command=='self':
  p=argparse.ArgumentParser(prog='ikant self');p.add_argument('--json',action='store_true');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   s=(rt.runtime.get('cognitive') or {}).get('psyche') or {};out={'schema':'ikant-self-inspection/v0.10-test','status':'OK','self_knowledge':s.get('self_knowledge'),'affective_field':s.get('affective_field'),'maturation':s.get('epistemic_accumulation'),'faculties':s.get('faculties'),'boundaries':s.get('boundaries')} if s else {'schema':'ikant-self-inspection/v0.10-test','status':'NOT_YET_MATERIALIZED','message':'Run at least one conforming cognitive turn to materialize the operational self-model.'}
   if a.json and _machine_channel():emit(out)
   else:_human(rt,persist_dashboard(rt),kind='SELF',width=a.width)
   return 0
  finally:rt.close()
 if command in {'history','shell'}:
  p=argparse.ArgumentParser(prog=f'ikant {command}');p.add_argument('--limit',type=int,default=20);p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
  try:
   log=_log(rt);log.verify();dash=persist_dashboard(rt);frame=_render_history_inside_dashboard(dash,log,limit=a.limit,width=a.width);_emit_prepared(rt,prepare_text_frame(rt,frame,kind=command.upper()));return 0
  finally:rt.close()
 p=argparse.ArgumentParser(prog='ikant integrity');p.add_argument('--json',action='store_true');p.add_argument('--width',type=int,default=96);a=p.parse_args(argv[1:]);rt=_runtime()
 try:
  core=rt.integrity();chat=_log(rt).verify();psyche=_psyche_integrity(rt);eg=existing_runtime_egress(rt);egress=eg.verify() if eg else {'ok':False,'status':'MISSING'};out={'schema':'ikant-host-integrity/v0.10-test','ok':bool(core.get('ok')) and bool(chat.get('ok')) and bool(psyche.get('ok')) and bool(egress.get('ok')),'runtime':core,'chat':chat,'psyche':psyche,'egress':egress}
  if a.json and _machine_channel():emit(out)
  else:_human(rt,persist_dashboard(rt),kind='INTEGRITY',notice='Integrita runtime: '+('OK' if out['ok'] else 'FAIL'),width=a.width)
  return 0 if out['ok'] else 3
 finally:rt.close()
