from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)
from qore.infrastructure.trader_lab.capitalizer_v50_target_stop_intelligence import (
    build_dual_invalidation,
    build_h1_target_ladder,
)


def _m1(minute: int, open_: str, high: str, low: str, close: str) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 10, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=5,
    )


def _h1(hour: int, open_: str, high: str, low: str, close: str) -> V48AggregatedBar:
    opened = datetime(2026, 1, 5, hour, 0, tzinfo=UTC)
    return V48AggregatedBar(
        opened_at=opened,
        closed_at=opened + timedelta(hours=1),
        source=CapitalizerSourceBar(
            open=Decimal(open_),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
        ),
        minute_count=60,
    )


def test_target_ladder_keeps_multiple_untouched_h1_pivots_without_selecting_one() -> None:
    h1 = (
        _h1(5, "100", "101", "99", "100"),
        _h1(6, "100", "105", "100", "104"),
        _h1(7, "103", "103.5", "101", "102"),
        _h1(8, "102", "108", "102", "107"),
        _h1(9, "106", "106.5", "103", "104"),
    )
    decision = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    ladder = build_h1_target_ladder(
        h1,
        (),
        side=CapitalizerSide.LONG,
        decision_at=decision,
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("98"),
    )
    assert len(ladder.candidates) == 2
    assert ladder.candidates[0].price == Decimal("105")
    assert ladder.candidates[1].price == Decimal("108")
    assert ladder.exact_target_selected is False
    assert ladder.has_two_r_destination is True


def test_touched_h1_pivot_is_removed_from_causal_ladder() -> None:
    h1 = (
        _h1(5, "100", "101", "99", "100"),
        _h1(6, "100", "105", "100", "104"),
        _h1(7, "103", "103.5", "101", "102"),
    )
    touch = (_m1(0, "103", "105.1", "102.9", "104"),)
    ladder = build_h1_target_ladder(
        h1,
        touch,
        side=CapitalizerSide.LONG,
        decision_at=touch[0].closed_at,
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("98"),
    )
    assert ladder.candidates == ()


def test_dual_invalidation_separates_m1_execution_from_m15_thesis_stop() -> None:
    bars = (
        _m1(0, "100", "100.2", "99.8", "100.1"),
        _m1(1, "100.1", "100.15", "99.5", "99.7"),
        _m1(2, "99.7", "100.1", "99.7", "100.0"),
        _m1(3, "100.0", "100.4", "99.9", "100.3"),
    )
    result = build_dual_invalidation(
        bars,
        side=CapitalizerSide.LONG,
        setup_confirmed_at=bars[0].opened_at,
        decision_at=bars[-1].closed_at,
        entry_price=Decimal("100.3"),
        thesis_stop_price=Decimal("98.0"),
    )
    assert result.execution_anchor_available is True
    assert result.execution_stop_price == Decimal("99.5")
    assert result.execution_risk_price == Decimal("0.8")
    assert result.thesis_risk_price == Decimal("2.3")
    assert result.execution_vs_thesis_ratio is not None
    assert result.execution_vs_thesis_ratio < Decimal("0.5")
    assert result.stop_widening_authorized is False


def test_dual_invalidation_rejects_breached_long_pivot_before_entry() -> None:
    bars = (
        _m1(0, "100", "100.2", "99.8", "100.1"),
        _m1(1, "100.1", "100.15", "99.5", "99.7"),
        _m1(2, "99.7", "100.1", "99.7", "100.0"),
        _m1(3, "100.0", "100.2", "99.4", "100.1"),
    )
    result = build_dual_invalidation(
        bars,
        side=CapitalizerSide.LONG,
        setup_confirmed_at=bars[0].opened_at,
        decision_at=bars[-1].closed_at,
        entry_price=Decimal("100.1"),
        thesis_stop_price=Decimal("98.0"),
    )
    assert result.execution_anchor_available is False
    assert result.execution_stop_price is None


def test_dual_invalidation_rejects_breached_short_pivot_before_entry() -> None:
    bars = (
        _m1(0, "100", "100.2", "99.8", "99.9"),
        _m1(1, "99.9", "100.5", "99.85", "100.3"),
        _m1(2, "100.3", "100.3", "99.9", "100.0"),
        _m1(3, "100.0", "100.6", "99.8", "99.9"),
    )
    result = build_dual_invalidation(
        bars,
        side=CapitalizerSide.SHORT,
        setup_confirmed_at=bars[0].opened_at,
        decision_at=bars[-1].closed_at,
        entry_price=Decimal("99.9"),
        thesis_stop_price=Decimal("102.0"),
    )
    assert result.execution_anchor_available is False
    assert result.execution_stop_price is None


def test_dual_invalidation_rejects_long_pivot_beyond_thesis_boundary() -> None:
    bars = (
        _m1(0, "100", "100.2", "99.8", "100.1"),
        _m1(1, "100.1", "100.15", "97.5", "99.0"),
        _m1(2, "99.0", "100.1", "98.0", "100.0"),
    )
    result = build_dual_invalidation(
        bars,
        side=CapitalizerSide.LONG,
        setup_confirmed_at=bars[0].opened_at,
        decision_at=bars[-1].closed_at,
        entry_price=Decimal("100.0"),
        thesis_stop_price=Decimal("98.0"),
    )
    assert result.execution_anchor_available is False


def test_dual_invalidation_rejects_short_pivot_beyond_thesis_boundary() -> None:
    bars = (
        _m1(0, "100", "100.2", "99.8", "99.9"),
        _m1(1, "99.9", "102.5", "99.85", "101.0"),
        _m1(2, "101.0", "102.0", "99.9", "100.0"),
    )
    result = build_dual_invalidation(
        bars,
        side=CapitalizerSide.SHORT,
        setup_confirmed_at=bars[0].opened_at,
        decision_at=bars[-1].closed_at,
        entry_price=Decimal("100.0"),
        thesis_stop_price=Decimal("102.0"),
    )
    assert result.execution_anchor_available is False
