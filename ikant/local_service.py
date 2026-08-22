from __future__ import annotations
import hashlib,json,re,threading,time
from pathlib import Path
from typing import Any
from .experience_projection import timing_mark,timing_public
from .local_web_host import LocalWebHostAdapter
from .model_broker import LocalModelBroker,LocalModelError
from .voice_input import LocalVoiceInputBroker
from .web_frame import wrap_prepared_frame,validate_web_ack

LOCAL_APP_SCHEMA='ikant-local-embodiment/v0.20-test'
class LocalAppError(RuntimeError):pass

def _sha_text(text:str)->str:return hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest()
def runtime_active(root:Path)->bool:
    try:return json.loads((root/'.ikant'/'runtime.json').read_text(encoding='utf-8')).get('status')=='ACTIVE'
    except Exception:return False

def _words(user_text:str)->list[str]:return re.findall(r"[a-zà-ÿ0-9']+",str(user_text).casefold())
def _looks_italian(user_text:str)->bool:
    words=set(_words(user_text));return bool(words&{'ciao','chi','sei','cosa','che','non','per','come','puoi','vorrei','fai','con','grazie','italiano','italiana','perché','perche','salve','buongiorno','buonasera'})
def operational_fallback(user_text:str,*,engine_label:str='local-engine')->str:
    from .interaction import build_interaction_contract
    interaction=build_interaction_contract(str(user_text),engine_label=str(engine_label));identity=bool((interaction.get('profile') or {}).get('identity_first'))
    if _looks_italian(user_text):
        if identity:return f'Sono iKant. Il motore linguistico locale {engine_label} non ha prodotto una risposta valida in questo turno; nessuna azione materiale è stata eseguita e puoi riprovare.'
        return 'Il motore linguistico locale non ha prodotto una risposta valida in questo turno; nessuna azione materiale è stata eseguita e puoi riprovare.'
    if identity:return f'I am iKant. The local language engine {engine_label} did not produce a valid reply for this turn; no material action was executed, and you can retry.'
    return 'The local language engine did not produce a valid reply for this turn; no material action was executed, and you can retry.'

_LOCAL_GREETING_IT=(r'(?:ciao|salve|buongiorno|buonasera)',r'ciao come va',r'ciao come stai')
_LOCAL_GREETING_EN=(r'(?:hi|hello|hey)',r'(?:hi|hello|hey) how are you')
_LOCAL_IDENTITY_IT=(r'(?:ciao )?chi sei',r'(?:ciao )?cosa sei',r'(?:ciao )?come ti chiami',r'(?:ciao )?(?:che|quale) modello(?: usi)?',r'(?:ciao )?che motore(?: usi)?')
_LOCAL_IDENTITY_EN=(r'(?:hi |hello )?who are you',r'(?:hi |hello )?what are you',r'(?:hi |hello )?what is your name',r'(?:hi |hello )?(?:what|which) model(?: do you use)?',r'(?:hi |hello )?what engine(?: do you use)?')

def _normalized_intent(text:str)->str:return ' '.join(_words(text))
def _matches_any(value:str,patterns:tuple[str,...])->bool:return any(re.fullmatch(pattern,value) for pattern in patterns)
def _local_social_surface(user_text:str,interaction:dict[str,Any],*,engine_label:str)->str|None:
    n=_normalized_intent(user_text)
    if _matches_any(n,_LOCAL_IDENTITY_IT):return f'Sono iKant. Il motore linguistico locale è {engine_label}; genera testo, ma non possiede autorità propria.'
    if _matches_any(n,_LOCAL_IDENTITY_EN):return f'I am iKant. The local language engine is {engine_label}; it generates text but has no authority of its own.'
    if _matches_any(n,_LOCAL_GREETING_IT):return 'Ciao, sono iKant. Dimmi pure come posso aiutarti oggi.'
    if _matches_any(n,_LOCAL_GREETING_EN):return 'Hello, I am iKant. Tell me how I can help today.'
    return None

