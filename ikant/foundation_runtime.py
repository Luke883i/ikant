from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
from typing import Any, Callable

from .epistemic_projection import load_json, object_projection
from .store import atomic_json_write

FOUNDATION_VERSION = 'v1-test'
FOUNDATION_RUNTIME_SCHEMA = 'ikant-foundation-runtime/v1-test'
FOUNDATION_SETTINGS_SCHEMA = 'ikant-foundation-settings/v1-test'
FOUNDATION_EVIDENCE_SCHEMA = 'ikant-foundation-evidence-summary/v1-test'
FOUNDATION_RECONCILIATION_SCHEMA = 'ikant-foundation-reconciliation/v1-test'
MAX_META_PROMPT_BYTES = 2048
MIN_REPLY_WORDS = 40
MAX_REPLY_WORDS = 500
DEFAULT_REPLY_WORDS = 160
IMMUTABLE_GUARDRAILS = (
    {'id': 'AUTHORITY_SEPARATION', 'label': 'Configurazione e modello non concedono autorita'},
    {'id': 'LOCAL_MODEL_BOUNDARY', 'label': 'Il modello resta locale, sostituibile e senza tool'},
    {'id': 'EVIDENCE_BOUNDARY', 'label': 'La risposta di iKant non diventa prova esterna'},
    {'id': 'EXACT_EGRESS', 'label': 'Output e controlli restano vincolati all ACK esatto'},
    {'id': 'NO_PRIVATE_RATIONALE', 'label': 'Nessuna catena di pensiero privata viene esposta'},
)
_DERIVED_SOURCES = frozenset({'runtime_derived', 'inference', 'cache', 'demo'})
_SOURCE_BACKED = frozenset({'repository', 'document', 'live'})
_SETTINGS_LOCK = threading.RLock()

class FoundationConfigError(ValueError):
    pass

def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def _fingerprint(core: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(core)).hexdigest()

def _clean_meta(value: object) -> str:
    text = str(value or '').replace('\r\n', '\n').strip()
    if '\x00' in text:
        raise FoundationConfigError('meta prompt contains forbidden NUL')
    if len(text.encode('utf-8')) > MAX_META_PROMPT_BYTES:
        raise FoundationConfigError('meta prompt exceeds bound')
    return text

