"""Bridge the official CIBO XAUUSD 10Y dossier into governed CIBO memory.

This module does not invent new knowledge. It validates the immutable
CIBO_XAUUSD_MARKET_INTELLIGENCE_DOSSIER_V1 artifact and records its sections
inside the provider-neutral CiboMemoryStore with explicit provenance,
freshness, evidence references, and E1 association-only limitations.

The market brain can then retrieve context through the same governed memory
contract used by CIBO rather than reading ad-hoc lab dictionaries.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
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
from qore.kernel.result import Success
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef

IDENTITY = "CIBO_XAUUSD_TRADER_MEMORY_BRIDGE_V1"
DOSSIER_IDENTITY = "CIBO_XAUUSD_MARKET_INTELLIGENCE_DOSSIER_V1"
DOSSIER_RUN_ID = 35291722997
DOSSIER_ARTIFACT_ID = 10526391489
DOSSIER_DIGEST = "sha256:88b7999e1bbbda7be592eb32f1779b63b7084bb0e6f85be9db7a5b777f28aec5"
EFFECTIVE_AT = datetime(2026, 9, 17, 23, 59, tzinfo=UTC)
RECORDED_AT = datetime(2026, 9, 18, 0, 35, 31, tzinfo=UTC)

_MARKET_SECTIONS = (
    "overall",
    "by_timeframe",
    "by_reference_type",
    "by_side",
    "by_session",
    "by_weekday",
    "by_year",
    "by_quarter",
    "by_prior_body_alignment",
    "equal_liquidity_association",
    "fvg_after_raid_association",
    "exact_c2",
    "target_destination_v2",
    "daily_path",
    "pre_departure_sequences",
)
_RESEARCH_SECTIONS = (
    "hypothesis_status",
)


@dataclass(frozen=True, slots=True)
class CiboXauusdMemoryContext:
    """Relevant memory facts for one pre-entry Turtle Soup observation."""

    overall: dict[str, Any]
    dimensions: tuple[tuple[str, str, dict[str, Any]], ...]
    support_votes: int
    caution_votes: int
    mixed_votes: int
    state: str

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.state,
            self.support_votes,
            self.caution_votes,
            self.mixed_votes,
            tuple((name, value) for name, value, _summary in self.dimensions),
        )


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def load_dossier(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    dossier = json.loads(
        _single(root, "xauusd-market-intelligence-dossier-v1.json").read_text()
    )
    manifest = json.loads(
        _single(root, "xauusd-market-intelligence-manifest-v1.json").read_text()
    )
    if dossier.get("identity") != DOSSIER_IDENTITY:
        raise ValueError("unexpected CIBO XAUUSD dossier identity")
    if manifest.get("identity") != DOSSIER_IDENTITY:
        raise ValueError("unexpected CIBO XAUUSD manifest identity")
    if dossier.get("symbol") != "XAUUSD":
        raise ValueError("unexpected CIBO dossier symbol")
    if int(dossier.get("retained_m5_bars", 0)) != 707716:
        raise ValueError("CIBO dossier retained-bar drift")
    if int(dossier.get("behavior_events", 0)) != 111925:
        raise ValueError("CIBO dossier behavior-event drift")
    if manifest.get("highest_automatic_evidence_tier") != "E1_ASSOCIATION_ONLY":
        raise ValueError("CIBO dossier evidence tier drift")
    if bool(manifest.get("rule_promotion_allowed")):
        raise ValueError("CIBO dossier unexpectedly allows rule promotion")
    return dossier, manifest


def _subject(section: str) -> str:
    return "xauusd.market." + section.replace("_", "-")


def _memory_item(
    *,
    section: str,
    value: Any,
    kind: CiboMemoryKind,
    evidence_ref: CiboCognitiveEvidenceRef,
) -> CiboMemoryItem:
    return CiboMemoryItem(
        item_id=uuid5(NAMESPACE_URL, f"{IDENTITY}:{section}"),
        kind=kind,
        subject_code=_subject(section),
        content=json.dumps(value, sort_keys=True, separators=(",", ":")),
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef(
                f"github:artifact:{DOSSIER_ARTIFACT_ID}:{section.replace('_', '-')}"
            ),
            effective_at=EFFECTIVE_AT,
            recorded_at=RECORDED_AT,
        ),
        freshness=CiboMemoryFreshness(
            state=CiboMemoryFreshnessState.CURRENT,
            as_of=RECORDED_AT,
        ),
        evidence_refs=(evidence_ref,),
        limitations=(
            "association-only",
            "consumed-research-evidence",
            "no-rule-promotion",
        ),
    )


def build_memory_store(root: Path) -> tuple[CiboMemoryStore, dict[str, Any]]:
    dossier, manifest = load_dossier(root)
    evidence_ref = CiboCognitiveEvidenceRef(
        f"cibo:xauusd:market-intelligence:v1:artifact:{DOSSIER_ARTIFACT_ID}"
    )
    store = CiboMemoryStore()

    # Retain the full dossier as immutable archive memory so decomposed indexes
    # never replace the original evidence-bearing knowledge object.
    archive = CiboMemoryItem(
        item_id=uuid5(NAMESPACE_URL, f"{IDENTITY}:full-dossier"),
        kind=CiboMemoryKind.LONG_TERM_ARCHIVE,
        subject_code="xauusd.market.full-dossier",
        content=json.dumps(dossier, sort_keys=True, separators=(",", ":")),
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef(
                f"github:artifact:{DOSSIER_ARTIFACT_ID}:full-dossier"
            ),
            effective_at=EFFECTIVE_AT,
            recorded_at=RECORDED_AT,
        ),
        freshness=CiboMemoryFreshness(
            state=CiboMemoryFreshnessState.CURRENT,
            as_of=RECORDED_AT,
        ),
        evidence_refs=(evidence_ref,),
        limitations=(
            "association-only",
            "consumed-research-evidence",
            "no-rule-promotion",
        ),
    )
    recorded = store.record(archive)
    if not isinstance(recorded, Success):
        raise ValueError(f"failed to record full CIBO dossier memory: {recorded}")
    store = recorded.value

    for section in _MARKET_SECTIONS:
        item = _memory_item(
            section=section,
            value=dossier[section],
            kind=CiboMemoryKind.MARKET,
            evidence_ref=evidence_ref,
        )
        recorded = store.record(item)
        if not isinstance(recorded, Success):
            raise ValueError(f"failed to record CIBO market section {section}: {recorded}")
        store = recorded.value

    for section in _RESEARCH_SECTIONS:
        item = _memory_item(
            section=section,
            value=dossier[section],
            kind=CiboMemoryKind.RESEARCH,
            evidence_ref=evidence_ref,
        )
        recorded = store.record(item)
        if not isinstance(recorded, Success):
            raise ValueError(f"failed to record CIBO research section {section}: {recorded}")
        store = recorded.value

    unresolved = {
        "protected_swing_scope": dossier["protected_swing_scope"],
        "stop_recovery_scope": dossier["stop_recovery_scope"],
        "regime_scope": dossier["regime_scope"],
    }
    item = _memory_item(
        section="unresolved_scope",
        value=unresolved,
        kind=CiboMemoryKind.RESEARCH,
        evidence_ref=evidence_ref,
    )
    recorded = store.record(item)
    if not isinstance(recorded, Success):
        raise ValueError(f"failed to record CIBO unresolved-scope memory: {recorded}")
    store = recorded.value

    return store, manifest


def memory_index(store: CiboMemoryStore) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for item in store.retrieve():
        if item.kind not in {
            CiboMemoryKind.MARKET,
            CiboMemoryKind.RESEARCH,
        }:
            continue
        index[item.subject_code] = json.loads(item.content)
    return index


def _ratio(summary: dict[str, Any]) -> float:
    mfe = float(summary["median_mfe_240m_ticks"])
    mae = float(summary["median_mae_240m_ticks"])
    return 0.0 if mae <= 0 else mfe / mae


def _dimension_vote(
    summary: dict[str, Any],
    overall: dict[str, Any],
) -> str:
    hit = float(summary["opposite_source_boundary_hit_24h_rate"])
    base_hit = float(overall["opposite_source_boundary_hit_24h_rate"])
    ratio = _ratio(summary)
    base_ratio = _ratio(overall)
    if hit >= base_hit and ratio >= base_ratio:
        return "SUPPORT"
    if hit < base_hit and ratio < base_ratio:
        return "CAUTION"
    return "MIXED"


def context_memory(
    store: CiboMemoryStore,
    *,
    timeframe: str,
    side: str,
    session: str,
    prior_body_alignment: str,
    fvg_before_entry: str,
    exact_equal_liquidity: str,
) -> CiboXauusdMemoryContext:
    index = memory_index(store)
    overall = index["xauusd.market.overall"]

    lookups = (
        ("timeframe", timeframe, "xauusd.market.by-timeframe"),
        ("side", side, "xauusd.market.by-side"),
        ("session", session, "xauusd.market.by-session"),
        (
            "prior_body_alignment",
            prior_body_alignment,
            "xauusd.market.by-prior-body-alignment",
        ),
        (
            "fvg_after_raid",
            "FVG_PRESENT" if fvg_before_entry == "yes" else "FVG_ABSENT",
            "xauusd.market.fvg-after-raid-association",
        ),
        (
            "equal_liquidity",
            "EXACT_EQUAL" if exact_equal_liquidity == "yes" else "NOT_EXACT_EQUAL",
            "xauusd.market.equal-liquidity-association",
        ),
    )

    dimensions: list[tuple[str, str, dict[str, Any]]] = []
    votes = {"SUPPORT": 0, "CAUTION": 0, "MIXED": 0}
    for name, value, subject in lookups:
        table = index[subject]
        summary = table.get(value)
        if summary is None:
            continue
        dimensions.append((name, value, summary))
        votes[_dimension_vote(summary, overall)] += 1

    if votes["SUPPORT"] > votes["CAUTION"]:
        state = "SUPPORTIVE"
    elif votes["CAUTION"] > votes["SUPPORT"]:
        state = "CAUTIOUS"
    else:
        state = "MIXED"

    return CiboXauusdMemoryContext(
        overall=overall,
        dimensions=tuple(dimensions),
        support_votes=votes["SUPPORT"],
        caution_votes=votes["CAUTION"],
        mixed_votes=votes["MIXED"],
        state=state,
    )


def memory_store_manifest(store: CiboMemoryStore) -> dict[str, Any]:
    items = store.retrieve()
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind.value] = counts.get(item.kind.value, 0) + 1
    return {
        "identity": IDENTITY,
        "dossier_identity": DOSSIER_IDENTITY,
        "dossier_run_id": DOSSIER_RUN_ID,
        "dossier_artifact_id": DOSSIER_ARTIFACT_ID,
        "dossier_digest": DOSSIER_DIGEST,
        "items": len(items),
        "kind_counts": counts,
        "subjects": [item.subject_code for item in items],
        "governed_cibo_memory_store": True,
        "transient_context_is_authoritative_memory": False,
        "evidence_tier": "E1_ASSOCIATION_ONLY",
        "rule_promotion_allowed": False,
    }
