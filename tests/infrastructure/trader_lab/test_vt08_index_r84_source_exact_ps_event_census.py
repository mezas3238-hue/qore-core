from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    opened: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r84_short_term_low_is_causal_three_bar_swing() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="101", high="102", low="100", close="101"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100",
            high="101",
            low="98",
            close="99",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="99",
            high="101",
            low="99",
            close="100",
        ),
    )
    assert r84._short_term_swings(
        bars,
        side=DemoTradingSetupSide.LONG,
    ) == ((1, Decimal("98"), 2),)


def test_r84_confirmed_series_preserves_exact_close_through() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="101", high="101.2", low="99", close="100"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100",
            high="100.2",
            low="98",
            close="99",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="99",
            high="102",
            low="98.8",
            close="101.5",
        ),
    )
    rows = r84._confirmed_opposing_series(
        bars,
        side=DemoTradingSetupSide.LONG,
    )
    assert len(rows) == 1
    assert rows[0].start_index == 0
    assert rows[0].end_index == 1
    assert rows[0].confirm_index == 2
    assert rows[0].series_open == Decimal("101")
    assert rows[0].extreme == Decimal("98")
    assert rows[0].extreme_index == 1


def test_r84_sweep_requires_extreme_after_poi_touch() -> None:
    series = r84.ConfirmedSeries(
        start_index=0,
        end_index=2,
        confirm_index=3,
        series_open=Decimal("101"),
        extreme=Decimal("98"),
        extreme_index=2,
    )
    swings = ((0, Decimal("99"), 1),)
    assert r84._swept_known_short_term_liquidity(
        swings,
        series=series,
        side=DemoTradingSetupSide.LONG,
        touch_index=1,
    )
    assert not r84._swept_known_short_term_liquidity(
        swings,
        series=series,
        side=DemoTradingSetupSide.LONG,
        touch_index=3,
    )


def test_r84_source_r83_evidence_is_pinned() -> None:
    assert r84.SOURCE_R83_RUN_ID == 35519881915
    assert r84.SOURCE_R83_ARTIFACT_ID == 10607958272
    assert r84.SOURCE_R83_ARTIFACT_DIGEST.startswith("sha256:")
