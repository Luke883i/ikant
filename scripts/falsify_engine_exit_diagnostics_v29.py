from dataclasses import dataclass
from hashlib import sha256
import json, random, re

MAX_TAIL = 4096
MAX_CAUSE = 6
MAX_EVENT = 16 * 1024
SECRET_PATTERNS = [
    re.compile(r'(?i)(token|password|secret|api[_-]?key)\s*[=:]\s*[^\s]+'),
    re.compile(r'(?i)bearer\s+[A-Za-z0-9._~-]+'),
]

def redact(text: str) -> str:
    out = text
    for p in SECRET_PATTERNS:
        out = p.sub('[REDACTED]', out)
    return out

def bounded_tail(raw: bytes) -> str:
    tail = raw[-MAX_TAIL:]
    text = tail.decode('utf-8', errors='replace')
    text = redact(text)
    encoded = text.encode('utf-8', errors='replace')
    if len(encoded) > MAX_TAIL:
        encoded = encoded[-MAX_TAIL:]
        text = encoded.decode('utf-8', errors='ignore')
    return text

@dataclass(frozen=True)
class EngineExitDiagnostic:
    kind: str
    returncode: int | None
    signal: int | None
    stderr_tail: str

    @classmethod
    def capture(cls, returncode: int | None, stderr: bytes):
        if returncode is None:
            kind, sig = 'UNKNOWN', None
        elif returncode < 0:
            kind, sig = 'SIGNAL', -returncode
        else:
            kind, sig = 'EXIT_STATUS', None
        return cls(kind, returncode, sig, bounded_tail(stderr))

    def as_dict(self):
        return {
            'kind': self.kind,
            'returncode': self.returncode,
            'signal': self.signal,
            'stderr_tail': self.stderr_tail,
        }

def event(diag: EngineExitDiagnostic, causes=1):
    chain = [{'type':'EngineSupervisorError','message':'llama-server exited before readiness','process_exit':diag.as_dict()}]
    chain.extend({'type':'WrapperError','message':f'wrapper-{i}'} for i in range(max(0, causes-1)))
    chain = chain[:MAX_CAUSE]
    e = {
        'schema':'ikant-bootstrap-event/v0.29-test',
        'seq':1,
        'step':'ENGINE_READINESS',
        'outcome':'FAIL',
        'code':'ENGINE_EXITED_EARLY',
        'detail':'llama-server exited before readiness',
        'epistemic_authority':0.0,
        'execution_authority':0.0,
        'cause_chain':chain,
    }
    blob = json.dumps(e, sort_keys=True, separators=(',',':')).encode()
    assert len(blob) <= MAX_EVENT
    return e, sha256(blob).hexdigest()

def assert_invariants(e):
    assert e['epistemic_authority'] == 0.0
    assert e['execution_authority'] == 0.0
    assert len(e['cause_chain']) <= MAX_CAUSE
    d = e['cause_chain'][0]['process_exit']
    assert d['kind'] in {'UNKNOWN','SIGNAL','EXIT_STATUS'}
    if d['kind'] == 'SIGNAL':
        assert d['returncode'] is not None and d['returncode'] < 0
        assert d['signal'] == -d['returncode'] and d['signal'] > 0
    elif d['kind'] == 'EXIT_STATUS':
        assert d['returncode'] is not None and d['returncode'] >= 0 and d['signal'] is None
    else:
        assert d['returncode'] is None and d['signal'] is None
    assert len(d['stderr_tail'].encode('utf-8', errors='replace')) <= MAX_TAIL
    low = d['stderr_tail'].lower()
    for needle in ('password=', 'password:', 'token=', 'token:', 'secret=', 'secret:', 'api_key=', 'api-key=', 'bearer abc'):
        assert needle not in low


