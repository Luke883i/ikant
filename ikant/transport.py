from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib, json, os, secrets, sys
from pathlib import Path
from typing import Any, TextIO
from .invariants import TRANSPORT_ATTESTATION_SCHEMA
from .store import atomic_json_write

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _digest(payload: dict[str, Any]) -> str:
    material = dict(payload); material.pop('sha256', None)
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()

@dataclass(frozen=True)
class TransportAttestation:
    schema: str
    host_transport_id: str
    human_sink: str
    machine_sink: str
    channels_separate: bool
    whole_message_serialization: bool
    post_delivery_ack: bool
    machine_human_visible: bool
    attested_at: str
    nonce: str
    sha256: str

def build_reference_attestation(*, machine_sink: str = 'disabled') -> TransportAttestation:
    payload = {
        'schema': TRANSPORT_ATTESTATION_SCHEMA,
        'host_transport_id': 'python-cli-stdio-v0.11',
        'human_sink': 'stdout',
        'machine_sink': str(machine_sink),
        'channels_separate': machine_sink not in {'stdout','stderr','/dev/stdout','/dev/stderr','-',''},
        'whole_message_serialization': True,
        'post_delivery_ack': True,
        'machine_human_visible': False,
        'attested_at': _now(),
        'nonce': secrets.token_hex(16),
    }
    payload['sha256'] = _digest(payload)
    return TransportAttestation(**payload)

def validate_transport_attestation(value: TransportAttestation | dict[str, Any] | None) -> tuple[bool, list[str]]:
    if value is None: return False, ['transport attestation missing']
    raw = asdict(value) if isinstance(value, TransportAttestation) else dict(value)
    errs = []
    if raw.get('schema') != TRANSPORT_ATTESTATION_SCHEMA: errs.append('transport attestation schema mismatch')
    if raw.get('human_sink') != 'stdout': errs.append('reference human sink must be stdout')
    if raw.get('machine_sink') in {'stdout','stderr','/dev/stdout','/dev/stderr','-','',None}: errs.append('machine sink must be explicit non-human file sink or disabled')
    if raw.get('channels_separate') is not True: errs.append('human/machine channels must be separate')
    if raw.get('whole_message_serialization') is not True: errs.append('whole-message serialization required')
    if raw.get('post_delivery_ack') is not True: errs.append('post-delivery acknowledgement required')
    if raw.get('machine_human_visible') is not False: errs.append('machine channel must not be human-visible')
    if _digest(raw) != raw.get('sha256'): errs.append('transport attestation digest mismatch')
    return not errs, errs

def deliver_human(text: str, *, stream: TextIO | None = None) -> int:
    target = stream or sys.stdout
    written = target.write(text)
    target.flush()
    if written is not None and written != len(text): raise OSError(f'partial human egress write: {written}/{len(text)} characters')
    return len(text) if written is None else written

def write_machine_payload(path_value: str | Path, payload: dict[str, Any]) -> str:
    raw = str(path_value or '').strip()
    if raw in {'','-','stdout','stderr','/dev/stdout','/dev/stderr'}: raise PermissionError('ACTIVE machine output requires an explicit non-human file path')
    path = Path(raw)
    try:
        resolved = path.resolve()
        for fd in ('/proc/self/fd/1','/proc/self/fd/2'):
            try:
                if resolved == Path(fd).resolve(): raise PermissionError('machine output may not alias stdout/stderr')
            except OSError:
                pass
    except OSError:
        resolved = path
    atomic_json_write(resolved, payload)
    return str(resolved)
