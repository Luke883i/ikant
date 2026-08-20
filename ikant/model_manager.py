from __future__ import annotations
import json,os,shutil
from pathlib import Path
from typing import Any,Callable
from .component_manifest import manifest_digest,select_engine_artifact
from .component_store import atomic_json,default_component_root,find_unique_regular,safe_extract_tar,tree_digest,verify_file
from .download_manager import download_verified
MODEL_BINDING_SCHEMA='ikant-managed-model-binding/v0.23-test'
class ModelManagerError(RuntimeError):pass
class ModelManager:
 def __init__(self,manifest:dict[str,Any],*,component_root:str|Path|None=None,platform:str|None=None,downloader:Callable[...,Path]=download_verified):self.manifest=manifest;self.manifest_sha256=manifest_digest(manifest);self.root=Path(component_root).resolve() if component_root else default_component_root();self.platform,self.engine_artifact=select_engine_artifact(manifest,key=platform);self.downloader=downloader
 @property
 def engine_version(self)->str:return str(self.manifest['engine']['release_tag'])
 @property
 def model(self)->dict[str,Any]:return dict(self.manifest['model'])
 def _download(self,url,target,sha256,max_bytes,progress=None):return self.downloader(url,target,sha256,progress=progress,max_bytes=max_bytes)
 def ensure_model(self,*,progress=None)->Path:
  spec=self.model;target=self.root/'models'/str(spec['id'])/str(spec['file'])
  if verify_file(target,str(spec['sha256'])):return target
  if target.exists():target.unlink()
  return self._download(str(spec['url']),target,str(spec['sha256']),int(spec['max_size_bytes']),progress=progress)
 def _valid_install(self,install:Path,marker:Path,spec:dict[str,Any])->Path|None:
  try:
   meta=json.loads(marker.read_text(encoding='utf-8'))
   if meta.get('artifact_sha256')!=spec['sha256'] or meta.get('tree_sha256')!=tree_digest(install):return None
   server=find_unique_regular(install,str(spec['server_basename']));return server if os.access(server,os.X_OK) else None
  except Exception:return None
 def ensure_engine(self,*,progress=None)->Path:
  spec=self.engine_artifact;install=self.root/'engines'/self.engine_version/self.platform;marker=install/'.ikant-install.json'
  if install.is_dir() and marker.is_file():
   server=self._valid_install(install,marker,spec)
   if server:return server
   shutil.rmtree(install,ignore_errors=True)
  archive_name=Path(str(spec['url']).split('?',1)[0]).name;archive=self.root/'downloads'/archive_name;self._download(str(spec['url']),archive,str(spec['sha256']),int(spec['max_size_bytes']),progress=progress)
  if install.exists():shutil.rmtree(install)
  safe_extract_tar(archive,install);server=find_unique_regular(install,str(spec['server_basename']));server.chmod(server.stat().st_mode|0o100);digest=tree_digest(install);atomic_json(marker,{'artifact_sha256':spec['sha256'],'tree_sha256':digest})
  if self._valid_install(install,marker,spec) is None:shutil.rmtree(install,ignore_errors=True);raise ModelManagerError('engine install verification failed')
  return server
 def ensure(self,*,progress=None)->dict[str,Any]:
  engine_path=self.ensure_engine(progress=progress);model_path=self.ensure_model(progress=progress);return {'schema':MODEL_BINDING_SCHEMA,'manifest_sha256':self.manifest_sha256,'engine':{'id':self.manifest['engine']['id'],'version':self.engine_version,'platform':self.platform,'artifact_sha256':self.engine_artifact['sha256'],'path':str(engine_path)},'model':{'id':self.model['id'],'revision':self.model['revision'],'sha256':self.model['sha256'],'path':str(model_path)},'model_output_is_authority':False,'epistemic_authority':0.0,'execution_authority':0.0}
