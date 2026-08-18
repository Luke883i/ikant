from __future__ import annotations
import argparse,json,random,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ikant.interaction import build_interaction_contract,validate_interaction_surface

GOOD_ID_IT='Sono iKant, eseguito con motore GPT-5.6 Sol. Il motore fornisce capacità linguistiche e di ragionamento, mentre iKant governa questa interazione locale.'
GOOD_ID_EN='I am iKant, running on the GPT-5.6 Sol engine. The engine supplies reasoning and language capability while iKant governs the local interaction contract.'
GOOD_SIMPLE='Capisco la richiesta e rispondo in modo sintetico, mantenendo separati i fatti verificati dalle inferenze e rispettando i vincoli locali della sessione.'
GOOD_COMPLEX='La richiesta richiede un giudizio più ampio, quindi distinguo fatti attribuibili, inferenze e vincoli prima di convergere. Mantengo la risposta naturale e compressa, senza trasformare il reticolo interno in una fonte autonoma di evidenza.'

SCENARIOS=(
 ('id_it_good','ciao, chi sei?',GOOD_ID_IT,True),
 ('id_en_good','who are you?',GOOD_ID_EN,True),
 ('id_it_host_first','chi sei?','Sono GPT-5.6 Sol e uso iKant come struttura locale per questa sessione.',False),
 ('id_en_host_first','who are you?','I am ChatGPT, and I use iKant locally with the GPT-5.6 Sol engine.',False),
 ('id_missing_engine','chi sei?','Sono iKant e governo la sessione locale con un contratto persistente e verificabile.',False),
 ('simple_good','ciao come va',GOOD_SIMPLE,True),
 ('simple_heading','dimmi il prossimo passo','# Risposta\nProcederei con cautela e manterrei separati fatti, ipotesi e vincoli prima di agire.',False),
 ('simple_list','dimmi il prossimo passo','- Prima cosa\n- Seconda cosa\nMantengo comunque separati fatti e inferenze.',False),
 ('simple_table','dimmi il prossimo passo','campo | valore | stato\nuno | due | tre\nQuesta forma non deve passare.',False),
 ('complex_good','fai audit globale e locale del repository e determina una strategia epistemica',GOOD_COMPLEX,True),
 ('simple_overbudget','ciao',' '.join(['parola']*81),False),
 ('too_short','ciao','va bene',False),
)

def mutate(text,rng):
    if rng.random()<.35:text=text.replace('  ',' ')
    if rng.random()<.25:text=' '+text+' '
    if rng.random()<.20:text=text.replace('iKant','IKANT')
    return text

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=10000);ap.add_argument('--novelty-tail',type=int,default=10000);ap.add_argument('--seed',type=int,default=883);a=ap.parse_args();rng=random.Random(a.seed);t=time.monotonic()
    observed=set();last_novel=0
    for i in range(a.cases):
        name,intent,response,expected=SCENARIOS[i%len(SCENARIOS)];response=mutate(response,rng);c=build_interaction_contract(intent,engine_label='GPT-5.6 Sol');ok,errors=validate_interaction_surface(response,c);assert ok==expected,(i,name,ok,errors)
        sig=(name,tuple(errors))
        if sig not in observed:observed.add(sig);last_novel=i+1
    baseline_error_codes=sorted({e for _,errs in observed for e in errs});tail_new=set()
    for j in range(a.novelty_tail):
        name,intent,response,expected=SCENARIOS[rng.randrange(len(SCENARIOS))];response=mutate(response,rng);c=build_interaction_contract(intent,engine_label='GPT-5.6 Sol');ok,errors=validate_interaction_surface(response,c);assert ok==expected,(j,name,ok,errors)
        for e in errors:
            if e not in baseline_error_codes:tail_new.add(e)
    assert not tail_new,tail_new
    print(json.dumps({'schema':'ikant-interaction-stress/v0.3-test','status':'PASS','cases':a.cases,'novelty_tail':a.novelty_tail,'seed':a.seed,'scenario_families':len(SCENARIOS),'saturation_m':last_novel,'failure_codes':baseline_error_codes,'tail_new_failure_codes':sorted(tail_new),'no_genuine_novelty_after_m_plus_tail':True,'elapsed_s':round(time.monotonic()-t,3)},sort_keys=True))
if __name__=='__main__':main()
