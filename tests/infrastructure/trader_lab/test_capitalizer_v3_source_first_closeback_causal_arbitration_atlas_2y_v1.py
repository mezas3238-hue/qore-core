from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_closeback_causal_arbitration_atlas_2y_v1 as atlas,
)


def test_causal_arbitration_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_CLOSEBACK_CAUSAL_ARBITRATION_ATLAS_2Y_V1"
    )
