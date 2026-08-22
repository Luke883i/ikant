from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import Any
from .foundation_runtime import FOUNDATION_RECONCILIATION_SCHEMA, FOUNDATION_RUNTIME_SCHEMA, FOUNDATION_VERSION, FoundationModelBroker, evidence_summary, load_settings, update_settings
from .local_service import runtime_active

class FoundationWorkspaceCoordinator:
    """Zero-authority projection of only currently fulfillable web services."""
    def __init__(self, base: Any): self.base = base; self.root = Path(base.root).resolve(); self._model_lock = threading.RLock()
    def __getattr__(self, name: str) -> Any:
        value = getattr(self.base, name)
        if not callable(value): return value
        def call(*args, **kwargs):
            self._ensure_model_wrapper()
            return value(*args, **kwargs)
        return call
    def _delegate(self):
        node: Any = self.base
        for _ in range(6):
            delegate = getattr(node, '_delegate', None)
            if delegate is not None: return delegate
            node = getattr(node, 'base', None)
            if node is None: break
        return None
    def _ensure_model_wrapper(self):
        with self._model_lock:
            delegate = self._delegate()
            if delegate is not None and not isinstance(getattr(delegate, 'model', None), FoundationModelBroker):
                delegate.model = FoundationModelBroker(self.root, delegate.model)
            return delegate
    def _runtime(self) -> dict[str, Any]:
        try: value = json.loads((self.root / '.ikant' / 'runtime.json').read_text(encoding='utf-8'))
        except Exception: return {}
        return value if isinstance(value, dict) else {}
    @staticmethod
    def _service(service_id: str, label: str, proof: str, detail: str | None = None) -> dict[str, Any]:
        return {'id': service_id, 'label': label, 'state': 'READY', 'proof': proof, 'detail': detail, 'epistemic_authority': 0.0, 'execution_authority': 0.0}
    @staticmethod
    def _shell_state(delegate: Any) -> dict[str, Any]:
        shell = getattr(delegate, 'web_shell', None)
        if shell is None: return {'claimed': False, 'pending': False, 'runtime_session_id': None, 'last_acked_frame': None}
        with shell._lock:
            return {'claimed': bool(shell._shell_id), 'pending': shell._pending is not None, 'runtime_session_id': shell._runtime_session_id, 'last_acked_frame': dict(shell._last_acked_frame) if isinstance(shell._last_acked_frame, dict) else None}
    def foundation_manifest(self) -> dict[str, Any]:
        settings = load_settings(self.root); evidence = evidence_summary(self.root); runtime = self._runtime(); session = str(runtime.get('session_id') or '') or None; active = runtime_active(self.root); delegate = self._ensure_model_wrapper(); shell_state = self._shell_state(delegate)
        services = [self._service('configuration', 'Configurazione', 'REVISIONED_LOCAL_SETTINGS')]
        try: bootstrap = self.bootstrap_status()
        except Exception: bootstrap = None
        if isinstance(bootstrap, dict) and bootstrap.get('schema'): services.append(self._service('bootstrap_diagnostics', 'Diagnostica avvio', 'HASH_CHAINED_BOOTSTRAP_JOURNAL'))
        if delegate is not None:
            model = delegate.model.status(); binding = str(model.get('runtime_binding_digest') or '')
            if model.get('configured') and model.get('managed_runtime') and len(binding) == 64: services.append(self._service('local_model', 'Motore locale', 'MANAGED_RUNTIME_BINDING', str(model.get('model') or 'local model')))
            if active: services.append(self._service('chat', 'Conversazione', 'ACTIVE_EXACT_EGRESS'))
            voice = delegate.voice.status()
            if voice.get('configured') is True: services.append(self._service('voice_input', 'Voce locale', 'LOOPBACK_STT_CONFIGURED'))
            ack = shell_state['last_acked_frame']; exact_ack = bool(active and shell_state['claimed'] and not shell_state['pending'] and isinstance(ack, dict) and ack.get('runtime_session_id') == session and shell_state['runtime_session_id'] == session)
            if exact_ack: services.append(self._service('epistemic_workspace', 'Evidenza e tracce', 'EXACT_LAST_ACK_BOUND'))
        checks = {'settings_fingerprinted': len(str(settings.get('sha256') or '')) == 64, 'runtime_identity_bound': (not active) or bool(session), 'evidence_cycle_bound': evidence.get('state') != 'MISMATCH', 'service_proofs_present': all(s.get('state') == 'READY' and bool(s.get('proof')) for s in services), 'future_supply_absent': all(s.get('id') not in {'browser_companion','native_control','provider_actions','floating_shell'} for s in services)}
        if any(s['id'] == 'epistemic_workspace' for s in services): checks['epistemic_exact_ack_bound'] = bool(shell_state['last_acked_frame']) and shell_state['runtime_session_id'] == session
        reconciled = all(checks.values()); reconciliation = {'schema': FOUNDATION_RECONCILIATION_SCHEMA, 'state': 'RECONCILED' if reconciled else 'BLOCKED', 'runtime_session_id': session, 'cycle_id': evidence.get('cycle_id'), 'settings_revision': settings['revision'], 'settings_sha256': settings['sha256'], 'checks': checks, 'epistemic_authority': 0.0, 'execution_authority': 0.0}
        return {'schema': FOUNDATION_RUNTIME_SCHEMA, 'foundation_version': FOUNDATION_VERSION, 'scope': 'CURRENT_WEB_FULFILLABLE_ONLY', 'settings': settings, 'services': services, 'evidence': evidence, 'reconciliation': reconciliation, 'only_proof_backed_services': True, 'future_supply_exposed': False, 'epistemic_authority': 0.0, 'execution_authority': 0.0}
    def update_foundation_settings(self, payload: object) -> dict[str, Any]: update_settings(self.root, payload); return self.foundation_manifest()