def random_stderr(rng: random.Random) -> bytes:
    parts = []
    alphabet = 'abcdefXYZ0123456789 /:_-.\n'
    for _ in range(rng.randint(0, 20)):
        if rng.random() < 0.18:
            key = rng.choice(['token','password','secret','api_key'])
            parts.append(f'{key}={rng.randrange(10**12):012d}')
        elif rng.random() < 0.05:
            parts.append('Bearer abc.DEF_123')
        else:
            parts.append(''.join(rng.choice(alphabet) for _ in range(rng.randint(0, 800))))
    raw = ('|'.join(parts)).encode('utf-8')
    if rng.random() < 0.1:
        raw += bytes([0xff,0xfe,0x80]) * rng.randint(1, 30)
    return raw


def run_matrix(n=10000, seed=20260822):
    rng = random.Random(seed)
    signatures = set()
    for i in range(n):
        mode = i % 3
        rc = None if mode == 0 else (rng.randint(0,255) if mode == 1 else -rng.randint(1,64))
        d = EngineExitDiagnostic.capture(rc, random_stderr(rng))
        e, h = event(d, causes=rng.randint(1,10))
        assert_invariants(e)
        signatures.add((d.kind, d.signal is not None, bool(d.stderr_tail), len(e['cause_chain']), h[:2]))

    mutation_survivors = 0
    for _ in range(n):
        rc = rng.choice([None, 0, 1, 2, 126, 127, 137, 255, -1, -6, -9, -11, -15, -64])
        raw = random_stderr(rng) + (b'X' * rng.randint(0, 12000))
        d = EngineExitDiagnostic.capture(rc, raw)
        e, _ = event(d, causes=rng.randint(1,20))
        try:
            assert_invariants(e)
        except AssertionError:
            mutation_survivors += 1

    kills = 0
    kill_survivors = 0
    for i in range(n):
        d = EngineExitDiagnostic.capture(rng.choice([0,1,-9,None]), random_stderr(rng))
        e, _ = event(d)
        variant = i % 10
        x = json.loads(json.dumps(e))
        pd = x['cause_chain'][0]['process_exit']
        if variant == 0: x['epistemic_authority'] = 1.0
        elif variant == 1: x['execution_authority'] = 1.0
        elif variant == 2: pd['kind'] = 'OOM_GUESS'
        elif variant == 3: pd['signal'] = 9; pd['returncode'] = 0; pd['kind'] = 'EXIT_STATUS'
        elif variant == 4: pd['returncode'] = -9; pd['signal'] = None; pd['kind'] = 'SIGNAL'
        elif variant == 5: pd['stderr_tail'] = 'token=abc123'
        elif variant == 6: pd['stderr_tail'] = 'Y' * (MAX_TAIL + 1)
        elif variant == 7: x['cause_chain'] = x['cause_chain'] * 7
        elif variant == 8: pd['kind'] = 'UNKNOWN'; pd['returncode'] = 7
        elif variant == 9: pd['kind'] = 'EXIT_STATUS'; pd['returncode'] = None
        try:
            assert_invariants(x)
        except AssertionError:
            kills += 1
        else:
            kill_survivors += 1

    tail_new = 0
    before = {(k[0],k[1],k[2],k[3]) for k in signatures}
    for _ in range(1000):
        rc = rng.choice([None,0,1,126,127,255,-1,-6,-9,-11,-15,-64])
        d = EngineExitDiagnostic.capture(rc, random_stderr(rng))
        e,_ = event(d, causes=rng.randint(1,10))
        assert_invariants(e)
        sig = (d.kind,d.signal is not None,bool(d.stderr_tail),len(e['cause_chain']))
        if sig not in before:
            tail_new += 1; before.add(sig)
    return {
        'simulations': n,
        'mutations': n,
        'mutation_survivors': mutation_survivors,
        'kills': n,
        'killed': kills,
        'kill_survivors': kill_survivors,
        'no_novelty_tail': 1000,
        'tail_novelty': tail_new,
        'semantic_signatures': len(signatures),
    }

if __name__ == '__main__':
    print(json.dumps(run_matrix(), sort_keys=True, indent=2))
