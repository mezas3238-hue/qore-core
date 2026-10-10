from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_census_2y_v1 import (
    EXPECTED_CISD_FIRST_BLOCKERS,
    EXPECTED_CLOSEBACKS,
    EXPECTED_SAME_BAR_CISD_ONLY,
    EXPECTED_VALID_MSS,
    IDENTITY,
    MATRIX_IDENTITY,
    _counter_template,
)


def test_m5_state_census_controls_are_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_M5_DIRECTIONAL_STATE_CENSUS_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_M5_DIRECTIONAL_STATE_CENSUS_2Y_V1"
    )
    assert EXPECTED_CLOSEBACKS == 8099
    assert EXPECTED_VALID_MSS == 1254
    assert EXPECTED_CISD_FIRST_BLOCKERS == 3007
    assert EXPECTED_SAME_BAR_CISD_ONLY == 1298


def test_state_counter_is_exhaustive() -> None:
    assert _counter_template() == {
        "ALIGNED": 0,
        "OPPOSED": 0,
        "NEUTRAL": 0,
    }
