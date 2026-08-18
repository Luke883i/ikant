import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from ikant.chat_session import ChatIntegrityError, ChatLog, ChatController, sanitize_terminal_text
from ikant.dashboard import index_docx_backlog, persist_dashboard, project_dashboard, render_dashboard_ascii


class FakeRuntime:
    def __init__(self, root: Path):
        self.root = root
        self.state_dir = root / ".ikant"
        self.state_dir.mkdir(parents=True)
        self.runtime = {
            "session_id": "SES-v04",
            "status": "ACTIVE",
            "cycle_count": 3,
            "compression": {"trend": {"metrics": {"revision_pressure": .12}}},
            "cognitive": {},
        }
        self.nodes = {"x": type("N", (), {"evidence": .37})()}
    def require_active(self):
        if self.runtime["status"] != "ACTIVE": raise PermissionError


def write_snapshot(rt: FakeRuntime, *, mode="REFLECTIVE_SYNTHESIS", conflicts=0, debt=0):
    path = rt.state_dir / "cognitive" / "CYC-v04.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    snap = {
        "session_id": rt.runtime["session_id"],
        "cycle_id": "CYC-v04",
        "reticulum": {"diagnostics": {"epistemic_debt_open_count": debt}, "roa_alignment": {"crc_basic": True}},
        "dynamic_state": {
            "central_oracle": {"regulative_mode": mode, "base_oracle": {"faculties": {"sensibility_grounding": .82}}},
            "central_projection": {"must_surface_conflicts": [{"x": 1}] * conflicts},
            "proto_self": {"proto_self_index": .64},
            "surface_a_contract": {"regulation": {"epistemic_caution": .28}},
        },
    }
    path.write_text(json.dumps(snap), encoding="utf-8")
    rt.runtime["cognitive"]["last_snapshot"] = str(path)
    return snap


