from __future__ import annotations

import hashlib
import json
import platform
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

MODEL_RUNTIME_SCHEMA = "ikant-model-runtime/v0.23-test"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")

class ComponentManifestError(ValueError):pass

def _canonical(data:dict[str,Any])->bytes:return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def manifest_digest(data:dict[str,Any])->str:return hashlib.sha256(_canonical(data)).hexdigest()

def platform_key(system:str|None=None,machine:str|None=None)->str:
    sysname=(system or platform.system()).strip().lower();arch=(machine or platform.machine()).strip().lower();sysname={"macos":"darwin"}.get(sysname,sysname);arch={"amd64":"x86_64","x64":"x86_64","arm64":"aarch64"}.get(arch,arch)
    if sysname=="darwin" and arch=="aarch64":arch="arm64"
    if sysname not in {"darwin","linux"} or arch not in {"arm64","aarch64","x86_64"}:raise ComponentManifestError(f"unsupported managed-runtime platform: {sysname}-{arch}")
    return f"{sysname}-{arch}"

def _https_exact(url:Any,*,forbidden:tuple[str,...]=())->bool:
    if not isinstance(url,str):return False
    parsed=urlparse(url);low=url.casefold();return parsed.scheme=="https" and bool(parsed.netloc) and all(token not in low for token in forbidden)

def validate_manifest(data:dict[str,Any])->list[str]:
    errors:list[str]=[]
    if not isinstance(data,dict):return ["manifest must be an object"]
    if data.get("schema")!=MODEL_RUNTIME_SCHEMA:errors.append("model runtime schema mismatch")
    if data.get("product_version")!="0.23.0a1":errors.append("model runtime product version mismatch")
    engine=data.get("engine") if isinstance(data.get("engine"),dict) else {}
    if engine.get("id")!="llama.cpp":errors.append("engine id mismatch")
    tag=engine.get("release_tag")
    if not isinstance(tag,str) or not re.fullmatch(r"b[0-9]+",tag):errors.append("engine release tag must be immutable b<number>")
    artifacts=engine.get("artifacts") if isinstance(engine.get("artifacts"),dict) else {}
    if not artifacts:errors.append("engine artifacts missing")
    for key,artifact in artifacts.items():
        if not isinstance(artifact,dict):errors.append(f"engine artifact {key} invalid");continue
        url=artifact.get("url")
        if not _https_exact(url,forbidden=("/latest/","/latest","releases/latest")):errors.append(f"engine artifact {key} URL must be pinned HTTPS")
        elif tag and f"/download/{tag}/" not in url:errors.append(f"engine artifact {key} does not bind release tag")
        if not _SHA256_RE.fullmatch(str(artifact.get("sha256",""))):errors.append(f"engine artifact {key} sha256 invalid")
        if artifact.get("archive")!="tar.gz":errors.append(f"engine artifact {key} archive unsupported")
        if not isinstance(artifact.get("max_size_bytes"),int) or int(artifact.get("max_size_bytes",0))<=0:errors.append(f"engine artifact {key} size bound missing")
        if artifact.get("server_basename")!="llama-server":errors.append(f"engine artifact {key} server basename mismatch")
    contract=engine.get("server_contract") if isinstance(engine.get("server_contract"),dict) else {};expected={"host":"127.0.0.1","ephemeral_port":True,"api_key_file":True,"webui_enabled":False,"agent_mode_enabled":False,"builtin_tools_enabled":False,"browser_model_transport":False}
    for key,value in expected.items():
        if contract.get(key)!=value:errors.append(f"engine server contract {key} mismatch")
    model=data.get("model") if isinstance(data.get("model"),dict) else {};revision=str(model.get("revision",""))
    if not _REVISION_RE.fullmatch(revision):errors.append("model revision must be a full immutable commit")
    model_url=model.get("url")
    if not _https_exact(model_url,forbidden=("/resolve/main/","/latest/")):errors.append("model URL must be pinned HTTPS")
    elif revision and f"/resolve/{revision}/" not in model_url:errors.append("model URL does not bind revision")
    if not _SHA256_RE.fullmatch(str(model.get("sha256",""))):errors.append("model sha256 invalid")
    if not str(model.get("file","")).endswith(".gguf"):errors.append("model file must be GGUF")
    if not isinstance(model.get("display_size_mb"),int) or int(model.get("display_size_mb",0))<=0:errors.append("model display size missing")
    if not isinstance(model.get("max_size_bytes"),int) or int(model.get("max_size_bytes",0))<=0:errors.append("model size bound missing")
    authority=data.get("authority") if isinstance(data.get("authority"),dict) else {}
    if authority.get("model_output_is_authority") is not False or authority.get("component_presence_is_authority") is not False or authority.get("runtime_readiness_is_authority") is not False:errors.append("managed runtime may not create authority")
    if authority.get("epistemic_authority")!=0.0 or authority.get("execution_authority")!=0.0:errors.append("managed runtime authority must remain zero")
    return errors

def load_manifest(path:str|Path)->dict[str,Any]:
    p=Path(path)
    try:data=json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:raise ComponentManifestError("model runtime manifest unreadable") from exc
    errors=validate_manifest(data)
    if errors:raise ComponentManifestError("; ".join(errors))
    return data

def select_engine_artifact(data:dict[str,Any],*,key:str|None=None)->tuple[str,dict[str,Any]]:
    chosen=key or platform_key();artifact=((data.get("engine") or {}).get("artifacts") or {}).get(chosen)
    if not isinstance(artifact,dict):raise ComponentManifestError(f"no pinned llama.cpp artifact for {chosen}")
    return chosen,dict(artifact)
