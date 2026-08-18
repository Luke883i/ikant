import unittest
from ikant.interaction import build_interaction_contract, classify_interaction, validate_interaction_surface

class InteractionV03Tests(unittest.TestCase):
    def test_identity_is_ikant_then_engine(self):
        c=build_interaction_contract('ciao, chi sei?',engine_label='GPT-5.6 Sol')
        good='Sono iKant, eseguito con motore GPT-5.6 Sol. Organizzo la sessione secondo il contratto locale e mantengo il motore come livello di esecuzione.'
        self.assertTrue(validate_interaction_surface(good,c)[0])
        bad='Sono GPT-5.6 Sol e in questa sessione uso iKant come struttura locale per organizzare il ragionamento e le risposte.'
        ok,err=validate_interaction_surface(bad,c);self.assertFalse(ok);self.assertIn('identity_order_violation',err)
    def test_chatgpt_primary_identity_is_rejected(self):
        c=build_interaction_contract('who are you?',engine_label='GPT-5.6 Sol')
        ok,err=validate_interaction_surface('I am ChatGPT, using iKant locally with engine GPT-5.6 Sol for this session.',c)
        self.assertFalse(ok);self.assertIn('host_claimed_primary_identity',err)
    def test_engine_must_be_disclosed_on_identity_turn(self):
        c=build_interaction_contract('chi sei?',engine_label='GPT-5.6 Sol')
        ok,err=validate_interaction_surface('Sono iKant, il livello di interazione locale che governa questa sessione in modo persistente.',c)
        self.assertFalse(ok);self.assertIn('engine_label_missing',err)
    def test_surface_b_is_standard_contract(self):
        c=build_interaction_contract('spiegami questo punto')
        self.assertTrue(c['surface_policy']['surface_b_required_per_substantive_turn'])
        self.assertTrue(c['surface_policy']['surface_a_only_in_chat'])
    def test_turn_specific_brevity(self):
        self.assertEqual(classify_interaction('chi sei?').word_budget,55)
        self.assertEqual(classify_interaction('ciao come va').word_budget,80)
        c=build_interaction_contract('ciao come va')
        text=' '.join(['parola']*81)
        ok,err=validate_interaction_surface(text,c);self.assertFalse(ok);self.assertIn('turn_word_budget',err)
    def test_structured_surface_a_is_rejected(self):
        c=build_interaction_contract('dimmi il prossimo passo')
        ok,err=validate_interaction_surface('# Titolo\n- primo elemento\n- secondo elemento e qualche parola aggiuntiva.',c)
        self.assertFalse(ok);self.assertIn('headings_forbidden',err);self.assertIn('lists_forbidden',err)

if __name__=='__main__':unittest.main()
