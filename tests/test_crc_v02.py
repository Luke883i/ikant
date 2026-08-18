import tempfile, unittest, zipfile
from pathlib import Path
from ikant.crc import EpistemicHorizon, evaluate_reticulum
from ikant.neurofunctional import validate_cluster_map, BY_RING, neuroscience_coverage_manifest
from ikant.proto_self import derive_proto_self, workspace_plan
from ikant.central import converge_kant_oracle, project_surface_content
from ikant.surfaces import build_surface_a_contract, validate_surface_a, build_surface_b_snapshot, export_surface_b_docx
from ikant.cognitive import compile_cognitive_turn, record_surface_a, apply_intention_atoms
from ikant.model import Node, NodeKind, Layer, Modulators, CONCENTRIC_ORDER
from tests.helpers import active_runtime


def row(i, layer, kind="claim", epi=.6, act=.3, stab=.2, nov=.8, pe=.1, source="user", text=None):
    return {"id":f"N{i}","layer":layer.value,"kind":kind,"epistemic_score":epi,"activation":act,"stability":stab,"novelty":nov,"prediction_error":pe,"source_mode":source,"text":text or f"evidence item {i}"}

def cycle_fixture():
    nodes = [
        row(1, Layer.SIGNAL, NodeKind.OBSERVATION.value, .75,.45,.25,.7,.05,"document","A measured observation about project state"),
        row(2, Layer.MEMORY, NodeKind.MEMORY.value, .62,.42,.58,.2,.08,"repository","A recurring memory about validation state"),
        row(3, Layer.PREDICTIVE_CONTROL, NodeKind.GOAL.value, .68,.48,.4,.5,.12,"user","Finish the implementation safely"),
        row(4, Layer.METACOGNITION, NodeKind.CONFLICT.value, .52,.5,.3,.5,.55,"runtime_derived","A conflict remains unresolved"),
        row(5, Layer.REFLECTIVE_SELF, NodeKind.SELF_MODEL.value, .55,.38,.52,.4,.15,"runtime_derived","Current commitment is to preserve evidence boundaries"),
        row(6, Layer.ARCHETYPAL_HYPOTHESIS, NodeKind.HYPOTHESIS.value, .15,.25,.5,.2,.1,"runtime_derived","Recurring bridge motif"),
    ]
    return {
        "cycle_id":"CYC-1",
        "semantic_slice":{"intent_sha256":"abc","nodes":nodes,"directives":[{"type":"goal","text":"Finish the implementation safely","strength":.65,"source_mode":"user"}]},
        "output_policy":{"epistemic_caution":.48},
        "output_projection":{"assertable_node_ids":["N1","N3"],"tentative_node_ids":["N2","N4","N5"],"interpretive_hypothesis_node_ids":["N6"],"authorized_directives":[{"type":"goal","text":"Finish the implementation safely"}],"must_surface_conflicts":[{"source":"N4","target":"N3","kind":"contradicts"}]},
        "kant_oracle":{"self_state":{"unity_index":.62,"critique_pressure":.38,"regulative_mode":"REFLECTIVE_SYNTHESIS"},"findings":[],"dispositions":[]},
    }

class FakeParams: oracle_retroaction_gain=.08
class FakeRuntime:
    def __init__(self):
        self.params=FakeParams(); self.state_dir=Path(tempfile.mkdtemp())/".ikant"; self.state_dir.mkdir(); self.events_mem=[]
        self.runtime={"session_id":"SES-X","status":"ACTIVE","compression":{"trend":{"metrics":{"revision_pressure":.2}}}}
        self._cycle=cycle_fixture()
        self.nodes={}
        for r in self._cycle["semantic_slice"]["nodes"]:
            self.nodes[r["id"]]=Node(r["id"],NodeKind(r["kind"]),Layer(r["layer"]),r["text"],r["epistemic_score"],r["epistemic_score"],r["source_mode"],activation=r["activation"],stability=r["stability"],novelty=r["novelty"],prediction_error=r["prediction_error"],modulators=Modulators())
    def require_active(self):
        if self.runtime["status"]!="ACTIVE": raise PermissionError
    def concentric_cycle(self,intent,limit=12): return self._cycle
    def _save(self,n): self.nodes[n.id]=n
    def _write_runtime(self): pass
    def _event(self,op,subject,payload): self.events_mem.append({"seq":len(self.events_mem)+1,"op":op,"subject":subject,"payload":payload})

