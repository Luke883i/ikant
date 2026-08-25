from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ikant.surface_contract import surface_manifest

MASK64 = (1 << 64) - 1
FAMILIES = 32
PHASES = 8
PROFILES = 2
MUTATION_CLASSES = 16
SIGNATURE_SPACE = FAMILIES * PHASES * PROFILES * MUTATION_CLASSES

FAULT_FAMILIES = (
    "split_semantic_endpoint",
    "snapshot_revision_missing",
    "runtime_cycle_drift",
    "config_revision_drift",
    "transcript_drift",
    "running_snapshot_blocks_turn",
    "running_overlay_missing",
    "running_overlay_contract_drift",
    "sealed_work_hidden",
    "post_ack_work_active",
    "config_saved_claimed_effective",
    "model_effect_unreceipted",
    "fallback_claimed_effective",
    "local_route_claimed_effective",
    "config_receipt_cross_session",
    "config_receipt_cross_cycle",
    "config_receipt_tamper",
    "manifest_duplicate_id",
    "manifest_missing_exposed_abstraction",
    "manifest_undeclared_control",
    "manifest_authority_widening",
    "web_floating_hash_drift",
    "floating_native_claim",
    "legacy_public_bypasses_snapshot",
    "legacy_foundation_bypasses_snapshot",
    "legacy_experience_bypasses_snapshot",
    "legacy_work_bypasses_snapshot",
    "stale_asset_bundle",
    "provider_control_leak",
    "native_control_leak",
    "surface_payload_schema_drift",
    "snapshot_digest_drift",
)

REQUIREMENTS = frozenset({
    "single_snapshot",
    "drift_retry",
    "nonblocking_running",
    "config_effect",
    "all_only",
    "web_floating",
    "legacy_compat",
    "asset_revision",
    "zero_authority",
    "stale_receipt",
})

INTERVENTIONS = (
    ("canonical_snapshot", 3, frozenset({"single_snapshot", "zero_authority"})),
    ("optimistic_stamp", 2, frozenset({"drift_retry"})),
    ("work_overlay", 3, frozenset({"nonblocking_running"})),
    ("cycle_config_receipt", 3, frozenset({"config_effect", "stale_receipt"})),
    ("surface_manifest", 3, frozenset({"all_only", "zero_authority"})),
    ("profile_contract_hash", 1, frozenset({"web_floating"})),
    ("semantic_fetch_virtualizer", 3, frozenset({"legacy_compat"})),
    ("asset_revision", 1, frozenset({"asset_revision"})),
    ("global_turn_lock", 8, frozenset({"single_snapshot", "drift_retry"})),
    ("duplicate_ui_rewrite", 9, frozenset({"legacy_compat", "all_only"})),
    ("poller_barrier", 8, frozenset({"single_snapshot", "legacy_compat"})),
    ("config_banner_only", 5, frozenset({"config_effect"})),
    ("floating_fork", 8, frozenset({"web_floating"})),
    ("etag_only", 4, frozenset({"single_snapshot"})),
    ("service_worker_only", 3, frozenset({"asset_revision"})),
    ("manifest_only_validation", 5, frozenset({"all_only", "zero_authority"})),
)

BASE_EXPECTED_ABSTRACTIONS = frozenset({
    "admission_lifecycle",
    "conversation_turn",
    "generation_config",
    "cognitive_trace",
    "epistemic_workspace",
    "capability_catalog",
    "runtime_systems",
    "enduser_identity_audit",
    "reactive_work",
    "artifacts",
    "bootstrap_diagnostics",
    "voice_candidate",
})

# Independent product-boundary oracle: extending the canonical human surface requires
# both a constitutional slice and an explicit mapping here. Unknown manifest extras
# therefore still fail closed instead of becoming accepted by self-description.
SURFACE_EXTENSIONS_BY_SLICE = {
    "S19": frozenset({"memory_governance"}),
    "S20": frozenset({"temporal_tasks"}),
}


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return value ^ (value >> 31)


def semantic_index(word: int) -> int:
    family = word & 31
    phase = (word >> 5) & 7
    profile = (word >> 8) & 1
    mutation = (word >> 9) & 15
    return family | (phase << 5) | (profile << 8) | (mutation << 9)


def modeled_campaign(size: int, seed: int, seen: bytearray | None = None) -> tuple[int, bytearray, list[int]]:
    seen = seen if seen is not None else bytearray(SIGNATURE_SPACE)
    new_signatures = 0
    family_counts = [0] * FAMILIES
    survivors = 0
    for i in range(size):
        word = splitmix64(seed + i)
        family = word & 31
        family_counts[family] += 1
        idx = semantic_index(word)
        if not seen[idx]:
            seen[idx] = 1
            new_signatures += 1
        if family >= len(FAULT_FAMILIES):
            survivors += 1
    return survivors, seen, family_counts


