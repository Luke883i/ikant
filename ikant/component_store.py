from __future__ import annotations
import hashlib,json,os,shutil,stat,tarfile,tempfile
from pathlib import Path,PurePosixPath
from typing import Any
class ComponentStoreError(RuntimeError):pass

def default_component_root(env:dict[str,str]|None=None)->Path:
 e=os.environ if env is None else env;override=str(e.get('IKANT_COMPONENT_HOME') or '').strip()
 if override:return Path(override).expanduser().resolve()
 xdg=str(e.get('XDG_DATA_HOME') or '').strip();base=Path(xdg).expanduser() if xdg else Path.home()/'.local'/'share';return (base/'ikant').resolve()
def sha256_file(path:str|Path,chunk_size:int=1024*1024)->str:
 h=hashlib.sha256()
 with Path(path).open('rb') as fh:
  while True:
   chunk=fh.read(chunk_size)
   if not chunk:break
   h.update(chunk)
 return h.hexdigest()
def verify_file(path:str|Path,expected_sha256:str)->bool:
 p=Path(path);return p.is_file() and not p.is_symlink() and sha256_file(p)==str(expected_sha256)
def fsync_dir(path:Path)->None:
 try:fd=os.open(path,os.O_RDONLY)
 except OSError:return
 try:os.fsync(fd)
 finally:os.close(fd)
def atomic_json(path:str|Path,payload:dict[str,Any],*,mode:int=0o600)->None:
 target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);fd,tmp_name=tempfile.mkstemp(prefix=target.name+'.',suffix='.tmp',dir=target.parent);tmp=Path(tmp_name)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'w',encoding='utf-8') as fh:json.dump(payload,fh,ensure_ascii=False,sort_keys=True,separators=(',',':'));fh.write('\n');fh.flush();os.fsync(fh.fileno())
  os.replace(tmp,target);fsync_dir(target.parent)
 finally:
  if tmp.exists():tmp.unlink()
def _safe_member_path(root:Path,name:str)->Path:
 if not name or '\x00' in name:raise ComponentStoreError('archive member path invalid')
 pure=PurePosixPath(name);parts=tuple(part for part in pure.parts if part not in {'','.'})
 if pure.is_absolute() or not parts or any(part=='..' for part in parts):raise ComponentStoreError('archive traversal rejected')
 out=root.joinpath(*parts).resolve()
 try:out.relative_to(root.resolve())
 except ValueError as exc:raise ComponentStoreError('archive escaped extraction root') from exc
 return out
def safe_extract_tar(archive:str|Path,destination:str|Path,*,max_total_bytes:int=512*1024*1024,max_members:int=4096)->Path:
 src=Path(archive);dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():raise ComponentStoreError('engine destination already exists')
 tmp=Path(tempfile.mkdtemp(prefix=dest.name+'.extract-',dir=dest.parent))
 try:
  with tarfile.open(src,'r:gz') as tf:
   members=tf.getmembers()
   if not members or len(members)>int(max_members):raise ComponentStoreError('engine archive member bound exceeded')
   if sum(int(m.size) for m in members if m.isfile())>int(max_total_bytes):raise ComponentStoreError('engine archive expansion bound exceeded')
   for member in members:
    target=_safe_member_path(tmp,member.name)
    if member.issym() or member.islnk() or member.isdev() or member.isfifo():raise ComponentStoreError('archive links/devices are forbidden')
    if member.isdir():target.mkdir(parents=True,exist_ok=True);continue
    if not member.isfile():raise ComponentStoreError('unsupported archive member')
    target.parent.mkdir(parents=True,exist_ok=True);source=tf.extractfile(member)
    if source is None:raise ComponentStoreError('archive member unreadable')
    with source,target.open('xb') as out:shutil.copyfileobj(source,out,length=1024*1024);out.flush();os.fsync(out.fileno())
    target.chmod(0o755 if (member.mode&stat.S_IXUSR) else 0o644)
  os.replace(tmp,dest);fsync_dir(dest.parent);return dest
 except Exception:shutil.rmtree(tmp,ignore_errors=True);raise
def tree_digest(root:str|Path,*,exclude:tuple[str,...]=('.ikant-install.json',))->str:
 base=Path(root).resolve();rows=[]
 for path in sorted(base.rglob('*'),key=lambda x:x.as_posix()):
  rel=path.relative_to(base).as_posix()
  if rel in exclude:continue
  st=path.lstat()
  if stat.S_ISLNK(st.st_mode):raise ComponentStoreError('installed engine contains symlink')
  if stat.S_ISDIR(st.st_mode):rows.append(('d',rel,stat.S_IMODE(st.st_mode),''))
  elif stat.S_ISREG(st.st_mode):rows.append(('f',rel,stat.S_IMODE(st.st_mode),sha256_file(path)))
  else:raise ComponentStoreError('installed engine contains unsupported node')
 return hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def find_unique_regular(root:str|Path,basename:str)->Path:
 candidates=[]
 for path in Path(root).rglob(basename):
  try:st=path.lstat()
  except OSError:continue
  if stat.S_ISREG(st.st_mode) and not path.is_symlink():candidates.append(path.resolve())
 if len(candidates)!=1:raise ComponentStoreError(f'expected exactly one regular {basename}, found {len(candidates)}')
 return candidates[0]
