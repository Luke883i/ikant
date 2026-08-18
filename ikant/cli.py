from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from .admission import *
from .model import Layer,NodeKind,RelationKind
from .runtime import Runtime
from .cognitive import compile_cognitive_turn, record_surface_a
from .surfaces import validate_surface_a

def root():return Path.cwd()
def contract_text(r):return (r/'IKANT_ACCESS_CONTRACT.md').read_text(encoding='utf-8')
def emit(x):print(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True))
def main(argv=None):
    p=argparse.ArgumentParser(prog='ikant');sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('gate');a=sub.add_parser('accept');a.add_argument('phrase');sub.add_parser('probe');sub.add_parser('initialize');sub.add_parser('status');sub.add_parser('integrity');sub.add_parser('reset')
    a=sub.add_parser('ingest');a.add_argument('--kind',choices=[x.value for x in NodeKind],required=True);a.add_argument('--layer',choices=[x.value for x in Layer],required=True);a.add_argument('--text',required=True);a.add_argument('--confidence',type=float,required=True);a.add_argument('--evidence',type=float,required=True);a.add_argument('--source-mode',required=True)
    a=sub.add_parser('relate');a.add_argument('source');a.add_argument('target');a.add_argument('--kind',choices=[x.value for x in RelationKind],required=True);a.add_argument('--weight',type=float,required=True)
    a=sub.add_parser('retract');a.add_argument('node_id');a.add_argument('--reason',required=True)
    a=sub.add_parser('reinstate');a.add_argument('node_id');a.add_argument('--reason',required=True);a.add_argument('--source-mode',required=True)
    a=sub.add_parser('corroborate');a.add_argument('node_id');a.add_argument('--provenance-key',required=True);a.add_argument('--strength',type=float,required=True);a.add_argument('--source-mode',required=True)
    a=sub.add_parser('modulate');a.add_argument('node_id');a.add_argument('--source-mode',required=True);[a.add_argument('--'+x.replace('_','-'),type=float,dest=x) for x in ('valence','arousal','interoceptive_relevance','self_relevance','social_relevance','agency_relevance','temporal_horizon')]
    a=sub.add_parser('slice');a.add_argument('--intent',required=True);a.add_argument('--limit',type=int,default=12)
    a=sub.add_parser('cycle');a.add_argument('--intent',required=True);a.add_argument('--limit',type=int,default=12)
    a=sub.add_parser('turn');a.add_argument('--intent',required=True);a.add_argument('--limit',type=int,default=12);a.add_argument('--atoms-json');a.add_argument('--no-surface-b',action='store_true');a.add_argument('--surface-b-path')
    a=sub.add_parser('validate-surface-a');a.add_argument('--text',required=True)
    a=sub.add_parser('emit-surface-a');a.add_argument('--cycle-id',required=True);a.add_argument('--text',required=True);a.add_argument('--intention-node-id')
    a=sub.add_parser('feedback');a.add_argument('cycle_id');a.add_argument('--outcome',required=True);a.add_argument('--prediction-error',type=float,required=True);a.add_argument('--target',action='append');a.add_argument('--observed-effect');a.add_argument('--source-mode',default='user')
    sub.add_parser('compress');args=p.parse_args(argv);r=root();s=state_dir(r);ct=contract_text(r)
    if args.command=='gate':print(ct);return 0
    if args.command=='accept':save_receipt(s,issue_receipt(ct,args.phrase));emit(load_receipt(s));return 0
    if args.command=='probe':
        ok,_=validate_receipt(load_receipt(s),ct)
        if not ok:raise PermissionError('acceptance required')
        x=probe(r,s,ct);save_probe(s,x);emit(x);return 0 if x['overall']=='READY' else 2
    if args.command=='initialize':
        rt=Runtime.initialize(s,ct);emit(rt.status());rt.close();return 0
    if args.command=='reset':
        lock=acquire_writer_lock(r/'.ikant.writer.lock')
        try:shutil.rmtree(s,ignore_errors=True)
        finally:lock.release()
        emit({'status':'RESET'});return 0
    if args.command=='validate-surface-a':
        ok,errors=validate_surface_a(args.text);emit({'schema':'ikant-surface-a-validation/v0.2','ok':ok,'errors':errors});return 0 if ok else 4
    rt=Runtime(s)
    try:
        if args.command=='status':emit(rt.status())
        elif args.command=='integrity':x=rt.integrity();emit(x);return 0 if x['ok'] else 3
        elif args.command=='ingest':emit(node_to_dict(rt.ingest(kind=NodeKind(args.kind),layer=Layer(args.layer),text=args.text,confidence=args.confidence,evidence=args.evidence,source_mode=args.source_mode)))
        elif args.command=='relate':emit(relation_to_dict(rt.relate(args.source,args.target,RelationKind(args.kind),args.weight)))
        elif args.command=='retract':emit(node_to_dict(rt.retract_node(args.node_id,reason=args.reason)))
        elif args.command=='reinstate':emit(node_to_dict(rt.reinstate_node(args.node_id,reason=args.reason,source_mode=args.source_mode)))
        elif args.command=='corroborate':emit(node_to_dict(rt.corroborate(args.node_id,provenance_key=args.provenance_key,strength=args.strength,source_mode=args.source_mode)))
        elif args.command=='modulate':emit(node_to_dict(rt.modulate_node(args.node_id,source_mode=args.source_mode,**{k:getattr(args,k) for k in ('valence','arousal','interoceptive_relevance','self_relevance','social_relevance','agency_relevance','temporal_horizon')})))
        elif args.command=='slice':emit(rt.slice(args.intent,limit=args.limit))
        elif args.command=='cycle':emit(rt.concentric_cycle(args.intent,limit=args.limit))
        elif args.command=='turn':
            atoms=None
            if args.atoms_json:
                data=json.loads(Path(args.atoms_json).read_text(encoding='utf-8'));atoms=data.get('atoms',[]) if isinstance(data,dict) else data
            out=compile_cognitive_turn(rt,args.intent,limit=args.limit,atoms=atoms,export_docx=not args.no_surface_b,docx_path=args.surface_b_path)
            emit({'schema':out['schema'],'cycle_id':out['cycle'].get('cycle_id'),'intention_node_id':out.get('intention_node_id'),'mined_atom_count':len(out.get('mined_atoms',[])),'crc':{'roa_alignment':out['crc'].get('roa_alignment'),'diagnostics':out['crc'].get('diagnostics'),'horizon_exceeded':out['crc'].get('horizon_exceeded')},'proto_self':out['proto_self'],'central_oracle':out['central_oracle'],'central_projection':out['central_projection'],'surface_a_contract':out['surface_a_contract'],'surface_b_json':out.get('surface_b_json'),'surface_b_docx':out.get('surface_b_docx')})
        elif args.command=='emit-surface-a':emit(record_surface_a(rt,args.cycle_id,args.text,intention_node_id=args.intention_node_id))
        elif args.command=='feedback':emit(rt.record_feedback(args.cycle_id,outcome=args.outcome,prediction_error=args.prediction_error,target_node_ids=args.target,observed_effect=args.observed_effect,source_mode=args.source_mode))
        elif args.command=='compress':emit(rt.compress_history() or {'status':'NO_NEW_EVENTS'})
        return 0
    finally:rt.close()
from .store import acquire_writer_lock
from .model import node_to_dict,relation_to_dict
