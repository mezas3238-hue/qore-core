from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r99_standard_ideal_wick_state as r99,
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


def test_r99_long_small_wick_expansion() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    observed = (
        _bar(t0, open_="100", high="103", low="99", close="102"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="102",
            high="106",
            low="101",
            close="105",
        ),
    )
    state, adverse, directional = r99._wick_state(
        observed,
        side=DemoTradingSetupSide.LONG,
        h4_open=Decimal("100"),
        entry=Decimal("105"),
    )
    assert state == r99.SMALL_WICK
    assert adverse == Decimal("1")
    assert directional == Decimal("5")


def test_r99_short_large_wick_reversal() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    observed = (
        _bar(t0, open_="100", high="106", low="98", close="99"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="99",
            high="101",
            low="96",
            close="98",
        ),
    )
    state, adverse, directional = r99._wick_state(
        observed,
        side=DemoTradingSetupSide.SHORT,
        h4_open=Decimal("100"),
        entry=Decimal("98"),
    )
    assert state == r99.LARGE_WICK
    assert adverse == Decimal("6")
    assert directional == Decimal("2")


def test_r99_equal_geometry_fails_closed_diagnostic() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    observed = (
        _bar(t0, open_="100", high="102", low="98", close="101"),
    )
    state, adverse, directional = r99._wick_state(
        observed,
        side=DemoTradingSetupSide.LONG,
        h4_open=Decimal("100"),
        entry=Decimal("102"),
    )
    assert state == r99.EQUAL_WICK
    assert adverse == directional == Decimal("2")


def test_r99_ps_state_uses_r82_source_qualification() -> None:
    assert r99._ps_state(r82.FAMILY_LIQUIDITY) == r99.QUALIFIED
    assert r99._ps_state(r82.FAMILY_FVG) == r99.QUALIFIED
    assert r99._ps_state(r82.FAMILY_BOTH) == r99.QUALIFIED
    assert r99._ps_state(r82.FAMILY_UNQUALIFIED) == r99.GENERIC


def test_r99_r98_evidence_is_pinned() -> None:
    assert r99.SOURCE_R98_RUN_ID == 35535639692
    assert r99.SOURCE_R98_ARTIFACT_ID == 10612860698
    assert r99.SOURCE_R98_ARTIFACT_DIGEST == (
        "sha256:c51e7dd0351c8e677f368cda182e13fceafaf926b0b39ca203720d7f6d0368bf"
    )
