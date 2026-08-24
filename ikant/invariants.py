from __future__ import annotations
from dataclasses import asdict
from typing import Any
from .invariants_legacy_s15 import *
from . import invariants_legacy_s15 as _legacy
from .invariants_runtime_v030 import S15BIS_INVARIANTS,S16_INVARIANTS,S16BIS_INVARIANTS,S17_INVARIANTS,S17BIS_INVARIANTS,S18_INVARIANTS

_INVARIANTS=_legacy.invariants()+S15BIS_INVARIANTS+S16_INVARIANTS+S16BIS_INVARIANTS+S17_INVARIANTS+S17BIS_INVARIANTS+S18_INVARIANTS

def invariants()->tuple[Invariant,...]:return _INVARIANTS
def critical_ids()->tuple[str,...]:return tuple(x.id for x in _INVARIANTS if x.severity=="CRITICAL")
def registry_manifest()->dict[str,Any]:
 out=_legacy.registry_manifest();out['invariants']=[asdict(x) for x in _INVARIANTS];return out
