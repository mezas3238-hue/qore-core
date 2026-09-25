from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
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


def test_r82_liquidity_sweep_requires_new_intrah4_extreme() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        _bar(t0, open_="100", high="101", low="99", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.4",
            high="100.6",
            low="98.5",
            close="99",
        ),
    )
    assert r82._liquidity_sweep_qualified(
        bars,
        side=DemoTradingSetupSide.LONG,
        sequence_start=1,
        protected_swing=Decimal("98.5"),
    )
    assert not r82._liquidity_sweep_qualified(
        bars,
        side=DemoTradingSetupSide.LONG,
        sequence_start=1,
        protected_swing=Decimal("99.2"),
    )


def test_r82_original_fvg_reaction_uses_original_source_poi() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    poi = v6.SourcePoi(
        kind=v6.PoiKind.FVG,
        low=Decimal("100"),
        high=Decimal("101"),
        observed_at=t0,
    )
    reacting = _bar(
        t0 + timedelta(minutes=15),
        open_="101",
        high="101.2",
        low="100.4",
        close="100.6",
    )
    assert r82._fvg_reaction_qualified(
        poi=poi,
        series_start_bar=reacting,
    )


def test_r82_family_contract_is_explicit() -> None:
    assert r82._family(liquidity=True, fvg_reaction=False) == (
        r82.FAMILY_LIQUIDITY
    )
    assert r82._family(liquidity=False, fvg_reaction=True) == r82.FAMILY_FVG
    assert r82._family(liquidity=True, fvg_reaction=True) == r82.FAMILY_BOTH
    assert r82._family(liquidity=False, fvg_reaction=False) == (
        r82.FAMILY_UNQUALIFIED
    )


def test_r82_source_r81_run_is_pinned() -> None:
    assert r82.SOURCE_R81_RUN_ID == 35519062875
