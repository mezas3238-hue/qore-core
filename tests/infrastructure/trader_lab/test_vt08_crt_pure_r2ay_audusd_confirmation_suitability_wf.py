from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2ay_audusd_confirmation_suitability_wf import (
    ADVANCEMENT_MIN_PF,
    ADVANCEMENT_MIN_TRADES_PER_YEAR,
    IDENTITY,
    MIN_REMOVED_TRADES_PER_YEAR,
    MIN_RETENTION,
    TRAINING_YEARS,
)


def test_r2ay_identity_and_training_contract_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AY_AUDUSD_CONFIRMATION_SUITABILITY_WF_001"
    assert TRAINING_YEARS == 3
    assert MIN_RETENTION == Decimal("0.75")
    assert MIN_REMOVED_TRADES_PER_YEAR == 8


def test_r2ay_advancement_gate_is_frozen() -> None:
    assert ADVANCEMENT_MIN_TRADES_PER_YEAR == Decimal("170")
    assert ADVANCEMENT_MIN_PF == Decimal("1.05")
