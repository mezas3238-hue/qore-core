"""Semantic tests for VT08 density census (no trading, no synthetic edge)."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    AggregatedCandle,
    ReplayBar,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_density_root_cause_audit import (
    _geometry_valid,
    density_root_cause_report,
    scheduled_parent_census,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

BASE = datetime(2026, 1, 12, 8, tzinfo=UTC)


def _h4(hi: int, lo: int) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=BASE, closed_at=BASE + timedelta(hours=4),
        open_price=100, high_price=hi, low_price=lo,
        close_price=100, m5_count=48,
    )


def _m15(hi: int, lo: int, opened_at: datetime | None = None) -> M15Bar:
    return M15Bar(
        opened_at=opened_at or BASE,
        open_price=100, high_price=hi,
        low_price=lo, close_price=100,
    )


@pytest.mark.parametrize(
    ("direction", "source_hi", "source_lo", "target_hi", "target_lo", "expected"),
    (
        (CrtPureCandidateDirection.BULLISH, 110, 90, 120, 100, True),
        (CrtPureCandidateDirection.BULLISH, 110, 100, 120, 100, False),
        (CrtPureCandidateDirection.BULLISH, 110, 90, 105, 95, False),
        (CrtPureCandidateDirection.BEARISH, 110, 90, 100, 80, True),
        (CrtPureCandidateDirection.BEARISH, 100, 90, 100, 80, False),
        (CrtPureCandidateDirection.BEARISH, 110, 90, 105, 95, False),
    ),
)
def test_geometry_census_is_structural_only(
    direction: CrtPureCandidateDirection,
    source_hi: int,
    source_lo: int,
    target_hi: int,
    target_lo: int,
    expected: bool,
) -> None:
    parent = ParentCrt(
        market=CrtPureMarket.AUDUSD, direction=direction, triplet="1",
        c3_opened_at=BASE + timedelta(hours=8),
        c3_closed_at=BASE + timedelta(hours=12),
        c1=_h4(target_hi, target_lo),
        c2=_h4(110, 90),
        c3_m5=(),
    )
    assert _geometry_valid(parent, _m15(source_hi, source_lo), _m15(105, 95)) is expected


def test_zero_bars_are_all_missing_and_never_misreported_as_no_crt() -> None:
    counts = scheduled_parent_census(CrtPureMarket.AUDUSD, ())
    assert counts["C3_SCHEDULED"] > 0
    assert counts["PARENT_REJECTED_INCOMPLETE_M5"] == counts["C3_SCHEDULED"]
    assert counts.get("C2_NOT_CURRENT_ONE_SIDED_TURTLE_SOUP", 0) == 0
    assert counts.get("C2_MATCHES_CURRENT_TURTLE_SOUP", 0) == 0


def test_density_census_rejects_duplicate_input() -> None:
    bar = ReplayBar(
        opened_at=BASE, open_price=100, high_price=110,
        low_price=90, close_price=100,
    )
    with pytest.raises(ValueError, match="duplicate M5"):
        scheduled_parent_census(CrtPureMarket.AUDUSD, (bar, bar))


def test_btcusd_frozen() -> None:
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        density_root_cause_report(CrtPureMarket.BTCUSD, ())
