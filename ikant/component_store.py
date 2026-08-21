from __future__ import annotations
import hashlib,json,os,shutil,stat,tarfile,tempfile
from pathlib import Path,PurePosixPath
from typing import Any

class ComponentStoreError(RuntimeError):
    pass

class ArchiveTopologyError(ComponentStoreError):
    pass

MAX_LINK_DEPTH=32

def default_component_root(env:dict[str,str]|None=None)->Path:
    e=os.environ if env is None else env
    override=str(e.get('IKANT_COMPONENT_HOME') or '').strip()
    if override:return Path(override).expanduser().resolve()
    xdg=str(e.get('XDG_DATA_HOME') or '').strip()
    base=Path(xdg).expanduser() if xdg else Path.home()/'.local'/'share'
    return (base/'ikant').resolve()

def sha256_file(path:str|Path,chunk_size:int=1024*1024)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as fh:
        while True:
            chunk=fh.read(chunk_size)
            if not chunk:break
            h.update(chunk)
    return h.hexdigest()

def verify_file(path:str|Path,expected_sha256:str)->bool:
    p=Path(path)
    return p.is_file() and not p.is_symlink() and sha256_file(p)==str(expected_sha256)

def fsync_dir(path:Path)->None:
    try:fd=os.open(path,os.O_RDONLY)
    except OSError:return
    try:os.fsync(fd)
    finally:os.close(fd)

def atomic_json(path:str|Path,payload:dict[str,Any],*,mode:int=0o600)->None:
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp_name=tempfile.mkstemp(prefix=target.name+'.',suffix='.tmp',dir=target.parent);tmp=Path(tmp_name)
    try:
        os.fchmod(fd,mode)
        with os.fdopen(fd,'w',encoding='utf-8') as fh:
            json.dump(payload,fh,ensure_ascii=False,sort_keys=True,separators=(',',':'));fh.write('\n');fh.flush();os.fsync(fh.fileno())
        os.replace(tmp,target);fsync_dir(target.parent)
    finally:
        if tmp.exists():tmp.unlink()

def _member_name(name:str)->str:
    if not name or '\x00' in name:raise ArchiveTopologyError('archive member path invalid')
    pure=PurePosixPath(name)
    parts=tuple(part for part in pure.parts if part not in {'','.'})
    if pure.is_absolute() or not parts or any(part=='..' for part in parts):raise ArchiveTopologyError('archive traversal rejected')
    return PurePosixPath(*parts).as_posix()

def _relative_link_name(base:str,linkname:str)->str:
    if not linkname or '\x00' in linkname:raise ArchiveTopologyError('archive link target invalid')
    pure=PurePosixPath(linkname)
    if pure.is_absolute():raise ArchiveTopologyError('archive absolute link rejected')
    stack=[p for p in PurePosixPath(base).parts if p not in {'','.'}]
    for part in pure.parts:
        if part in {'','.'}:continue
        if part=='..':
            if not stack:raise ArchiveTopologyError('archive link escaped extraction root')
            stack.pop()
        else:stack.append(part)
    if not stack:raise ArchiveTopologyError('archive link target invalid')
    return PurePosixPath(*stack).as_posix()

def _safe_member_path(root:Path,name:str)->Path:
    rel=_member_name(name)
    out=root.joinpath(*PurePosixPath(rel).parts).resolve()
    try:out.relative_to(root.resolve())
    except ValueError as exc:raise ArchiveTopologyError('archive escaped extraction root') from exc
    return out

def _link_target(member:tarfile.TarInfo)->str:
    name=_member_name(member.name)
    if member.issym():
        parent=PurePosixPath(name).parent.as_posix()
        return _relative_link_name('' if parent=='.' else parent,member.linkname)
    if member.islnk():return _relative_link_name('',member.linkname)
    raise ArchiveTopologyError('archive member is not a link')

def _resolve_regular(member:tarfile.TarInfo,by_name:dict[str,tarfile.TarInfo],*,max_link_depth:int=MAX_LINK_DEPTH)->tarfile.TarInfo:
    current=member;seen=set()
    for _ in range(max_link_depth+1):
        name=_member_name(current.name)
        if name in seen:raise ArchiveTopologyError('archive link cycle rejected')
        seen.add(name)
        if current.isfile():return current
        if not (current.issym() or current.islnk()):raise ArchiveTopologyError('archive link target is not a regular file')
        target_name=_link_target(current)
        current=by_name.get(target_name)
        if current is None:raise ArchiveTopologyError('archive link target missing')
    raise ArchiveTopologyError('archive link depth exceeded')

def _root_dir_member(member:tarfile.TarInfo)->bool:
    pure=PurePosixPath(member.name)
    return member.isdir() and all(part in {'','.'} for part in pure.parts)

def _preflight_members(members:list[tarfile.TarInfo],*,max_total_bytes:int,max_members:int)->tuple[dict[str,tarfile.TarInfo],int]:
    if not members or len(members)>int(max_members):raise ComponentStoreError('engine archive member bound exceeded')
    by_name={}
    for member in members:
        if _root_dir_member(member):continue
        name=_member_name(member.name)
        if name in by_name:raise ArchiveTopologyError('archive duplicate member rejected')
        if member.isdev() or member.isfifo():raise ArchiveTopologyError('archive devices/fifos are forbidden')
        if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):raise ArchiveTopologyError('unsupported archive member')
        by_name[name]=member
    for name in by_name:
        parts=PurePosixPath(name).parts
        for i in range(1,len(parts)):
            parent=by_name.get(PurePosixPath(*parts[:i]).as_posix())
            if parent is not None and not parent.isdir():raise ArchiveTopologyError('archive member parent is not a directory')
    expanded=0
    for member in members:
        if _root_dir_member(member):continue
        if member.isfile():expanded+=int(member.size)
        elif member.issym() or member.islnk():expanded+=int(_resolve_regular(member,by_name).size)
        if expanded>int(max_total_bytes):raise ComponentStoreError('engine archive expansion bound exceeded')
    return by_name,expanded

def safe_extract_tar(archive:str|Path,destination:str|Path,*,max_total_bytes:int=512*1024*1024,max_members:int=4096)->Path:
    src=Path(archive);dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():raise ComponentStoreError('engine destination already exists')
    tmp=Path(tempfile.mkdtemp(prefix=dest.name+'.extract-',dir=dest.parent))
    try:
        with tarfile.open(src,'r:gz') as tf:
            members=tf.getmembers();by_name,_=_preflight_members(members,max_total_bytes=max_total_bytes,max_members=max_members)
            for member in members:
                if _root_dir_member(member):continue
                if member.isdir():_safe_member_path(tmp,member.name).mkdir(parents=True,exist_ok=True)
            for member in members:
                if _root_dir_member(member) or member.isdir():continue
                target=_safe_member_path(tmp,member.name);target.parent.mkdir(parents=True,exist_ok=True)
                source_member=_resolve_regular(member,by_name) if member.issym() or member.islnk() else member
                source=tf.extractfile(source_member)
                if source is None:raise ComponentStoreError('archive member unreadable')
                with source,target.open('xb') as out:
                    shutil.copyfileobj(source,out,length=1024*1024);out.flush();os.fsync(out.fileno())
                target.chmod(0o755 if (source_member.mode&stat.S_IXUSR) else 0o644)
        os.replace(tmp,dest);fsync_dir(dest.parent);return dest
    except Exception:
        shutil.rmtree(tmp,ignore_errors=True);raise

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