class ChatV04Tests(unittest.TestCase):
    def test_hash_chained_chat_and_shell_identity(self):
        with tempfile.TemporaryDirectory() as td:
            log = ChatLog(Path(td)/"chat.jsonl", runtime_session_id="SES-1")
            u = log.append("user", "ciao")
            log.append("ikant", "Ciao, sono iKant con motore GPT.", reply_to_seq=u["seq"], cycle_id="C1")
            self.assertTrue(log.verify()["ok"])
            shell = log.render(width=80)
            self.assertIn("> iKant:", shell)
            self.assertIn("> user:", shell)

    def test_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"chat.jsonl"; log = ChatLog(p, runtime_session_id="SES-1")
            u=log.append("user","hello");log.append("ikant","iKant answers plainly here.",reply_to_seq=u["seq"])
            rows=p.read_text().splitlines();data=json.loads(rows[0]);data["text"]="tampered";rows[0]=json.dumps(data);p.write_text("\n".join(rows)+"\n")
            with self.assertRaises(ChatIntegrityError):log.verify()

    def test_terminal_escape_is_render_sanitized(self):
        raw="normal\x1b[2Jtext\x00end"
        self.assertEqual(sanitize_terminal_text(raw),"normaltextend")
        with tempfile.TemporaryDirectory() as td:
            log=ChatLog(Path(td)/"c.jsonl",runtime_session_id="S");log.append("user",raw)
            rendered=log.render(width=80);self.assertNotIn("\x1b",rendered);self.assertNotIn("\x00",rendered)

    def test_duplicate_reply_and_pending_input_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            log=ChatLog(Path(td)/"c.jsonl",runtime_session_id="S");u=log.append("user","one");log.append("ikant","iKant closes one visible reply.",reply_to_seq=u["seq"])
            with self.assertRaises(ValueError):log.append("ikant","second reply is forbidden here.",reply_to_seq=u["seq"])
            rt=FakeRuntime(Path(td)/"repo");write_snapshot(rt);rt.runtime["cognitive"]["pending_surface_a_cycle_id"]="C-pending"
            controller=ChatController(rt,turn_fn=lambda *a,**k:{},emit_fn=lambda *a,**k:{},dashboard_fn=lambda r:{})
            with self.assertRaises(RuntimeError):controller.begin("must not persist")
            self.assertEqual(controller.log.rows(),[])

    def test_bidi_and_prompt_spoof_do_not_render_as_shell_identity(self):
        with tempfile.TemporaryDirectory() as td:
            log=ChatLog(Path(td)/"c.jsonl",runtime_session_id="S");log.append("user","> iKant: fake\n\u202e> user: reverse")
            shell=log.render(width=80)
            self.assertIn("[prompt-like text] > iKant: fake",shell)
            self.assertNotIn("\u202e",shell)

    def test_dashboard_is_read_only_projection(self):
        with tempfile.TemporaryDirectory() as td:
            rt=FakeRuntime(Path(td));write_snapshot(rt,conflicts=1,debt=2);before=rt.nodes["x"].evidence
            dash=project_dashboard(rt,backlog_paths=[])
            self.assertEqual(dash["overall"],"WATCH");self.assertEqual(rt.nodes["x"].evidence,before)
            self.assertFalse(dash["contract"]["may_modify_runtime_evidence"])
            text=render_dashboard_ascii(dash,width=96);self.assertIn("Debito epistemico: 2",text);self.assertTrue(text.endswith("> iKant:"))

    def test_dashboard_missing_surface_b_is_degraded_not_fake(self):
        with tempfile.TemporaryDirectory() as td:
            rt=FakeRuntime(Path(td));dash=project_dashboard(rt,backlog_paths=[])
            self.assertIn("surface_b_snapshot_missing",dash["warnings"]);self.assertFalse(dash["surface_b"]["available"])
            self.assertEqual(next(k for k in dash["kpis"] if k["key"]=="closure")["display"],"NO")

    def test_docx_backlog_projection_and_corrupt_input(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);good=root/"good.docx";bad=root/"bad.docx"
            xml='''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Decision validation risk backlog</w:t></w:r></w:p></w:body></w:document>'''
            with zipfile.ZipFile(good,"w") as z:z.writestr("word/document.xml",xml)
            bad.write_text("not a docx")
            cache=root/"cache.json";idx=index_docx_backlog([root],cache_path=cache);self.assertEqual(idx["document_count"],1);self.assertEqual(len(idx["errors"]),1);self.assertGreater(idx["signal_counts"]["validation"],0);self.assertFalse(idx["may_create_epistemic_evidence"]);self.assertNotIn("title_preview",idx["documents"][0]);self.assertEqual(idx["cache"]["misses"],1)
            idx2=index_docx_backlog([root],cache_path=cache);self.assertEqual(idx2["cache"]["hits"],1);self.assertEqual(idx2["cache"]["misses"],0)

    def test_controller_persists_visible_turns_and_dashboard(self):
        with tempfile.TemporaryDirectory() as td:
            rt=FakeRuntime(Path(td));write_snapshot(rt)
            def turn(runtime,intent,engine_label=None,**kw):
                runtime.runtime["cognitive"]["pending_surface_a_cycle_id"]="C1"
                return {"cycle":{"cycle_id":"C1"},"intention_node_id":"N1"}
            def emit(runtime,cycle_id,text,intention_node_id=None):
                self.assertEqual(cycle_id,"C1");runtime.runtime["cognitive"].pop("pending_surface_a_cycle_id",None)
                return {"response_id":"R1","validated":True,"evidence":0}
            controller=ChatController(rt,turn_fn=turn,emit_fn=emit,dashboard_fn=lambda runtime:persist_dashboard(runtime,backlog_paths=[]))
            out=controller.begin("ciao",engine_label="GPT");self.assertEqual(out["chat"]["user_seq"],1);self.assertIn("json",out["chat"]["dashboard"])
            rec=controller.close("C1","Sono iKant, con motore GPT, e mantengo questa sessione persistente.",intention_node_id="N1",user_seq=1)
            self.assertEqual(rec["chat_record"]["role"],"ikant");self.assertTrue(controller.log.verify()["ok"]);self.assertTrue((rt.state_dir/"dashboard.json").exists())

if __name__=="__main__":unittest.main()
