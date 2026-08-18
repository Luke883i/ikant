from __future__ import annotations
import hashlib
from pathlib import Path

CRITICAL_PATTERNS=(
    'ikant/*.py',
    'scripts/stress.py','scripts/dynamic_stress.py','scripts/crc_stress.py','scripts/cognitive_stress.py','scripts/surface_a_stress.py','scripts/tune_dynamics.py',
    'tests/*.py',
)

def source_fingerprint(root: str | Path | None = None) -> str:
    root=Path(root) if root else Path(__file__).resolve().parents[1]
    files=[]
    for pattern in CRITICAL_PATTERNS:
        files.extend(root.glob(pattern))
    h=hashlib.sha256()
    for p in sorted({x.resolve() for x in files if x.is_file()}, key=lambda x:str(x.relative_to(root.resolve()))):
        rel=str(p.relative_to(root.resolve())).replace('\\','/')
        h.update(rel.encode());h.update(b'\0');h.update(p.read_bytes());h.update(b'\0')
    return h.hexdigest()
