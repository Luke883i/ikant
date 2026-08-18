from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from typing import Any

def atomic_json_write(path:Path,payload:dict[str,Any]):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as h:
            json.dump(payload,h,ensure_ascii=False,sort_keys=True,indent=2); h.write('\n'); h.flush(); os.fsync(h.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def read_json(path:Path,default=None):
    if not path.exists(): return {} if default is None else default
    return json.loads(path.read_text(encoding='utf-8'))
def append_jsonl(path:Path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as h: h.write(json.dumps(payload,ensure_ascii=False,sort_keys=True)+'\n'); h.flush(); os.fsync(h.fileno())
class WriterLock:
    def __init__(self,path): self.path=Path(path); self.handle=None
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); h=self.path.open('a+',encoding='utf-8')
        try:
            try:
                import fcntl; fcntl.flock(h.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB); self.backend='fcntl'
            except ImportError: # pragma: no cover
                import msvcrt; h.seek(0); h.write('0') if h.read(1)=='' else None; h.seek(0); msvcrt.locking(h.fileno(),msvcrt.LK_NBLCK,1); self.backend='msvcrt'
        except (BlockingIOError,OSError): h.close(); raise RuntimeError('iKant state is already locked by another writer')
        self.handle=h; h.seek(0); h.truncate(); h.write(str(os.getpid())); h.flush(); return self
    def release(self):
        if not self.handle:return
        h=self.handle
        try:
            if self.backend=='fcntl': import fcntl; fcntl.flock(h.fileno(),fcntl.LOCK_UN)
            else: # pragma: no cover
                import msvcrt; h.seek(0); msvcrt.locking(h.fileno(),msvcrt.LK_UNLCK,1)
        finally:h.close(); self.handle=None
def acquire_writer_lock(path):return WriterLock(path).acquire()
