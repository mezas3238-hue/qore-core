"""Market-situation and journey-intelligence contracts for Shared Core.

Shared must understand the market, not merely filter entries. This layer
represents causal market state and post-entry journey capacity. It has no order,
risk, stop, target, or execution authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum


class MarketMode(StrEnum):
    TREND = "TREND"
    RANGE = "RANGE"
    TRANSITION = "TRANSITION"
    ANOMALOUS = "ANOMALOUS"
    UNRESOLVED = "UNRESOLVED"


class JourneyDisposition(StrEnum):
    EXTEND_SUPPORTED = "EXTEND_SUPPORTED"
    HOLD_ORIGINAL_TARGET = "HOLD_ORIGINAL_TARGET"
    DEFEND_LOSS = "DEFEND_LOSS"
    EXIT_RISK_WARNING = "EXIT_RISK_WARNING"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class MarketSituationEvidence:
    market: str
    as_of: datetime
    evidence_cutoff_at: datetime
    anomaly_state: str
    volatility_state: str
    trend_state: str
    range_state: str
    regime_state: str
    regime_transition_state: str
    liquidity_state: str
    structure_state: str
    displacement_state: str
    compression_state: str
    expansion_state: str
    exhaustion_state: str
    cross_market_state: str
    historical_analog_state: str
    uncertainty_state: str

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if (
            self.evidence_cutoff_at.tzinfo is None
            or self.evidence_cutoff_at.utcoffset() is None
        ):
            raise ValueError("evidence_cutoff_at must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future market evidence is forbidden")


@dataclass(frozen=True, slots=True)
class SharedMarketSituation:
    market: str
    as_of: datetime
    mode: MarketMode
    anomaly_state: str
    volatility_state: str
    trend_state: str
    range_state: str
    regime_state: str
    regime_transition_state: str
    liquidity_state: str
    structure_state: str
    displacement_state: str
    compression_state: str
    expansion_state: str
    exhaustion_state: str
    cross_market_state: str
    historical_analog_state: str
    uncertainty_state: str
    confidence_bps: int
    evidence_cutoff_at: datetime

    def __post_init__(self) -> None:
        if not 0 <= self.confidence_bps <= 10_000:
            raise ValueError("confidence_bps must be within 0..10000")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future market evidence is forbidden")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["as_of"] = self.as_of.astimezone(UTC).isoformat()
        payload["evidence_cutoff_at"] = self.evidence_cutoff_at.astimezone(
            UTC
        ).isoformat()
        payload["mode"] = self.mode.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedJourneyIntelligence:
    market: str
    as_of: datetime
    disposition: JourneyDisposition
    target_capacity_state: str
    loss_defense_state: str
    supporting_evidence: tuple[str, ...]
    contradictory_evidence: tuple[str, ...]
    uncertainty_reasons: tuple[str, ...]
    confidence_bps: int
    evidence_cutoff_at: datetime
    order_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    stop_widening_allowed: bool = False
    target_mutation_authority: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.confidence_bps <= 10_000:
            raise ValueError("confidence_bps must be within 0..10000")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future journey evidence is forbidden")
        if (
            self.order_authority
            or self.risk_authority
            or self.execution_authority
            or self.stop_widening_allowed
            or self.target_mutation_authority
        ):
            raise ValueError(
                "Shared journey intelligence cannot carry trading authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["as_of"] = self.as_of.astimezone(UTC).isoformat()
        payload["evidence_cutoff_at"] = self.evidence_cutoff_at.astimezone(
            UTC
        ).isoformat()
        payload["disposition"] = self.disposition.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
