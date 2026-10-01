from qore.infrastructure.cibo_phase22_demo_calibration_contract import (
    CALIBRATION_AUTHORIZATION_TOKEN,
    CALIBRATION_LABEL_PREFIX,
    MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL,
    PHASE22_DEMO_CALIBRATION_GOVERNANCE,
    REQUIRED_SYMBOLS,
)


def test_phase22_demo_calibration_surface_is_strict() -> None:
    assert CALIBRATION_AUTHORIZATION_TOKEN == (
        "CIBO_PHASE22_DEMO_EXECUTION_CALIBRATION_AUTHORIZED"
    )
    assert CALIBRATION_LABEL_PREFIX == "QORE:CIBO-CAL:"
    assert MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL == 8
    assert REQUIRED_SYMBOLS == (
        "AUDJPY",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "XAUUSD",
    )


def test_phase22_demo_calibration_never_grants_live_or_real_capital() -> None:
    governance = PHASE22_DEMO_CALIBRATION_GOVERNANCE

    assert governance.environment == "demo"
    assert governance.endpoint_host == "demo.ctraderapi.com"
    assert governance.account_must_be_non_live is True
    assert governance.minimum_volume_only is True
    assert governance.close_created_position_only is True
    assert governance.holdout_outcomes_allowed is False
    assert governance.fundednext_allowed is False
    assert governance.live_allowed is False
    assert governance.real_capital_allowed is False
    assert governance.vps_required is False
