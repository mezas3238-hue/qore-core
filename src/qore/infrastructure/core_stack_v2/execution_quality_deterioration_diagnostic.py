"""MC-28 execution-quality deterioration diagnostic over real DEMO evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from statistics import median
from typing import Final

IDENTITY: Final = "QORE_SHARED_MC28_EXECUTION_QUALITY_DETERIORATION_001"
MINIMUM_ATTEMPTS_PER_WINDOW: Final = 30
MINIMUM_FILLS_PER_WINDOW: Final = 20
MAX_MEDIAN_SPREAD_RATIO_BPS: Final = 15_000
MIN_MEDIAN_SPREAD_UPLIFT_BPS: Final = 1
MAX_P90_ADVERSE_SLIPPAGE_UPLIFT_BPS: Final = 5
MAX_REJECTION_RATE_UPLIFT_BPS: Final = 500


class ExecutionQualityOutcome(StrEnum):
    FILLED = "FILLED"
    REJECTED = "REJECTED"


class ExecutionQualitySide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class ExecutionQualityStatus(StrEnum):
    PASS = "PASS"
    DETERIORATED = "DETERIORATED"
    INSUFFICIENT = "INSUFFICIENT"


def _aware(value: datetime, *, field: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware datetime")
    return value.astimezone(UTC)


def _bps(value: Decimal) -> int:
    return int(
        value.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def _ratio_bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("ratio denominator must be positive")
    return int(
        (
            Decimal(numerator)
            * Decimal(10_000)
            / Decimal(denominator)
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def _percentile_nearest_rank(values: list[int], percentile: int) -> int:
    if not values:
        raise ValueError("percentile requires values")
    if not 1 <= percentile <= 100:
        raise ValueError("percentile must be within 1..100")
    ordered = sorted(values)
    rank = (percentile * len(ordered) + 99) // 100
    return ordered[max(0, min(rank - 1, len(ordered) - 1))]


@dataclass(frozen=True, slots=True)
class ExecutionQualityObservation:
    observation_id: str
    instrument: str
    side: ExecutionQualitySide
    outcome: ExecutionQualityOutcome
    observed_at: datetime
    quote_bid: Decimal
    quote_ask: Decimal
    fill_price: Decimal | None
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id must be non-empty")
        if not self.instrument.strip():
            raise ValueError("instrument must be non-empty")
        if not isinstance(self.side, ExecutionQualitySide):
            raise ValueError("side must be ExecutionQualitySide")
        if not isinstance(self.outcome, ExecutionQualityOutcome):
            raise ValueError("outcome must be ExecutionQualityOutcome")
        _aware(self.observed_at, field="observed_at")
        for name, value in (
            ("quote_bid", self.quote_bid),
            ("quote_ask", self.quote_ask),
        ):
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= Decimal("0")
            ):
                raise ValueError(f"{name} must be positive finite Decimal")
        if self.quote_ask < self.quote_bid:
            raise ValueError("quote_ask must not be below quote_bid")
        if self.outcome is ExecutionQualityOutcome.FILLED:
            if (
                not isinstance(self.fill_price, Decimal)
                or not self.fill_price.is_finite()
                or self.fill_price <= Decimal("0")
            ):
                raise ValueError("filled observation requires positive fill_price")
        elif self.fill_price is not None:
            raise ValueError("rejected observation cannot carry fill_price")
        if not self.evidence_ref.strip():
            raise ValueError("evidence_ref must be non-empty")

    @property
    def spread_bps(self) -> int:
        midpoint = (self.quote_bid + self.quote_ask) / Decimal("2")
        return _bps(
            (self.quote_ask - self.quote_bid)
            / midpoint
            * Decimal(10_000)
        )

    @property
    def adverse_slippage_bps(self) -> int | None:
        if self.outcome is not ExecutionQualityOutcome.FILLED:
            return None
        assert self.fill_price is not None
        if self.side is ExecutionQualitySide.BUY:
            raw = (
                (self.fill_price - self.quote_ask)
                / self.quote_ask
                * Decimal(10_000)
            )
        else:
            raw = (
                (self.quote_bid - self.fill_price)
                / self.quote_bid
                * Decimal(10_000)
            )
        return _bps(raw)


@dataclass(frozen=True, slots=True)
class ExecutionQualityWindowMetrics:
    attempt_count: int
    fill_count: int
    rejection_count: int
    median_spread_bps: int
    p90_adverse_slippage_bps: int
    rejection_rate_bps: int


@dataclass(frozen=True, slots=True)
class ExecutionQualityAssessment:
    status: ExecutionQualityStatus
    instrument: str | None
    baseline: ExecutionQualityWindowMetrics | None
    recent: ExecutionQualityWindowMetrics | None
    spread_ratio_bps: int | None
    spread_uplift_bps: int | None
    p90_slippage_uplift_bps: int | None
    rejection_rate_uplift_bps: int | None
    reason_codes: tuple[str, ...]

    @property
    def diagnostic_pass(self) -> bool:
        return self.status is ExecutionQualityStatus.PASS


def _validate_window(
    rows: tuple[ExecutionQualityObservation, ...],
) -> tuple[str | None, tuple[ExecutionQualityObservation, ...]]:
    if not rows:
        return None, rows
    instruments = {row.instrument for row in rows}
    if len(instruments) != 1:
        raise ValueError("execution-quality window must contain one instrument")
    ordered = tuple(
        sorted(
            rows,
            key=lambda row: (
                _aware(row.observed_at, field="observed_at"),
                row.observation_id,
            ),
        )
    )
    if len({row.observation_id for row in ordered}) != len(ordered):
        raise ValueError("execution-quality observation ids must be unique")
    return next(iter(instruments)), ordered


def _metrics(
    rows: tuple[ExecutionQualityObservation, ...],
) -> ExecutionQualityWindowMetrics | None:
    if len(rows) < MINIMUM_ATTEMPTS_PER_WINDOW:
        return None
    fills = [
        row
        for row in rows
        if row.outcome is ExecutionQualityOutcome.FILLED
    ]
    if len(fills) < MINIMUM_FILLS_PER_WINDOW:
        return None
    spreads = [row.spread_bps for row in rows]
    slippage = [
        value
        for row in fills
        for value in (row.adverse_slippage_bps,)
        if value is not None
    ]
    rejections = sum(
        row.outcome is ExecutionQualityOutcome.REJECTED
        for row in rows
    )
    return ExecutionQualityWindowMetrics(
        attempt_count=len(rows),
        fill_count=len(fills),
        rejection_count=rejections,
        median_spread_bps=int(median(spreads)),
        p90_adverse_slippage_bps=_percentile_nearest_rank(
            slippage,
            90,
        ),
        rejection_rate_bps=_ratio_bps(rejections, len(rows)),
    )


def assess_execution_quality(
    *,
    baseline: tuple[ExecutionQualityObservation, ...],
    recent: tuple[ExecutionQualityObservation, ...],
) -> ExecutionQualityAssessment:
    baseline_instrument, baseline_rows = _validate_window(baseline)
    recent_instrument, recent_rows = _validate_window(recent)
    if (
        baseline_instrument is not None
        and recent_instrument is not None
        and baseline_instrument != recent_instrument
    ):
        raise ValueError("baseline and recent instrument must match")

    instrument = baseline_instrument or recent_instrument
    baseline_metrics = _metrics(baseline_rows)
    recent_metrics = _metrics(recent_rows)
    if baseline_metrics is None or recent_metrics is None:
        return ExecutionQualityAssessment(
            status=ExecutionQualityStatus.INSUFFICIENT,
            instrument=instrument,
            baseline=baseline_metrics,
            recent=recent_metrics,
            spread_ratio_bps=None,
            spread_uplift_bps=None,
            p90_slippage_uplift_bps=None,
            rejection_rate_uplift_bps=None,
            reason_codes=("INSUFFICIENT_REAL_EXECUTION_EVIDENCE",),
        )

    baseline_spread = max(1, baseline_metrics.median_spread_bps)
    spread_ratio = _ratio_bps(
        recent_metrics.median_spread_bps,
        baseline_spread,
    )
    spread_uplift = (
        recent_metrics.median_spread_bps
        - baseline_metrics.median_spread_bps
    )
    slippage_uplift = (
        recent_metrics.p90_adverse_slippage_bps
        - baseline_metrics.p90_adverse_slippage_bps
    )
    rejection_uplift = (
        recent_metrics.rejection_rate_bps
        - baseline_metrics.rejection_rate_bps
    )

    reasons: list[str] = []
    if (
        spread_ratio > MAX_MEDIAN_SPREAD_RATIO_BPS
        and spread_uplift >= MIN_MEDIAN_SPREAD_UPLIFT_BPS
    ):
        reasons.append("MEDIAN_SPREAD_DETERIORATION")
    if slippage_uplift > MAX_P90_ADVERSE_SLIPPAGE_UPLIFT_BPS:
        reasons.append("P90_ADVERSE_SLIPPAGE_DETERIORATION")
    if rejection_uplift > MAX_REJECTION_RATE_UPLIFT_BPS:
        reasons.append("REJECTION_RATE_DETERIORATION")

    if reasons:
        status = ExecutionQualityStatus.DETERIORATED
    else:
        status = ExecutionQualityStatus.PASS
        reasons.append("EXECUTION_QUALITY_WITHIN_FROZEN_LIMITS")

    return ExecutionQualityAssessment(
        status=status,
        instrument=instrument,
        baseline=baseline_metrics,
        recent=recent_metrics,
        spread_ratio_bps=spread_ratio,
        spread_uplift_bps=spread_uplift,
        p90_slippage_uplift_bps=slippage_uplift,
        rejection_rate_uplift_bps=rejection_uplift,
        reason_codes=tuple(sorted(reasons)),
    )
