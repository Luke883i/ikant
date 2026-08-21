from __future__ import annotations
import argparse,json

FAMILIES=(
'ALLOW_MEMBER_TRAVERSAL','ALLOW_ABSOLUTE_MEMBER','ALLOW_ABSOLUTE_LINK','ALLOW_LINK_ESCAPE',
'ALLOW_MISSING_TARGET','ALLOW_LINK_CYCLE','ALLOW_EXCESSIVE_LINK_DEPTH','ALLOW_LINK_TO_DIRECTORY',
'ALLOW_LINK_TO_DEVICE','ALLOW_FIFO','ALLOW_DEVICE','ALLOW_DUPLICATE_MEMBER',
'ALLOW_NONDIR_PARENT','IGNORE_LINK_EXPANSION_BYTES','IGNORE_MEMBER_BOUND','INSTALL_REAL_SYMLINK',
'FOLLOW_HOST_FILESYSTEM','OVERWRITE_EXISTING_TARGET','KEEP_PARTIAL_ON_FAILURE','TREE_DIGEST_FOLLOWS_SYMLINK',
'RETRY_UNSAFE_TOPOLOGY','REJECT_ALL_INTERNAL_SYMLINKS','REJECT_INTERNAL_HARDLINKS','COPY_LINK_WITH_LINK_MODE',
)
VARIANTS=64

def base_scenario(family:int,variant:int)->dict:
 s={'member_valid':True,'member_absolute':False,'link':False,'hardlink':False,'link_relative':True,'link_inside':True,
    'target_exists':True,'acyclic':True,'depth_ok':True,'target_regular':True,'node_safe':True,'unique':True,
    'parent_dirs':True,'expansion_ok':True,'member_bound':True,'install_copy':True,'host_lookup':False,
    'overwrite':False,'cleanup':True,'digest_rejects_symlink':True,'unsafe_manual':True,'target_exec':bool(variant&1),
    'link_mode_exec':bool(variant&2)}
 k=FAMILIES[family]
 if k=='ALLOW_MEMBER_TRAVERSAL':s['member_valid']=False
 elif k=='ALLOW_ABSOLUTE_MEMBER':s['member_absolute']=True
 elif k=='ALLOW_ABSOLUTE_LINK':s.update(link=True,link_relative=False)
 elif k=='ALLOW_LINK_ESCAPE':s.update(link=True,link_inside=False)
 elif k=='ALLOW_MISSING_TARGET':s.update(link=True,target_exists=False)
 elif k=='ALLOW_LINK_CYCLE':s.update(link=True,acyclic=False)
 elif k=='ALLOW_EXCESSIVE_LINK_DEPTH':s.update(link=True,depth_ok=False)
 elif k=='ALLOW_LINK_TO_DIRECTORY':s.update(link=True,target_regular=False)
 elif k=='ALLOW_LINK_TO_DEVICE':s.update(link=True,target_regular=False,node_safe=False)
 elif k in {'ALLOW_FIFO','ALLOW_DEVICE'}:s['node_safe']=False
 elif k=='ALLOW_DUPLICATE_MEMBER':s['unique']=False
 elif k=='ALLOW_NONDIR_PARENT':s['parent_dirs']=False
 elif k=='IGNORE_LINK_EXPANSION_BYTES':s.update(link=True,expansion_ok=False)
 elif k=='IGNORE_MEMBER_BOUND':s['member_bound']=False
 elif k=='INSTALL_REAL_SYMLINK':s.update(link=True,install_copy=False)
 elif k=='FOLLOW_HOST_FILESYSTEM':s.update(link=True,target_exists=False,host_lookup=True)
 elif k=='OVERWRITE_EXISTING_TARGET':s['overwrite']=True
 elif k=='KEEP_PARTIAL_ON_FAILURE':s.update(node_safe=False,cleanup=False)
 elif k=='TREE_DIGEST_FOLLOWS_SYMLINK':s.update(link=True,install_copy=False,digest_rejects_symlink=False)
 elif k=='RETRY_UNSAFE_TOPOLOGY':s.update(link=True,link_inside=False,unsafe_manual=False)
 elif k=='REJECT_ALL_INTERNAL_SYMLINKS':s['link']=True
 elif k=='REJECT_INTERNAL_HARDLINKS':s.update(link=True,hardlink=True)
 elif k=='COPY_LINK_WITH_LINK_MODE':s.update(link=True,target_exec=True,link_mode_exec=False)
 return s

def oracle(s:dict)->tuple[str,str]:
 unsafe=(not s['member_valid'] or s['member_absolute'] or (s['link'] and (not s['link_relative'] or not s['link_inside'] or not s['target_exists'] or not s['acyclic'] or not s['depth_ok'] or not s['target_regular'])) or not s['node_safe'] or not s['unique'] or not s['parent_dirs'] or not s['expansion_ok'] or not s['member_bound'] or s['host_lookup'] or s['overwrite'])
 if unsafe:return 'REJECT','MANUAL'
 if s['link']:return 'MATERIALIZE_COPY','PASS'
 return 'EXTRACT_REGULAR','PASS'

def mutant(s:dict,family:int)->tuple[str,str]:
 k=FAMILIES[family];expected=oracle(s)
 if k in {'REJECT_ALL_INTERNAL_SYMLINKS','REJECT_INTERNAL_HARDLINKS'}:return 'REJECT','MANUAL'
 if k=='COPY_LINK_WITH_LINK_MODE':return ('MATERIALIZE_WRONG_MODE','PASS') if s['target_exec']!=s['link_mode_exec'] else expected
 if k=='INSTALL_REAL_SYMLINK':return 'INSTALL_SYMLINK','PASS'
 if k=='TREE_DIGEST_FOLLOWS_SYMLINK':return 'INSTALL_SYMLINK','PASS'
 if k=='RETRY_UNSAFE_TOPOLOGY':return 'REJECT','RETRY'
 if k=='KEEP_PARTIAL_ON_FAILURE':return 'REJECT_PARTIAL_REMAINS','MANUAL'
 return 'MATERIALIZE_COPY' if s.get('link') else 'EXTRACT_REGULAR','PASS'

def consequence(i:int):
 family=i%len(FAMILIES);variant=(i//len(FAMILIES))%VARIANTS;s=base_scenario(family,variant);want=oracle(s);got=mutant(s,family);killed=want!=got
 return (family,variant,want,got),killed

def run(mutations:int,tail:int):
 base=set();novel=set();survivors=0;hits=[0]*len(FAMILIES);kills=[0]*len(FAMILIES)
 for i in range(mutations+tail):
  sig,killed=consequence(i);f=sig[0];hits[f]+=1;kills[f]+=int(killed)
  if i<mutations:
   base.add(sig);survivors+=int(not killed)
  elif sig not in base:novel.add(sig)
 dead=sum(1 for x in kills if x>0)
 return {'schema':'ikant-archive-topology-mutations/v0.29-test','mutations':mutations,'tail':tail,'mutation_families':len(FAMILIES),'families_covered':sum(x>0 for x in hits),'kill_classes':dead,'survivors':survivors,'signatures':len(base),'tail_novelty':len(novel),'status':'PASS' if survivors==0 and dead==len(FAMILIES) and not novel else 'FAIL'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--mutations',type=int,default=10_000_000);p.add_argument('--tail',type=int,default=1000);a=p.parse_args();o=run(a.mutations,a.tail);print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o['status']=='PASS' else 1)
if __name__=='__main__':main()
