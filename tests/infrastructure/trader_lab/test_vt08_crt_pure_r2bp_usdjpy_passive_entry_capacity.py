from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bp_usdjpy_passive_entry_capacity import (
    HORIZON,
    IDENTITY,
    RETRACE_FRACTION,
    EntryArm,
)


def test_r2bp_usdjpy_family_is_frozen_independently() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BP_USDJPY_PASSIVE_ENTRY_CAPACITY_001"
    assert HORIZON.total_seconds() == 30 * 60
    assert tuple(EntryArm) == (
        EntryArm.NEXT_OPEN_CONTROL,
        EntryArm.RISK_RETRACE_025,
        EntryArm.RISK_RETRACE_050,
        EntryArm.RISK_RETRACE_075,
    )
    assert str(RETRACE_FRACTION[EntryArm.RISK_RETRACE_025]) == "0.25"
    assert str(RETRACE_FRACTION[EntryArm.RISK_RETRACE_050]) == "0.50"
    assert str(RETRACE_FRACTION[EntryArm.RISK_RETRACE_075]) == "0.75"
