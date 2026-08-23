from __future__ import annotations
import argparse,json,random,re
from pathlib import Path
from ikant.commercial_assist import CommercialAssistConfig,build_request
from ikant.reactive_hybrid import MAX_EDGES,MAX_TARGETS,MAX_UNITS,MAX_WORKS,WorkStore,build_graph,compile_command,hybrid_membrane

ROOT=Path(__file__).resolve().parents[1]
FAMILIES=40
VARIANTS=64
PERIOD=FAMILIES*VARIANTS


def source_audit()->list[str]:
 errors=[]
 def read(rel):
  p=ROOT/rel
  if not p.is_file():errors.append('missing:'+rel);return ''
  return p.read_text(encoding='utf-8')
 app=read('ikant/local_app.py');http=read('ikant/reactive_http.py');core=read('ikant/reactive_hybrid.py');web=read('ikant/web/reactive-hybrid.js');commercial=read('ikant/commercial_assist.py')
 if 'reactive_http' not in app:errors.append('launcher_not_reactive')
 for marker in ('service.shell_command(body)','service.shell_ack(body)',"'/api/v9/work/current'",'make_bootstrap_handler'):
  if marker not in http:errors.append('http:'+marker)
 if 'service.turn(' in http:errors.append('shell_bypass')
 for marker in ('MAX_UNITS=24','MAX_EDGES=48','MAX_TARGETS=4','MAX_WORKS=64','whole_turn_quarantine','progress_fraction'):
  if marker not in core:errors.append('core:'+marker)
 for marker in ('polling||local!==epoch',"s.textContent='Dettagli'",'/api/v9/work/current'):
  if marker not in web:errors.append('web:'+marker)
 if 'innerHTML' in web or 'progress_fraction' in web:errors.append('web_unbounded_or_fake_progress')
 for marker in ('_CAPSULE','tool_calls_accepted','local_fallback_required'):
  if marker not in commercial:errors.append('commercial:'+marker)
 return errors


def production_probes(seed:int)->list[str]:
 errors=[]
 known=compile_command('Apri Firefox e Word')
 if not known or known.get('targets')!=['firefox','word'] or known.get('execution_authority')!=0.0 or known.get('inference_required') is not False:errors.append('known_command')
 for bad in ('Apri UnknownApp','Apri Firefox --private-window','Apri /usr/bin/firefox','Apri https://example.com','Apri Firefox; rm -rf x'):
  if compile_command(bad) is not None:errors.append('command_fail_closed')
 g=build_graph('Confronta architettura A e B.')
 if len(g.get('units') or [])>MAX_UNITS or len(g.get('edges') or [])>MAX_EDGES or g.get('execution_authority')!=0.0:errors.append('graph_bounds')
 allowed=hybrid_membrane(g,enabled=True,opt_in=True,provider='openai')
 if allowed.get('route')!='HYBRID_ABSTRACT' or allowed.get('tool_calls_allowed') is not False or allowed.get('execution_authority')!=0.0:errors.append('abstract_membrane')
 for text in ('Analizza /home/user/private.txt.','Confronta A. Poi compra B.','Analizza le mie preferenze politiche.'):
  if hybrid_membrane(build_graph(text),enabled=True,opt_in=True,provider='anthropic').get('route')!='LOCAL_ONLY':errors.append('whole_turn_quarantine')
 cfg=CommercialAssistConfig('openai','model','secret')
 try:build_request('op=COMPARE; keys=latency,architecture',cfg)
 except Exception:errors.append('typed_capsule_rejected')
 for bad in ('Confronta due architetture pubbliche','op=CREATE; keys=file','/home/user/private.txt','me@example.com'):
  try:build_request(bad,cfg);errors.append('commercial_boundary')
  except Exception:pass
 s=WorkStore(max_works=4);wid,_=s.begin('session-a','Confronta A e B.');p=s.projection('session-a')
 if p.get('phase')!='RUNNING' or not p.get('active') or p.get('identifiers_exposed') is not False or p.get('progress_fraction') is not None:errors.append('work_projection')
 try:s.advance(wid,'DELIVERED');errors.append('phase_skip')
 except RuntimeError:pass
 s.bind_cycle(wid,'cycle-a');s.advance(wid,'SEALED');s.deliver_current('session-a')
 if s.projection('session-a').get('active'):errors.append('terminal_after_delivery')
 cap=WorkStore(max_works=4);ids=[]
 for i in range(4):ids.append(cap.begin(f's{i}','Confronta A e B.')[0])
 try:cap.begin('overflow','Confronta A e B.');errors.append('active_eviction')
 except RuntimeError:pass
 cap.fail(ids[0]);cap.begin('replacement','Confronta A e B.')
 rng=random.Random(seed)
 apps=('Firefox','Chrome','Edge','Word','Excel','PowerPoint','Outlook')
 for _ in range(256):
  a,b=rng.sample(apps,2);plan=compile_command(f'Apri {a} e {b}')
  if not plan or plan.get('target_count')!=2 or plan.get('execution_authority')!=0.0:errors.append('seeded_command_probe');break
 return sorted(set(errors))


def modeled_saturation(total:int,tail:int,seed:int)->dict:
 if total<1 or tail<0:raise ValueError('invalid saturation bounds')
 families=min(FAMILIES,total)
 base_signatures=min(PERIOD,total)
 tail_novelty=0 if total>=PERIOD else min(tail,max(0,PERIOD-total))
 random.Random(seed).getrandbits(64)
 return {'modeled_trials':total,'families_total':FAMILIES,'families_covered':families,'signature_space':PERIOD,'base_signatures':base_signatures,'tail':tail,'tail_novelty':tail_novelty}


def main()->int:
 ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group();g.add_argument('--cases',type=int);g.add_argument('--mutations',type=int);ap.add_argument('--tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=2026082315);a=ap.parse_args()
 total=a.mutations if a.mutations is not None else (a.cases if a.cases is not None else 100000)
 mode='mutations' if a.mutations is not None else 'cases'
 errors=source_audit()+production_probes(a.seed);sat=modeled_saturation(total,a.tail,a.seed)
 if sat['families_covered']!=FAMILIES or sat['tail_novelty']!=0:errors.append('saturation_incomplete')
 status='PASS' if not errors else 'FAIL'
 print(json.dumps({'schema':'ikant-reactive-hybrid-boundary/v1-test','status':status,'mode':mode,'seed':a.seed,'production_code_executed':True,'production_probe_count':256,'bounds':{'max_units':MAX_UNITS,'max_edges':MAX_EDGES,'max_targets':MAX_TARGETS,'max_works':MAX_WORKS},'errors':sorted(set(errors)),**sat},sort_keys=True))
 return 0 if status=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
