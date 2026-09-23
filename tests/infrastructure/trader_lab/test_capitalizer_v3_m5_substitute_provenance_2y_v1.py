from qore.infrastructure.trader_lab.capitalizer_v3_m5_substitute_provenance_2y_v1 import (
    EXPECTED_CISD_FIRST_BLOCKER_SUBSTITUTES,
    EXPECTED_STEP4_SUBSTITUTE_CONFIRMATIONS,
    IDENTITY,
    MATRIX_IDENTITY,
)


def test_substitute_provenance_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_M5_SUBSTITUTE_PROVENANCE_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_M5_SUBSTITUTE_PROVENANCE_2Y_V1"
    )
    assert EXPECTED_STEP4_SUBSTITUTE_CONFIRMATIONS == 44
    assert EXPECTED_CISD_FIRST_BLOCKER_SUBSTITUTES == 28
