from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_v3_m5_aligned_gate_experiment_2y_v1 import (
    BASELINE_DD_R,
    BASELINE_MAX3_TRADES,
    BASELINE_MEAN_R,
    BASELINE_PF,
    BASELINE_RAW_TRADES,
    BASELINE_TOTAL_R,
    IDENTITY,
    MATRIX_IDENTITY,
)


def test_m5_aligned_experiment_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_M5_ALIGNED_GATE_EXPERIMENT_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_M5_ALIGNED_GATE_EXPERIMENT_2Y_V1"
    )
    assert BASELINE_RAW_TRADES == 475
    assert BASELINE_MAX3_TRADES == 474
    assert BASELINE_PF == Decimal("1.283270342004661566350801358")
    assert BASELINE_TOTAL_R == Decimal("50.34686423146549474995387094")
    assert BASELINE_MEAN_R == Decimal("0.1062170131465516766876663944")
    assert BASELINE_DD_R == Decimal("13.43559872546085473546771142")
