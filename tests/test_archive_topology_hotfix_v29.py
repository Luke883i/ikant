from __future__ import annotations
import io,tarfile,tempfile,unittest
from pathlib import Path
from ikant.bootstrap_observability import classify_failure
from ikant.component_store import ArchiveTopologyError,ComponentStoreError,safe_extract_tar,tree_digest

class ArchiveTopologyHotfixV29Tests(unittest.TestCase):
 def _archive(self,path,entries):
  with tarfile.open(path,'w:gz') as tf:
   for kind,name,payload in entries:
    info=tarfile.TarInfo(name);info.mode=0o755 if name.endswith('llama-server') else 0o644
    if kind=='file':
     raw=payload if isinstance(payload,bytes) else str(payload).encode();info.size=len(raw);tf.addfile(info,io.BytesIO(raw))
    elif kind=='dir':info.type=tarfile.DIRTYPE;tf.addfile(info)
    elif kind=='symlink':info.type=tarfile.SYMTYPE;info.linkname=str(payload);tf.addfile(info)
    elif kind=='hardlink':info.type=tarfile.LNKTYPE;info.linkname=str(payload);tf.addfile(info)
    elif kind=='fifo':info.type=tarfile.FIFOTYPE;tf.addfile(info)
 def _extract(self,entries,**kwargs):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);archive=Path(td.name)/'engine.tar.gz';self._archive(archive,entries);dest=Path(td.name)/'engine';safe_extract_tar(archive,dest,**kwargs);return dest
 def test_openvino_shape_internal_links_materialize_as_regular_files(self):
  dest=self._extract([('dir','bin',''),('dir','lib',''),('file','bin/llama-server',b'ENGINE'),('file','lib/libopenvino.so.2600',b'OV'),('symlink','lib/libopenvino.so','libopenvino.so.2600'),('file','lib/libtbb.so.12',b'TBB'),('symlink','bin/libtbb.so','../lib/libtbb.so.12')]);self.assertFalse((dest/'lib/libopenvino.so').is_symlink());self.assertFalse((dest/'bin/libtbb.so').is_symlink());self.assertEqual((dest/'lib/libopenvino.so').read_bytes(),b'OV');self.assertEqual((dest/'bin/libtbb.so').read_bytes(),b'TBB');tree_digest(dest)
 def test_internal_hardlink_and_link_chain_materialize(self):
  dest=self._extract([('file','real',b'X'),('hardlink','hard','real'),('symlink','alias1','real'),('symlink','alias2','alias1')]);self.assertEqual((dest/'hard').read_bytes(),b'X');self.assertEqual((dest/'alias2').read_bytes(),b'X');self.assertFalse(any(p.is_symlink() for p in dest.rglob('*')))
 def test_traversal_absolute_escape_missing_cycle_and_nonregular_fail_closed(self):
  cases=[[('file','../escape',b'x')],[('file','real',b'x'),('symlink','alias','/tmp/escape')],[('file','real',b'x'),('symlink','d/alias','../../real')],[('symlink','alias','missing')],[('symlink','a','b'),('symlink','b','a')],[('dir','d',''),('symlink','alias','d')],[('fifo','pipe','')],[('file','dup',b'a'),('file','dup',b'b')],[('file','parent',b'a'),('file','parent/child',b'b')]]
  for entries in cases:
   with self.subTest(entries=entries),self.assertRaises(ComponentStoreError):self._extract(entries)
 def test_materialized_alias_bytes_are_in_expansion_bound(self):
  entries=[('file','real',b'12345'),('symlink','a','real'),('symlink','b','real')]
  with self.assertRaises(ComponentStoreError):self._extract(entries,max_total_bytes=14)
  self.assertEqual((self._extract(entries,max_total_bytes=15)/'b').read_bytes(),b'12345')
 def test_unsafe_topology_has_manual_nonretry_remediation(self):
  try:raise ArchiveTopologyError('archive link escaped extraction root')
  except ArchiveTopologyError as cause:
   try:raise RuntimeError('managed local runtime failed closed') from cause
   except RuntimeError as exc:code,remediation=classify_failure('ENGINE_COMPONENT',exc)
  self.assertEqual(code,'ENGINE_ARCHIVE_UNSAFE_TOPOLOGY');self.assertEqual(remediation['id'],'VERIFY_ENGINE_ARTIFACT');self.assertEqual(remediation['action'],'manual')

if __name__=='__main__':unittest.main()
