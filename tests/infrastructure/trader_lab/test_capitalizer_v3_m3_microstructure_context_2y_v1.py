from qore.infrastructure.trader_lab.capitalizer_v3_m3_microstructure_context_2y_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    _metrics,
)


def test_v3_m3_microstructure_adapter_identity() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_M3_MICROSTRUCTURE_CONTEXT_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_M3_MICROSTRUCTURE_CONTEXT_2Y_V1"
    )


def test_empty_metrics_are_safe() -> None:
    assert _metrics(()) == {
        "observations": 0,
        "median_body_fraction": None,
        "median_close_location": None,
        "median_previous_range_ratio": None,
    }
