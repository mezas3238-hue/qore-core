from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bj_audusd_root_cause_expected_r_family import (
    ABSTENTION_FRACTION,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bk_audusd_passive_entry_capacity import (
    EntryArm,
)
from importlib import import_module

r2bt = import_module(
    "qore.infrastructure.trader_lab."
    "vt08_crt_pure_r2bt_audusd_passive_opportunity_expected_r_wf"
)


def test_r2bt_contract_is_frozen() -> None:
    assert r2bt.IDENTITY == (
        "VT08_CRT_PURE_R2BT_AUDUSD_PASSIVE_OPPORTUNITY_EXPECTED_R_WF_001"
    )
    assert r2bt.PASSIVE_ARM is EntryArm.CONF_RANGE_MID
    assert ABSTENTION_FRACTION == 0.20
    assert tuple(r2bt.MemoryHead) == (
        r2bt.MemoryHead.REF_DELAY,
        r2bt.MemoryHead.REF_DELAY_DIRECTION,
        r2bt.MemoryHead.TIMING_REF_DELAY,
    )
