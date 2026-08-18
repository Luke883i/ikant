from __future__ import annotations
import argparse,json,random,tempfile,sys
from pathlib import Path
if __package__ in {None,''}:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.helpers import active_runtime
from ikant.validation import source_fingerprint
from ikant.model import *
def run(operations=10000,novelty_tail=1000,seed=883):
 rng=random.Random(seed)
 with tempfile.TemporaryDirectory() as td:
  rt=active_runtime(Path(td));active=[];cycles=[];counts={k:0 for k in ('ingest','relate','cycle','feedback','corroborate','retract','reinstate','modulate','compress','slice')};inactive=[];maxmean=maxfrac=s85=s95=0.
  for i in range(48):active.append(rt.ingest(kind=NodeKind.CLAIM,layer=list(Layer)[i%len(Layer)],text=f'seed {i} shared',confidence=.6,evidence=.5,source_mode='repository').id)
  for step in range(operations):
   roll=rng.random();active=[x for x in active if x in rt.nodes and rt.nodes[x].active]
   if roll<.34:
    counts['ingest']+=1
    if active and rng.random()<.7:
     x=rt.nodes[rng.choice(active)];n=rt.ingest(kind=x.kind,layer=x.layer,text=x.text,confidence=rng.random(),evidence=rng.random(),source_mode=x.source_mode)
    else:
     n=rt.ingest(kind=rng.choice(list(NodeKind)),layer=rng.choice(list(Layer)),text=f'dynamic {step%701} token {rng.randrange(71)}',confidence=rng.random(),evidence=rng.random(),source_mode=rng.choice(('user','repository','document','live','inference')));active.append(n.id)
   elif roll<.53 and len(active)>1:counts['relate']+=1;s,t=rng.sample(active,2);rt.relate(s,t,rng.choice(list(RelationKind)),rng.random())
   elif roll<.60:counts['cycle']+=1;c=rt.concentric_cycle(rng.choice(('shared evidence','revision action','memory conflict')),limit=10);cycles.append(c['cycle_id'])
   elif roll<.66 and cycles:counts['feedback']+=1;cid=rng.choice(cycles[-50:]);rows=rt._cycle(cid)['semantic_slice']['nodes'];targets=[rng.choice(rows)['id']] if rows else None;rt.record_feedback(cid,outcome=rng.choice(('success','failure','corrected','partial')),prediction_error=rng.random(),target_node_ids=targets)
   elif roll<.75 and active:counts['corroborate']+=1;rt.corroborate(rng.choice(active),provenance_key=f'p-{seed}-{step}',strength=rng.random(),source_mode='document')
   elif roll<.79 and active:
    cand=[x for x in active if not (rt.nodes[x].kind==NodeKind.PRINCIPLE)]
    if cand:counts['retract']+=1;v=rng.choice(cand);rt.retract_node(v,reason='stress');active.remove(v);inactive.append(v)
   elif roll<.81 and inactive:counts['reinstate']+=1;v=inactive.pop();rt.reinstate_node(v,reason='stress reconsideration',source_mode='document');active.append(v)
   elif roll<.85 and active:counts['modulate']+=1;rt.modulate_node(rng.choice(active),source_mode='user',arousal=rng.random(),social_relevance=rng.random(),agency_relevance=rng.random(),self_relevance=rng.random())
   elif roll<.89:counts['compress']+=1;rt.compress_history()
   else:counts['slice']+=1;rt.slice('shared evidence conflict',limit=10)
   if step%43==0:
    xs=[n for n in rt.nodes.values() if n.active];m=mean([n.activation for n in xs]);fr=mean([n.activation/max(.001,n.activation_ceiling) for n in xs]);maxmean=max(maxmean,m);maxfrac=max(maxfrac,fr);s85=max(s85,mean([1 if n.activation/n.activation_ceiling>=.85 else 0 for n in xs]));s95=max(s95,mean([1 if n.activation/n.activation_ceiling>=.95 else 0 for n in xs]));
  s=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.ARCHETYPAL_HYPOTHESIS,text='dynamic no novelty sentinel',confidence=1,evidence=1,source_mode='inference');e=s.evidence;n=len(rt.nodes)
  for _ in range(novelty_tail):rt.ingest(kind=NodeKind.CLAIM,layer=Layer.ARCHETYPAL_HYPOTHESIS,text='dynamic no novelty sentinel',confidence=0,evidence=0,source_mode='inference')
  if len(rt.nodes)!=n or rt.nodes[s.id].evidence!=e:raise AssertionError('no novelty')
  if operations>=1000:
   for k in ('cycle','feedback','corroborate','retract','reinstate','modulate','compress'):
    if counts[k]==0:raise AssertionError('missing coverage '+k)
  active_summaries=[x for x in rt.nodes.values() if x.active and x.metadata.get('compression_owned') and x.metadata.get('derivation_kind')=='summary']
  inactive_derived=[x for x in rt.nodes.values() if not x.active and x.metadata.get('compression_owned')]
  if len(active_summaries)>rt.params.max_active_summaries or len(inactive_derived)>rt.params.max_inactive_derived_nodes:raise AssertionError('derived working set exceeded')
  return {'source_fingerprint':source_fingerprint(),'schema':'ikant-dynamic-stress/v0.1','seed':seed,'operations':operations,'novelty_tail':novelty_tail,'nodes':len(rt.nodes),'relations':len(rt.relations),'cycles':len(cycles),'compressions':rt.runtime['compression']['count'],'active_derived_summaries':len(active_summaries),'inactive_derived_nodes':len(inactive_derived),'archived_derived_nodes':len(rt.derived_archive_mem),'operation_counts':counts,'max_mean_activation_sampled':round(maxmean,6),'max_mean_activation_ceiling_fraction_sampled':round(maxfrac,6),'max_activation_saturation_share_85_sampled':round(s85,6),'max_activation_saturation_share_95_sampled':round(s95,6),'status':'PASS'}
def mean(xs):return sum(xs)/len(xs) if xs else 0
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--operations',type=int,default=10000);p.add_argument('--novelty-tail',type=int,default=1000);p.add_argument('--seed',type=int,default=883);a=p.parse_args();print(json.dumps(run(a.operations,a.novelty_tail,a.seed),indent=2,sort_keys=True))
