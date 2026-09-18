"""VT08 Index Three-Memory Brain V2 with full CIBO index dossiers.

V2 upgrades only the Market Memory domain. Strategy Identity remains the frozen
VT08 V7 contract and Trader Experience remains the validated VT08-specific
2,294-episode dossier. Full CIBO market dossiers are independent of VT08
outcomes and remain E1 association-only research memory.

No trading decision, target, stop, trailing, rearm, specialist freeze, holdout
opening, or execution authority is created by this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.cibo_executive_memory import (
    CiboMemoryFreshness,
    CiboMemoryFreshnessState,
    CiboMemoryItem,
    CiboMemoryKind,
    CiboMemoryProvenance,
    CiboMemorySourceRef,
    CiboMemoryStore,
)
from qore.infrastructure.trader_lab import vt08_index_three_memory_brain_v1 as v1
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.kernel.result import Success
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef

IDENTITY = "VT08_INDEX_THREE_MEMORY_BRAIN_V2_FULL_CIBO"
FULL_MARKET_PACKAGE_IDENTITY = "CIBO_INDEX_MARKET_INTELLIGENCE_DOSSIER_V1"
FULL_MARKET_RUN_ID = 35300432246
FULL_MARKET_GIT_SHA = "3ee6b4786ce42bbfcdbd3a3f3572d3f485cd7165"
FULL_MARKET_ARTIFACT_ID = 10529467508
FULL_MARKET_ARTIFACT_DIGEST = (
    "sha256:604a7d324842b46874179a39567b2cc982e03564ac18bfb3046f8e511dfe6a72"
)
FULL_MARKET_EFFECTIVE_AT = datetime(2026, 9, 18, 2, 48, 7, tzinfo=UTC)
RECORDED_AT = datetime(2026, 9, 18, 2, 50, 0, tzinfo=UTC)

EXPECTED_DOSSIER_SHA256 = {
    "NAS100": "93cf657be391e8d21c2ea98c7c75f4bd9262227c0ac20c02312e1c328eddf3dc",
    "SP500": "68cee81b1d4fd6ee4bd8fcd122d1eb7148f6c06ffe2f013360f730f60ee81c24",
    "US30": "57d42455a393b271571f9c5c5a04bcbf309d65e20cfb4be3e73d194b7331fa0f",
}
EXPECTED_MARKET = {
    "NAS100": (701457, 110471, 39060),
    "SP500": (693064, 102863, 31445),
    "US30": (700856, 109341, 38053),
}


@dataclass(frozen=True, slots=True)
class Vt08IndexSituationInput:
    symbol: str
    side: str
    anchor_hour_new_york: int
    weekday_new_york: str
    session: str
    model_kind: str
    poi_kind: str
    prior_h4_range_regime: str
    prior_body_alignment: str | None = None
    fvg_after_raid: bool | None = None

    def __post_init__(self) -> None:
        if self.symbol not in v1.SYMBOLS:
            raise ValueError(f"unsupported VT08 Index symbol: {self.symbol}")
        if self.side not in {"long", "short"}:
            raise ValueError(f"unsupported VT08 Index side: {self.side}")


@dataclass(frozen=True, slots=True)
class Vt08IndexSituationModel:
    observation: Vt08IndexSituationInput
    strategy_memory: dict[str, Any]
    full_market_memory: dict[str, Any]
    market_dimensions: tuple[tuple[str, str, dict[str, Any]], ...]
    cross_index_market_memory: dict[str, Any]
    trader_experience_memory: dict[str, Any]
    experience_dimensions: tuple[tuple[str, str, dict[str, Any]], ...]
    cross_index_experience_memory: dict[str, Any]
    unknown_dimensions: tuple[str, ...]
    market_memory_status: str
    evidence_tier: str
    decision_authority: bool
    automatic_rule_promotion: bool


def _single(root: Path, name: str) -> Path:
    paths = list(root.rglob(name))
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {name} under {root}, got {len(paths)}")
    return paths[0]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object in {path}")
    return cast(dict[str, Any], payload)


def _int(value: object) -> int:
    return int(str(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_full_market_memory(
    root: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    package_path = _single(root, "CIBO_INDEX_MARKET_INTELLIGENCE_PACKAGE_V1.json")
    package = _read_json(package_path)
    if package.get("identity") != FULL_MARKET_PACKAGE_IDENTITY:
        raise ValueError("unexpected full CIBO index package identity")
    if package.get("evidence_tier") != "E1_ASSOCIATION_ONLY":
        raise ValueError("full CIBO index evidence tier drift")
    if not bool(package.get("full_market_memory_ready")):
        raise ValueError("full CIBO index package is not memory-ready")
    if bool(package.get("vt08_outcomes_used")):
        raise ValueError("general CIBO market memory is contaminated by VT08 outcomes")
    if bool(package.get("rule_promotion_allowed")):
        raise ValueError("full CIBO index package unexpectedly allows rule promotion")
    if bool(package.get("fresh_holdout_opened")):
        raise ValueError("full CIBO index package unexpectedly opened fresh holdout")
    expected_total_m5 = sum(values[0] for values in EXPECTED_MARKET.values())
    expected_total_events = sum(values[1] for values in EXPECTED_MARKET.values())
    expected_total_departures = sum(values[2] for values in EXPECTED_MARKET.values())
    if _int(package.get("total_retained_m5_bars", 0)) != expected_total_m5:
        raise ValueError("full CIBO retained M5 population drift")
    if _int(package.get("total_behavior_events", 0)) != expected_total_events:
        raise ValueError("full CIBO behavior population drift")
    if _int(package.get("total_resolved_departures", 0)) != expected_total_departures:
        raise ValueError("full CIBO departure population drift")

    package_manifests = cast(dict[str, Any], package.get("market_manifests", {}))
    dossiers: dict[str, dict[str, Any]] = {}
    for symbol in v1.SYMBOLS:
        code = symbol.lower()
        path = _single(root, f"{code}-market-intelligence-dossier-v1.json")
        manifest = cast(dict[str, Any], package_manifests.get(symbol))
        if not manifest:
            raise ValueError(f"missing full CIBO package manifest for {symbol}")
        expected_sha = EXPECTED_DOSSIER_SHA256[symbol]
        if manifest.get("dossier_sha256") != expected_sha:
            raise ValueError(f"full CIBO manifest dossier digest drift for {symbol}")
        if _sha256(path) != expected_sha:
            raise ValueError(f"full CIBO dossier bytes drift for {symbol}")
        dossier = _read_json(path)
        expected_m5, expected_events, expected_departures = EXPECTED_MARKET[symbol]
        if dossier.get("identity") != f"CIBO_{symbol}_MARKET_INTELLIGENCE_DOSSIER_V1":
            raise ValueError(f"full CIBO dossier identity drift for {symbol}")
        if dossier.get("symbol") != symbol:
            raise ValueError(f"full CIBO dossier symbol drift for {symbol}")
        if dossier.get("memory_role") != (
            "general-market-memory-independent-of-vt08-outcomes"
        ):
            raise ValueError(f"full CIBO memory role drift for {symbol}")
        if dossier.get("evidence_tier") != "E1_ASSOCIATION_ONLY":
            raise ValueError(f"full CIBO evidence tier drift for {symbol}")
        if bool(dossier.get("rule_promotion_allowed")):
            raise ValueError(f"full CIBO dossier promotes rules for {symbol}")
        if _int(dossier.get("retained_m5_bars", 0)) != expected_m5:
            raise ValueError(f"full CIBO M5 count drift for {symbol}")
        if _int(dossier.get("behavior_events", 0)) != expected_events:
            raise ValueError(f"full CIBO event count drift for {symbol}")
        if _int(dossier.get("resolved_departures", 0)) != expected_departures:
            raise ValueError(f"full CIBO departure count drift for {symbol}")
        target_v2 = cast(dict[str, Any], dossier["target_destination_v2"])
        target_summary = cast(dict[str, Any], target_v2["summary"])
        if bool(target_summary.get("complete_all_dol_claim")):
            raise ValueError(f"full CIBO dossier overclaims DOL coverage for {symbol}")
        cross = cast(dict[str, Any], dossier["cross_index"])
        if bool(cross.get("causal_leader_claim")):
            raise ValueError(f"full CIBO dossier overclaims cross-index causality for {symbol}")
        dossiers[symbol] = dossier
    return package, dossiers


def _memory_item(
    *,
    subject: str,
    content: Any,
    kind: CiboMemoryKind,
    source_ref: str,
    effective_at: datetime,
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...],
    limitations: tuple[str, ...],
) -> CiboMemoryItem:
    return CiboMemoryItem(
        item_id=uuid5(NAMESPACE_URL, f"{IDENTITY}:{subject}"),
        kind=kind,
        subject_code=subject,
        content=json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False),
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef(source_ref),
            effective_at=effective_at,
            recorded_at=RECORDED_AT,
        ),
        freshness=CiboMemoryFreshness(
            state=CiboMemoryFreshnessState.CURRENT,
            as_of=RECORDED_AT,
        ),
        evidence_refs=evidence_refs,
        limitations=limitations,
    )


def _record(store: CiboMemoryStore, item: CiboMemoryItem) -> CiboMemoryStore:
    result = store.record(item)
    if not isinstance(result, Success):
        raise ValueError(f"failed to record VT08 full-CIBO memory: {result}")
    return result.value


def build_memory_store(
    *,
    full_market_root: Path,
    experience_root: Path,
) -> tuple[CiboMemoryStore, dict[str, Any]]:
    package, dossiers = load_full_market_memory(full_market_root)
    experience = v1.load_trader_experience(experience_root)
    strategy = v1._strategy_payload()

    strategy_ref = CiboCognitiveEvidenceRef(
        f"cibo:vt08:index:v7:fingerprint:{v1.V7_RULE_FINGERPRINT}"
    )
    market_ref = CiboCognitiveEvidenceRef(
        f"cibo:index:full-market-memory:v1:artifact:{FULL_MARKET_ARTIFACT_ID}"
    )
    experience_ref = CiboCognitiveEvidenceRef(
        f"cibo:vt08:index:experience:v1:artifact:{v1.EXPERIENCE_ARTIFACT_ID}"
    )
    semantic_ref = CiboCognitiveEvidenceRef(
        f"cibo:vt08:index:semantic-v2:artifact:{v1.SEMANTIC_V2_ARTIFACT_ID}"
    )
    complete_ref = CiboCognitiveEvidenceRef(
        f"cibo:vt08:index:complete-ledgers:v1:artifact:{v1.COMPLETE_LEDGERS_ARTIFACT_ID}"
    )

    store = CiboMemoryStore()
    store = _record(
        store,
        _memory_item(
            subject="vt08.index.strategy.identity",
            content=strategy,
            kind=CiboMemoryKind.SEMANTIC,
            source_ref=f"github:commit:{v1.V7_FREEZE_SHA}:vt08-index-v7",
            effective_at=v1.STRATEGY_EFFECTIVE_AT,
            evidence_refs=(strategy_ref,),
            limitations=("strategy-frozen", "no-retrospective-mutation"),
        ),
    )

    archive = {
        "package": package,
        "dossiers": dossiers,
    }
    store = _record(
        store,
        _memory_item(
            subject="indices.market.full-cibo.archive",
            content=archive,
            kind=CiboMemoryKind.LONG_TERM_ARCHIVE,
            source_ref=f"github:artifact:{FULL_MARKET_ARTIFACT_ID}:full-index-market-memory",
            effective_at=FULL_MARKET_EFFECTIVE_AT,
            evidence_refs=(market_ref,),
            limitations=(
                "association-only",
                "consumed-research-evidence",
                "no-rule-promotion",
                "supported-dol-universe-not-all-dols",
            ),
        ),
    )

    for symbol in v1.SYMBOLS:
        code = symbol.lower()
        store = _record(
            store,
            _memory_item(
                subject=f"{code}.market.full-cibo",
                content=dossiers[symbol],
                kind=CiboMemoryKind.MARKET,
                source_ref=f"github:artifact:{FULL_MARKET_ARTIFACT_ID}:{code}",
                effective_at=FULL_MARKET_EFFECTIVE_AT,
                evidence_refs=(market_ref,),
                limitations=(
                    "association-only",
                    "consumed-research-evidence",
                    "no-rule-promotion",
                    "not-vt08-outcome-conditioned",
                    "supported-dol-universe-not-all-dols",
                ),
            ),
        )

    cross_market = {
        symbol: dossiers[symbol]["cross_index"]
        for symbol in v1.SYMBOLS
    }
    store = _record(
        store,
        _memory_item(
            subject="indices.market.cross-index.full-cibo",
            content=cross_market,
            kind=CiboMemoryKind.MARKET,
            source_ref=f"github:artifact:{FULL_MARKET_ARTIFACT_ID}:cross-index",
            effective_at=FULL_MARKET_EFFECTIVE_AT,
            evidence_refs=(market_ref,),
            limitations=(
                "association-only",
                "no-causal-leader-claim",
                "no-rule-promotion",
            ),
        ),
    )

    experience_archive = {
        "manifest": experience["manifest"],
        "markets": experience["markets"],
        "cross_index": experience["cross_index"],
    }
    store = _record(
        store,
        _memory_item(
            subject="vt08.index.experience.archive",
            content=experience_archive,
            kind=CiboMemoryKind.LONG_TERM_ARCHIVE,
            source_ref=f"github:artifact:{v1.EXPERIENCE_ARTIFACT_ID}:full-package",
            effective_at=v1.EXPERIENCE_EFFECTIVE_AT,
            evidence_refs=(experience_ref, semantic_ref, complete_ref),
            limitations=(
                "consumed-research-evidence",
                "vt08-specific",
                "no-rule-promotion",
                "fresh-holdout-sealed",
            ),
        ),
    )

    experience_markets = cast(dict[str, Any], experience["markets"])
    for symbol in v1.SYMBOLS:
        code = symbol.lower()
        store = _record(
            store,
            _memory_item(
                subject=f"vt08.index.{code}.experience",
                content=experience_markets[symbol],
                kind=CiboMemoryKind.TRADER,
                source_ref=f"github:artifact:{v1.EXPERIENCE_ARTIFACT_ID}:{code}",
                effective_at=v1.EXPERIENCE_EFFECTIVE_AT,
                evidence_refs=(experience_ref, semantic_ref, complete_ref),
                limitations=(
                    "consumed-research-evidence",
                    "vt08-specific",
                    "diagnostic-only",
                    "no-rule-promotion",
                ),
            ),
        )

    store = _record(
        store,
        _memory_item(
            subject="vt08.index.cross-index.experience",
            content=experience["cross_index"],
            kind=CiboMemoryKind.TRADER,
            source_ref=f"github:artifact:{v1.EXPERIENCE_ARTIFACT_ID}:cross-index",
            effective_at=v1.EXPERIENCE_EFFECTIVE_AT,
            evidence_refs=(experience_ref, semantic_ref, complete_ref),
            limitations=(
                "consumed-research-evidence",
                "vt08-specific",
                "cross-index-association-only",
                "no-rule-promotion",
            ),
        ),
    )

    unresolved = {
        "identity": IDENTITY,
        "full_cibo_market_memory": True,
        "market_memory_artifact_id": FULL_MARKET_ARTIFACT_ID,
        "market_memory_evidence_tier": "E1_ASSOCIATION_ONLY",
        "market_atlas_known_gaps": (
            "universal-order-block-breaker-fvg-chronology-not-complete",
            "dedicated-equal-liquidity-chronology-not-complete",
            "generic-regime-thresholds-not-frozen",
            "target-v2-supported-reference-universe-is-not-all-dols",
            "cross-index-nearest-departure-is-not-causal-leadership",
        ),
        "strategy_identity_mutable_by_memory": False,
        "reasoning_policy_selected": False,
        "target_depth_policy_selected": False,
        "position_policy_selected": False,
        "contextual_trailing_policy_selected": False,
        "structural_rearm_policy_selected": False,
        "specialists_frozen": False,
        "fresh_holdout_opened": False,
    }
    store = _record(
        store,
        _memory_item(
            subject="vt08.index.memory.limitations",
            content=unresolved,
            kind=CiboMemoryKind.RESEARCH,
            source_ref=f"github:artifact:{FULL_MARKET_ARTIFACT_ID}:limitations",
            effective_at=FULL_MARKET_EFFECTIVE_AT,
            evidence_refs=(market_ref, experience_ref),
            limitations=("research-only", "no-rule-promotion"),
        ),
    )
    return store, {
        "full_market_package": package,
        "experience_manifest": experience["manifest"],
    }


def memory_index(store: CiboMemoryStore) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in store.retrieve():
        if item.kind is CiboMemoryKind.LONG_TERM_ARCHIVE:
            continue
        result[item.subject_code] = json.loads(item.content)
    return result


def _lookup_dimension(
    table: Any,
    *,
    name: str,
    value: str,
    unknown: list[str],
) -> tuple[str, str, dict[str, Any]] | None:
    if not isinstance(table, dict):
        unknown.append(name)
        return None
    payload = table.get(value)
    if not isinstance(payload, dict):
        unknown.append(name)
        return None
    return name, value, cast(dict[str, Any], payload)


def build_situation_model(
    store: CiboMemoryStore,
    observation: Vt08IndexSituationInput,
) -> Vt08IndexSituationModel:
    index = memory_index(store)
    code = observation.symbol.lower()
    strategy = cast(dict[str, Any], index["vt08.index.strategy.identity"])
    market = cast(dict[str, Any], index[f"{code}.market.full-cibo"])
    experience = cast(dict[str, Any], index[f"vt08.index.{code}.experience"])
    cross_market = cast(
        dict[str, Any],
        index["indices.market.cross-index.full-cibo"],
    )
    cross_experience = cast(
        dict[str, Any],
        index["vt08.index.cross-index.experience"],
    )

    matrix_detail = cast(dict[str, Any], market["market_matrix"])
    market_dimensions: list[tuple[str, str, dict[str, Any]]] = []
    experience_dimensions: list[tuple[str, str, dict[str, Any]]] = []
    unknown: list[str] = []

    market_lookups: list[tuple[str, str, Any]] = [
        ("market.side", observation.side, matrix_detail.get("by_side")),
        ("market.session", observation.session, matrix_detail.get("by_session")),
        (
            "market.weekday",
            observation.weekday_new_york,
            matrix_detail.get("by_weekday"),
        ),
    ]
    if observation.prior_body_alignment is not None:
        market_lookups.append(
            (
                "market.prior-body-alignment",
                observation.prior_body_alignment,
                matrix_detail.get("by_prior_body_alignment"),
            )
        )
    if observation.fvg_after_raid is not None:
        market_lookups.append(
            (
                "market.fvg-after-raid",
                "FVG_PRESENT" if observation.fvg_after_raid else "FVG_ABSENT",
                matrix_detail.get("by_fvg_presence"),
            )
        )
    for name, value, table in market_lookups:
        found = _lookup_dimension(table, name=name, value=value, unknown=unknown)
        if found is not None:
            market_dimensions.append(found)

    slices = cast(dict[str, Any], experience["behavior_slices"])
    experience_lookups: tuple[tuple[str, str, Any], ...] = (
        ("experience.anchor", str(observation.anchor_hour_new_york), slices.get("by_anchor")),
        ("experience.side", observation.side, slices.get("by_side")),
        ("experience.model", observation.model_kind, slices.get("by_model")),
        ("experience.poi", observation.poi_kind, slices.get("by_poi")),
        (
            "experience.weekday",
            observation.weekday_new_york,
            slices.get("by_weekday"),
        ),
        (
            "experience.prior-h4-range-regime",
            observation.prior_h4_range_regime,
            slices.get("by_prior_h4_range_regime"),
        ),
    )
    for name, value, table in experience_lookups:
        found = _lookup_dimension(table, name=name, value=value, unknown=unknown)
        if found is not None:
            experience_dimensions.append(found)

    return Vt08IndexSituationModel(
        observation=observation,
        strategy_memory=strategy,
        full_market_memory=market,
        market_dimensions=tuple(market_dimensions),
        cross_index_market_memory=cross_market,
        trader_experience_memory=experience,
        experience_dimensions=tuple(experience_dimensions),
        cross_index_experience_memory=cross_experience,
        unknown_dimensions=tuple(sorted(set(unknown))),
        market_memory_status="FULL_CIBO_INDEX_DOSSIER_V1_PRESENT",
        evidence_tier="MIXED_E0_E1_CONSUMED_DIAGNOSTIC",
        decision_authority=False,
        automatic_rule_promotion=False,
    )


def memory_store_manifest(store: CiboMemoryStore) -> dict[str, Any]:
    items = store.retrieve()
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind.value] = counts.get(item.kind.value, 0) + 1
    return {
        "identity": IDENTITY,
        "strategy_candidate_id": v7.CANDIDATE_ID,
        "strategy_rule_fingerprint": v7.RULE_FINGERPRINT,
        "strategy_freeze_sha": v1.V7_FREEZE_SHA,
        "full_market_run_id": FULL_MARKET_RUN_ID,
        "full_market_git_sha": FULL_MARKET_GIT_SHA,
        "full_market_artifact_id": FULL_MARKET_ARTIFACT_ID,
        "full_market_artifact_digest": FULL_MARKET_ARTIFACT_DIGEST,
        "experience_run_id": v1.EXPERIENCE_RUN_ID,
        "experience_artifact_id": v1.EXPERIENCE_ARTIFACT_ID,
        "items": len(items),
        "kind_counts": counts,
        "subjects": [item.subject_code for item in items],
        "three_memory_architecture": True,
        "full_cibo_market_memory": True,
        "market_memory_markets": list(v1.SYMBOLS),
        "trader_experience_markets": list(v1.SYMBOLS),
        "market_memory_evidence_tier": "E1_ASSOCIATION_ONLY",
        "reasoning_policy_selected": False,
        "target_depth_policy_selected": False,
        "position_policy_selected": False,
        "contextual_trailing_policy_selected": False,
        "structural_rearm_policy_selected": False,
        "specialists_frozen": False,
        "fresh_holdout_opened": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def write_memory_artifact(
    *,
    full_market_root: Path,
    experience_root: Path,
    out_dir: Path,
) -> None:
    store, sources = build_memory_store(
        full_market_root=full_market_root,
        experience_root=experience_root,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "VT08_INDEX_THREE_MEMORY_V2_MANIFEST.json").write_text(
        json.dumps(
            memory_store_manifest(store),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "VT08_INDEX_THREE_MEMORY_V2_INDEX.json").write_text(
        json.dumps(
            memory_index(store),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "VT08_INDEX_THREE_MEMORY_V2_SOURCES.json").write_text(
        json.dumps(sources, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-market-root", type=Path, required=True)
    parser.add_argument("--experience-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    write_memory_artifact(
        full_market_root=args.full_market_root,
        experience_root=args.experience_root,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
