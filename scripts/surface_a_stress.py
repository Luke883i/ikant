from __future__ import annotations
import argparse,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.validation import source_fingerprint
from ikant.surfaces import validate_surface_a

WORDS='capisco questo punto il reticolo mantiene memoria locale e regola la risposta con cautela senza inventare prove nuove mentre conserva conflitti e limiti in modo naturale semplice umano diretto'.split()

def valid_text(rng):
    n=rng.randint(5,85); words=[rng.choice(WORDS) for _ in range(n)]
    chunks=[]
    while words:
        take=min(len(words),rng.randint(6,22));chunk=words[:take];words=words[take:]
        chunks.append(' '.join(chunk).capitalize()+'.')
    return ' '.join(chunks)

def invalid_text(rng):
    kind=rng.randrange(6)
    if kind==0:return '# Titolo\nTesto semplice ma con un titolo vietato.'
    if kind==1:return '- elemento uno\n- elemento due\nQuesta forma a lista non deve passare.'
    if kind==2:return 'campo | valore | stato\nuno | due | tre'
    if kind==3:return '```python\nprint(1)\n```'
    if kind==4:return 'troppo breve'
    return ' '.join(['parola']*501)+'.'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);t=time.monotonic();valid=invalid=0
    for i in range(a.cases):
        should=i%2==0;text=valid_text(rng) if should else invalid_text(rng);ok,errors=validate_surface_a(text)
        if should:
            assert ok,(text,errors);valid+=1
        else:
            assert not ok,(text,errors);invalid+=1
    print(json.dumps({'source_fingerprint':source_fingerprint(),'schema':'ikant-surface-a-stress/v0.2','status':'PASS','cases':a.cases,'valid_cases':valid,'invalid_cases':invalid,'seed':a.seed,'elapsed_s':round(time.monotonic()-t,3)},sort_keys=True))
if __name__=='__main__':main()
