from __future__ import annotations
from dataclasses import asdict
from typing import Any
from .chat_session import ChatController
from .human_dashboard import persist_dashboard,render_dashboard_ascii
from .runtime_host import conforming_turn,emit_incarnate_surface_a
from .session_egress import DashboardEgressGuard,FrameReceipt,EgressState,EgressViolation,existing_runtime_egress
from .transport import TransportAttestation
SESSION_HOST_SCHEMA='ikant-dashboard-session-host/v0.11-test'
def _guard(runtime):
    guard=existing_runtime_egress(runtime)
    if not guard: raise EgressViolation('ACTIVE runtime requires initialized egress guard')
    return guard
def _controller(runtime):return ChatController(runtime,turn_fn=conforming_turn,emit_fn=emit_incarnate_surface_a,dashboard_fn=persist_dashboard)
def prepare_text_frame(runtime,frame_text,*,kind,cycle_id=None,release_after_frame=False):
    guard=_guard(runtime);guard.require_locked();receipt=guard.seal_frame(frame_text,kind=kind,cycle_id=cycle_id,release_after_frame=release_after_frame);return {'schema':SESSION_HOST_SCHEMA,'text':frame_text,'receipt':asdict(receipt),'delivery_state':guard.state.value,'acknowledged':False}
def prepare_human_frame(runtime,dashboard,*,kind,cycle_id=None,release_after_frame=False,notice=None,width=96):
    guard=_guard(runtime);guard.require_locked();projected=guard.attach_projection(dashboard,notice=notice);return prepare_text_frame(runtime,render_dashboard_ascii(projected,width=width),kind=kind,cycle_id=cycle_id,release_after_frame=release_after_frame)
def acknowledge_prepared_frame(runtime,prepared,actual_visible_text):
    guard=_guard(runtime);receipt=FrameReceipt(**dict(prepared['receipt']))
    if not guard.acknowledge_visible(receipt,actual_visible_text):raise EgressViolation('visible dashboard delivery acknowledgement failed')
    return {**prepared,'delivery_state':guard.state.value,'acknowledged':True}
def recover_prepared_frame(runtime):
    pending=_guard(runtime).pending_frame()
    if pending is None:return None
    receipt,text=pending;return {'schema':SESSION_HOST_SCHEMA,'text':text,'receipt':asdict(receipt),'delivery_state':_guard(runtime).state.value,'acknowledged':False,'recovery':True}
def canonical_human_frame(runtime,dashboard,**kwargs):return prepare_human_frame(runtime,dashboard,**kwargs)
class DashboardOnlySession:
    def __init__(self,runtime,*,transport_attestation:TransportAttestation|dict|None=None):
        runtime.require_active();self.runtime=runtime;self.guard=_guard(runtime);self.controller=_controller(runtime);self.transport_attestation=transport_attestation
    def pending_recovery(self):return recover_prepared_frame(self.runtime)
    def acknowledge(self,prepared,actual_visible_text):return acknowledge_prepared_frame(self.runtime,prepared,actual_visible_text)
    def activation_frame(self,*,width=96):return prepare_human_frame(self.runtime,persist_dashboard(self.runtime),kind='INITIALIZE',notice='iKant ACTIVE. Canale umano vincolato alla dashboard.',width=width)
    def begin_user(self,intent,*,engine_label=None,width=96,**kwargs):
        if self.guard.state in {EgressState.FRAME_PENDING,EgressState.RELEASE_PENDING}:return {'control':'RECOVER','human':recover_prepared_frame(self.runtime)}
        self.guard.require_locked()
        if self.guard.classify_user_text(intent)=='EXIT':return {'control':'EXIT','human':prepare_human_frame(self.runtime,persist_dashboard(self.runtime),kind='EXIT',release_after_frame=True,notice="Uscita da iKant confermata: dal prossimo turno risponde l'assistente locale. RESUME IKANT per rientrare se il runtime resta integro.",width=width)}
        return {'control':'TURN','machine':self.controller.begin(intent,engine_label=engine_label,**kwargs)}
    def finalize(self,cycle_id,text,*,intention_node_id=None,width=96):
        self.guard.require_locked();self.controller.close(cycle_id,text,intention_node_id=intention_node_id);dash=persist_dashboard(self.runtime,surface_a_text=text,cycle_id=cycle_id,surface_a_validated=True);return prepare_human_frame(self.runtime,dash,kind='TURN',cycle_id=cycle_id,width=width)
    def resume_frame(self,user_text,*,width=96):
        if user_text!='RESUME IKANT':raise EgressViolation('exact RESUME IKANT required outside iKant')
        integrity=self.runtime.integrity();self.guard.resume(runtime_integrity_ok=bool(integrity.get('ok')),transport_attestation=self.transport_attestation);return prepare_human_frame(self.runtime,persist_dashboard(self.runtime),kind='RESUME',notice='iKant riattivato: output umano nuovamente vincolato alla dashboard.',width=width)
