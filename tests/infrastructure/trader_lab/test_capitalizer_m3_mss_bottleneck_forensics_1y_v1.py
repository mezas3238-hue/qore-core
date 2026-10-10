from collections import Counter

from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_1y_v1 import (
    EXPECTED_CLOSEBACKS,
    EXPECTED_VALID_M3,
    FAILURE_NAMES,
    IDENTITY,
    MATRIX_IDENTITY,
)


def test_identity_and_frozen_baseline() -> None:
    assert IDENTITY.endswith("M3_MSS_BOTTLENECK_FORENSICS_1Y_V1")
    assert MATRIX_IDENTITY.startswith("QORE_CAPITALIZER_NINE_MARKET_")
    assert EXPECTED_CLOSEBACKS == 4039
    assert EXPECTED_VALID_M3 == 621


def test_failure_names_are_predeclared() -> None:
    assert FAILURE_NAMES == (
        "DIRECTION",
        "SWING_BREAK",
        "CISD",
        "BODY_LT_60",
        "ATR_LE_1_2",
    )


def test_first_blocker_categories_are_disjoint_by_construction() -> None:
    rows = ["DIRECTION", "SWING_BREAK", "VALID", "BODY_LT_60"]
    counts = Counter(rows)
    assert sum(counts.values()) == len(rows)


def test_forensics_does_not_define_outcome_categories() -> None:
    assert "WIN" not in FAILURE_NAMES
    assert "LOSS" not in FAILURE_NAMES
