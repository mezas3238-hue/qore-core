from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    *,
    opened: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(days=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r74_body_direction_is_pre_entry_ohlc_only() -> None:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    previous = _bar(
        opened=opened,
        open_="100",
        high="110",
        low="90",
        close="101",
    )
    bullish = _bar(
        opened=opened + timedelta(days=1),
        open_="99",
        high="108",
        low="92",
        close="105",
    )
    bearish = _bar(
        opened=opened + timedelta(days=2),
        open_="106",
        high="108",
        low="92",
        close="95",
    )
    assert r74._body_direction(previous, bullish) is DemoTradingSetupSide.LONG
    assert r74._body_direction(previous, bearish) is DemoTradingSetupSide.SHORT


def test_r74_previous_midpoint_direction_is_deterministic() -> None:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    previous = _bar(
        opened=opened,
        open_="100",
        high="110",
        low="90",
        close="101",
    )
    above = _bar(
        opened=opened + timedelta(days=1),
        open_="99",
        high="108",
        low="92",
        close="105",
    )
    below = _bar(
        opened=opened + timedelta(days=2),
        open_="101",
        high="108",
        low="92",
        close="95",
    )
    at_mid = _bar(
        opened=opened + timedelta(days=3),
        open_="99",
        high="108",
        low="92",
        close="100",
    )
    assert r74._previous_midpoint(previous, above) is DemoTradingSetupSide.LONG
    assert r74._previous_midpoint(previous, below) is DemoTradingSetupSide.SHORT
    assert r74._previous_midpoint(previous, at_mid) is None


def test_r74_consensus_abstains_on_disagreement() -> None:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    previous = _bar(
        opened=opened,
        open_="100",
        high="110",
        low="90",
        close="101",
    )
    disagree = _bar(
        opened=opened + timedelta(days=1),
        open_="106",
        high="108",
        low="92",
        close="104",
    )
    assert r74._body_direction(previous, disagree) is DemoTradingSetupSide.SHORT
    assert r74._previous_midpoint(previous, disagree) is DemoTradingSetupSide.LONG
    assert r74._body_mid_consensus(previous, disagree) is None


def test_r74_resolver_set_is_frozen_and_no_outcome_resolver_exists() -> None:
    assert r74.RESOLVERS == (
        "BODY_DIRECTION",
        "PREVIOUS_MIDPOINT",
        "BODY_MID_CONSENSUS",
    )
    assert r74.TARGET_FAMILIES == (
        "INSIDE_NO_EXTREME_SWEEP",
        "DOUBLE_SWEEP_CLOSE_INSIDE",
    )


def test_r74_window_contract_preserves_canonical_samples() -> None:
    assert r74._window_contract("5Y")[2] == 2448
    assert r74._window_contract("2Y")[2] == 1017
    assert r74._window_contract("R66")[2] == 773
