from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bp_usdjpy_passive_entry_capacity import (
    EntryArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bq_usdjpy_passive_entry_economics import (
    COST_STRESS_R,
    IDENTITY,
    TARGET_R,
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
