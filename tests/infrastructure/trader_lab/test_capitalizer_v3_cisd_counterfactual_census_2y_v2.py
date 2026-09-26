from qore.infrastructure.trader_lab.capitalizer_v3_cisd_counterfactual_census_2y_v2 import (
    EXPECTED_CISD_FIRST_BLOCKERS,
    IDENTITY,
    MATRIX_IDENTITY,
    STEP4_EXPECTED_ALIGNED_SUBSTITUTE_CONFIRMATIONS,
)


def test_corrected_cisd_census_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_CISD_COUNTERFACTUAL_CENSUS_2Y_V2"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_COUNTERFACTUAL_CENSUS_2Y_V2"
    )
    assert EXPECTED_CISD_FIRST_BLOCKERS == 3007
    assert STEP4_EXPECTED_ALIGNED_SUBSTITUTE_CONFIRMATIONS == 44
