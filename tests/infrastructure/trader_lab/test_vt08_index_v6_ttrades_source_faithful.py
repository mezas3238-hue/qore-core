from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_v6_ttrades_source_faithful import (
    _RULE_MATERIAL,
    H4_ANCHORS_NY,
    TARGET_R_MULTIPLE,
    H4ModelKind,
    PoiKind,
    SourcePoi,
    _c2_side,
    _c3_side,
    _first_cisd,
    _first_continuation,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar


def _bar(
    opened: datetime,
    open_price: str,
    high: str,
    low: str,
    close: str,
    *,
    minutes: int = 15,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=minutes),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_v6_removes_qore_filters_and_restores_source_cycle() -> None:
    assert H4_ANCHORS_NY == (18, 22, 2, 6, 10, 14)
    assert TARGET_R_MULTIPLE == Decimal("2")
    assert _RULE_MATERIAL["v3_geometry"] is False
    assert _RULE_MATERIAL["daily_unique_only"] is False
    assert _RULE_MATERIAL["d1_peer_count_gate"] is False
    assert _RULE_MATERIAL["smt_mandatory"] is False
    assert _RULE_MATERIAL["forced_h4_lifecycle"] is False
    assert _RULE_MATERIAL["entry"] == "continuation-close"
    assert _RULE_MATERIAL["stop"] == "protected-swing-extreme"


def test_source_c2_is_sweep_and_close_back_inside() -> None:
    opened = datetime(2026, 1, 5, tzinfo=UTC)
    reference = _bar(opened, "100", "105", "95", "102", minutes=240)
    bullish = _bar(
        opened + timedelta(hours=4), "100", "103", "94", "99", minutes=240
    )
    bearish = _bar(
        opened + timedelta(hours=8), "101", "106", "97", "101", minutes=240
    )
    assert _c2_side(reference, bullish) is DemoTradingSetupSide.LONG
    assert _c2_side(reference, bearish) is DemoTradingSetupSide.SHORT


def test_source_c3_requires_body_engulf_without_directional_extreme_sweep() -> None:
    opened = datetime(2026, 1, 5, tzinfo=UTC)
    candle1 = _bar(opened, "100", "105", "95", "102", minutes=240)
    candle2 = _bar(
        opened + timedelta(hours=4), "100", "103", "96", "98", minutes=240
    )
    candle3 = _bar(
        opened + timedelta(hours=8), "97", "102", "96", "101", minutes=240
    )
    assert _c3_side(candle1, candle2, candle3) is DemoTradingSetupSide.LONG


def test_m15_cisd_confirms_protected_swing_without_numeric_wick_threshold() -> None:
    opened = datetime(2026, 1, 5, 6, 0, tzinfo=UTC)
    bars = (
        _bar(opened, "100", "100.5", "98.5", "99"),
        _bar(opened + timedelta(minutes=15), "99", "99.5", "97.5", "98"),
        _bar(opened + timedelta(minutes=30), "98", "101", "97.8", "100.5"),
    )
    confirmed = _first_cisd(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=0,
    )
    assert confirmed is not None
    index, cisd_level, protected_swing = confirmed
    assert index == 2
    assert cisd_level == Decimal("100")
    assert protected_swing == Decimal("97.5")


def test_entry_waits_for_continuation_closure_after_cisd() -> None:
    opened = datetime(2026, 1, 5, 6, 0, tzinfo=UTC)
    bars = (
        _bar(opened, "100", "101", "99", "100.5"),
        _bar(opened + timedelta(minutes=15), "100.5", "101.2", "100", "101"),
        _bar(opened + timedelta(minutes=30), "101", "102", "100.8", "101.8"),
    )
    index = _first_continuation(
        bars,
        side=DemoTradingSetupSide.LONG,
        start_index=1,
        protected_swing=Decimal("98"),
    )
    assert index == 2


def test_poi_is_a_range_or_level_with_causal_timestamp() -> None:
    observed = datetime(2026, 1, 5, 6, 0, tzinfo=UTC)
    poi = SourcePoi(PoiKind.FVG, Decimal("99"), Decimal("100"), observed)
    touched = _bar(observed + timedelta(hours=1), "101", "101.5", "99.5", "100.5")
    assert poi.touched_by(touched)
    assert poi.payload()["kind"] == "fvg"


def test_model_kinds_keep_same_c2_and_completed_c2_c3_paths() -> None:
    assert set(H4ModelKind) == {
        H4ModelKind.SAME_C2,
        H4ModelKind.C2_EXPANSION,
        H4ModelKind.C3_EXPANSION,
    }
