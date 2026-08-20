from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .host_capabilities import build_manifest, digest
from .web_frame import build_web_ack, validate_web_ack, wrap_prepared_frame

HUMAN_CAPABILITIES = frozenset({
    'human.whole_message_write',
    'human.partial_write_detection',
    'human.flush_failure_detection',
    'control.receipt_integrity',
    'control.config_binding',
})

@dataclass(frozen=True)
class LocalWebHostAdapter:
    bind_host: str
    port: int
    allowed_hosts: tuple[str, ...]
    adapter_id: str = 'python-local-web-v0.20'
    adapter_version: str = '0.20.0a1'

    @property
    def config_fingerprint(self) -> str:
        return digest({
            'adapter_id': self.adapter_id,
            'adapter_version': self.adapter_version,
            'bind_host': str(self.bind_host),
            'port': int(self.port),
            'allowed_hosts': tuple(sorted(self.allowed_hosts)),
            'human_render_mode': 'VERBATIM_TEXT',
        })

    def manifest(self):
        return build_manifest(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            config_fingerprint=self.config_fingerprint,
            capabilities=HUMAN_CAPABILITIES,
        )

    @staticmethod
    def _prepared(text: str = 'frame-bytes') -> dict[str, Any]:
        import hashlib
        return {
            'text': text,
            'receipt': {
                'schema': 'ikant-dashboard-frame/v0.11-test',
                'runtime_session_id': 'probe-session',
                'epoch': 1,
                'frame_seq': 1,
                'kind': 'PROBE',
                'cycle_id': None,
                'frame_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                'release_after_frame': False,
            },
            'delivery_state': 'FRAME_PENDING',
            'acknowledged': False,
        }

    def probe_human(self, mode: str = 'normal') -> dict[str, Any]:
        frame = wrap_prepared_frame(self._prepared())
        if mode == 'normal':
            visible = frame['text']; flush_ok = True
        elif mode == 'partial':
            visible = frame['text'][:-1]; flush_ok = True
        else:
            visible = frame['text']; flush_ok = False
        if not flush_ok:
            return {'accepted': False, 'error': 'DeliveryNotCommitted'}
        ack = build_web_ack(frame, visible)
        ok, errors = validate_web_ack(frame, ack)
        return {
            'accepted': ok,
            'written': len(visible) if ok else 0,
            'value': visible if ok else '',
            'errors': errors,
        }

    # S2 certifies only HUMAN_EGRESS. Unsupported surfaces fail their executable vectors.
    def probe_machine(self, target: str) -> dict[str, Any]:
        return {'accepted': False, 'error': 'UnsupportedProfile'}

    def probe_revalidation(self, drift: bool = False) -> dict[str, Any]:
        return {'accepted': False, 'errors': ['unsupported profile'], 'receipt': {}}

    def probe_legacy_attestation(self) -> dict[str, Any]:
        return {'accepted': False, 'errors': ['unsupported profile']}
