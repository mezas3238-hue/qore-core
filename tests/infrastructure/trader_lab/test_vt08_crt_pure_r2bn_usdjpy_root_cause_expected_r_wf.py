from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bn_usdjpy_root_cause_expected_r_wf import (
    ABSTENTION_FRACTION,
    IDENTITY,
    MARKET,
    MemoryHead,
    TRAINING_YEARS,
    _record,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def _trade() -> Model1LabTrade:
    return Model1LabTrade(
        schema="test",
        identity="test",
        market="USDJPY",
        reference_policy="test",
        reference_count=2,
        reference_ids=("a", "b"),
        parent_direction="BULLISH",
        timing_triplet="5",
        c3_opened_at="2025-01-01T00:00:00+00:00",
        source_opened_at="2025-01-01T00:15:00+00:00",
        confirmation_opened_at="2025-01-01T00:45:00+00:00",
        entry_opened_at="2025-01-01T01:00:00+00:00",
        entry_price_relative=100,
        stop_price_relative=90,
        target_price_relative="115",
        exit_price_relative="115",
        exit_reason="TARGET_FIXED_1_5R",
        r_multiple=1.5,
    )


def test_r2bn_contract_is_usdjpy_specific() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BN_USDJPY_ROOT_CAUSE_EXPECTED_R_WF_001"
    assert MARKET is CrtPureMarket.USDJPY
    assert TRAINING_YEARS == 4
    assert ABSTENTION_FRACTION == 0.20
    assert tuple(MemoryHead) == (
        MemoryHead.REF_DELAY,
        MemoryHead.REF_DELAY_DIRECTION,
        MemoryHead.TIMING_REF_DELAY,
    )


def test_r2bn_features_are_small_pre_entry_root_cause_memory() -> None:
    record = _record(_trade())
    assert dict(record.features) == {
        "confirmation_delay": "D2",
        "direction": "BULLISH",
        "source_reference_count": "REF2_PLUS",
        "timing_triplet": "5",
    }
