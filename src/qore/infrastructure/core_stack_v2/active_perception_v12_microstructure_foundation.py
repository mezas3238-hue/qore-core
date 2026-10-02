"""Outcome-blind causal microstructure foundation for WP-05 V12.

The representation consumes only independently retained BID/ASK provider events
that are already available at-or-before one evaluation timestamp.  It never
forces one-to-one quote pairing and it has no target, model or trading
authority.

Numerical staleness limits and the final feature set are intentionally caller
supplied until the source-only integrity/coverage audit freezes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from qore.infrastructure.historical_quote_side_evidence import (
    HistoricalQuoteSideObservation,
)
from qore.infrastructure.market_observation import MarketPriceSide


class V12MicrostructureAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class V12MicrostructureWindowStats:
    window_ms: int
    bid_update_count: int
    ask_update_count: int
    update_imbalance_bps: int
    bid_path_variation: int
    ask_path_variation: int
    bid_displacement: int
    ask_displacement: int

    def __post_init__(self) -> None:
        if self.window_ms <= 0:
            raise ValueError("window_ms must be positive")
        if self.bid_update_count < 0 or self.ask_update_count < 0:
            raise ValueError("update counts cannot be negative")
        if not -10_000 <= self.update_imbalance_bps <= 10_000:
            raise ValueError("update imbalance must be within -10000..10000")
        if self.bid_path_variation < 0 or self.ask_path_variation < 0:
            raise ValueError("path variation cannot be negative")


@dataclass(frozen=True, slots=True)
class V12CausalMicrostructureSnapshot:
    evaluation_at: datetime
    staleness_limit_ms: int
    availability: V12MicrostructureAvailability
    bid_age_ms: int | None
    ask_age_ms: int | None
    bid_relative_price: int | None
    ask_relative_price: int | None
    spread_relative_price: int | None
    crossed_quote: bool | None
    side_age_skew_ms: int | None
    windows: tuple[V12MicrostructureWindowStats, ...]
    target_or_outcome_read: bool = False
    methodology_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.evaluation_at.tzinfo is None or self.evaluation_at.utcoffset() is None:
            raise ValueError("evaluation_at must be timezone-aware")
        if self.staleness_limit_ms <= 0:
            raise ValueError("staleness_limit_ms must be positive")
        if self.target_or_outcome_read:
            raise ValueError("microstructure snapshot cannot read target/outcome")
        if (
            self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("microstructure snapshot cannot carry trading authority")
        if self.availability is V12MicrostructureAvailability.AVAILABLE:
            if (
                self.bid_age_ms is None
                or self.ask_age_ms is None
                or self.bid_relative_price is None
                or self.ask_relative_price is None
                or self.spread_relative_price is None
                or self.crossed_quote is None
                or self.side_age_skew_ms is None
            ):
                raise ValueError("available snapshot requires complete two-side state")
        elif self.spread_relative_price is not None or self.crossed_quote is not None:
            raise ValueError("insufficient snapshot cannot synthesize a spread")


def _utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def _validate_side_stream(
    observations: tuple[HistoricalQuoteSideObservation, ...],
    *,
    expected_side: MarketPriceSide,
    evaluation_at: datetime,
) -> None:
    previous: datetime | None = None
    identity: tuple[object, ...] | None = None
    for item in observations:
        if item.quote_side is not expected_side:
            raise ValueError("quote-side stream contains wrong side")
        event_at = _utc(item.provider_event_at, field="provider_event_at")
        if event_at > evaluation_at:
            raise ValueError("future provider event supplied to causal representation")
        if previous is not None and event_at < previous:
            raise ValueError("quote-side stream must be chronological")
        previous = event_at
        current_identity = (
            item.instrument.symbol,
            item.provider_account_id,
            item.provider_symbol_id,
            item.provider_symbol,
        )
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise ValueError("quote-side stream changed provider identity")


def _latest_age_ms(
    observations: tuple[HistoricalQuoteSideObservation, ...],
    *,
    evaluation_at: datetime,
) -> tuple[int, int] | None:
    if not observations:
        return None
    latest = observations[-1]
    age_ms = int(
        (evaluation_at - latest.provider_event_at.astimezone(UTC)).total_seconds()
        * 1000
    )
    if age_ms < 0:
        raise ValueError("future quote escaped causal guard")
    return age_ms, latest.relative_price


def _trunc_ratio_bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    magnitude = abs(numerator) * 10_000 // denominator
    return magnitude if numerator >= 0 else -magnitude


def _window_side_stats(
    observations: tuple[HistoricalQuoteSideObservation, ...],
    *,
    evaluation_at: datetime,
    window_ms: int,
) -> tuple[int, int, int]:
    cutoff = evaluation_at - timedelta(milliseconds=window_ms)
    selected = tuple(
        item
        for item in observations
        if cutoff < item.provider_event_at.astimezone(UTC) <= evaluation_at
    )
    if not selected:
        return 0, 0, 0
    variation = sum(
        abs(right.relative_price - left.relative_price)
        for left, right in zip(selected, selected[1:], strict=False)
    )
    displacement = selected[-1].relative_price - selected[0].relative_price
    return len(selected), variation, displacement


def build_v12_causal_microstructure_snapshot(
    *,
    bid_observations: tuple[HistoricalQuoteSideObservation, ...],
    ask_observations: tuple[HistoricalQuoteSideObservation, ...],
    evaluation_at: datetime,
    staleness_limit_ms: int,
    windows_ms: tuple[int, ...] = (1_000, 5_000, 15_000, 60_000),
) -> V12CausalMicrostructureSnapshot:
    """Build source-only as-of state from independent BID and ASK streams."""

    evaluation = _utc(evaluation_at, field="evaluation_at")
    if type(staleness_limit_ms) is not int or staleness_limit_ms <= 0:
        raise ValueError("staleness_limit_ms must be positive int")
    if (
        not windows_ms
        or any(type(value) is not int or value <= 0 for value in windows_ms)
        or tuple(sorted(set(windows_ms))) != windows_ms
    ):
        raise ValueError("windows_ms must be unique positive ascending ints")

    _validate_side_stream(
        bid_observations,
        expected_side=MarketPriceSide.BID,
        evaluation_at=evaluation,
    )
    _validate_side_stream(
        ask_observations,
        expected_side=MarketPriceSide.ASK,
        evaluation_at=evaluation,
    )
    if bid_observations and ask_observations:
        bid_identity = (
            bid_observations[-1].instrument.symbol,
            bid_observations[-1].provider_account_id,
            bid_observations[-1].provider_symbol_id,
            bid_observations[-1].provider_symbol,
        )
        ask_identity = (
            ask_observations[-1].instrument.symbol,
            ask_observations[-1].provider_account_id,
            ask_observations[-1].provider_symbol_id,
            ask_observations[-1].provider_symbol,
        )
        if bid_identity != ask_identity:
            raise ValueError("BID and ASK streams have different provider identity")

    bid_latest = _latest_age_ms(bid_observations, evaluation_at=evaluation)
    ask_latest = _latest_age_ms(ask_observations, evaluation_at=evaluation)
    bid_age = None if bid_latest is None else bid_latest[0]
    ask_age = None if ask_latest is None else ask_latest[0]
    bid_price = None if bid_latest is None else bid_latest[1]
    ask_price = None if ask_latest is None else ask_latest[1]

    available = (
        bid_age is not None
        and ask_age is not None
        and bid_age <= staleness_limit_ms
        and ask_age <= staleness_limit_ms
    )
    spread = (
        ask_price - bid_price
        if available and ask_price is not None and bid_price is not None
        else None
    )
    crossed = None if spread is None else spread < 0
    age_skew = (
        bid_age - ask_age
        if available and bid_age is not None and ask_age is not None
        else None
    )

    window_stats: list[V12MicrostructureWindowStats] = []
    for window_ms in windows_ms:
        bid_count, bid_variation, bid_displacement = _window_side_stats(
            bid_observations,
            evaluation_at=evaluation,
            window_ms=window_ms,
        )
        ask_count, ask_variation, ask_displacement = _window_side_stats(
            ask_observations,
            evaluation_at=evaluation,
            window_ms=window_ms,
        )
        total = bid_count + ask_count
        window_stats.append(
            V12MicrostructureWindowStats(
                window_ms=window_ms,
                bid_update_count=bid_count,
                ask_update_count=ask_count,
                update_imbalance_bps=_trunc_ratio_bps(
                    bid_count - ask_count,
                    total,
                ),
                bid_path_variation=bid_variation,
                ask_path_variation=ask_variation,
                bid_displacement=bid_displacement,
                ask_displacement=ask_displacement,
            )
        )

    return V12CausalMicrostructureSnapshot(
        evaluation_at=evaluation,
        staleness_limit_ms=staleness_limit_ms,
        availability=(
            V12MicrostructureAvailability.AVAILABLE
            if available
            else V12MicrostructureAvailability.INSUFFICIENT
        ),
        bid_age_ms=bid_age,
        ask_age_ms=ask_age,
        bid_relative_price=bid_price,
        ask_relative_price=ask_price,
        spread_relative_price=spread,
        crossed_quote=crossed,
        side_age_skew_ms=age_skew,
        windows=tuple(window_stats),
    )
