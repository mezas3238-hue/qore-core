from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r86_dynamic_m15_fvg_rearm as r86,
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
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r86_bullish_fvg_is_known_only_after_third_bar_closes() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="100.2",
            close="101.7",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="102",
            high="103",
            low="101.5",
            close="102.8",
        ),
    )
    fvgs = r86._directional_fvgs(
        bars,
        side=DemoTradingSetupSide.LONG,
        earliest_formed_index=0,
    )
    assert len(fvgs) == 1
    assert fvgs[0].low == Decimal("101")
    assert fvgs[0].high == Decimal("101.5")
    assert fvgs[0].formed_index == 2
    poi = fvgs[0].as_source_poi(bars)
    assert poi.observed_at == bars[2].closed_at
    assert poi.kind is v6.PoiKind.FVG


def test_r86_does_not_use_fvg_formed_before_rearm_cursor() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="100.2",
            close="101.7",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="102",
            high="103",
            low="101.5",
            close="102.8",
        ),
        _bar(
            t0 + timedelta(minutes=45),
            open_="102.8",
            high="104",
            low="102.7",
            close="103.8",
        ),
    )
    assert r86._directional_fvgs(
        bars,
        side=DemoTradingSetupSide.LONG,
        earliest_formed_index=3,
    ) == ()


def test_r86_owner_disabled_14_remains_disabled() -> None:
    assert 14 not in tuple(r4.V7_ANCHORS)


def test_r86_r85_evidence_is_pinned() -> None:
    assert r86.SOURCE_R85_RUN_ID == 35525680874
    assert r86.SOURCE_R85_ARTIFACT_ID == 10609721617
    assert r86.SOURCE_R85_ARTIFACT_DIGEST == (
        "sha256:fa2c1516354ba38a9b0d9fccf1853b5b7e62eb25a080c69150f57faef1e1e059"
    )
