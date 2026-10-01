from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.core_stack_v2.execution_quality_deterioration_diagnostic import (
    ExecutionQualityObservation,
    ExecutionQualityOutcome,
    ExecutionQualitySide,
    ExecutionQualityStatus,
    assess_execution_quality,
)


_BASE = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _row(
    index: int,
    *,
    recent: bool,
    outcome: ExecutionQualityOutcome = ExecutionQualityOutcome.FILLED,
    spread_bps: int = 2,
    adverse_slippage_bps: int = 0,
) -> ExecutionQualityObservation:
    mid = Decimal("100")
    half_spread = (
        mid
        * Decimal(spread_bps)
        / Decimal(20_000)
    )
    bid = mid - half_spread
    ask = mid + half_spread
    side = ExecutionQualitySide.BUY
    fill = None
    if outcome is ExecutionQualityOutcome.FILLED:
        fill = ask * (
            Decimal("1")
            + Decimal(adverse_slippage_bps) / Decimal(10_000)
        )
    return ExecutionQualityObservation(
        observation_id=f"{'R' if recent else 'B'}-{index:03d}",
        instrument="EURUSD",
        side=side,
        outcome=outcome,
        observed_at=_BASE
        + timedelta(days=1 if recent else 0, minutes=index),
        quote_bid=bid,
        quote_ask=ask,
        fill_price=fill,
        evidence_ref=f"sealed:{'r' if recent else 'b'}:{index}",
    )


def test_execution_quality_passes_stable_real_population() -> None:
    baseline = tuple(_row(i, recent=False) for i in range(30))
    recent = tuple(_row(i, recent=True) for i in range(30))
    result = assess_execution_quality(
        baseline=baseline,
        recent=recent,
    )
    assert result.status is ExecutionQualityStatus.PASS
    assert result.diagnostic_pass is True


def test_execution_quality_detects_spread_slippage_and_rejections() -> None:
    baseline = tuple(_row(i, recent=False) for i in range(30))
    recent = tuple(
        _row(
            i,
            recent=True,
            outcome=(
                ExecutionQualityOutcome.REJECTED
                if i < 5
                else ExecutionQualityOutcome.FILLED
            ),
            spread_bps=5,
            adverse_slippage_bps=10,
        )
        for i in range(30)
    )
    result = assess_execution_quality(
        baseline=baseline,
        recent=recent,
    )
    assert result.status is ExecutionQualityStatus.DETERIORATED
    assert "MEDIAN_SPREAD_DETERIORATION" in result.reason_codes
    assert "P90_ADVERSE_SLIPPAGE_DETERIORATION" in result.reason_codes
    assert "REJECTION_RATE_DETERIORATION" in result.reason_codes


def test_execution_quality_abstains_without_real_population() -> None:
    baseline = tuple(_row(i, recent=False) for i in range(10))
    recent = tuple(_row(i, recent=True) for i in range(10))
    result = assess_execution_quality(
        baseline=baseline,
        recent=recent,
    )
    assert result.status is ExecutionQualityStatus.INSUFFICIENT
    assert result.diagnostic_pass is False
    assert result.reason_codes == (
        "INSUFFICIENT_REAL_EXECUTION_EVIDENCE",
    )


def test_execution_quality_rejects_mixed_instrument_population() -> None:
    baseline = list(_row(i, recent=False) for i in range(30))
    baseline[0] = ExecutionQualityObservation(
        observation_id="OTHER",
        instrument="XAUUSD",
        side=ExecutionQualitySide.BUY,
        outcome=ExecutionQualityOutcome.FILLED,
        observed_at=_BASE,
        quote_bid=Decimal("1999"),
        quote_ask=Decimal("2001"),
        fill_price=Decimal("2001"),
        evidence_ref="sealed:other",
    )
    with pytest.raises(ValueError, match="one instrument"):
        assess_execution_quality(
            baseline=tuple(baseline),
            recent=tuple(_row(i, recent=True) for i in range(30)),
        )