def _structured_primary_from_chat(rt,*,cycle_id:str|None=None)->str|None:
    from .chat_session import ChatLog
    session_id=str((rt.runtime or {}).get('session_id') or '')
    if not session_id:return None
    log=ChatLog(Path(rt.state_dir)/'chat'/'transcript.jsonl',runtime_session_id=session_id);log.verify()
    for row in reversed(log.rows()):
        if row.get('role')!='ikant':continue
        if cycle_id is not None and str(row.get('cycle_id') or '')!=str(cycle_id):continue
        value=str(row.get('text') or '').strip()
        if value:return 'iKant: '+value
    return None

class LocalEmbodimentService:
    def __init__(self,root:str|Path,*,model:LocalModelBroker,voice:LocalVoiceInputBroker):
        self.root=Path(root).resolve();self.model=model;self.voice=voice;self.web_adapter:LocalWebHostAdapter|None=None;self._cert=None;self._lock=threading.RLock();self._turn_origins:dict[str,float]={};self._artifact_lock=threading.Lock()
    @property
    def state_dir(self):return self.root/'.ikant'
    def contract_text(self):return (self.root/'IKANT_ACCESS_CONTRACT.md').read_text(encoding='utf-8')
    def bind_web_adapter(self,adapter:LocalWebHostAdapter):self.web_adapter=adapter;self._cert=None
    def require_web_conformance(self)->dict[str,Any]:
        if self.web_adapter is None:raise LocalAppError('local web host adapter not bound')
        if self._cert is None:
            from .host_negotiation import certify_host
            self._cert=certify_host(self.web_adapter,profiles=['HUMAN_EGRESS'],persist_path=self.state_dir/'local-web-conformance.json')
        n=(self._cert.get('negotiations') or {}).get('HUMAN_EGRESS') or {}
        if n.get('status')!='CONFORMING':raise LocalAppError('local web HUMAN_EGRESS profile is not conforming')
        return self._cert
    def lifecycle(self):
        if runtime_active(self.root):
            try:
                from .runtime import Runtime
                from .session_egress import existing_runtime_egress
                rt=Runtime(self.state_dir)
                try:g=existing_runtime_egress(rt);egress=g.state.value if g else 'MISSING'
                finally:rt.close()
            except Exception:egress='INTEGRITY_CHECK_REQUIRED'
            return {'schema':LOCAL_APP_SCHEMA,'state':'ACTIVE','egress':egress}
        from .admission import load_probe,load_receipt,validate_receipt
        contract=self.contract_text();ok,_=validate_receipt(load_receipt(self.state_dir),contract)
        if not ok:state='AWAITING_ACCEPTANCE'
        else:
            p=load_probe(self.state_dir);state='PROBED' if p.get('overall')=='READY' and p.get('consumed') is False else 'ACCEPTED'
        return {'schema':LOCAL_APP_SCHEMA,'state':state,'contract_sha256':_sha_text(contract),'model':self.model.status(),'voice':self.voice.status()}
    def admission_view(self):
        if runtime_active(self.root):raise LocalAppError('admission view unavailable after ACTIVE')
        text=self.contract_text();return {'schema':LOCAL_APP_SCHEMA,'state':self.lifecycle()['state'],'terms':text,'terms_sha256':_sha_text(text),'acceptance_phrase':'I ACCEPT'}
    def accept(self,phrase,presented_terms_sha256):
        with self._lock:
            if runtime_active(self.root):raise LocalAppError('accept unavailable after ACTIVE')
            from .admission import issue_receipt,save_receipt
            r=issue_receipt(self.contract_text(),str(phrase),presented_terms_sha256=str(presented_terms_sha256));save_receipt(self.state_dir,r);return {'schema':LOCAL_APP_SCHEMA,'state':'ACCEPTED','receipt_id':r.get('receipt_id')}
    def probe(self):
        with self._lock:
            if runtime_active(self.root):raise LocalAppError('probe unavailable after ACTIVE')
            from .admission import load_receipt,probe,save_probe,validate_receipt
            contract=self.contract_text();ok,e=validate_receipt(load_receipt(self.state_dir),contract)
            if not ok:raise PermissionError('; '.join(e))
            out=probe(self.root,self.state_dir,contract);save_probe(self.state_dir,out);return out
    def initialize(self):
        with self._lock:
            if runtime_active(self.root):return self.frame()
            self.require_web_conformance()
            from .runtime import Runtime
            from .session_egress import activate_runtime_egress
            from .session_host import prepare_human_frame
            from .human_dashboard import persist_dashboard
            rt=Runtime.initialize(self.state_dir,self.contract_text())
            try:
                activate_runtime_egress(rt,initialization=True);p=prepare_human_frame(rt,persist_dashboard(rt),kind='INITIALIZE',notice='iKant ACTIVE. Canale umano vincolato alla dashboard.');return wrap_prepared_frame(p)
            finally:rt.close()
    def frame(self):
        with self._lock:
            self.require_web_conformance()
            from .runtime import Runtime
            from .session_egress import EgressState,existing_runtime_egress
            from .session_host import recover_prepared_frame,prepare_human_frame
            from .human_dashboard import persist_dashboard
            rt=Runtime(self.state_dir)
            try:
                g=existing_runtime_egress(rt)
                if not g:raise LocalAppError('ACTIVE runtime requires egress guard')
                if g.state in {EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING}:
                    p=recover_prepared_frame(rt)
                    if not p:raise LocalAppError('pending egress has no recoverable frame')
                    receipt=dict(p.get('receipt') or {});primary=_structured_primary_from_chat(rt,cycle_id=receipt.get('cycle_id')) if str(receipt.get('kind') or '').upper()=='TURN' else None;return wrap_prepared_frame(p,primary_text=primary)
                if g.state==EgressState.RELEASED:return {'schema':LOCAL_APP_SCHEMA,'released':True,'state':'RELEASED'}
                g.require_locked();p=prepare_human_frame(rt,persist_dashboard(rt),kind='WEB_DASHBOARD');return wrap_prepared_frame(p,primary_text=_structured_primary_from_chat(rt))
            finally:rt.close()
    def _render_cycle_artifact(self,cycle:str)->None:
        if not cycle:return
        with self._artifact_lock:
            json_path=self.state_dir/'cognitive'/f'{cycle}.json';docx_path=self.state_dir/'artifacts'/f'CRC_SNAPSHOT_{cycle}.docx'
            if docx_path.is_file() or not json_path.is_file():return
            try:
                from .surfaces import export_surface_b_docx
                snapshot=json.loads(json_path.read_text(encoding='utf-8'))
                if str(snapshot.get('cycle_id') or '')!=cycle:return
                export_surface_b_docx(snapshot,docx_path)
            except Exception:return
    def _schedule_cycle_artifact(self,cycle:str)->None:
        if not cycle:return
        threading.Thread(target=self._render_cycle_artifact,args=(cycle,),name='ikant-cycle-artifact',daemon=True).start()

    def acknowledge(self,ack):
        with self._lock:
            self.require_web_conformance()
            from .runtime import Runtime
            from .session_egress import existing_runtime_egress
            from .session_host import recover_prepared_frame,acknowledge_prepared_frame
            rt=Runtime(self.state_dir)
            try:
                p=recover_prepared_frame(rt)
                if not p:raise LocalAppError('acknowledgement requires a pending sealed frame')
                frame=wrap_prepared_frame(p);ok,e=validate_web_ack(frame,ack)
                if not ok:raise LocalAppError('web frame acknowledgement mismatch: '+'; '.join(e))
                result=acknowledge_prepared_frame(rt,p,ack['visible_text'])
                receipt=dict(p.get('receipt') or {});cycle=str(receipt.get('cycle_id') or '')
                if cycle:
                    cog=rt.runtime.setdefault('cognitive',{});timing=dict(cog.get('last_turn_timing') or {});origin=self._turn_origins.pop(cycle,None)
                    if origin is not None:
                        timing['_origin']=origin;timing_mark(timing,'ACK_DONE',time.perf_counter());cog['last_turn_timing']=timing_public(timing);rt._write_runtime()
                    self._schedule_cycle_artifact(cycle)
                return {'schema':LOCAL_APP_SCHEMA,'acknowledged':True,'delivery_state':existing_runtime_egress(rt).state.value}
            finally:rt.close()
    def turn(self,user_text):
        with self._lock:
            self.require_web_conformance();text=str(user_text)
            if not text.strip() or len(text.encode())>65536:raise LocalAppError('intent outside bound')
            from .runtime import Runtime
            from .session_host import DashboardOnlySession
            from .surfaces import validate_surface_a
            from .interaction import build_interaction_contract,validate_interaction_surface
            turn_origin=time.perf_counter();rt=Runtime(self.state_dir)
            try:
                s=DashboardOnlySession(rt);begin=s.begin_user(text,engine_label=self.model.model,timing_origin=turn_origin)
                if begin.get('control')!='TURN':
                    human=begin.get('human')
                    if not human:raise LocalAppError('control transition missing human frame')
                    return wrap_prepared_frame(human)
                out=begin['machine'];cycle=str(out['cycle']['cycle_id']);intent=out.get('intention_node_id');contract=out['surface_a_contract'];interaction=out.get('interaction_contract') or build_interaction_contract(text,engine_label=self.model.model);timing=out.get('turn_timing') or {};self._turn_origins[cycle]=turn_origin
                timing_mark(timing,'MODEL_START',time.perf_counter());started=time.perf_counter();surface=_local_social_surface(text,interaction,engine_label=self.model.model)
                if surface is not None:
                    source='LOCAL_INTERACTION_KERNEL';ok,e=validate_surface_a(surface);iok,ie=validate_interaction_surface(surface,interaction);errors=list(dict.fromkeys(list(e)+list(ie)))
                    if not (ok and iok):raise LocalAppError('local interaction kernel failed: '+'; '.join(errors))
                    metrics={'status':'VALIDATED','route':'LOCAL_INTERACTION_KERNEL','attempts':0,'request_ms':[],'total_ms':round((time.perf_counter()-started)*1000,3),'prompt_tokens':0,'completion_tokens':0,'epistemic_authority':0.0,'execution_authority':0.0}
                else:
                    source='MODEL'
                    try:surface=self.model.complete_surface_a(contract,text,validator=validate_surface_a)
                    except LocalModelError:
                        source='OPERATIONAL_FALLBACK';surface=operational_fallback(text,engine_label=self.model.model);ok,e=validate_surface_a(surface);iok,ie=validate_interaction_surface(surface,interaction);errors=list(dict.fromkeys(list(e)+list(ie)))
                        if not (ok and iok):raise LocalAppError('operational fallback failed: '+'; '.join(errors))
                    metrics=dict(getattr(self.model,'last_completion_metrics',{}) or {})
                timing_mark(timing,'MODEL_DONE',time.perf_counter());ok,e=validate_surface_a(surface);iok,ie=validate_interaction_surface(surface,interaction)
                if not (ok and iok):raise LocalAppError('validated reply contract drift: '+'; '.join(list(e)+list(ie)))
                timing_mark(timing,'VALIDATION_DONE',time.perf_counter());prepared=s.finalize(cycle,surface,intention_node_id=intent);timing_mark(timing,'FRAME_SEALED',time.perf_counter())
                generation={'cycle_id':cycle,'source':source,'model_generation_valid':source=='MODEL','model_metrics':metrics,'epistemic_authority':0.0,'execution_authority':0.0};cog=rt.runtime.setdefault('cognitive',{});cog['last_surface_a_generation']=generation;timing_mark(timing,'PRIMARY_DELIVERED',time.perf_counter());cog['last_turn_timing']=timing_public(timing);rt._write_runtime();rt._event('SURFACE_A_GENERATION',cycle,dict(generation));frame=wrap_prepared_frame(prepared,primary_text='iKant: '+surface);frame['generation']=generation;frame['turn_timing']=timing_public(timing);return frame
            finally:rt.close()
    def notice(self,message,*,kind='LOCAL_WEB_NOTICE'):
        with self._lock:
            self.require_web_conformance()
            from .runtime import Runtime
            from .human_dashboard import persist_dashboard
            from .session_host import prepare_human_frame
            rt=Runtime(self.state_dir)
            try:return wrap_prepared_frame(prepare_human_frame(rt,persist_dashboard(rt),kind=kind,notice=str(message)))
            finally:rt.close()
    def resume(self,user_text):
        with self._lock:
            self.require_web_conformance()
            from .runtime import Runtime
            from .session_host import DashboardOnlySession
            rt=Runtime(self.state_dir)
            try:return wrap_prepared_frame(DashboardOnlySession(rt).resume_frame(str(user_text)))
            finally:rt.close()
    def transcribe(self,audio,content_type):return self.voice.transcribe(audio,content_type)
