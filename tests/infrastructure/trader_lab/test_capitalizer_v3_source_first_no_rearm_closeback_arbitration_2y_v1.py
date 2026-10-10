from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_no_rearm_closeback_arbitration_2y_v1 as candidate,
)


def test_causal_closeback_arbitration_contract_is_frozen() -> None:
    assert candidate.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_NO_REARM_CLOSEBACK_ARBITRATION_2Y_V1"
    )
    assert candidate.POLICY == "EARLIEST_CAUSAL_EXECUTABLE_CLOSEBACK_WINS"
    assert candidate.BASELINE_RAW == 804
    assert candidate.BASELINE_MAX3 == 793