def _clean_limit(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not MIN_REPLY_WORDS <= value <= MAX_REPLY_WORDS:
        raise FoundationConfigError('reply word limit outside bound')
    return value

def _core(revision: int, meta_prompt: str, reply_word_limit: int) -> dict[str, Any]:
    return {'schema': FOUNDATION_SETTINGS_SCHEMA, 'revision': revision, 'meta_prompt': meta_prompt, 'reply_word_limit': reply_word_limit}

def _project(core: dict[str, Any]) -> dict[str, Any]:
    out = dict(core)
    out['sha256'] = _fingerprint(core)
    out['meta_prompt_scope'] = 'MODEL_GENERATION_ONLY'
    out['immutable_guardrails'] = [dict(x) for x in IMMUTABLE_GUARDRAILS]
    out['epistemic_authority'] = 0.0
    out['execution_authority'] = 0.0
    return out

def default_settings() -> dict[str, Any]:
    return _project(_core(0, '', DEFAULT_REPLY_WORDS))

def settings_path(root: str | Path) -> Path:
    return Path(root).resolve() / '.ikant' / 'foundation-settings.json'

def load_settings(root: str | Path) -> dict[str, Any]:
    path = settings_path(root)
    if not path.exists():
        return default_settings()
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise FoundationConfigError('foundation settings unreadable') from exc
    if not isinstance(value, dict) or set(value) != {'schema', 'revision', 'meta_prompt', 'reply_word_limit'} or value.get('schema') != FOUNDATION_SETTINGS_SCHEMA:
        raise FoundationConfigError('foundation settings schema drift')
    revision = value.get('revision')
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise FoundationConfigError('foundation settings revision invalid')
    return _project(_core(revision, _clean_meta(value.get('meta_prompt')), _clean_limit(value.get('reply_word_limit'))))

def update_settings(root: str | Path, payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {'schema', 'expected_revision', 'meta_prompt', 'reply_word_limit'}:
        raise FoundationConfigError('foundation settings update shape invalid')
    if payload.get('schema') != FOUNDATION_SETTINGS_SCHEMA:
        raise FoundationConfigError('foundation settings update schema mismatch')
    with _SETTINGS_LOCK:
        current = load_settings(root)
        expected = payload.get('expected_revision')
        if not isinstance(expected, int) or isinstance(expected, bool) or expected != current['revision']:
            raise FoundationConfigError('foundation settings revision conflict')
        core = _core(current['revision'] + 1, _clean_meta(payload.get('meta_prompt')), _clean_limit(payload.get('reply_word_limit')))
        path = settings_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json_write(path, core)
        return _project(core)

def generation_policy(root: str | Path) -> dict[str, Any]:
    settings = load_settings(root)
    return {'meta_prompt': settings['meta_prompt'], 'reply_word_limit': settings['reply_word_limit'], 'settings_revision': settings['revision'], 'settings_sha256': settings['sha256']}

class FoundationModelBroker:
    """Narrow generation-policy wrapper over the existing zero-authority local model."""
    def __init__(self, root: str | Path, base: Any):
        self.root = Path(root).resolve(); self.base = base
        self.model = str(getattr(base, 'model', 'local-model'))
        self.managed_runtime = bool(getattr(base, 'managed_runtime', False))
        self.runtime_binding_digest = getattr(base, 'runtime_binding_digest', None)
        self.last_completion_metrics: dict[str, Any] = {}
    @property
    def configured(self) -> bool:
        return bool(getattr(self.base, 'configured', True))
    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)
    def health(self) -> bool:
        return bool(self.base.health())
    def status(self) -> dict[str, Any]:
        out = dict(self.base.status()); settings = load_settings(self.root)
        out['foundation_settings_revision'] = settings['revision']; out['foundation_settings_sha256'] = settings['sha256']
        out['meta_prompt_scope'] = 'MODEL_GENERATION_ONLY'; out['configuration_is_authority'] = False
        out['epistemic_authority'] = 0.0; out['execution_authority'] = 0.0
        return out
    def complete_surface_a(self, contract: dict[str, Any], user_text: str, *, validator: Callable[[str], tuple[bool, list[str]]] | None = None, max_repairs: int = 1) -> str:
        if validator is None:
            from .surfaces import validate_surface_a
            validator = validate_surface_a
        policy = generation_policy(self.root); effective = deepcopy(dict(contract or {})); fmt = effective.setdefault('format', {})
        existing = fmt.get('max_words'); current_max = int(existing) if isinstance(existing, int) and not isinstance(existing, bool) and existing > 0 else MAX_REPLY_WORDS
        effective_max = min(current_max, int(policy['reply_word_limit'])); fmt['max_words'] = effective_max
        meta = str(policy['meta_prompt'] or '').strip()
        if meta:
            base_style = str(fmt.get('style') or 'simple natural colloquial humanistic-formal prose')
            fmt['style'] = base_style + '; optional user preference, subordinate to all immutable iKant constraints: ' + meta
        def bounded_validator(text: str) -> tuple[bool, list[str]]:
            ok, errors = validator(text); errors = list(errors)
            if len(str(text).split()) > effective_max: errors.append(f'reply exceeds configured {effective_max}-word limit')
            return bool(ok and not errors), errors
        try:
            result = self.base.complete_surface_a(effective, user_text, validator=bounded_validator, max_repairs=max_repairs)
        finally:
            metrics = dict(getattr(self.base, 'last_completion_metrics', {}) or {})
            metrics.update({'foundation_settings_revision': policy['settings_revision'], 'foundation_settings_sha256': policy['settings_sha256'], 'foundation_reply_word_limit': effective_max, 'meta_prompt_persisted_in_metrics': False, 'epistemic_authority': 0.0, 'execution_authority': 0.0})
            self.last_completion_metrics = metrics
        return result

def _runtime(root: Path) -> dict[str, Any]:
    try: value = json.loads((root / '.ikant' / 'runtime.json').read_text(encoding='utf-8'))
    except Exception: return {}
    return value if isinstance(value, dict) else {}

def _empty_evidence(base: dict[str, Any], state: str, label: str) -> dict[str, Any]:
    return {**base, 'state': state, 'label': label, 'source_backed': 0, 'user_supplied': 0, 'derived': 0, 'conflicts': 0, 'low_evidence': 0, 'closure': False, 'information_value': 'NONE'}

def evidence_summary(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve(); runtime = _runtime(root); session = str(runtime.get('session_id') or '')
    cognitive = runtime.get('cognitive') if isinstance(runtime.get('cognitive'), dict) else {}; cycle = str(cognitive.get('last_surface_a_cycle_id') or '')
    base = {'schema': FOUNDATION_EVIDENCE_SCHEMA, 'runtime_session_id': session or None, 'cycle_id': cycle or None, 'presentation_is_not_evidence': True, 'epistemic_authority': 0.0, 'execution_authority': 0.0}
    if runtime.get('status') != 'ACTIVE' or not session or not cycle: return _empty_evidence(base, 'NONE', 'Nessun ciclo disponibile')
    try: snapshot = load_json(root / '.ikant' / 'cognitive' / f'{cycle}.json')
    except Exception: return _empty_evidence(base, 'UNAVAILABLE', 'Evidenza non disponibile')
    if str(snapshot.get('session_id') or '') != session or str(snapshot.get('cycle_id') or '') != cycle: return _empty_evidence(base, 'MISMATCH', 'Riconciliazione non valida')
    objects = object_projection(snapshot); source_backed = user_supplied = derived = conflicts = low = 0
    for obj in objects:
        source = str(obj.get('source') or ''); evidence = obj.get('evidence')
        numeric = float(evidence) if isinstance(evidence, (int, float)) and not isinstance(evidence, bool) else None
        source_backed += int(source in _SOURCE_BACKED and numeric is not None and numeric > 0); user_supplied += int(source == 'user'); derived += int(source in _DERIVED_SOURCES)
        conflicts += int(str(obj.get('kind') or '') == 'conflict'); low += int(numeric is not None and numeric <= .25)
    reticulum = snapshot.get('reticulum') if isinstance(snapshot.get('reticulum'), dict) else {}; roa = reticulum.get('roa_alignment') if isinstance(reticulum.get('roa_alignment'), dict) else {}; closure = bool(roa.get('crc_basic'))
    if conflicts: label, information_value = 'Evidenza in conflitto', 'CONFLICTED'
    elif source_backed: label, information_value = ('Base informativa mista', 'MIXED') if derived or user_supplied else ('Fonti attribuibili presenti', 'SOURCE_BACKED')
    elif user_supplied: label, information_value = 'Basata soprattutto sul tuo input', 'USER_GROUNDED'
    else: label, information_value = 'Evidenza esterna limitata', 'LIMITED'
    return {**base, 'state': 'READY', 'label': label, 'information_value': information_value, 'source_backed': source_backed, 'user_supplied': user_supplied, 'derived': derived, 'conflicts': conflicts, 'low_evidence': low, 'closure': closure, 'object_count': len(objects)}
