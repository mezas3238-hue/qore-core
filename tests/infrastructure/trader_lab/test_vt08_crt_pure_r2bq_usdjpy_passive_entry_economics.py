from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bp_usdjpy_passive_entry_capacity import (
    EntryArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bq_usdjpy_passive_entry_economics import (
    COST_STRESS_R,
    IDENTITY,
    TARGET_R,
    _m15_exit,
)


def test_r2bq_contract_is_market_specific_and_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BQ_USDJPY_PASSIVE_ENTRY_ECONOMICS_001"
    assert TARGET_R == Decimal("1.5")
    assert COST_STRESS_R == (0.02, 0.05)
    assert tuple(EntryArm) == (
        EntryArm.NEXT_OPEN_CONTROL,
        EntryArm.RISK_RETRACE_025,
        EntryArm.RISK_RETRACE_050,
        EntryArm.RISK_RETRACE_075,
    )


def _bar(*, low: int, high: int) -> SimpleNamespace:
    return SimpleNamespace(low_price=low, high_price=high)


def test_r2bq_same_m15_target_then_stop_resolves_stop_first() -> None:
    outcome = _m15_exit(
        bullish=True,
        stop=Decimal("90"),
        target=Decimal("110"),
        bars=(
            _bar(low=100, high=111),
            _bar(low=89, high=105),
        ),
    )
    assert outcome == ("STOP", Decimal("90"))


def test_r2bq_passive_fill_bar_target_is_not_credited() -> None:
    outcome = _m15_exit(
        bullish=True,
        stop=Decimal("90"),
        target=Decimal("110"),
        bars=(
            _bar(low=100, high=111),
        ),
        target_bars=(),
    )
    assert outcome is None
