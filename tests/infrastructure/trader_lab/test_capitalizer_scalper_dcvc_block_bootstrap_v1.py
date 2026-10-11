"""Dependence-aware scientific uncertainty helper is diagnostic, never an entry gate."""
from __future__ import annotations

from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_block_bootstrap_v1 import (
    BLOCK_DAYS,
    COST,
    DRAWS,
    _percentile,
    _pf_dd,
    analyze,
)


def test_blocks_are_prewritten_and_frozen() -> None:
    assert BLOCK_DAYS==5
    assert DRAWS==500
    assert COST==Decimal("0.025")


def test_maxdd_uses_temporal_order_and_no_hindsight_reordering() -> None:
    first=_pf_dd((Decimal("1"),Decimal("-2"),Decimal("0.5")))
    reverse=_pf_dd((Decimal("-2"),Decimal("1"),Decimal("0.5")))
    assert first[1]==Decimal("2")
    assert reverse[1]==Decimal("2")
    assert first[0]==reverse[0]
    assert first[2]==reverse[2]


def test_percentiles_require_values() -> None:
    with pytest.raises(ValueError,match="bootstrap"):
        _percentile([],0.1)
    assert _percentile([3,1,2],0)==1
    assert _percentile([3,1,2],1)==3


def test_missing_historical_ledgers_fail_closed(tmp_path) -> None:
    with pytest.raises(ValueError,match="nine frozen"):
        analyze(tmp_path,tmp_path,tmp_path)
