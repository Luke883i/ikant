from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .local_security import PairingSession, allowed_hostnames, origin_allowed
from .local_web_host import LocalWebHostAdapter
from .model_broker import LocalModelBroker, LocalModelError
from .voice_input import LocalVoiceInputBroker, LocalVoiceError
from .web_frame import wrap_prepared_frame, validate_web_ack

LOCAL_APP_SCHEMA = "ikant-local-embodiment/v0.20-test"
_MAX_JSON = 128 * 1024
_MAX_AUDIO = 8 * 1024 * 1024


class LocalAppError(RuntimeError):
    pass


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _read_json(handler: BaseHTTPRequestHandler, *, limit: int = _MAX_JSON) -> dict[str, Any]:
    try:
        size = int(handler.headers.get("Content-Length") or "0")
    except ValueError as exc:
        raise LocalAppError("invalid Content-Length") from exc
    if size <= 0 or size > limit:
        raise LocalAppError("request body outside bound")
    raw = handler.rfile.read(size)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise LocalAppError("invalid JSON request") from exc
    if not isinstance(payload, dict):
        raise LocalAppError("JSON request must be object")
    return payload


def _runtime_active(root: Path) -> bool:
    try:
        return json.loads((root / ".ikant" / "runtime.json").read_text(encoding="utf-8")).get("status") == "ACTIVE"
    except Exception:
        return False


def _operational_fallback(user_text: str) -> str:
    lower = " " + str(user_text).casefold() + " "
    italian = any(token in lower for token in (" che ", " non ", " per ", " come ", " puoi ", " vorrei ", " fai ", " con "))
    if italian:
        return "Il motore linguistico locale non ha prodotto una risposta valida; nessuna azione materiale è stata eseguita e puoi riprovare il turno."
    return "The local language engine did not produce a valid reply; no material action was executed, and you can retry this turn."


