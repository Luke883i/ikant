from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,os,secrets,stat
from typing import Any
from .native_actions import validate_native_action
from .native_snapshot import build_target_snapshot,canonical_native_path,stat_identity

class NativeDriverError(RuntimeError):pass
@dataclass
class PreparedNativeAction:
    action:dict[str,Any];snapshot:dict[str,Any]

class InMemoryNativeAdapter:
    adapter_id='native-memory-v0.22'
    capabilities=frozenset({'native.fs.read','native.fs.create'})
    def __init__(self,*,session_id='S',files=None):
        self.session_id=str(session_id);self.files=dict(files or {});self.generation=1;self.workspace_fingerprint='mem-'+hashlib.sha256(self.session_id.encode()).hexdigest()
        self.security_profile={'workspace_rooted':True,'strong_path_binding':True,'symlink_safe':True,'shell_disabled':True,'process_execution_disabled':True,'secret_access_disabled':True,'workspace_fingerprint':self.workspace_fingerprint}
    def snapshot(self,path,*,allow_missing_leaf=True):
        p=canonical_native_path(path);exists=p in self.files;parent={'dev':1,'ino':1,'mode':stat.S_IFDIR|0o700,'size':0,'mtime_ns':self.generation};leaf={'dev':1,'ino':100+abs(hash(p))%100000,'mode':stat.S_IFREG|0o600,'size':len(self.files[p].encode()),'mtime_ns':self.generation} if exists else None
        return build_target_snapshot(session_id=self.session_id,adapter_id=self.adapter_id,workspace_fingerprint=self.workspace_fingerprint,path=p,parent_identity=parent,leaf_identity=leaf,exists=exists)
    def preflight(self,action):
        s=self.snapshot(action['path']);ok,e=validate_native_action(action,s)
        if not ok:raise NativeDriverError('native preflight failed: '+'; '.join(e))
        return PreparedNativeAction(dict(action),s)
    def commit(self,prepared):
        now=self.snapshot(prepared.action['path'])
        if now['sha256']!=prepared.snapshot['sha256']:raise NativeDriverError('native target drift before commit')
        a=prepared.action
        if a['verb']=='READ_FILE':
            text=self.files[a['path']];return {'status':'EXECUTED','execution_ref':'nativemem-'+secrets.token_hex(8),'text':text,'content_sha256':__import__('hashlib').sha256(text.encode()).hexdigest(),'observed_predicates':[],'world_truth_verified':False,'epistemic_authority':0.0}
        if a['verb']=='CREATE_FILE':
            if a['path'] in self.files:raise NativeDriverError('S4 create requires absent target')
            self.files[a['path']]=a['text'];self.generation+=1;return {'status':'EXECUTED','execution_ref':'nativemem-'+secrets.token_hex(8),'bytes_written':len(a['text'].encode()),'content_sha256':a['content_sha256'],'observed_predicates':[],'world_truth_verified':False,'epistemic_authority':0.0}
        raise NativeDriverError('unsupported native verb')

