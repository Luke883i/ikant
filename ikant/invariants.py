from __future__ import annotations
from dataclasses import asdict
from typing import Any
from .invariants_legacy_s15 import *
from . import invariants_legacy_s15 as _legacy

_S16_INVARIANTS=(
 Invariant('SFC-001','surface_contract_s16','Authenticated runtime semantic reads converge through one versioned canonical Surface Contract. Stable reads use bounded optimistic consistency checks; an active synchronous TURN is represented by a nonblocking work overlay and may never be delayed by a presentation snapshot lock.',"CRITICAL",'tests.test_surface_contract_s16'),
 Invariant('SFC-002','surface_contract_s16','The runtime surface manifest is the all-and-only declaration of currently user-readable or user-governable abstractions. Webapp and floating PWA profiles share the same semantic contract digest; layout cannot widen authority or imply native OS-overlay capability.',"CRITICAL",'tests.test_surface_contract_s16'),
 Invariant('SFC-003','surface_contract_s16','Generation configuration effect is session-, cycle-, revision- and route-bound. Saving configuration is not evidence that it affected the visible answer; MODEL, fallback and local non-model routes are distinguished and every receipt remains zero-authority.',"CRITICAL",'tests.test_surface_contract_s16'),
 Invariant('SFC-004','surface_contract_s16','Legacy experience/foundation/public/work semantic reads remain compatibility projections of the canonical Surface Contract, while mutation routes, S8 single-writer/exact-ACK semantics and S15bis browser liveness remain authoritative and unchanged; the S16 asset boundary invalidates stale pre-contract bundles.',"CRITICAL",'tests.test_surface_contract_s16'),
)
_INVARIANTS=_legacy.invariants()+_S16_INVARIANTS

def invariants()->tuple[Invariant,...]:return _INVARIANTS
def critical_ids()->tuple[str,...]:return tuple(x.id for x in _INVARIANTS if x.severity=="CRITICAL")
def registry_manifest()->dict[str,Any]:
 out=_legacy.registry_manifest();out['invariants']=[asdict(x) for x in _INVARIANTS];return out
