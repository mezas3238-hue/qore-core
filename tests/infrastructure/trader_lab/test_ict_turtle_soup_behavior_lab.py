from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.ict_turtle_soup_behavior_lab import (
    Event,
    Reference,
    ReferenceType,
    _forward_extremes,
    _geometry,
    _reclaim,
    _references,
    group_rows,
    survival_rows,
    write_outputs,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
    SourceCandle,
)

D = Decimal
T0 = datetime(2026, 1, 5, 0, tzinfo=UTC)


def _bar(minutes: int, o: str, h: str, lo: str, c: str) -> Bar:
    opened = T0 + timedelta(minutes=minutes)
    return Bar(opened, opened + timedelta(minutes=5), D(o), D(h), D(lo), D(c))


def _candle(hours: int, o: str, h: str, lo: str, c: str) -> SourceCandle:
    opened = T0 + timedelta(hours=hours)
    bars = (_bar(hours * 60, o, h, lo, c),)
    return SourceCandle(
        opened,
        opened + timedelta(hours=1),
        D(o),
        D(h),
        D(lo),
        D(c),
        bars,
    )


def _event(**changes: object) -> Event:
    base = Event(
        evidence_id="consumed:test:EURUSD",
        symbol="EURUSD",
        asset_class="fx",
        provider="test",
        timeframe="H1",
        reference_type="swing-3",
        side="long",
        reference_opened_at=T0,
        source_opened_at=T0 + timedelta(hours=1),
        raid_at=T0 + timedelta(hours=1),
        reference_level=D("1.1000"),
        opposite_reference=D("1.1100"),
        tick_size=D("0.00001"),
        reference_age_bars=2,
        exact_equal_count=1,
        nearest_peer_ticks=D("20"),
        raid_depth_ticks=D("10"),
        raid_depth_pct=D("0.01"),
        raid_depth_range_units=D("0.2"),
        source_range_ticks=D("50"),
        body_fraction=D("0.4"),
        rejection_wick_fraction=D("0.5"),
        close_location=D("0.8"),
        prior_body_alignment="opposed",
        session_bucket="london",
        ny_minute_of_day=240,
        same_source_reclaim=True,
        reclaim_latency_minutes=10,
        reclaim_depth_ticks=D("5"),
        cisd_confirmed=True,
        cisd_latency_minutes=20,
        protected_swing_distance_ticks=D("30"),
        fvg_after_raid=True,
        opposite_reference_hit_24h=True,
        opposite_reference_hit_minutes=120,
        mfe_15m_ticks=D("20"),
        mae_15m_ticks=D("5"),
        mfe_30m_ticks=D("30"),
        mae_30m_ticks=D("7"),
        mfe_60m_ticks=D("50"),
        mae_60m_ticks=D("8"),
        mfe_240m_ticks=D("90"),
        mae_240m_ticks=D("12"),
        mfe_1440m_ticks=D("150"),
        mae_1440m_ticks=D("20"),
        outcome="rejection-with-cisd",
    )
    return replace(base, **changes)


def test_references_include_prior_and_swing_for_both_sides() -> None:
    candles = (
        _candle(0, "10", "11", "9", "10"),
        _candle(1, "10", "13", "8", "12"),
        _candle(2, "12", "12", "9", "10"),
        _candle(3, "10", "11", "7", "8"),
    )
    refs = _references(candles, "H1", 3, D("1"))
    assert {item.kind for item in refs} == {
        ReferenceType.PRIOR_CANDLE,
        ReferenceType.SWING_3,
    }
    assert {item.side for item in refs} == {Side.LONG, Side.SHORT}
    short_swing = next(
        item
        for item in refs
        if item.kind is ReferenceType.SWING_3 and item.side is Side.SHORT
    )
    assert short_swing.level == D("13")
    assert short_swing.age_bars == 2


def test_geometry_is_directionally_symmetric() -> None:
    candle = _candle(0, "10", "14", "8", "13")
    long_body, long_wick, long_close = _geometry(candle, Side.LONG)
    short_body, short_wick, short_close = _geometry(candle, Side.SHORT)
    assert long_body == short_body == D("0.5")
    assert long_wick == D("2") / D("6")
    assert short_wick == D("1") / D("6")
    assert long_close + short_close == D("1")


def test_reclaim_measures_latency_and_depth_without_clock_gate() -> None:
    bars = (
        _bar(0, "1.1000", "1.1002", "1.0990", "1.0995"),
        _bar(5, "1.0995", "1.1005", "1.0994", "1.1003"),
    )
    ref = Reference(
        "H1",
        ReferenceType.PRIOR_CANDLE,
        Side.LONG,
        D("1.1000"),
        D("1.1100"),
        T0,
        T0,
        1,
        1,
        None,
    )
    latency, depth = _reclaim(
        bars,
        ref,
        T0,
        T0 + timedelta(hours=1),
        D("0.0001"),
    )
    assert latency == 10
    assert depth == D("3")


def test_forward_extremes_are_normalized_in_ticks() -> None:
    bars = (
        _bar(0, "1.1000", "1.1010", "1.0995", "1.1005"),
        _bar(5, "1.1005", "1.1020", "1.0990", "1.1015"),
    )
    mfe, mae = _forward_extremes(
        bars,
        Side.LONG,
        D("1.1000"),
        T0,
        15,
        D("0.0001"),
    )
    assert mfe == D("20")
    assert mae == D("10")
    short_mfe, short_mae = _forward_extremes(
        bars,
        Side.SHORT,
        D("1.1000"),
        T0,
        15,
        D("0.0001"),
    )
    assert short_mfe == D("10")
    assert short_mae == D("20")


def test_group_rows_preserve_sessions_as_diagnostics() -> None:
    events = [
        _event(session_bucket="asia"),
        _event(session_bucket="london", raid_at=T0 + timedelta(days=1)),
        _event(session_bucket="new-york", raid_at=T0 + timedelta(days=2)),
    ]
    rows = group_rows(events)
    sessions = {row["value"] for row in rows if row["dimension"] == "session"}
    assert sessions == {"asia", "london", "new-york"}


def test_survival_table_uses_observed_reclaim_latency() -> None:
    events = [_event(reclaim_latency_minutes=5), _event(reclaim_latency_minutes=45)]
    rows = survival_rows(events)
    at_15 = next(row for row in rows if row["minutes"] == 15)
    at_60 = next(row for row in rows if row["minutes"] == 60)
    assert at_15["fraction"] == 0.5
    assert at_60["fraction"] == 1.0


def test_write_outputs_is_research_only(tmp_path: Path) -> None:
    events = [
        _event(session_bucket="asia"),
        _event(session_bucket="london", raid_at=T0 + timedelta(days=1)),
    ]
    summary = write_outputs(events, tmp_path, ["consumed:test"])
    assert summary["evidence_status"] == "CONSUMED_DIAGNOSTIC_ONLY"
    assert summary["session_filter_applied"] is False
    assert summary["pnl_used_for_filter_selection"] is False
    assert summary["demo_eligible"] is False
    assert summary["live_authorized"] is False
    assert summary["real_capital_authorized"] is False
    assert summary["production_authorized"] is False
    assert (tmp_path / "events.csv").exists()
    assert (tmp_path / "group_stats.csv").exists()
    assert (tmp_path / "quantile_response.csv").exists()
    assert (tmp_path / "survival.csv").exists()
    assert (tmp_path / "leave_one_out.csv").exists()
