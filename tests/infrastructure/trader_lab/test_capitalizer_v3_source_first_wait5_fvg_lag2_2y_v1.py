from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_fvg_lag2_2y_v1 as candidate,
)


def test_fvg_lag2_candidate_contract_is_frozen() -> None:
    assert candidate.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_FVG_LAG2_2Y_V1"
    )
    assert candidate.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_FVG_LAG2_2Y_V1"
    )
    assert candidate.MAX_CONFIRMATION_LAG_MINUTES == 2
    assert candidate.WAIT5_BASELINE_RAW == 1003
    assert candidate.WAIT5_BASELINE_MAX3 == 983


def test_lag2_trade_detection_uses_fvg_confirmation_after_mss() -> None:
    class Trade:
        m1_fvg_confirmed_at = "2026-01-01T10:02:00+00:00"
        m3_mss_at = "2026-01-01T10:01:00+00:00"

    assert candidate._is_lag2_trade(Trade()) is True
