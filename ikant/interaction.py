from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass

_WORD_RE = re.compile(r"\b[\w'’]+\b", re.UNICODE)
_LIST_RE = re.compile(r"^\s*(?:[-*+•‣▪◦]\s+|\d+[.)]\s+)")

IDENTITY_PATTERNS = (
    r"\bchi\s+sei\b", r"\bcosa\s+sei\b", r"\bcome\s+ti\s+chiami\b",
    r"\bwho\s+are\s+you\b", r"\bwhat\s+are\s+you\b", r"\bwhat(?:'s|\s+is)\s+your\s+name\b",
)
ENGINE_PATTERNS = (
    r"\bche\s+modello\b", r"\bquale\s+modello\b", r"\bche\s+motore\b",
    r"\bwhat\s+model\b", r"\bwhich\s+model\b", r"\bwhat\s+engine\b",
)
COMPLEXITY_MARKERS = {
    "audit", "analizza", "analisi", "confronta", "globale", "locale", "etico", "etica", "strategia", "architettura",
    "simulate", "simulation", "stress", "governance", "epistemic", "reticolo", "repository", "causale", "causal",
}


@dataclass(frozen=True)
class InteractionProfile:
    kind: str
    word_budget: int
    identity_first: bool
    engine_disclosure: bool
    surface_b_required: bool


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def classify_interaction(intent: str) -> InteractionProfile:
    n = _norm(intent)
    identity = any(re.search(p, n) for p in IDENTITY_PATTERNS)
    engine = any(re.search(p, n) for p in ENGINE_PATTERNS)
    if identity or engine:
        return InteractionProfile("identity", 55, True, True, True)
    words = n.split()
    markers = len(set(words) & COMPLEXITY_MARKERS)
    if len(words) <= 12 and markers == 0:
        return InteractionProfile("simple", 80, False, False, True)
    if len(words) <= 45 and markers <= 2:
        return InteractionProfile("standard", 160, False, False, True)
    return InteractionProfile("complex", 280, False, False, True)


def build_interaction_contract(intent: str, *, engine_label: str | None = None) -> dict:
    profile = classify_interaction(intent)
    engine = (engine_label or "").strip() or "UNDECLARED_HOST_ENGINE"
    return {
        "schema": "ikant-interaction-contract/v0.3-test",
        "intent_sha256": hashlib.sha256(intent.encode()).hexdigest(),
        "profile": asdict(profile),
        "identity": {
            "interface_identity": "iKant",
            "engine_label": engine,
            "ordering": "interface_then_engine",
            "host_is_execution_engine_not_primary_interface": True,
            "accepted_hierarchy_required": True,
        },
        "surface_policy": {
            "surface_a_only_in_chat": True,
            "surface_b_required_per_substantive_turn": profile.surface_b_required,
            "surface_b_is_audit_telemetry_not_chain_of_thought": True,
            "min_words": 5,
            "max_words": 500,
            "turn_word_budget": profile.word_budget,
            "headings": False,
            "lists": False,
            "tables": False,
            "code_blocks": False,
        },
    }


def _format_errors(text: str, budget: int) -> list[str]:
    errors: list[str] = []
    words = _WORD_RE.findall(text)
    if not 5 <= len(words) <= 500:
        errors.append("surface_word_bounds")
    if len(words) > budget:
        errors.append("turn_word_budget")
    lines = text.splitlines()
    if any(line.lstrip().startswith("#") for line in lines) or any(re.fullmatch(r"\s*(?:={3,}|-{3,})\s*", line) for line in lines):
        errors.append("headings_forbidden")
    if any(_LIST_RE.match(line) for line in lines) or re.search(r"<(?:ul|ol|li)\b", text, re.I):
        errors.append("lists_forbidden")
    if re.search(r"<table\b", text, re.I) or any("|" in line and line.count("|") >= 2 for line in lines):
        errors.append("tables_forbidden")
    if "```" in text or any(line.startswith("    ") and line.strip() for line in lines):
        errors.append("code_blocks_forbidden")
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if len(paragraphs) > 4:
        errors.append("paragraph_budget")
    return errors


def validate_interaction_surface(text: str, contract: dict) -> tuple[bool, list[str]]:
    profile = contract["profile"]
    identity = contract["identity"]
    errors = _format_errors(text, int(profile["word_budget"]))
    n = _norm(text)
    if profile.get("identity_first"):
        ik = n.find("ikant")
        if ik < 0:
            errors.append("identity_ikant_missing")
        engine_label = identity.get("engine_label", "UNDECLARED_HOST_ENGINE")
        if engine_label == "UNDECLARED_HOST_ENGINE":
            engine_positions = [p for p in (n.find("motore"), n.find("engine"), n.find("modello"), n.find("model")) if p >= 0]
            if not engine_positions:
                errors.append("engine_disclosure_missing")
            engine_pos = min(engine_positions) if engine_positions else -1
        else:
            en = _norm(engine_label)
            engine_pos = n.find(en)
            if engine_pos < 0:
                errors.append("engine_label_missing")
        if ik >= 0 and engine_pos >= 0 and ik > engine_pos:
            errors.append("identity_order_violation")
        if re.match(r"^(sono|io sono|i am|im)\s+(chatgpt|gpt|un modello|a model)\b", n):
            errors.append("host_claimed_primary_identity")
    return not errors, list(dict.fromkeys(errors))


def validate_turn(intent: str, response: str, *, engine_label: str | None = None) -> dict:
    contract = build_interaction_contract(intent, engine_label=engine_label)
    ok, errors = validate_interaction_surface(response, contract)
    return {"ok": ok, "errors": errors, "contract": contract}
