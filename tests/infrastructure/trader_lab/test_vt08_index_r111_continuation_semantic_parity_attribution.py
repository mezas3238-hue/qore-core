from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r111_continuation_semantic_parity_attribution as r111,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_r111_body_state_is_discrete_and_directional() -> None:
    assert r111._body_state(
        side=DemoTradingSetupSide.LONG,
        open_=Decimal("100"),
        close=Decimal("101"),
    ) == "BIAS_DIRECTION_BODY"
    assert r111._body_state(
        side=DemoTradingSetupSide.LONG,
        open_=Decimal("101"),
        close=Decimal("100"),
    ) == "OPPOSING_BODY"
    assert r111._body_state(
        side=DemoTradingSetupSide.SHORT,
        open_=Decimal("101"),
        close=Decimal("100"),
    ) == "BIAS_DIRECTION_BODY"
    assert r111._body_state(
        side=DemoTradingSetupSide.SHORT,
        open_=Decimal("100"),
        close=Decimal("101"),
    ) == "OPPOSING_BODY"
    assert r111._body_state(
        side=DemoTradingSetupSide.LONG,
        open_=Decimal("100"),
        close=Decimal("100"),
    ) == "DOJI"


def test_r111_breakout_origin_distinguishes_cross_from_gap_open() -> None:
    assert r111._breakout_origin(
        side=DemoTradingSetupSide.LONG,
        open_=Decimal("100"),
        previous_high=Decimal("101"),
        previous_low=Decimal("99"),
    ) == "CROSSED_EXTREME_DURING_BAR"
    assert r111._breakout_origin(
        side=DemoTradingSetupSide.LONG,
        open_=Decimal("102"),
        previous_high=Decimal("101"),
        previous_low=Decimal("99"),
    ) == "OPENED_BEYOND_PREVIOUS_EXTREME"
    assert r111._breakout_origin(
        side=DemoTradingSetupSide.SHORT,
        open_=Decimal("100"),
        previous_high=Decimal("101"),
        previous_low=Decimal("99"),
    ) == "CROSSED_EXTREME_DURING_BAR"
    assert r111._breakout_origin(
        side=DemoTradingSetupSide.SHORT,
        open_=Decimal("98"),
        previous_high=Decimal("101"),
        previous_low=Decimal("99"),
    ) == "OPENED_BEYOND_PREVIOUS_EXTREME"


def test_r111_standard_surface_and_r110_source_are_pinned() -> None:
    assert r111.EXPECTED_STANDARD == {"5Y": 1756, "2Y": 746, "R66": 546}
    assert r111.SOURCE_R110_RUN_ID == 35660671874
    assert r111.SOURCE_R110_ARTIFACT_ID == 10667527471
    assert r111.SOURCE_R110_ARTIFACT_DIGEST == (
        "sha256:cdf274169f12d74126b4be417b2a1ac2baa4f8051895d883a393e79877ac4f42"
    )
