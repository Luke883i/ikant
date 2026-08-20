from __future__ import annotations

from pathlib import Path

from .agency_host import AgencyHostBinding
from .agency_kernel import AgencyKernel
from .host_sdk import HostRuntimeBinding
from .web_agency import WebAgency
from .web_host import WebExecutionHostAdapter


def build_web_agency_runtime(*, state_dir: str | Path, session_id: str, actor_binding, interaction_secret: bytes, browser, persist_host_certification: bool = True) -> WebAgency:
    state = Path(state_dir)
    agency = AgencyKernel(state, session_id=str(session_id), binding=actor_binding, interaction_secret=interaction_secret)
    host_adapter = WebExecutionHostAdapter(browser_engine=type(browser).__name__, isolated_context=True)
    host = HostRuntimeBinding(host_adapter, persist_path=(state / 'web-host-conformance.json') if persist_host_certification else None)
    bridge = AgencyHostBinding(host, agency)
    return WebAgency(browser=browser, agency_kernel=agency, agency_host_binding=bridge)
