from __future__ import annotations

import ast
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HTTP_SOURCES = [ROOT / "ikant" / name for name in ("local_http.py", "epistemic_http.py", "bootstrap_http.py", "reactive_http.py")]
EXPECTED_ROUTES = {
    "/api/v1/public", "/api/v1/state", "/api/v1/admission", "/api/v1/frame", "/api/v1/pair",
    "/api/v1/accept", "/api/v1/probe", "/api/v1/initialize", "/api/v1/frame/ack", "/api/v1/turn", "/api/v1/resume", "/api/v1/voice/transcribe",
    "/api/v2/shell/open", "/api/v2/shell/command", "/api/v2/shell/ack",
    "/api/v3/product/status", "/api/v3/product/retry", "/api/v3/voice/transcribe",
    "/api/v4/epistemic/index", "/api/v4/epistemic/cycle", "/api/v4/epistemic/artifact",
    "/api/v5/bootstrap/status", "/api/v5/bootstrap/events", "/api/v5/bootstrap/raw",
    "/api/v6/experience", "/api/v7/foundation", "/api/v7/config", "/api/v8/public", "/api/v9/work/current", "/api/v10/surface",
}
EXPECTED_REACTIVE_JS = {"app.js", "epistemic.js", "bootstrap.js", "surface-contract.js", "reactive-hybrid.js"}
REQUIRED_DOM_IDS = {"pair-panel", "pair-form", "active-panel", "turn-form", "intent", "send-button", "status-button", "inspector", "foundation-config-disclosure", "foundation-save", "released-panel", "resume-button", "command-palette", "semantic-window"}


def string_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def route_census() -> set[str]:
    routes = set()
    for path in HTTP_SOURCES:
        for value in string_literals(path):
            if re.fullmatch(r"/api/v\d+/[A-Za-z0-9._/-]+", value) and not value.endswith("/"):
                routes.add(value)
    return routes


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=set(); self.buttons=0; self.forms=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if attrs.get("id"): self.ids.add(attrs["id"])
        if tag=="button": self.buttons+=1
        if tag=="form": self.forms+=1


def dom_source_census() -> IdParser:
    p=IdParser(); p.feed((ROOT / "ikant" / "web" / "index.html").read_text(encoding="utf-8")); return p


def composed_asset_census() -> set[str]:
    text=(ROOT / "ikant" / "reactive_http.py").read_text(encoding="utf-8")
    return set(re.findall(r"assets_dir/'([^']+\.js)'", text))


def main() -> int:
    routes=route_census(); assets=composed_asset_census(); dom=dom_source_census(); errors=[]
    if routes != EXPECTED_ROUTES: errors.append({"route_missing":sorted(EXPECTED_ROUTES-routes),"route_unexpected":sorted(routes-EXPECTED_ROUTES)})
    if assets != EXPECTED_REACTIVE_JS: errors.append({"asset_missing":sorted(EXPECTED_REACTIVE_JS-assets),"asset_unexpected":sorted(assets-EXPECTED_REACTIVE_JS)})
    missing_dom=sorted(REQUIRED_DOM_IDS-dom.ids)
    if missing_dom or dom.buttons < 15 or dom.forms < 2: errors.append({"dom_missing":missing_dom,"buttons":dom.buttons,"forms":dom.forms})
    material={"routes":sorted(routes),"reactive_js":sorted(assets),"required_dom_ids":sorted(REQUIRED_DOM_IDS),"buttons":dom.buttons,"forms":dom.forms}
    receipt={"schema":"ikant-independent-surface-census/v1-test","status":"PASS" if not errors else "FAIL","independent_of_surface_manifest":True,"route_count":len(routes),"reactive_js_count":len(assets),"dom_required_count":len(REQUIRED_DOM_IDS),"material_sha256":hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode()).hexdigest(),"errors":errors,"epistemic_authority":0.0,"execution_authority":0.0}
    print(json.dumps(receipt,sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
