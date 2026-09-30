from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait_rejected_parallel_rearm_atlas_2y_v1 as atlas,
)


def test_rejected_wait_parallel_rearm_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT_REJECTED_PARALLEL_REARM_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_POPULATION == 165
    assert atlas.WAIT_MINUTES == 5
    assert atlas.REJECTED == {"WAIT_STOP_INVALIDATED", "WAIT_NO_REFILL"}
