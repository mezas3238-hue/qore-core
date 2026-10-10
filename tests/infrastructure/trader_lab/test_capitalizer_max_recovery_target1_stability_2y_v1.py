from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target1_stability_2y_v1 as stability,
)


def test_target1_stability_contract_is_frozen() -> None:
    assert stability.IDENTITY == (
        "QORE_CAPITALIZER_MAX_RECOVERY_TARGET1_STABILITY_2Y_V1"
    )
    assert stability.CANDIDATE_TARGET_R == Decimal("1.00")
    assert stability.SOURCE_TARGET_RUN_ID == 35941710028
    assert stability.SOURCE_TARGET_SHA == (
        "00dcd48d702d6a0c1c45abb69a3714a8ac66497b"
    )
    assert stability.EXPECTED_RAW_TRADES == 963
    assert stability.EXPECTED_MAX3_TRADES == 948
    assert stability.EXPECTED_PF == Decimal(
        "2.608801712095744666571338155"
    )
    assert stability.EXPECTED_DD_R == Decimal(
        "8.671360188479779752380440576"
    )
    assert stability.EXPECTED_LS == 5