class CRCV02Tests(unittest.TestCase):
    def test_cluster_map_complete_and_bounded(self):
        ok, errors=validate_cluster_map(); self.assertTrue(ok, errors); self.assertEqual(set(BY_RING),set(CONCENTRIC_ORDER))
        self.assertFalse(BY_RING[Layer.ARCHETYPAL_HYPOTHESIS].anatomical_anchors)
        self.assertFalse(BY_RING[Layer.KANT_ORACLE].anatomical_anchors)
    def test_neuroscience_coverage_declares_active_host_and_inactive_boundaries(self):
        rows=neuroscience_coverage_manifest();by={x["domain"]:x for x in rows}
        self.assertEqual(by["language_and_distributed_semantics"]["status"],"host_boundary")
        self.assertEqual(by["cellular_molecular_genetic_glial"]["status"],"inactive_v02")
        self.assertIn("active_ring",{x["status"] for x in rows});self.assertTrue(all(x["biological_claim"] for x in rows))

    def test_crc_real_transmissions_and_diagnostics(self):
        crc=evaluate_reticulum(cycle_fixture()["semantic_slice"])
        self.assertEqual(len(crc["transmissions"]),8)
        self.assertTrue(crc["roa_alignment"]["levels_are_state_rule_pairs"])
        self.assertTrue(crc["roa_alignment"]["transmissions_explicit"])
        self.assertTrue(crc["roa_alignment"]["crc_basic"])
        for t in crc["transmissions"]:
            self.assertGreaterEqual(t["coefficient_of_collapse"],0); self.assertLessEqual(t["coefficient_of_collapse"],1)
            self.assertLessEqual(t["output_count"],t["input_count"])
        d=crc["diagnostics"]; self.assertTrue(0<=d["emergence_index_proxy"]<=1); self.assertTrue(0<=d["reticular_irreducibility_proxy"]<=1)
    def test_neurofunctional_control_is_causal_not_decorative(self):
        borderline={"nodes":[{"id":"X","layer":"signal","kind":"observation","epistemic_score":.51,"activation":.3,"stability":.2,"novelty":.8,"prediction_error":.2,"source_mode":"document","text":"borderline sensory evidence","modulators":{}}],"directives":[]}
        baseline=evaluate_reticulum(borderline)
        primed=evaluate_reticulum(borderline,previous_neurofunctional_state={Layer.SALIENCE_HOMEOSTASIS.value:{"gain":1,"precision":1,"inhibition":0,"plasticity":.5,"persistence":.5}})
        self.assertEqual(baseline["ring_states"]["salience_homeostasis"][0]["bucket"],"background")
        self.assertEqual(primed["ring_states"]["salience_homeostasis"][0]["bucket"],"foreground")
        self.assertNotEqual(baseline["transmissions"][0]["functional_control"],primed["transmissions"][0]["functional_control"])
        self.assertFalse(primed["diagnostics"]["neurofunctional_state_is_neural_measurement"])

    def test_freud_jung_are_typed_bounded_interpretive_transforms(self):
        rows=[]
        for i,layer in enumerate(CONCENTRIC_ORDER[:6]):
            rows.append({"id":f"A{i}","layer":layer.value,"kind":NodeKind.SELF_MODEL.value if i==5 else (NodeKind.GOAL.value if i==3 else NodeKind.OBSERVATION.value),"epistemic_score":.75,"activation":.3,"stability":.9,"novelty":.02,"prediction_error":.02,"source_mode":"user" if i in {3,5} else "document","text":"stable recurring self goal context","modulators":{}})
        crc=evaluate_reticulum({"nodes":rows,"directives":[]})
        psych=crc["ring_states"][Layer.PSYCHODYNAMIC_HYPOTHESIS.value][0]["properties"]
        arch=crc["ring_states"][Layer.ARCHETYPAL_HYPOTHESIS.value][0]["properties"]
        self.assertIn("freudian_structural_hypothesis",psych); self.assertEqual(psych["historical_model_status"],"interpretive_not_neuroscientific")
        self.assertEqual(arch["jungian_archetype_candidate"],"self_candidate"); self.assertEqual(arch["historical_model_status"],"jung_inspired_interpretive_label")
        self.assertGreater(crc["diagnostics"]["archetypal_interpretive_pressure"],0)

    def test_post_crc_projection_can_only_downgrade_under_material_block(self):
        c=cycle_fixture();crc=evaluate_reticulum(c["semantic_slice"]);central=converge_kant_oracle(c["kant_oracle"],crc,derive_proto_self(crc,c));central["regulative_mode"]="PRACTICAL_BLOCK"
        p=project_surface_content(c,crc,central)
        self.assertIn("N1",p["assertable_node_ids"]);self.assertNotIn("N3",p["assertable_node_ids"]);self.assertIn("N3",p["tentative_node_ids"]);self.assertFalse(p["authorized_directives"]);self.assertEqual(p["material_action"],"BLOCK")

    def test_mined_atoms_are_auditable_and_derived_evidence_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td))
            atoms=[{"kind":"goal","layer":"predictive_control","text":"Complete the requested audit","confidence":.8,"evidence":.8,"source_mode":"user"},{"kind":"hypothesis","layer":"metacognition","text":"A derived possibility","confidence":.6,"evidence":.2,"source_mode":"inference"}]
            out=compile_cognitive_turn(rt,"Audit the system",atoms=atoms)
            self.assertEqual(len(out["mined_atoms"]),2);self.assertTrue(all(x["metadata"]["mined_from_intention"] for x in out["mined_atoms"]))
            with self.assertRaises(ValueError):apply_intention_atoms(rt,[{"kind":"hypothesis","layer":"metacognition","text":"overclaim","confidence":.8,"evidence":.9,"source_mode":"inference"}])
            rt.close()

    def test_surface_a_emission_is_non_evidential_and_links_turns(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            first=compile_cognitive_turn(rt,"Valuta il prossimo passo con prudenza",export_docx=True)
            text="Procederei con prudenza, mantenendo espliciti i limiti e verificando prima i punti ancora incerti nel reticolo locale."
            receipt=record_surface_a(rt,first["cycle"]["cycle_id"],text,intention_node_id=first["intention_node_id"])
            response=rt.nodes[receipt["response_id"]];self.assertEqual(response.kind,NodeKind.RESPONSE);self.assertEqual(response.evidence,0);self.assertTrue(response.metadata["speech_act_not_evidence"])
            snap=__import__('json').loads(Path(receipt["surface_b_json"]).read_text());self.assertEqual(snap["dynamic_state"]["surface_a_emission"]["text"],text);self.assertTrue(Path(receipt["surface_b_docx"]).exists())
            second=compile_cognitive_turn(rt,"Continua solo se i vincoli restano rispettati")
            temporal=[r for r in rt.relations.values() if r.kind.value=="precedes"]
            self.assertTrue(any(r.source==response.id and r.target==second["intention_node_id"] for r in temporal))
            surfaced=second["surface_a_contract"]["content"]["assertable"]+second["surface_a_contract"]["content"]["tentative"]
            self.assertNotIn(text,surfaced);rt.close()

    def test_horizon_can_block_closure(self):
        h=EpistemicHorizon(required_answer_type="legal_certification")
        crc=evaluate_reticulum(cycle_fixture()["semantic_slice"],horizon=h)
        self.assertFalse(crc["roa_alignment"]["crc_basic"]); self.assertTrue(crc["horizon_exceeded"])
    def test_proto_self_is_functional_not_consciousness_claim(self):
        c=cycle_fixture(); crc=evaluate_reticulum(c["semantic_slice"]); p=derive_proto_self(crc,c)
        self.assertFalse(p["is_consciousness_claim"]); self.assertTrue(0<=p["proto_self_index"]<=1)
        p2=derive_proto_self(crc,c,p); self.assertGreaterEqual(p2["temporal_continuity"],p["temporal_continuity"])
    def test_central_oracle_closure_changes_mode(self):
        c=cycle_fixture(); crc=evaluate_reticulum(c["semantic_slice"]); p=derive_proto_self(crc,c)
        central=converge_kant_oracle(c["kant_oracle"],crc,p); self.assertNotEqual(central["regulative_mode"],"HORIZON_BLOCK");self.assertTrue(0<=central["transcendental_apperception_proxy"]<=1);self.assertIn("transcendental_apperception_proxy",central["integrated_faculties"])
        bad=evaluate_reticulum(c["semantic_slice"],horizon=EpistemicHorizon(required_answer_type="forbidden"))
        blocked=converge_kant_oracle(c["kant_oracle"],bad,p); self.assertEqual(blocked["regulative_mode"],"HORIZON_BLOCK")
    def test_workspace_never_changes_evidence(self):
        rt=FakeRuntime(); before={k:n.evidence for k,n in rt.nodes.items()}; out=compile_cognitive_turn(rt,"finish safely")
        after={k:n.evidence for k,n in rt.nodes.items()}; self.assertEqual(before,after); self.assertFalse(out["workspace"]["evidence_modified"])
        self.assertIn("cognitive",rt.runtime); self.assertEqual(rt.events_mem[-1]["op"],"COGNITIVE_COMPILE")
    def test_surface_a_contract_and_validator(self):
        rt=FakeRuntime(); out=compile_cognitive_turn(rt,"finish safely"); contract=out["surface_a_contract"]
        self.assertEqual(contract["format"]["min_words"],5); self.assertEqual(contract["format"]["max_words"],500); self.assertFalse(contract["format"]["headings"])
        ok,err=validate_surface_a("Capisco il punto. Il reticolo ora deve comprimere davvero i livelli e lasciare che il centro regoli la risposta senza inventare prove.")
        self.assertTrue(ok,err)
        self.assertFalse(validate_surface_a("# Titolo\n- elemento uno\n- elemento due")[0])
    def test_surface_b_docx_is_valid_package(self):
        rt=FakeRuntime(); out=compile_cognitive_turn(rt,"finish safely"); snap=build_surface_b_snapshot(out)
        with tempfile.TemporaryDirectory() as td:
            p=export_surface_b_docx(snap,Path(td)/"snapshot.docx"); self.assertTrue(p.exists())
            with zipfile.ZipFile(p) as z:
                names=set(z.namelist()); self.assertIn("word/document.xml",names)
                text=z.read("word/document.xml").decode(); self.assertIn("CRC Runtime Snapshot",text); self.assertIn("Proto-self index",text)

    def test_empty_reticulum_is_not_crc_closed(self):
        crc=evaluate_reticulum({"nodes":[],"directives":[]})
        self.assertFalse(crc["roa_alignment"]["crc_basic"])
        self.assertFalse(crc["roa_alignment"]["representational_path_complete"])

    def test_real_durable_turn_records_intention_and_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            rt=active_runtime(Path(td),durable=True)
            claim=rt.ingest(kind=NodeKind.CLAIM,layer=Layer.SIGNAL,text="The current build passed locally",confidence=.8,evidence=.7,source_mode="repository")
            before=claim.evidence
            out=compile_cognitive_turn(rt,"Decide whether to proceed carefully",export_docx=True)
            self.assertTrue(out["crc"]["roa_alignment"]["crc_basic"])
            self.assertTrue(Path(out["surface_b_json"]).exists())
            self.assertTrue(Path(out["surface_b_docx"]).exists())
            intentions=[n for n in rt.nodes.values() if n.kind==NodeKind.INTENTION]
            self.assertEqual(len(intentions),1);self.assertTrue(intentions[0].metadata["not_factual_claim"])
            surfaced=out["surface_a_contract"]["content"]["assertable"]+out["surface_a_contract"]["content"]["tentative"]
            self.assertNotIn("Decide whether to proceed carefully",surfaced)
            self.assertEqual(rt.nodes[claim.id].evidence,before)
            self.assertIn("last_snapshot",rt.runtime["cognitive"])
            p=rt.state_dir;rt.close()
            reopened=__import__("ikant.runtime",fromlist=["Runtime"]).Runtime(p)
            out2=compile_cognitive_turn(reopened,"Decide whether to proceed carefully",export_docx=False)
            self.assertEqual(out2["proto_self"]["cycle_index"],2)
            self.assertEqual(reopened.nodes[claim.id].evidence,before)
            reopened.close()

    def test_central_critique_changes_workspace_gain_not_evidence(self):
        c=cycle_fixture();crc=evaluate_reticulum(c["semantic_slice"]);p=derive_proto_self(crc,c)
        central=converge_kant_oracle(c["kant_oracle"],crc,p);central["critique_pressure"]=.9;central["regulative_mode"]="CRITIQUE"
        plan=workspace_plan(crc,c,p,central=central)
        self.assertEqual(plan["regulative_mode"],"CRITIQUE")
        self.assertFalse(plan["evidence_modified"]);self.assertTrue(plan["retroactive_routes"])

    def test_compile_turn_can_export_surface_b(self):
        rt=FakeRuntime(); p=rt.state_dir/"artifacts"/"x.docx"; out=compile_cognitive_turn(rt,"finish safely",export_docx=True,docx_path=p)
        self.assertEqual(out["surface_b_docx"],str(p)); self.assertTrue(p.exists()); self.assertEqual(rt.events_mem[-1]["op"],"SURFACE_B_SNAPSHOT")

if __name__=='__main__': unittest.main()
