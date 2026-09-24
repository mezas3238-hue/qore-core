"""Authority-free contracts for QORE CORE STACK V2.

The shared Core represents causal facts and uncertainty. It never owns strategy,
capital, risk, or execution authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Final


CORE_STACK_VERSION: Final = "2.0.0-research"


class KnowledgeState(StrEnum):
    KNOW = "I_KNOW"
    THINK = "I_THINK"
    UNCERTAIN = "I_AM_UNCERTAIN"
    CONFLICT = "EVIDENCE_CONFLICTS"
    INSUFFICIENT = "DATA_IS_INSUFFICIENT"


class HypothesisStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WAIT = "WAIT"
    CONFIRMED = "CONFIRMED"
    FALSIFIED = "FALSIFIED"
    INVALIDATED = "INVALIDATED"


class CognitiveState(StrEnum):
    PASS = "PASS"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"
    INVALIDATED = "INVALIDATED"


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def freeze_facts(values: dict[str, str]) -> tuple[tuple[str, str], ...]:
    """Canonicalize a small factual mapping for deterministic hashing."""
    if any(not key or not value for key, value in values.items()):
        raise ValueError("fact keys and values must be non-empty")
    return tuple(sorted(values.items()))


@dataclass(frozen=True, slots=True)
class MarketEvent:
    event_id: str
    market: str
    event_type: str
    source_at: datetime
    observed_at: datetime
    sequence: int
    complete: bool
    timeframe_seconds: int | None
    facts: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.event_id or not self.market or not self.event_type:
            raise ValueError("event identity fields must be non-empty")
        _iso(self.source_at)
        _iso(self.observed_at)
        if self.source_at > self.observed_at:
            raise ValueError("source_at cannot be after observed_at")
        if self.sequence < 0:
            raise ValueError("sequence cannot be negative")
        if self.timeframe_seconds is not None and self.timeframe_seconds <= 0:
            raise ValueError("timeframe_seconds must be positive")
        if self.facts != tuple(sorted(self.facts)):
            raise ValueError("facts must be canonical/sorted")
        if len({key for key, _ in self.facts}) != len(self.facts):
            raise ValueError("facts cannot contain duplicate keys")

    def payload(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "market": self.market,
            "event_type": self.event_type,
            "source_at": _iso(self.source_at),
            "observed_at": _iso(self.observed_at),
            "sequence": self.sequence,
            "complete": self.complete,
            "timeframe_seconds": self.timeframe_seconds,
            "facts": list(self.facts),
        }

    def fingerprint(self) -> str:
        raw = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PerceptionIntegrity:
    valid: bool
    codes: tuple[str, ...]
    state_age_ms: int
    newest_source_at: datetime

    def __post_init__(self) -> None:
        if self.state_age_ms < 0:
            raise ValueError("state_age_ms cannot be negative")
        _iso(self.newest_source_at)


@dataclass(frozen=True, slots=True)
class WorldState:
    market_state: str
    session_state: str
    liquidity_state: str
    structure_state: str
    volatility_state: str
    expansion_state: str
    compression_state: str
    directional_state: str
    reversal_state: str
    continuation_state: str


@dataclass(frozen=True, slots=True)
class CoreHypothesis:
    hypothesis_id: str
    market: str
    thesis: str
    status: HypothesisStatus
    supporting_event_ids: tuple[str, ...]
    contradictory_event_ids: tuple[str, ...]
    confidence_bps: int
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.market or not self.thesis:
            raise ValueError("hypothesis identity must be non-empty")
        if not 0 <= self.confidence_bps <= 10_000:
            raise ValueError("confidence_bps must be within 0..10000")
        _iso(self.updated_at)


@dataclass(frozen=True, slots=True)
class UncertaintyState:
    knowledge_state: KnowledgeState
    context_confidence_bps: int
    data_integrity_bps: int
    evidence_strength_bps: int
    contradiction_level_bps: int
    regime_confidence_bps: int
    cross_market_confirmation_bps: int
    state_age_ms: int

    def __post_init__(self) -> None:
        for value in (
            self.context_confidence_bps,
            self.data_integrity_bps,
            self.evidence_strength_bps,
            self.contradiction_level_bps,
            self.regime_confidence_bps,
            self.cross_market_confirmation_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("uncertainty basis points must be within 0..10000")
        if self.state_age_ms < 0:
            raise ValueError("state_age_ms cannot be negative")


@dataclass(frozen=True, slots=True)
class PortfolioIntent:
    trader_id: str
    market: str
    side: str
    hypothesis_id: str
    factor_tags: tuple[str, ...]
    generated_at: datetime
    order_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if self.side not in {"LONG", "SHORT"}:
            raise ValueError("side must be LONG or SHORT")
        if self.order_authority or self.risk_authority:
            raise ValueError("portfolio intent cannot carry order/risk authority")
        _iso(self.generated_at)


@dataclass(frozen=True, slots=True)
class PortfolioSituation:
    intents: tuple[PortfolioIntent, ...]
    duplicated_exposures: tuple[str, ...]
    factor_clusters: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PositionContext:
    market: str
    as_of: datetime
    expansion_state: str
    contradiction_state: str
    liquidity_target_state: str
    opposite_displacement_state: str
    volatility_state: str

    def __post_init__(self) -> None:
        _iso(self.as_of)


@dataclass(frozen=True, slots=True)
class CoreSnapshot:
    snapshot_id: str
    version: str
    generated_at: datetime
    source_cutoff_at: datetime
    market: str
    perception_integrity: PerceptionIntegrity
    world_state: WorldState
    cross_market_state: tuple[tuple[str, str], ...]
    portfolio_state: PortfolioSituation
    attention_events: tuple[str, ...]
    active_hypotheses: tuple[CoreHypothesis, ...]
    contradictions: tuple[str, ...]
    uncertainty: UncertaintyState
    position_context: PositionContext
    source_event_ids: tuple[str, ...]
    order_authority: bool = False
    risk_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        if not self.snapshot_id or not self.market:
            raise ValueError("snapshot identity must be non-empty")
        _iso(self.generated_at)
        _iso(self.source_cutoff_at)
        if self.source_cutoff_at > self.generated_at:
            raise ValueError("source cutoff cannot be in the future")
        if (
            self.order_authority
            or self.risk_authority
            or self.strategy_mutation_authority
        ):
            raise ValueError("CoreSnapshot cannot carry trading authority")
        if self.cross_market_state != tuple(sorted(self.cross_market_state)):
            raise ValueError("cross_market_state must be canonical/sorted")

    def payload(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "version": self.version,
            "generated_at": _iso(self.generated_at),
            "source_cutoff_at": _iso(self.source_cutoff_at),
            "market": self.market,
            "perception_integrity": {
                **asdict(self.perception_integrity),
                "newest_source_at": _iso(self.perception_integrity.newest_source_at),
            },
            "world_state": asdict(self.world_state),
            "cross_market_state": list(self.cross_market_state),
            "portfolio_state": {
                "intents": [
                    {
                        **asdict(intent),
                        "generated_at": _iso(intent.generated_at),
                    }
                    for intent in self.portfolio_state.intents
                ],
                "duplicated_exposures": self.portfolio_state.duplicated_exposures,
                "factor_clusters": self.portfolio_state.factor_clusters,
            },
            "attention_events": self.attention_events,
            "active_hypotheses": [
                {
                    **asdict(item),
                    "updated_at": _iso(item.updated_at),
                    "status": item.status.value,
                }
                for item in self.active_hypotheses
            ],
            "contradictions": self.contradictions,
            "uncertainty": {
                **asdict(self.uncertainty),
                "knowledge_state": self.uncertainty.knowledge_state.value,
            },
            "position_context": {
                **asdict(self.position_context),
                "as_of": _iso(self.position_context.as_of),
            },
            "source_event_ids": self.source_event_ids,
            "order_authority": self.order_authority,
            "risk_authority": self.risk_authority,
            "strategy_mutation_authority": self.strategy_mutation_authority,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
