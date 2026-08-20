from __future__ import annotations
from pathlib import Path
from .agency_host import AgencyHostBinding
from .agency_kernel import AgencyKernel
from .host_sdk import HostRuntimeBinding
from .native_agency import NativeAgency
from .native_driver import PosixWorkspaceAdapter
from .native_host import NativeExecutionHostAdapter

def build_native_agency_runtime(*,state_dir:str|Path,session_id:str,actor_binding,interaction_secret:bytes,workspace_root:str|Path,active:bool,persist_host_certification:bool=True)->NativeAgency:
    if active is not True:raise PermissionError('S4 native runtime requires ACTIVE admission before touching workspace')
    state=Path(state_dir);agency=AgencyKernel(state,session_id=str(session_id),binding=actor_binding,interaction_secret=interaction_secret);driver=PosixWorkspaceAdapter(session_id=str(session_id),workspace_root=str(workspace_root));adapter=NativeExecutionHostAdapter(driver_kind=type(driver).__name__,security_profile=driver.security_profile);host=HostRuntimeBinding(adapter,persist_path=(state/'native-host-conformance.json') if persist_host_certification else None);return NativeAgency(driver=driver,agency_kernel=agency,agency_host_binding=AgencyHostBinding(host,agency))
