"""Deterministic shared market-context engine for QORE CORE STACK V2."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from qore.infrastructure.core_stack_v2.contracts import (
    CORE_STACK_VERSION,
    CoreHypothesis,
    CoreSnapshot,
    HypothesisStatus,
    KnowledgeState,
    MarketEvent,
    PerceptionIntegrity,
    PortfolioIntent,
    PortfolioSituation,
    PositionContext,
    UncertaintyState,
    WorldState,
    freeze_facts,
)

_WORLD_KEYS: Final = (
    "market_state",
    "session_state",
    "liquidity_state",
    "structure_state",
    "volatility_state",
    "expansion_state",
    "compression_state",
    "directional_state",
    "reversal_state",
    "continuation_state",
)


@dataclass(frozen=True, slots=True)
class CoreStackConfig:
    stale_after_ms: int = 2_000

    def __post_init__(self) -> None:
        if self.stale_after_ms <= 0:
            raise ValueError("stale_after_ms must be positive")


def _latest_facts(events: tuple[MarketEvent, ...]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for event in events:
        for key, value in event.facts:
            merged[key] = value
    return merged


def _integrity(
    events: tuple[MarketEvent, ...],
    *,
    generated_at: datetime,
    stale_after_ms: int,
) -> PerceptionIntegrity:
    if not events:
        raise ValueError("at least one market event is required")

    codes: list[str] = []
    ids = [event.event_id for event in events]
    if len(ids) != len(set(ids)):
        codes.append("DUPLICATE_EVENT_ID")

    identities = [
        (event.market, event.event_type, event.source_at, event.timeframe_seconds)
        for event in events
    ]
    if len(identities) != len(set(identities)):
        codes.append("DUPLICATE_MARKET_EVENT")

    sequences = [event.sequence for event in events]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        codes.append("OUT_OF_ORDER_EVENT")

    if any(not event.complete for event in events):
        codes.append("INCOMPLETE_EVENT")

    if any(event.source_at > generated_at for event in events):
        codes.append("FUTURE_SOURCE_TIMESTAMP")
    if any(event.observed_at > generated_at for event in events):
        codes.append("FUTURE_OBSERVED_TIMESTAMP")

    bars = [event for event in events if event.event_type == "NEW_BAR"]
    by_tf: dict[int, list[MarketEvent]] = {}
    for event in bars:
        if event.timeframe_seconds is not None:
            by_tf.setdefault(event.timeframe_seconds, []).append(event)
    for timeframe, series in by_tf.items():
        ordered = sorted(series, key=lambda event: event.source_at)
        for left, right in zip(ordered, ordered[1:], strict=False):
            delta = int((right.source_at - left.source_at).total_seconds())
            if delta > timeframe:
                codes.append(f"MISSING_CANDLE:{timeframe}")
                break

    newest = max(event.source_at for event in events)
    state_age_ms = max(0, int((generated_at - newest).total_seconds() * 1_000))
    if state_age_ms > stale_after_ms:
        codes.append("STALE_SNAPSHOT_SOURCE")

    return PerceptionIntegrity(
        valid=not codes,
        codes=tuple(sorted(set(codes))),
        state_age_ms=state_age_ms,
        newest_source_at=newest,
    )


def _portfolio(intents: tuple[PortfolioIntent, ...]) -> PortfolioSituation:
    duplicate_keys: dict[tuple[str, str], list[str]] = {}
    factor_keys: dict[tuple[str, str], list[str]] = {}
    for intent in intents:
        duplicate_keys.setdefault((intent.market, intent.side), []).append(
            intent.trader_id
        )
        for factor in intent.factor_tags:
            factor_keys.setdefault((factor, intent.side), []).append(intent.trader_id)

    duplicates = tuple(
        sorted(
            f"{market}:{side}:{','.join(sorted(traders))}"
            for (market, side), traders in duplicate_keys.items()
            if len(traders) >= 2
        )
    )
    clusters = tuple(
        sorted(
            f"{factor}:{side}:{','.join(sorted(traders))}"
            for (factor, side), traders in factor_keys.items()
            if len(traders) >= 2
        )
    )
    return PortfolioSituation(
        intents=tuple(sorted(intents, key=lambda item: (item.trader_id, item.market))),
        duplicated_exposures=duplicates,
        factor_clusters=clusters,
    )


def _attention(events: tuple[MarketEvent, ...]) -> tuple[str, ...]:
    changed: list[str] = []
    previous: dict[str, str] = {}
    for event in events:
        event_changed = False
        for key, value in event.facts:
            if previous.get(key) != value:
                event_changed = True
            previous[key] = value
        if event_changed:
            changed.append(event.event_id)
    return tuple(changed)


def _uncertainty(
    integrity: PerceptionIntegrity,
    hypotheses: tuple[CoreHypothesis, ...],
    event_count: int,
    cross_market_count: int,
) -> UncertaintyState:
    contradicted = sum(
        item.status in {HypothesisStatus.FALSIFIED, HypothesisStatus.INVALIDATED}
        or bool(item.contradictory_event_ids)
        for item in hypotheses
    )
    contradiction_bps = min(10_000, contradicted * 2_500)
    evidence_bps = min(10_000, event_count * 1_000)
    cross_bps = min(10_000, cross_market_count * 2_500)
    if not integrity.valid:
        state = KnowledgeState.INSUFFICIENT
    elif contradiction_bps >= 5_000:
        state = KnowledgeState.CONFLICT
    elif evidence_bps < 4_000:
        state = KnowledgeState.UNCERTAIN
    elif evidence_bps < 8_000:
        state = KnowledgeState.THINK
    else:
        state = KnowledgeState.KNOW
    data_bps = 10_000 if integrity.valid else 0
    context_bps = min(data_bps, (evidence_bps + cross_bps) // 2)
    return UncertaintyState(
        knowledge_state=state,
        context_confidence_bps=context_bps,
        data_integrity_bps=data_bps,
        evidence_strength_bps=evidence_bps,
        contradiction_level_bps=contradiction_bps,
        regime_confidence_bps=context_bps,
        cross_market_confirmation_bps=cross_bps,
        state_age_ms=integrity.state_age_ms,
    )


def build_snapshot(
    *,
    events: tuple[MarketEvent, ...],
    generated_at: datetime,
    hypotheses: tuple[CoreHypothesis, ...] = (),
    portfolio_intents: tuple[PortfolioIntent, ...] = (),
    cross_market_facts: dict[str, str] | None = None,
    position_context: PositionContext | None = None,
    config: CoreStackConfig = CoreStackConfig(),
) -> CoreSnapshot:
    """Build one immutable shared snapshot from already-observable causal inputs."""
    integrity = _integrity(
        events,
        generated_at=generated_at,
        stale_after_ms=config.stale_after_ms,
    )
    markets = {event.market for event in events}
    if len(markets) != 1:
        raise ValueError("one snapshot must represent exactly one primary market")
    market = next(iter(markets))

    ordered = tuple(sorted(events, key=lambda event: (event.sequence, event.event_id)))
    facts = _latest_facts(ordered)
    world = WorldState(**{key: facts.get(key, "UNKNOWN") for key in _WORLD_KEYS})
    cross = freeze_facts(cross_market_facts or {})
    portfolio = _portfolio(portfolio_intents)
    hypotheses_sorted = tuple(sorted(hypotheses, key=lambda item: item.hypothesis_id))
    contradictions = tuple(
        sorted(
            {
                *integrity.codes,
                *(
                    f"HYPOTHESIS:{item.hypothesis_id}:{item.status.value}"
                    for item in hypotheses_sorted
                    if item.status
                    in {HypothesisStatus.FALSIFIED, HypothesisStatus.INVALIDATED}
                ),
            }
        )
    )
    uncertainty = _uncertainty(
        integrity,
        hypotheses_sorted,
        len(ordered),
        len(cross),
    )
    position = position_context or PositionContext(
        market=market,
        as_of=generated_at,
        expansion_state=facts.get("expansion_state", "UNKNOWN"),
        contradiction_state=(
            "CONFLICTING" if contradictions else "NO_CONTRADICTION_OBSERVED"
        ),
        liquidity_target_state=facts.get("liquidity_target_state", "UNKNOWN"),
        opposite_displacement_state=facts.get(
            "opposite_displacement_state", "UNKNOWN"
        ),
        volatility_state=facts.get("volatility_state", "UNKNOWN"),
    )

    identity_payload = {
        "version": CORE_STACK_VERSION,
        "generated_at": generated_at.isoformat(),
        "market": market,
        "event_fingerprints": [event.fingerprint() for event in ordered],
        "hypotheses": [item.hypothesis_id for item in hypotheses_sorted],
        "cross_market": list(cross),
        "portfolio": [
            (item.trader_id, item.market, item.side, item.hypothesis_id)
            for item in portfolio.intents
        ],
    }
    digest = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    return CoreSnapshot(
        snapshot_id=f"CORE_SNAPSHOT_{digest[:24]}",
        version=CORE_STACK_VERSION,
        generated_at=generated_at,
        source_cutoff_at=integrity.newest_source_at,
        market=market,
        perception_integrity=integrity,
        world_state=world,
        cross_market_state=cross,
        portfolio_state=portfolio,
        attention_events=_attention(ordered),
        active_hypotheses=hypotheses_sorted,
        contradictions=contradictions,
        uncertainty=uncertainty,
        position_context=position,
        source_event_ids=tuple(event.event_id for event in ordered),
    )
