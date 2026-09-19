"""Causal state contracts for the QORE Capitalizer fast brain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    EvidenceStrength,
    ExecutionQuality,
    MarketState,
)


def _require_non_negative(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{field_name} must be a finite non-negative Decimal")


@dataclass(frozen=True, slots=True)
class CapitalizerExecutionState:
    """Decision-time execution environment; never an assumed broker constant."""

    spread_points: Decimal
    commission_cost_r: Decimal
    expected_slippage_r: Decimal
    quote_age_ms: int
    observed_latency_ms: int
    quality: ExecutionQuality

    def __post_init__(self) -> None:
        _require_non_negative(self.spread_points, field_name="spread_points")
        _require_non_negative(self.commission_cost_r, field_name="commission_cost_r")
        _require_non_negative(self.expected_slippage_r, field_name="expected_slippage_r")
        if self.quote_age_ms < 0:
            raise ValueError("quote_age_ms must be non-negative")
        if self.observed_latency_ms < 0:
            raise ValueError("observed_latency_ms must be non-negative")


@dataclass(frozen=True, slots=True)
class CapitalizerSituationModel:
    """Ephemeral causal snapshot used by the boundary-critical reasoner.

    Every field must be knowable at decision time. Terminal trade outcomes, future bars,
    future MFE/MAE and later target touches do not belong here.
    """

    symbol: str
    session: CapitalizerSession
    observed_at: datetime
    hypothesis_id: str
    source_event_id: str
    event_generation: int
    market_state: MarketState
    evidence_strength: EvidenceStrength
    execution: CapitalizerExecutionState
    strategy_trigger_ready: bool
    displacement_confirmed: bool
    destination_available: bool
    late_entry: bool
    correlated_exposure_blocked: bool
    contradictions: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()
    failure_state_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be a non-empty uppercase token")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id must be non-empty")
        if not self.source_event_id:
            raise ValueError("source_event_id must be non-empty")
        if self.event_generation < 1:
            raise ValueError("event_generation must be >= 1")
        if self.failure_state_fingerprint == "":
            raise ValueError("failure_state_fingerprint cannot be empty")
