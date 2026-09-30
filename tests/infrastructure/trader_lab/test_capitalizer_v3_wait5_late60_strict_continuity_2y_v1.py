from qore.infrastructure.trader_lab import (
    capitalizer_v3_wait5_late60_strict_continuity_2y_v1 as candidate,
)


def test_strict_continuity_contract_is_frozen() -> None:
    assert candidate.IDENTITY == (
        "QORE_CAPITALIZER_V3_WAIT5_LATE60_STRICT_CONTINUITY_2Y_V1"
    )
    assert candidate.EXPECTED_ATLAS_ROWS == 365
    assert candidate.EXPECTED_LATE_RAW == 365
    assert candidate.EXPECTED_ELIGIBLE_LATE == 57
    assert candidate.EXPECTED_WAIT5_RAW == 1003
    assert candidate.EXPECTED_WAIT5_MAX3 == 983


def test_strict_continuity_requires_all_three_structural_conditions() -> None:
    valid = {
        "continuity_state": "NO_NEW_H1_SWEEP",
        "deadline_m5_state": "ALIGNED",
        "any_opposed_since_deadline": False,
    }
    assert candidate._strict_continuity_admitted(valid) is True

    for key, value in (
        ("continuity_state", "NEW_H1_SWEEP_PENDING"),
        ("deadline_m5_state", "NEUTRAL"),
        ("any_opposed_since_deadline", True),
    ):
        row = dict(valid)
        row[key] = value
        assert candidate._strict_continuity_admitted(row) is False
