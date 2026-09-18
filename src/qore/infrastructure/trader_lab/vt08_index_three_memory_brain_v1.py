"""Governed three-memory brain foundation for VT-08 Index.

This module materializes the architecture learned from Turtle Soup without copying
its trading parameters. It keeps three distinct memory domains:

1. Strategy Identity Memory -- the frozen VT08 V7 rule material.
2. CIBO Market Memory -- general 10Y NAS100/SP500/US30 market knowledge that was
   learned independently of VT08 outcomes.
3. Trader Experience Memory -- the consumed VT08-specific journey/forensics
   dossiers built from 2,294 VT08-market interactions.

The resulting Situation Model is descriptive and pre-decision. It does not emit
ENTER/WAIT/ABSTAIN, alter V7, promote E1 associations, open a holdout, or grant
execution authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
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
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.kernel.result import Success
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef

IDENTITY = "VT08_INDEX_THREE_MEMORY_BRAIN_V1"
MARKET_MATRIX_IDENTITY = "CIBO_12_MARKET_INTELLIGENCE_MATRIX_V1"
JOURNEY_SUMMARY_IDENTITY = "CIBO_MARKET_JOURNEY_SUMMARY_V1"
EXPERIENCE_SCHEMA = "qore.trader_lab.vt08_index_cibo_market_dossiers.v1"

V7_FREEZE_SHA = "c37412c877f2fda8b32bda652b6bc74663159761"
V7_RULE_FINGERPRINT = (
    "a7f3b7afa3a98bfcb4daad1595762ce3925000fb256e2cbd2db84b8ec80b1308"
)

MARKET_MATRIX_RUN_ID = 35235739642
MARKET_MATRIX_ARTIFACT_ID = 10503960571
MARKET_MATRIX_ARTIFACT_DIGEST = (
    "sha256:0a2ddcea40054c3724e0910a7437d823c38224093699dc5d630dd2a6619b01e8"
)
JOURNEY_SUMMARY_RUN_ID = 35200408430
JOURNEY_SUMMARY_ARTIFACT_ID = 10487577113
JOURNEY_SUMMARY_ARTIFACT_DIGEST = (
    "sha256:0394ea6e64bddf3315f331d710084441868e50182341ff13511d13c6d95abe4d"
)
EXPERIENCE_RUN_ID = 35288271920
EXPERIENCE_ARTIFACT_ID = 10526040777
EXPERIENCE_ARTIFACT_DIGEST = (
    "sha256:8dc34a84aee03480fc83e76b53c476200da72751edba6d904dd6be6440ea5394"
)
SEMANTIC_V2_ARTIFACT_ID = 10525006904
COMPLETE_LEDGERS_ARTIFACT_ID = 10479912540

SYMBOLS = ("NAS100", "SP500", "US30")
EXPECTED_MARKET_EPISODES = {
    "NAS100": 110471,
    "SP500": 102863,
    "US30": 109341,
}
EXPECTED_VT08_EPISODES = {
    "NAS100": 761,
    "SP500": 747,
    "US30": 786,
}

STRATEGY_EFFECTIVE_AT = datetime(2026, 9, 16, 9, 49, 25, tzinfo=UTC)
MARKET_EFFECTIVE_AT = datetime(2026, 9, 17, 14, 58, 34, tzinfo=UTC)
EXPERIENCE_EFFECTIVE_AT = datetime(2026, 9, 17, 23, 57, 45, tzinfo=UTC)
RECORDED_AT = datetime(2026, 9, 18, 1, 0, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Vt08IndexSituationInput:
    """Causal/pre-entry descriptors supplied by the frozen strategy/runtime."""

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
        if self.symbol not in SYMBOLS:
            raise ValueError(f"unsupported VT08 Index symbol: {self.symbol}")
        if self.side not in {"long", "short"}:
            raise ValueError(f"unsupported VT08 Index side: {self.side}")


@dataclass(frozen=True, slots=True)
class Vt08IndexSituationModel:
    """Evidence-bearing memory view assembled before any trading decision."""

    observation: Vt08IndexSituationInput
    strategy_memory: dict[str, Any]
    market_memory: dict[str, Any]
    market_dimensions: tuple[tuple[str, str, dict[str, Any]], ...]
    cross_index_market_memory: dict[str, Any]
    trader_experience_memory: dict[str, Any]
    experience_dimensions: tuple[tuple[str, str, dict[str, Any]], ...]
    cross_index_experience_memory: dict[str, Any]
    unknown_dimensions: tuple[str, ...]
    evidence_tier: str
    decision_authority: bool
    automatic_rule_promotion: bool

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation,
            tuple((name, value) for name, value, _payload in self.market_dimensions),
            tuple(
                (name, value) for name, value, _payload in self.experience_dimensions
            ),
            self.unknown_dimensions,
            self.evidence_tier,
            self.decision_authority,
            self.automatic_rule_promotion,
        )


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object in {path}")
    return cast(dict[str, Any], payload)


def _strategy_payload() -> dict[str, Any]:
    if v7.RULE_FINGERPRINT != V7_RULE_FINGERPRINT:
        raise ValueError("VT08 V7 rule fingerprint drift")
    material = cast(dict[str, Any], v7._RULE_MATERIAL)
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    if sha256(encoded.encode("utf-8")).hexdigest() != V7_RULE_FINGERPRINT:
        raise ValueError("VT08 V7 rule material no longer matches frozen fingerprint")
    return {
        "candidate_id": v7.CANDIDATE_ID,
        "rule_fingerprint": v7.RULE_FINGERPRINT,
        "economic_freeze_sha": V7_FREEZE_SHA,
        "rule_material": material,
        "strategy_memory_role": "identity-and-methodology",
        "cibo_may_modify_strategy_identity": False,
    }


def load_market_memory(
    matrix_root: Path,
    journey_summary_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    matrix = _read_json(_single(matrix_root, "cibo-12-market-intelligence-matrix-v1.json"))
    manifest = _read_json(
        _single(matrix_root, "cibo-12-market-intelligence-matrix-v1-manifest.json")
    )
    journey = _read_json(_single(journey_summary_root, "cibo-journey-10y-summary.json"))

    if matrix.get("identity") != MARKET_MATRIX_IDENTITY:
        raise ValueError("unexpected CIBO market matrix identity")
    if manifest.get("identity") != MARKET_MATRIX_IDENTITY:
        raise ValueError("unexpected CIBO market matrix manifest identity")
    if journey.get("identity") != JOURNEY_SUMMARY_IDENTITY:
        raise ValueError("unexpected CIBO journey summary identity")
    if manifest.get("highest_automatic_evidence_tier") != "E1_ASSOCIATION_ONLY":
        raise ValueError("market matrix evidence tier drift")
    if matrix.get("evidence_tier") != "E1_ASSOCIATION_ONLY":
        raise ValueError("market matrix payload evidence tier drift")
    if bool(manifest.get("rule_promotion_allowed")):
        raise ValueError("market matrix unexpectedly allows rule promotion")
    if bool(journey.get("rule_promotion_allowed")):
        raise ValueError("journey summary unexpectedly allows rule promotion")
    if int(manifest.get("source_journey_run_id", 0)) != 35175979474:
        raise ValueError("market matrix journey provenance drift")
    if int(manifest.get("source_m5_run_id", 0)) != 35166210458:
        raise ValueError("market matrix M5 provenance drift")
    if int(manifest.get("source_target_run_id", 0)) != 35204892665:
        raise ValueError("market matrix target provenance drift")
    if int(journey.get("source_run_id", 0)) != 35175979474:
        raise ValueError("journey summary source provenance drift")
    if journey.get("cross_index_evidence_tier") != "E1_ASSOCIATION_ONLY":
        raise ValueError("cross-index journey evidence tier drift")
    if int(cast(dict[str, Any], journey["cross_index"]).get("rows", 0)) != 108558:
        raise ValueError("cross-index journey row-count drift")

    details = cast(dict[str, Any], matrix["market_detail"])
    journey_symbols = {
        str(row["symbol"]): row
        for row in cast(list[dict[str, Any]], journey["symbols"])
    }
    for symbol in SYMBOLS:
        detail = cast(dict[str, Any], details.get(symbol))
        if not detail or detail.get("symbol") != symbol:
            raise ValueError(f"missing CIBO market detail for {symbol}")
        if detail.get("evidence_tier") != "E1_ASSOCIATION_ONLY":
            raise ValueError(f"CIBO evidence tier drift for {symbol}")
        if bool(detail.get("rule_promotion_allowed")):
            raise ValueError(f"CIBO market memory unexpectedly promotes rules for {symbol}")
        if int(cast(dict[str, Any], detail["overall"]).get("events", 0)) != (
            EXPECTED_MARKET_EPISODES[symbol]
        ):
            raise ValueError(f"CIBO market episode-count drift for {symbol}")
        journey_row = cast(dict[str, Any], journey_symbols.get(symbol))
        if not journey_row:
            raise ValueError(f"missing Journey summary for {symbol}")
        if int(journey_row.get("episodes", 0)) != EXPECTED_MARKET_EPISODES[symbol]:
            raise ValueError(f"Journey summary episode-count drift for {symbol}")
    return matrix, manifest, journey


def load_trader_experience(root: Path) -> dict[str, Any]:
    manifest = _read_json(_single(root, "CIBO_MARKET_DOSSIER_MANIFEST.json"))
    if manifest.get("schema") != EXPERIENCE_SCHEMA:
        raise ValueError("unexpected VT08 experience dossier schema")
    if int(manifest.get("market_episode_count", 0)) != 2294:
        raise ValueError("VT08 experience episode-count drift")
    if int(manifest.get("cross_index_cohort_count", 0)) != 1765:
        raise ValueError("VT08 experience cross-index cohort drift")
    if tuple(manifest.get("markets", ())) != SYMBOLS:
        raise ValueError("VT08 experience market-universe drift")
    governance = cast(dict[str, Any], manifest.get("governance", {}))
    if bool(governance.get("fresh_holdout_opened")):
        raise ValueError("VT08 experience artifact unexpectedly opened fresh holdout")
    if bool(governance.get("specialists_frozen")):
        raise ValueError("VT08 experience artifact unexpectedly froze specialists")

    markets: dict[str, Any] = {}
    total = 0
    for symbol in SYMBOLS:
        dossier = _read_json(_single(root, f"{symbol}_MARKET_DOSSIER.json"))
        if dossier.get("schema") != EXPERIENCE_SCHEMA or dossier.get("symbol") != symbol:
            raise ValueError(f"unexpected VT08 experience dossier for {symbol}")
        sample = int(cast(dict[str, Any], dossier["overall"]).get("sample", 0))
        if sample != EXPECTED_VT08_EPISODES[symbol]:
            raise ValueError(f"VT08 experience sample drift for {symbol}")
        total += sample
        markets[symbol] = dossier
    if total != 2294:
        raise ValueError("VT08 experience total sample drift")

    cross = _read_json(_single(root, "CROSS_INDEX_MARKET_DOSSIER.json"))
    if cross.get("schema") != EXPERIENCE_SCHEMA:
        raise ValueError("unexpected VT08 cross-index experience schema")
    if int(cross.get("cohort_count", 0)) != 1765:
        raise ValueError("VT08 cross-index experience cohort drift")
    return {"manifest": manifest, "markets": markets, "cross_index": cross}


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
    recorded = store.record(item)
    if not isinstance(recorded, Success):
        raise ValueError(f"failed to record governed VT08 memory: {recorded}")
    return recorded.value


def build_memory_store(
    *,
    matrix_root: Path,
    journey_summary_root: Path,
    experience_root: Path,
) -> tuple[CiboMemoryStore, dict[str, Any]]:
    matrix, matrix_manifest, journey = load_market_memory(
        matrix_root,
        journey_summary_root,
    )
    experience = load_trader_experience(experience_root)
    strategy = _strategy_payload()

    strategy_ref = CiboCognitiveEvidenceRef(
        f"cibo:vt08:index:v7:fingerprint:{V7_RULE_FINGERPRINT}"
    )
    matrix_ref = CiboCognitiveEvidenceRef(
        f"cibo:market-atlas:matrix:v1:artifact:{MARKET_MATRIX_ARTIFACT_ID}"
    )
    journey_ref = CiboCognitiveEvidenceRef(
        f"cibo:market-atlas:journey-summary:v1:artifact:{JOURNEY_SUMMARY_ARTIFACT_ID}"
    )
    experience_ref = CiboCognitiveEvidenceRef(
        f"cibo:vt08:index:experience:v1:artifact:{EXPERIENCE_ARTIFACT_ID}"
    )
    semantic_ref = CiboCognitiveEvidenceRef(
        f"cibo:vt08:index:semantic-v2:artifact:{SEMANTIC_V2_ARTIFACT_ID}"
    )
    complete_ref = CiboCognitiveEvidenceRef(
        f"cibo:vt08:index:complete-ledgers:v1:artifact:{COMPLETE_LEDGERS_ARTIFACT_ID}"
    )

    store = CiboMemoryStore()
    store = _record(
        store,
        _memory_item(
            subject="vt08.index.strategy.identity",
            content=strategy,
            kind=CiboMemoryKind.SEMANTIC,
            source_ref=f"github:commit:{V7_FREEZE_SHA}:vt08-index-v7",
            effective_at=STRATEGY_EFFECTIVE_AT,
            evidence_refs=(strategy_ref,),
            limitations=("strategy-frozen", "no-retrospective-mutation"),
        ),
    )

    store = _record(
        store,
        _memory_item(
            subject="indices.market.cibo-matrix-10y.archive",
            content=matrix,
            kind=CiboMemoryKind.LONG_TERM_ARCHIVE,
            source_ref=f"github:artifact:{MARKET_MATRIX_ARTIFACT_ID}:full-matrix",
            effective_at=MARKET_EFFECTIVE_AT,
            evidence_refs=(matrix_ref,),
            limitations=(
                "association-only",
                "consumed-research-evidence",
                "no-rule-promotion",
            ),
        ),
    )
    store = _record(
        store,
        _memory_item(
            subject="indices.market.journey-summary-10y.archive",
            content=journey,
            kind=CiboMemoryKind.LONG_TERM_ARCHIVE,
            source_ref=f"github:artifact:{JOURNEY_SUMMARY_ARTIFACT_ID}:journey-summary",
            effective_at=MARKET_EFFECTIVE_AT,
            evidence_refs=(journey_ref,),
            limitations=(
                "association-only",
                "consumed-research-evidence",
                "deterministic-supported-subset",
            ),
        ),
    )

    details = cast(dict[str, Any], matrix["market_detail"])
    journey_symbols = {
        str(row["symbol"]): row
        for row in cast(list[dict[str, Any]], journey["symbols"])
    }
    for symbol in SYMBOLS:
        code = symbol.lower()
        payload = {
            "symbol": symbol,
            "matrix_detail": details[symbol],
            "journey_summary": journey_symbols[symbol],
            "evidence_tier": "E1_ASSOCIATION_ONLY",
            "memory_role": "general-market-memory-independent-of-vt08-outcomes",
            "source_run_ids": {
                "m5": matrix_manifest["source_m5_run_id"],
                "journey": matrix_manifest["source_journey_run_id"],
                "target_destination": matrix_manifest["source_target_run_id"],
            },
        }
        store = _record(
            store,
            _memory_item(
                subject=f"{code}.market.general-10y",
                content=payload,
                kind=CiboMemoryKind.MARKET,
                source_ref=f"github:artifact:{MARKET_MATRIX_ARTIFACT_ID}:{code}",
                effective_at=MARKET_EFFECTIVE_AT,
                evidence_refs=(matrix_ref, journey_ref),
                limitations=(
                    "association-only",
                    "consumed-research-evidence",
                    "no-rule-promotion",
                    "not-vt08-outcome-conditioned",
                ),
            ),
        )

    store = _record(
        store,
        _memory_item(
            subject="indices.market.cross-index-general-10y",
            content=journey["cross_index"],
            kind=CiboMemoryKind.MARKET,
            source_ref=f"github:artifact:{JOURNEY_SUMMARY_ARTIFACT_ID}:cross-index",
            effective_at=MARKET_EFFECTIVE_AT,
            evidence_refs=(journey_ref,),
            limitations=(
                "association-only",
                "nearest-departure-matcher",
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
            source_ref=f"github:artifact:{EXPERIENCE_ARTIFACT_ID}:full-package",
            effective_at=EXPERIENCE_EFFECTIVE_AT,
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
    for symbol in SYMBOLS:
        code = symbol.lower()
        store = _record(
            store,
            _memory_item(
                subject=f"vt08.index.{code}.experience",
                content=experience_markets[symbol],
                kind=CiboMemoryKind.TRADER,
                source_ref=f"github:artifact:{EXPERIENCE_ARTIFACT_ID}:{code}",
                effective_at=EXPERIENCE_EFFECTIVE_AT,
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
            source_ref=f"github:artifact:{EXPERIENCE_ARTIFACT_ID}:cross-index",
            effective_at=EXPERIENCE_EFFECTIVE_AT,
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
        "market_memory_evidence_tier": "E1_ASSOCIATION_ONLY",
        "market_atlas_known_gaps": (
            "universal-order-block-breaker-fvg-chronology-not-complete",
            "equal-liquidity-dedicated-chronology-not-complete",
            "generic-regime-thresholds-not-frozen",
            "cross-index-nearest-departure-is-not-causal-leadership",
        ),
        "experience_memory_status": "CONSUMED_DIAGNOSTIC_EVIDENCE",
        "strategy_identity_mutable_by_memory": False,
        "reasoning_policy_selected": False,
        "position_policy_selected": False,
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
            source_ref=f"github:artifact:{EXPERIENCE_ARTIFACT_ID}:memory-limitations",
            effective_at=EXPERIENCE_EFFECTIVE_AT,
            evidence_refs=(matrix_ref, journey_ref, experience_ref),
            limitations=("research-only", "no-rule-promotion"),
        ),
    )
    return store, {
        "matrix_manifest": matrix_manifest,
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
    market = cast(dict[str, Any], index[f"{code}.market.general-10y"])
    experience = cast(dict[str, Any], index[f"vt08.index.{code}.experience"])
    cross_market = cast(dict[str, Any], index["indices.market.cross-index-general-10y"])
    cross_experience = cast(
        dict[str, Any],
        index["vt08.index.cross-index.experience"],
    )

    matrix_detail = cast(dict[str, Any], market["matrix_detail"])
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
    experience_lookups = (
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
        market_memory=market,
        market_dimensions=tuple(market_dimensions),
        cross_index_market_memory=cross_market,
        trader_experience_memory=experience,
        experience_dimensions=tuple(experience_dimensions),
        cross_index_experience_memory=cross_experience,
        unknown_dimensions=tuple(sorted(set(unknown))),
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
        "strategy_freeze_sha": V7_FREEZE_SHA,
        "market_matrix_run_id": MARKET_MATRIX_RUN_ID,
        "market_matrix_artifact_id": MARKET_MATRIX_ARTIFACT_ID,
        "market_matrix_artifact_digest": MARKET_MATRIX_ARTIFACT_DIGEST,
        "journey_summary_run_id": JOURNEY_SUMMARY_RUN_ID,
        "journey_summary_artifact_id": JOURNEY_SUMMARY_ARTIFACT_ID,
        "journey_summary_artifact_digest": JOURNEY_SUMMARY_ARTIFACT_DIGEST,
        "experience_run_id": EXPERIENCE_RUN_ID,
        "experience_artifact_id": EXPERIENCE_ARTIFACT_ID,
        "experience_artifact_digest": EXPERIENCE_ARTIFACT_DIGEST,
        "items": len(items),
        "kind_counts": counts,
        "subjects": [item.subject_code for item in items],
        "three_memory_architecture": True,
        "strategy_memory_present": any(
            item.subject_code == "vt08.index.strategy.identity" for item in items
        ),
        "market_memory_markets": list(SYMBOLS),
        "trader_experience_markets": list(SYMBOLS),
        "market_memory_evidence_tier": "E1_ASSOCIATION_ONLY",
        "reasoning_policy_selected": False,
        "position_policy_selected": False,
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
    matrix_root: Path,
    journey_summary_root: Path,
    experience_root: Path,
    out_dir: Path,
) -> None:
    store, sources = build_memory_store(
        matrix_root=matrix_root,
        journey_summary_root=journey_summary_root,
        experience_root=experience_root,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "VT08_INDEX_THREE_MEMORY_MANIFEST.json").write_text(
        json.dumps(
            memory_store_manifest(store),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "VT08_INDEX_MEMORY_INDEX.json").write_text(
        json.dumps(
            memory_index(store),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "VT08_INDEX_MEMORY_SOURCES.json").write_text(
        json.dumps(
            sources,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-matrix-root", type=Path, required=True)
    parser.add_argument("--journey-summary-root", type=Path, required=True)
    parser.add_argument("--experience-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    write_memory_artifact(
        matrix_root=args.market_matrix_root,
        journey_summary_root=args.journey_summary_root,
        experience_root=args.experience_root,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
