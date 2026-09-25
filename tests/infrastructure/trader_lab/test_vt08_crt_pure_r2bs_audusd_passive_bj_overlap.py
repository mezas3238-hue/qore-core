from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bj_audusd_root_cause_expected_r_family import (
    MemoryHead,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bk_audusd_passive_entry_capacity import (
    EntryArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bs_audusd_passive_bj_overlap import (
    BJ_HEAD,
    IDENTITY,
    PASSIVE_ARM,
)


def test_r2bs_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BS_AUDUSD_PASSIVE_BJ_OVERLAP_001"
    assert BJ_HEAD is MemoryHead.REF_DELAY_DIRECTION
    assert PASSIVE_ARM is EntryArm.CONF_RANGE_MID
