from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r109_standard_retest_timing_decay_attribution as r109,
)


def test_r109_delay_buckets_are_preregistered() -> None:
    assert r109._delay_bucket(1) == "NEXT_M15"
    assert r109._delay_bucket(2) == "M15_2_3"
    assert r109._delay_bucket(3) == "M15_2_3"
    assert r109._delay_bucket(4) == "M15_4_PLUS"


def test_r109_mfe_buckets_use_structural_r_milestones() -> None:
    assert r109._mfe_bucket(Decimal("0.49")) == "LT_0_5R"
    assert r109._mfe_bucket(Decimal("0.5")) == "R_0_5_TO_1"
    assert r109._mfe_bucket(Decimal("1")) == "R_1_TO_2"
    assert r109._mfe_bucket(Decimal("2")) == "R_2_TO_2_5"
    assert r109._mfe_bucket(Decimal("2.5")) == "GE_2_5R"


def test_r109_entry_improvement_buckets_are_fixed() -> None:
    assert r109._improvement_bucket(Decimal("-0.01")) == "LE_0"
    assert r109._improvement_bucket(Decimal("0.05")) == "GT_0_LT_10PCT"
    assert r109._improvement_bucket(Decimal("0.10")) == "PCT_10_TO_25"
    assert r109._improvement_bucket(Decimal("0.25")) == "PCT_25_TO_50"
    assert r109._improvement_bucket(Decimal("0.50")) == "GE_50PCT"


def test_r109_r108_source_is_pinned() -> None:
    assert r109.SOURCE_R108_RUN_ID == 35588274260
    assert r109.SOURCE_R108_ARTIFACT_ID == 10633277043
    assert r109.SOURCE_R108_ARTIFACT_DIGEST == (
        "sha256:dabea18405b56a58f9c0cf69aa2e60b7f9efd30788ed4a1f4372c9d7cdc33564"
    )