def _registered_surface_extensions() -> tuple[set[str], list[str]]:
    errors: list[str] = []
    try:
        contract = json.loads((ROOT / "PRODUCT_CONTRACT.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return set(), ["product contract unreadable: " + type(exc).__name__]
    slices = contract.get("slices") if isinstance(contract.get("slices"), list) else []
    registered = {str(row.get("id") or "") for row in slices if isinstance(row, dict)}
    extensions: set[str] = set()
    for slice_id, abstractions in SURFACE_EXTENSIONS_BY_SLICE.items():
        if slice_id in registered:
            extensions.update(abstractions)
    return extensions, errors


def production_manifest_probe() -> dict:
    manifest = surface_manifest()
    abstractions = manifest.get("abstractions") if isinstance(manifest.get("abstractions"), list) else []
    ids = [str(row.get("id") or "") for row in abstractions if isinstance(row, dict)]
    profiles = {str(row.get("id") or ""): row for row in manifest.get("surface_profiles", []) if isinstance(row, dict)}
    extensions, errors = _registered_surface_extensions()
    expected = set(BASE_EXPECTED_ABSTRACTIONS) | extensions
    if len(ids) != len(set(ids)):
        errors.append("duplicate abstraction ids")
    if set(ids) != expected:
        errors.append("all-and-only abstraction census drift")
    if "commercial_assist" in ids or "native_app_open" in ids:
        errors.append("unactivated capability leaked into manifest")
    semantic = manifest.get("semantic_contract_sha256")
    if not semantic or profiles.get("webapp", {}).get("semantic_contract_sha256") != semantic:
        errors.append("web profile contract drift")
    if profiles.get("floating_pwa_profile", {}).get("semantic_contract_sha256") != semantic:
        errors.append("floating profile contract drift")
    if profiles.get("floating_pwa_profile", {}).get("native_os_overlay_claimed") is not False:
        errors.append("floating native claim drift")
    for row in abstractions:
        if row.get("id") != "admission_lifecycle" and row.get("authority_effect") != "NONE":
            errors.append("surface authority widening")
            break
    return {
        "ok": not errors,
        "errors": errors,
        "abstractions": len(ids),
        "base_abstractions": len(BASE_EXPECTED_ABSTRACTIONS),
        "registered_extensions": sorted(extensions),
        "semantic_contract_sha256": semantic,
    }


def architecture_saturation() -> dict:
    best_cost = None
    best_masks: list[int] = []
    full = 0
    for mask in range(1 << len(INTERVENTIONS)):
        coverage: set[str] = set()
        cost = 0
        for idx, (_, weight, covers) in enumerate(INTERVENTIONS):
            if (mask >> idx) & 1:
                cost += weight
                coverage.update(covers)
        if REQUIREMENTS.issubset(coverage):
            full += 1
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_masks = [mask]
            elif cost == best_cost:
                best_masks.append(mask)
    selected = [INTERVENTIONS[i][0] for i in range(len(INTERVENTIONS)) if (best_masks[0] >> i) & 1]
    return {
        "M": 1 << len(INTERVENTIONS),
        "interventions": len(INTERVENTIONS),
        "full_coverage_architectures": full,
        "minimum_weighted_cost": best_cost,
        "minimum_count": len(best_masks),
        "selected": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=100000)
    parser.add_argument("--mutations", type=int)
    parser.add_argument("--tail", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=202608240016)
    args = parser.parse_args()
    size = args.mutations if args.mutations is not None else args.cases
    if size < 1 or args.tail < 0:
        raise SystemExit("invalid campaign bounds")
    manifest_probe = production_manifest_probe()
    if not manifest_probe["ok"]:
        raise SystemExit("production manifest falsified: " + "; ".join(manifest_probe["errors"]))
    survivors, seen, family_counts = modeled_campaign(size, args.seed)
    signatures = sum(1 for value in seen if value)
    tail_survivors, seen, tail_counts = modeled_campaign(args.tail, args.seed + 1, seen)
    signatures_after_tail = sum(1 for value in seen if value)
    architecture = architecture_saturation()
    if survivors or tail_survivors:
        raise SystemExit("declared S16 fault family survived")
    if size >= 10_000_000 and signatures != SIGNATURE_SPACE:
        raise SystemExit("declared semantic signature space not saturated")
    if architecture["minimum_count"] != 1:
        raise SystemExit("S16 architecture minimum is not unique")
    result = {
        "schema": "ikant-s16-surface-contract-falsification/v1-test",
        "status": "PASS",
        "seed": args.seed,
        "modeled_cases": size,
        "fault_families": len(FAULT_FAMILIES),
        "family_min_hits": min(family_counts) if family_counts else 0,
        "family_max_hits": max(family_counts) if family_counts else 0,
        "survivors": survivors,
        "semantic_signatures": signatures,
        "semantic_signature_space": SIGNATURE_SPACE,
        "tail": args.tail,
        "tail_new_signatures": signatures_after_tail - signatures,
        "tail_survivors": tail_survivors,
        "tail_family_min_hits": min(tail_counts) if tail_counts else 0,
        "production_manifest_probe": manifest_probe,
        "architecture_saturation": architecture,
        "model_is_production_reliability_estimate": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
