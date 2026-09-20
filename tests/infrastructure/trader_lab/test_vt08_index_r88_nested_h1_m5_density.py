from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r88_nested_h1_m5_density as r88,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
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
        closed_at=opened + timedelta(minutes=5),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r88_complete_h1_requires_all_twelve_m5() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    complete = tuple(
        _bar(
            t0 + timedelta(minutes=5 * i),
            open_=str(100 + i),
            high=str(101 + i),
            low=str(99 + i),
            close=str(100.5 + i),
        )
        for i in range(12)
    )
    h1, parts = r88._complete_h1(complete)
    assert tuple(h1) == (t0,)
    assert len(parts[t0]) == 12

    h1_missing, _ = r88._complete_h1(complete[:-1])
    assert h1_missing == {}


def test_r88_h1_source_poi_uses_three_complete_h1_bars() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    h1 = {
        t0: Vt08IndexC2R1Bar(
            t0, t0 + timedelta(hours=1),
            Decimal("100"), Decimal("101"), Decimal("99"), Decimal("100"),
        ),
        t0 + timedelta(hours=1): Vt08IndexC2R1Bar(
            t0 + timedelta(hours=1), t0 + timedelta(hours=2),
            Decimal("102"), Decimal("103"), Decimal("101"), Decimal("102"),
        ),
        t0 + timedelta(hours=2): Vt08IndexC2R1Bar(
            t0 + timedelta(hours=2), t0 + timedelta(hours=3),
            Decimal("104"), Decimal("105"), Decimal("102"), Decimal("104"),
        ),
    }
    components = {
        key: tuple(
            _bar(
                key + timedelta(minutes=5 * i),
                open_="100",
                high="101",
                low="99",
                close="100",
            )
            for i in range(12)
        )
        for key in h1
    }
    pois = r88._h1_source_pois(
        h1=h1,
        h1_keys=tuple(sorted(h1)),
        components=components,
        before=t0 + timedelta(hours=3),
        side=DemoTradingSetupSide.LONG,
    )
    assert any(poi.kind is v6.PoiKind.FVG for poi in pois)


def test_r88_predecessor_evidence_is_pinned() -> None:
    assert r88.SOURCE_R86_RUN_ID == 35526025751
    assert r88.SOURCE_R86_ARTIFACT_ID == 10610380553
    assert r88.SOURCE_R87_RUN_ID == 35526010382
    assert r88.SOURCE_R87_ARTIFACT_ID == 10609054819


def test_r88_owner_disabled_14_is_preserved() -> None:
    assert 14 not in tuple(r4.V7_ANCHORS)
