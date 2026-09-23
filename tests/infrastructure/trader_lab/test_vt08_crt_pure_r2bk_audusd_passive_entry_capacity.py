from __future__ import annotations

from datetime import timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bk_audusd_passive_entry_capacity import (
    EntryArm,
    HORIZON,
    IDENTITY,
)


def test_r2bk_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BK_AUDUSD_PASSIVE_ENTRY_CAPACITY_001"
    assert HORIZON == timedelta(minutes=30)
    assert tuple(EntryArm) == (
        EntryArm.NEXT_OPEN_CONTROL,
        EntryArm.CONF_BODY_MID,
        EntryArm.CONF_RANGE_MID,
        EntryArm.SOURCE_OPEN,
    )
