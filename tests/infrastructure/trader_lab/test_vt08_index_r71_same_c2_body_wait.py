from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r71_same_c2_body_wait as r71,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_r71_body_side_transition_is_directional() -> None:
    assert r71._body_side_pass(
        side=DemoTradingSetupSide.LONG,
        close=Decimal("101"),
        h4_open=Decimal("100"),
    )
    assert not r71._body_side_pass(
        side=DemoTradingSetupSide.LONG,
        close=Decimal("99"),
        h4_open=Decimal("100"),
    )
    assert r71._body_side_pass(
        side=DemoTradingSetupSide.SHORT,
        close=Decimal("99"),
        h4_open=Decimal("100"),
    )
    assert not r71._body_side_pass(
        side=DemoTradingSetupSide.SHORT,
        close=Decimal("101"),
        h4_open=Decimal("100"),
    )


def test_r71_source_ref_is_frozen_ttrades_body_source() -> None:
    assert r71.SOURCE_REF == "ttrades:let-wick-form-trade-body:2026-08-29"


def test_r71_window_contract_preserves_consumed_samples() -> None:
    assert r71._window_contract("5Y")[2] == 2448
    assert r71._window_contract("2Y")[2] == 1017
    assert r71._window_contract("R66")[2] == 773


def test_r71_fixed_target_stays_current_source_complete_target() -> None:
    assert r71.TARGET_R == Decimal("2.5")
