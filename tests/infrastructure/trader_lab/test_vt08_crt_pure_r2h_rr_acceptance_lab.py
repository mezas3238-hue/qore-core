from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import AggregatedCandle
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2h_rr_acceptance_lab import (
    BASE_POLICY,
    RR_THRESHOLDS,
    CompetitionPolicy,
    projected_rr,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _candle(opened_at: datetime) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=4),
        open_price=100,
        high_price=120,
        low_price=80,
        close_price=100,
        m5_count=48,
    )


def _parent(direction: CrtPureCandidateDirection) -> ParentCrt:
    opened_at = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    return ParentCrt(
        market=CrtPureMarket.AUDUSD,
        direction=direction,
        triplet="1",
        c3_opened_at=opened_at,
        c3_closed_at=opened_at + timedelta(hours=4),
        c1=_candle(opened_at - timedelta(hours=8)),
        c2=_candle(opened_at - timedelta(hours=4)),
        c3_m5=(),
    )


def _bar(
    opened_at: datetime,
    open_price: int,
    high_price: int,
    low_price: int,
    close_price: int,
) -> M15Bar:
    return M15Bar(
        opened_at=opened_at,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
    )


def test_rr_threshold_family_is_frozen() -> None:
    assert RR_THRESHOLDS == (
        Decimal("0.00"),
        Decimal("0.50"),
        Decimal("0.75"),
        Decimal("1.00"),
        Decimal("1.25"),
        Decimal("1.50"),
        Decimal("2.00"),
    )
    assert BASE_POLICY is CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


def test_projected_rr_bullish_uses_source_low_and_midpoint() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source = _bar(t0, 95, 100, 90, 94)
    entry = _bar(t0 + timedelta(minutes=30), 96, 98, 95, 97)

    # C1 midpoint = 100. Reward = 4, risk = 6.
    assert projected_rr(
        parent=_parent(CrtPureCandidateDirection.BULLISH),
        source=source,
        entry=entry,
    ) == Decimal(4) / Decimal(6)


def test_projected_rr_bearish_uses_source_high_and_midpoint() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source = _bar(t0, 105, 110, 100, 106)
    entry = _bar(t0 + timedelta(minutes=30), 104, 105, 102, 103)

    # C1 midpoint = 100. Reward = 4, risk = 6.
    assert projected_rr(
        parent=_parent(CrtPureCandidateDirection.BEARISH),
        source=source,
        entry=entry,
    ) == Decimal(4) / Decimal(6)


def test_projected_rr_rejects_nonpositive_reward_geometry() -> None:
    t0 = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
    source = _bar(t0, 101, 103, 95, 99)
    entry = _bar(t0 + timedelta(minutes=30), 101, 102, 100, 101)

    assert (
        projected_rr(
            parent=_parent(CrtPureCandidateDirection.BULLISH),
            source=source,
            entry=entry,
        )
        is None
    )
