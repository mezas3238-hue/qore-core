from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2o_btcusd_block_robustness import (
    BLOCK_LENGTHS,
    RESAMPLE_COUNT,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r3b_btcusd_block_bootstrap import (
    MAX_P95_DD_R,
    MIN_POSITIVE_TERMINAL,
)


def test_r3b_bootstrap_family_is_frozen() -> None:
    assert BLOCK_LENGTHS == (2, 4, 8)
    assert RESAMPLE_COUNT == 5_000


def test_r3b_certification_thresholds_are_frozen() -> None:
    assert MIN_POSITIVE_TERMINAL == 0.90
    assert MAX_P95_DD_R == 15.0
