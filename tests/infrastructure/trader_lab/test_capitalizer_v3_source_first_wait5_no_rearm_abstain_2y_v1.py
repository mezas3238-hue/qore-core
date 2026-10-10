from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_no_rearm_abstain_2y_v1 as candidate,
)


def test_wait5_no_rearm_contract_is_frozen() -> None:
    assert candidate.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_NO_REARM_ABSTAIN_2Y_V1"
    )
    assert candidate.ARCHITECTURE_RULE == "WAIT_REARM_REQUIRES_NEW_CAUSAL_EVIDENCE"
    assert candidate.WAIT5_BASELINE_MAX3 == 983


def test_wait5_no_rearm_abstains_current_setup() -> None:
    fill, status = candidate._abstain_wait_fill()
    assert fill is None
    assert status == "ABSTAIN_NO_REARM"