class LocalEmbodimentService:
    """Version-neutral service boundary used by the S2 web host.

    ACTIVE human output remains the exact v0.12 sealed dashboard text. The web shell and voice
    controls are input affordances, not additional cognitive surfaces.
    """

    def __init__(self, root: str | Path, *, model: LocalModelBroker, voice: LocalVoiceInputBroker):
        self.root = Path(root).resolve()
        self.model = model
        self.voice = voice
        self.web_adapter: LocalWebHostAdapter | None = None
        self._web_certification: dict[str, Any] | None = None
        self._lock = threading.RLock()

    def bind_web_adapter(self, adapter: LocalWebHostAdapter) -> None:
        self.web_adapter = adapter
        self._web_certification = None

    def require_web_conformance(self) -> dict[str, Any]:
        if self.web_adapter is None:
            raise LocalAppError("local web host adapter not bound")
        if self._web_certification is None:
            from .host_negotiation import certify_host
            self._web_certification = certify_host(
                self.web_adapter,
                profiles=["HUMAN_EGRESS"],
                persist_path=self.state_dir / "local-web-conformance.json",
            )
        negotiation = (self._web_certification.get("negotiations") or {}).get("HUMAN_EGRESS") or {}
        if negotiation.get("status") != "CONFORMING":
            raise LocalAppError("local web HUMAN_EGRESS profile is not conforming")
        return self._web_certification

    @property
    def contract_path(self) -> Path:
        return self.root / "IKANT_ACCESS_CONTRACT.md"

    @property
    def state_dir(self) -> Path:
        return self.root / ".ikant"

    def contract_text(self) -> str:
        return self.contract_path.read_text(encoding="utf-8")

    def lifecycle(self) -> dict[str, Any]:
        if _runtime_active(self.root):
            try:
                from .runtime import Runtime
                from .session_egress import existing_runtime_egress

                rt = Runtime(self.state_dir)
                try:
                    guard = existing_runtime_egress(rt)
                    egress = guard.state.value if guard else "MISSING"
                finally:
                    rt.close()
            except Exception:
                egress = "INTEGRITY_CHECK_REQUIRED"
            return {"schema": LOCAL_APP_SCHEMA, "state": "ACTIVE", "egress": egress}
        from .admission import load_probe, load_receipt, validate_receipt

        contract = self.contract_text()
        receipt = load_receipt(self.state_dir)
        ok, _ = validate_receipt(receipt, contract)
        if not ok:
            state = "AWAITING_ACCEPTANCE"
        else:
            probe = load_probe(self.state_dir)
            state = "PROBED" if probe.get("overall") == "READY" and probe.get("consumed") is False else "ACCEPTED"
        return {
            "schema": LOCAL_APP_SCHEMA,
            "state": state,
            "contract_sha256": _sha_text(contract),
            "model": self.model.status(),
            "voice": self.voice.status(),
        }

    def admission_view(self) -> dict[str, Any]:
        if _runtime_active(self.root):
            raise LocalAppError("admission view unavailable after ACTIVE")
        text = self.contract_text()
        return {
            "schema": LOCAL_APP_SCHEMA,
            "state": self.lifecycle()["state"],
            "terms": text,
            "terms_sha256": _sha_text(text),
            "acceptance_phrase": "I ACCEPT",
        }

    def accept(self, phrase: str, presented_terms_sha256: str) -> dict[str, Any]:
        with self._lock:
            if _runtime_active(self.root):
                raise LocalAppError("accept unavailable after ACTIVE")
            from .admission import issue_receipt, save_receipt

            contract = self.contract_text()
            receipt = issue_receipt(contract, str(phrase), presented_terms_sha256=str(presented_terms_sha256))
            save_receipt(self.state_dir, receipt)
            return {"schema": LOCAL_APP_SCHEMA, "state": "ACCEPTED", "receipt_id": receipt.get("receipt_id")}

    def probe(self) -> dict[str, Any]:
        with self._lock:
            if _runtime_active(self.root):
                raise LocalAppError("probe unavailable after ACTIVE")
            from .admission import load_receipt, probe, save_probe, validate_receipt

            contract = self.contract_text()
            ok, errors = validate_receipt(load_receipt(self.state_dir), contract)
            if not ok:
                raise PermissionError("; ".join(errors))
            result = probe(self.root, self.state_dir, contract)
            save_probe(self.state_dir, result)
            return result

    def initialize(self) -> dict[str, Any]:
        with self._lock:
            if _runtime_active(self.root):
                return self.frame()
            from .human_dashboard import persist_dashboard
            from .runtime import Runtime
            from .session_egress import activate_runtime_egress
            from .session_host import prepare_human_frame

            self.require_web_conformance()
            rt = Runtime.initialize(self.state_dir, self.contract_text())
            try:
                activate_runtime_egress(rt, initialization=True)
                dash = persist_dashboard(rt)
                prepared = prepare_human_frame(rt, dash, kind="INITIALIZE", notice="iKant ACTIVE. Canale umano vincolato alla dashboard.")
                return wrap_prepared_frame(prepared)
            finally:
                rt.close()

    def frame(self) -> dict[str, Any]:
        with self._lock:
            self.require_web_conformance()
            from .runtime import Runtime
            from .session_egress import ExitState, existing_runtime_egress
            from .session_host import recover_prepared_frame, prepare_human_frame
            from .human_dashboard import persist_dashboard

            rt = get_runtime(self.state_dir)
            try:
                guard = existing_runtime_egress(rt)
                if guard.state in {ExitState.FRAME_PENDING, ExitState.RELEASE_PENDING}:
                    prepared = recover_prepared_frame(rt)
                    if not prepared:
                        raise LocalAppError("pending egress has no recoverable frame")
                    return wrap_prepared_frame(prepared)
                if guard.state == ExitState.RELEASED:
                    return {"schema": LOCAL_APP_SCHEMA, "released": True, "state": "RELEASED"}
                gard.require_locked()
                prepared = prepare_human_frame(rt, persist_dashboard(rt), kind="WEB_DASHBOARD")
                return wrap_prepared_frame(prepared)
            finally:
                rt.close()

    def acknowledge(self, web_ack: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.require_web_conformance()
            from .runtime import Runtime
            from .session_host import recover_prepared_frame, acknowledge_prepared_frame

            rt = Runtime(self.state_dir)
            try:
                prepared = recover_prepared_frame(rt)
                if not prepared:
                    raise LocalAppError("acknowledgement requires a pending sealed frame")
                frame = wrap_prepared_frame(prepared)
                ok, errors = validate_web_ack(frame, web_ack)
                if not ok:
                    raise LocalAppError("web frame acknowledgement mismatch: " + "; ".join(errors))
                acknowledge_prepared_frame(rt, prepared, web_ack["visible_text"])
                return {"schema": LOCAL_APP_SCHEMA, "acknowledged": True, "delivery_state": existing_runtime_egress(rt).state.value}
            finally:
                rt.close()

    def turn(self, user_text: str) -> dict[str, Any]:
        with self._lock:
            self.require_web_conformance()
            text = str(user_text)
            if not text.strip() or len(text.encode("utf-8")) > 65536:
                raise LocalAppError("intent outside bound")
            from .runtime import Runtime
            from .session_host import DashboardOnlySession, prepare_human_frame
            from .human_dashboard import persist_dashboard
            from .runtime_host import conforming_turn
            from .surfaces import validate_surface_a

            rt = Runtime(self.state_dir)
            try:
                session = DashboardOnlySession(rt)
                begin = session.begin_user(text, engine_label=self.model.model)
                if begin.get("control") != "TURN":
                    human = begin.get("human")
                    if not human:
                        raise LocalAppError("control transition missing human frame")
                    return wrap_prepared_frame(human)
                out = begin["machine"]
                cycle_id = str(out["cycle"]["cycle_id"])
                intention_node_id = out.get("intention_node_id")
                contract = out["surface_a_contract"]
                try:
                    if not self.model.health():
                        raise LocalModelError("local model server unavailable")
                    surface_a = self.model.complete_surface_a(contract, text, validator=validate_surface_a)
                except LocalModelError:
                    surface_a = _operational_fallback(text)
                    ok, errors = validate_surface_a(surface_a)
                    if not ok:
                        raise LocalAppError("operational fallback failed: " + "; ".join(errors))
                prepared = session.finalize(cycle_id, surface_a, intention_node_id=intention_node_id)
                return wrap_prepared_frame(prepared)
            finally:
                rt.close()

    def notice(self, message: str, *, kind: str = "LOCAL_WEB_NOTICE") -> dict[str, Any]:
        with self._lock:
            from .runtime import Runtime
            from .human_dashboard import persist_dashboard
            from .session_host import prepare_human_frame

            rt = Runtime(self.state_dir)
            try:
                self.require_web_conformance()
                prepared = prepare_human_frame(rt, persist_dashboard(rt), kind=kind, notice=str(message))
                return wrap_prepared_frame(prepared)
            finally:
                rt.close()

    def resume(self, user_text: str) -> dict[str, Any]:
        with self._lock:
            self.require_web_conformance()
            from .runtime import Runtime
            from .session_host import DashboardOnlySession

            rt = Runtime(self.state_dir)
            try:
                session = DashboardOnlySession(rt)
                prepared = session.resume_frame(str(user_text))
                return wrap_prepared_frame(prepared)
            finally:
                rt.close()

    def transcribe(self, audio: bytes, content_type: str) -> dict[str, Any]:
        return self.voice.transcribe(audio, content_type)


def make_handler(service: LocalEmbodimentService, pairing: PairingSession, *, assets_dir: Path, allowed_hosts: frozenset[str]):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _security_headers(self, *, content_type: str = "application/json; charset=utf-8") -> None:
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
                "img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; font-src 'none'",
            )

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(int(status))
            self._security_headers()
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _empty(self, status: int) -> None:
            self.send_response(int(status))
            self._security_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _error(self, status: int, message: str) -> None:
            if _runtime_active(service.root):
                self._empty(status)
            else:
                self._json(status, {"schema": LOCAL_APP_SCHEMA, "error": str(message)})

        def _guard(self, *, auth: bool = True, origin: bool = False) -> bool:
            host_header = str(self.headers.get("Host") or "").strip().lower()
            if host_header not in allowed_hosts:
                self._error(421, "host not allowed")
                return False
            if origin and not origin_allowed(self.headers.get("Origin"), host_header):
                self._error(403, "origin not allowed")
                return False
            if auth and not pairing.authenticate(self.headers.get("Authorization")):
                self._error(401, "pairing authentication required")
                return False
            return True

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path.startswith("/api/"):
                if path == "/api/v1/public":
                    if not self._guard(auth=False):
                        return
                    self._json(200, pairing.public_status())
                    return
                if not self._guard():
                    return
                try:
                    if path == "/api/v1/state":
                        self._json(200, service.lifecycle())
                    elif path == "/api/v1/admission":
                        self._json(200, service.admission_view())
                    elif path == "/api/v1/frame":
                        self._json(200, service.frame())
                    else:
                        self._error(404, "unknown API route")
                except PermissionError as exc:
                    self._error(403, str(exc))
                except Exception as exc:
                    self._error(409, str(exc))
                return
            if not self._guard(auth=Falsi:
                return
            name = "index.html" if path in {"", "/"} else path.lstrip("/")
            if name not in {"index.html", "app.js", "styles.css", "manifest.webmanifest", "sw.js"}:
                self._error(404, "asset not found")
                return
            file = assets_dir / name
            if not file.is_file():
                self._error(404, "asset missing")
                return
            raw = file.read_bytes()
            content_type = mimetypes.guess_type(str(file))[0] or "application/octet-stream"
            if name.endswith(".js"):
                content_type = "text/javascript; charset=utf-8"
            elif name.endswith(".html"):
                content_type = "text/html; charset=utf-8"
            elif name.endswith(".css"):
                content_type = "text/css; charset=utf-8"
            elif name.endswith(".webmanifest"):
                content_type = "application/manifest+json; charset=utf-8"
          self.send_response(200)
            self._security_headers(content_type=content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/api/v1/pair":
                if not self._guard(auth=False, origin=True):
                    return
                try:
                    body = _read_json(self)
                    token = pairing.pair(str(body.get("code") or ""))
                    self._json(200, {"schema": LOCAL_APP_SCHEMA,"paired": True, "bearer_token": token})
                except PermissionError as exc:
                    self._error(403, str(exc))
                except Exception as exc:
                    self._error(400, str(exc))
                return
            if not self._guard(origin=True):
                return
            try:
                if path == "/api/v1/voice/transcribe":
                    try:
                        size = int(self.headers.get("Content-Length") or "0")
                    except ValueError as exc:
                        raise LocalAppError("invalid Content-Length") from exc
                    if size <= 0 or size > _MAX_AUDIO:
                        raise LocalAppError("audio body outside bound")
                    audio = self.rfile.read(size)
                    self._json(200, service.transcribe(audio, self.headers.get("Content-Type") or ""))
                    return
                body = _read_json(self)
                if path == "/api/v1/accept":
                    out = service.accept(str(body.get("phrase") or ""), str(body.get("presented_terms_sha256") or ""))
                elif path == "/api/v1/probe":
                    out = service.probe()
                elif path == "/api/v1/initialize":
                    out = service.initialize()
                elif path == "/api/v1/frame/ack":
                    out = service.acknowledge(body)
                elif path == "/api/v1/turn":
                    out = service.turn(str(body.get("text") or ""))
                elif path == "/api/v1/resume":
                    out = service.resume(str(body.get("text") or ""))
                else:
                    self._error(404, "unknown API route")
                    return
                self._json(200, out)
            except (PermissionError, LocalVoiceError) as exc:
                if _runtime_active(service.root):
                    try:
                        self._json(200, service.notice(str(exc), kind="LOCAL_INPUT_ERROR"))
                    except Exception:
                        self._error(403, "local input rejected")
                else:
                    self._error(403, str(exc))
            except Exception as exc:
                if _runtime_active(service.root):
                    try:
                        self._json(200, service.notice(str(exc), kind="LOCAL_RUNTIME_ERROR"))
                    except Exception:
                        self._error(409, "local runtime unavailable")
                else:
                    self._error(409, str(exc))

    return Handler


def build_server(
    service: LocalEmbodimentService,
    *,
    host: str,
    port: int,
    pairing: PairingSession | None = None,
    assets_dir: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[ThreadingHTTPServer, PairingSession]:
    pairing = pairing or PairingSession.create()
    assets = Path(assets_dir) if assets_dir is not None else Path(__file__).with_name("web")
    hosts = allowed_hostnames(int(port), bind_host=host, env=env)
    handler = make_handler(service, pairing, assets_dir=assets, allowed_hosts=hosts)
    server = ThreadingHTTPServer((host, int(port)), handler)
    server.daemon_threads = True
    effective_port = int(server.server_address[1])
    effective_hosts = allowed_hostnames(effective_port, bind_host=host, env=env)
    if effective_hosts != hosts:
        server.RequestHandlerClass = make_handler(service, pairing, assets_dir=assets, allowed_hosts=effective_hosts)
    service.bind_web_adapter(LocalWebHostAdapter(str(host), effective_port, tuple(sorted(effective_hosts)))
    return server, pairing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ikant-web")
    ap.add_argument("--host")
    ap.add_argument("--port", type=int, default=int(os.environ.get("IKANT_PORT", "8765")))
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args(argv)
    codespaces = str(os.environ.get("CODESPACES") or "").lower() == "true"
    host = args.host or ("0.0.0.0" if codespaces else "127.0.0.1")
    root = Path.cwd()
    from .store import acquire_writer_lock

    lock = acquire_writer_lock(root / ".ikant" / "local-app.writer.lock")
    model = LocalModelBroker(
        os.environ.get("IKANT_MODEL_ENDPOINT", "http://127.0.0.1:8080/v1/chat/completions"),
        model=os.environ.get("IKANT_MODEL_NAME", "Qwen3.5-0.8B"),
    )
    voice = LocalVoiceInputBroker(os.environ.get("IKANT_STT_ENDPOINT"))
    service = LocalEmbodimentService(root, model=model, voice=voice)
    server, pairing = build_server(service, host=host, port=args.port)
    local_url = f"http://localhost:{args.port}/"
    pair_url = local_url + "#pair=" + pairing.code
    print(f"iKant Local Embodiment: {local_url}", flush=True)
    print(f"Pairing code: {pairing.code}", flush=True)
    if codespaces:
        print("Codespaces: port forwarding remains private by default; open the forwarded port and enter the pairing code.", flush=True)
    elif not args.no_open:
        webbrowser.open(pair_url, new=2)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        lock.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