class PosixWorkspaceAdapter:
    adapter_id='native-posix-workspace-v0.22'
    capabilities=frozenset({'native.fs.read','native.fs.create'})
    def __init__(self,*,session_id:str,workspace_root:str,max_read_bytes:int=128*1024):
        if os.name!='posix' or not hasattr(os,'O_NOFOLLOW') or os.open not in os.supports_dir_fd:raise NativeDriverError('S4 strong native path binding requires POSIX dir_fd + O_NOFOLLOW')
        self.session_id=str(session_id);self.workspace_root=os.path.abspath(str(workspace_root));self.max_read_bytes=int(max_read_bytes)
        if self.workspace_root==os.path.abspath(os.sep):raise NativeDriverError('filesystem root cannot be an S4 workspace root')
        rootfd=os.open(self.workspace_root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            st=os.fstat(rootfd)
            if not stat.S_ISDIR(st.st_mode):raise NativeDriverError('workspace root is not a directory')
            self._root_identity=stat_identity(st);self.workspace_fingerprint='ws-'+hashlib.sha256(json.dumps(self._root_identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        finally:os.close(rootfd)
        self.security_profile={'workspace_rooted':True,'strong_path_binding':True,'symlink_safe':True,'shell_disabled':True,'process_execution_disabled':True,'secret_access_disabled':True,'workspace_fingerprint':self.workspace_fingerprint}
    def _open_parent(self,path):
        p=canonical_native_path(path);parts=p.split('/');fd=os.open(self.workspace_root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            for seg in parts[:-1]:
                nxt=os.open(seg,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
            return fd,parts[-1]
        except Exception:
            os.close(fd);raise
    def snapshot(self,path,*,allow_missing_leaf=True):
        p=canonical_native_path(path);fd,name=self._open_parent(p)
        try:
            parent=stat_identity(os.fstat(fd));leaf=None;exists=False
            try:
                st=os.stat(name,dir_fd=fd,follow_symlinks=False);exists=True;leaf=stat_identity(st)
                if stat.S_ISLNK(st.st_mode):raise NativeDriverError('symlink target forbidden')
            except FileNotFoundError:
                if not allow_missing_leaf:raise NativeDriverError('native target missing')
            return build_target_snapshot(session_id=self.session_id,adapter_id=self.adapter_id,workspace_fingerprint=self.workspace_fingerprint,path=p,parent_identity=parent,leaf_identity=leaf,exists=exists)
        finally:os.close(fd)
    def preflight(self,action):
        s=self.snapshot(action['path']);ok,e=validate_native_action(action,s)
        if not ok:raise NativeDriverError('native preflight failed: '+'; '.join(e))
        return PreparedNativeAction(dict(action),s)
    @staticmethod
    def _same_identity(expected,st):
        got=stat_identity(st);return expected is not None and all(got[k]==expected[k] for k in ('dev','ino','mode','size','mtime_ns'))
    def commit(self,prepared):
        a=prepared.action;fd,name=self._open_parent(a['path'])
        try:
            if stat_identity(os.fstat(fd))!=prepared.snapshot['parent_identity']:raise NativeDriverError('native parent drift before commit')
            expected=prepared.snapshot['leaf_identity']
            if a['verb']=='READ_FILE':
                f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
                try:
                    st=os.fstat(f)
                    if not self._same_identity(expected,st) or not stat.S_ISREG(st.st_mode):raise NativeDriverError('native file identity drift before read')
                    chunks=[];total=0
                    while True:
                        chunk=os.read(f,min(65536,self.max_read_bytes+1-total))
                        if not chunk:break
                        chunks.append(chunk);total+=len(chunk)
                        if total>self.max_read_bytes:raise NativeDriverError('native read exceeds bounded S4 observation size')
                    data=b''.join(chunks)
                    if not self._same_identity(expected,os.fstat(f)):raise NativeDriverError('native file drift during read')
                    if len(data)!=int(expected.get('size',-1)):raise NativeDriverError('native read size drift')
                    try:text=data.decode('utf-8')
                    except UnicodeDecodeError as exc:raise NativeDriverError('S4 native read is UTF-8 text only') from exc
                    return {'status':'EXECUTED','execution_ref':'nativefs-'+secrets.token_hex(8),'text':text,'content_sha256':__import__('hashlib').sha256(data).hexdigest(),'observed_predicates':[],'world_truth_verified':False,'epistemic_authority':0.0}
                finally:os.close(f)
            if a['verb']=='CREATE_FILE':
                if expected is not None:raise NativeDriverError('S4 create requires an absent target')
                try:
                    os.stat(name,dir_fd=fd,follow_symlinks=False)
                    raise NativeDriverError('native create target unexpectedly exists')
                except FileNotFoundError:
                    pass
                tmp='.ikant-tmp-'+secrets.token_hex(16);created=False
                try:
                    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW
                    tf=os.open(tmp,flags,0o600,dir_fd=fd)
                    try:
                        data=a['text'].encode('utf-8');view=memoryview(data)
                        while view:
                            n=os.write(tf,view)
                            if n<=0:raise NativeDriverError('native create write made no progress')
                            view=view[n:]
                        os.fsync(tf)
                    finally:os.close(tf)
                    # link() is atomic and refuses to clobber a concurrently-created target.
                    os.link(tmp,name,src_dir_fd=fd,dst_dir_fd=fd,follow_symlinks=False);created=True
                    os.unlink(tmp,dir_fd=fd);os.fsync(fd)
                except FileExistsError as exc:
                    raise NativeDriverError('native create lost no-clobber race') from exc
                finally:
                    if not created:
                        try:os.unlink(tmp,dir_fd=fd)
                        except FileNotFoundError:pass
                        except Exception:pass
                return {'status':'EXECUTED','execution_ref':'nativefs-'+secrets.token_hex(8),'bytes_written':len(data),'content_sha256':a['content_sha256'],'observed_predicates':[],'world_truth_verified':False,'epistemic_authority':0.0}
            raise NativeDriverError('unsupported native verb')
        finally:os.close(fd)
