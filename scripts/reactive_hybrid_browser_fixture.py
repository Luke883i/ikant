from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ikant.reactive_http import build_server


class SlowTurnFixtureService:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.web_adapter = None

    def bind_web_adapter(self, adapter) -> None:
        self.web_adapter = adapter

    def shell_command(self, body):
        time.sleep(1.25)
        return {
            "schema": "ikant-reactive-browser-fixture/v1-test",
            "frame": {
                "receipt": {
                    "cycle_id": "cycle-reactive-browser",
                }
            },
        }

    def shell_ack(self, body):
        return {"acknowledged": True}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ikant-reactive-browser-") as tmp:
        root = Path(tmp).resolve()
        state = root / ".ikant"
        state.mkdir(parents=True, exist_ok=True)
        (state / "runtime.json").write_text(
            json.dumps({"status": "ACTIVE", "session_id": "browser-s15bis"}),
            encoding="utf-8",
        )
        service = SlowTurnFixtureService(root)
        server, pairing = build_server(
            service,
            host="127.0.0.1",
            port=0,
            assets_dir=ROOT / "ikant" / "web",
        )
        print(
            json.dumps(
                {
                    "schema": "ikant-reactive-browser-fixture/v1-test",
                    "port": int(server.server_address[1]),
                    "pairing_code": pairing.code,
                }
            ),
            flush=True,
        )
        try:
            server.serve_forever(poll_interval=0.05)
        finally:
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
