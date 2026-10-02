"""Authority-free intelligence contracts for Shared Core V2.

These contracts make the capabilities in the Owner freeze executable rather than
merely descriptive. They contain market/context intelligence only: no setup,
entry, stop, target, risk, order or execution authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum


class OpportunityDisposition(StrEnum):
    FAVORABLE = "FAVORABLE"
    NEUTRAL = "NEUTRAL"
    CAUTION = "CAUTION"
    CONFLICT = "CONFLICT"
    INSUFFICIENT = "INSUFFICIENT"


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class RegimeVector:
    as_of: datetime
    volatility: str
    structure: str
    liquidity: str
    directional: str
    compression: str
    expansion: str
    transition_from: str
    transition_to: str
    transition_confidence_bps: int

    def __post_init__(self) -> None:
        _iso(self.as_of)
        if not 0 <= self.transition_confidence_bps <= 10_000:
            raise ValueError("transition confidence must be within 0..10000")


@dataclass(frozen=True, slots=True)
class CausalEdge:
    source: str
    relation: str
    target: str
    evidence_ids: tuple[str, ...]
    confidence_bps: int
    observable_at: datetime

    def __post_init__(self) -> None:
        if not self.source or not self.relation or not self.target:
            raise ValueError("causal edge identity must be non-empty")
        if not 0 <= self.confidence_bps <= 10_000:
            raise ValueError("edge confidence must be within 0..10000")
        _iso(self.observable_at)


@dataclass(frozen=True, slots=True)
class SituationGraph:
    market: str
    as_of: datetime
    nodes: tuple[tuple[str, str], ...]
    edges: tuple[CausalEdge, ...]
    contradictions: tuple[str, ...]

    def __post_init__(self) -> None:
        _iso(self.as_of)
        if self.nodes != tuple(sorted(self.nodes)):
            raise ValueError("situation nodes must be canonical")
        if any(edge.observable_at > self.as_of for edge in self.edges):
            raise ValueError("future causal edge forbidden")


@dataclass(frozen=True, slots=True)
class HistoricalAnalogEvidence:
    episode_id: str
    market: str
    closed_at: datetime
    similarity_bps: int
    predecision_signature: tuple[tuple[str, str], ...]
    terminal_r: str

    def __post_init__(self) -> None:
        _iso(self.closed_at)
        if not 0 <= self.similarity_bps <= 10_000:
            raise ValueError("similarity must be within 0..10000")


@dataclass(frozen=True, slots=True)
class AnalogSummary:
    as_of: datetime
    analogs: tuple[HistoricalAnalogEvidence, ...]
    effective_sample_size: str
    weighted_mean_r: str | None
    weighted_loss_rate: str | None
    confidence_bps: int

    def __post_init__(self) -> None:
        _iso(self.as_of)
        if any(item.closed_at >= self.as_of for item in self.analogs):
            raise ValueError("current/future episode cannot be historical analog")
        if not 0 <= self.confidence_bps <= 10_000:
            raise ValueError("analog confidence must be within 0..10000")


@dataclass(frozen=True, slots=True)
class FailurePatternEvidence:
    pattern_id: str
    description: str
    support_count: int
    loss_count: int
    winner_count: int
    estimated_loss_rate: str | None
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.support_count < 0 or self.loss_count < 0 or self.winner_count < 0:
            raise ValueError("failure counts cannot be negative")
        if self.loss_count + self.winner_count > self.support_count:
            raise ValueError("failure outcomes cannot exceed support count")


@dataclass(frozen=True, slots=True)
class CrossMarketRelation:
    source_market: str
    target_market: str
    relation: str
    state: str
    observed_at: datetime
    confidence_bps: int

    def __post_init__(self) -> None:
        _iso(self.observed_at)
        if not 0 <= self.confidence_bps <= 10_000:
            raise ValueError("cross-market confidence must be within 0..10000")


@dataclass(frozen=True, slots=True)
class HypothesisView:
    hypothesis_id: str
    thesis: str
    support_bps: int
    contradiction_bps: int
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (self.support_bps, self.contradiction_bps):
            if not 0 <= value <= 10_000:
                raise ValueError("hypothesis basis points must be within 0..10000")


@dataclass(frozen=True, slots=True)
class TraderOpportunityContext:
    trader_id: str
    market: str
    as_of: datetime
    disposition: OpportunityDisposition
    regime: RegimeVector
    situation: SituationGraph
    analog_summary: AnalogSummary
    failure_patterns: tuple[FailurePatternEvidence, ...]
    cross_market: tuple[CrossMarketRelation, ...]
    hypotheses: tuple[HypothesisView, ...]
    support_reasons: tuple[str, ...]
    contradiction_reasons: tuple[str, ...]
    uncertainty_reasons: tuple[str, ...]
    order_authority: bool = False
    risk_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        _iso(self.as_of)
        if self.regime.as_of > self.as_of or self.situation.as_of > self.as_of:
            raise ValueError("future situation/regime forbidden")
        if any(item.observed_at > self.as_of for item in self.cross_market):
            raise ValueError("future cross-market observation forbidden")
        if (
            self.order_authority
            or self.risk_authority
            or self.strategy_mutation_authority
        ):
            raise ValueError("Shared intelligence cannot carry trading authority")

    def payload(self) -> dict[str, object]:
        def encode(value: object) -> object:
            if isinstance(value, datetime):
                return _iso(value)
            if isinstance(value, StrEnum):
                return value.value
            if isinstance(value, tuple):
                return [encode(item) for item in value]
            if isinstance(value, list):
                return [encode(item) for item in value]
            if isinstance(value, dict):
                return {str(k): encode(v) for k, v in value.items()}
            return value

        return encode(asdict(self))  # type: ignore[return-value]

    def fingerprint(self) -> str:
        raw = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
