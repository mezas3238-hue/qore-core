from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_added_causal_forensics_2y_v1 as atlas,
)


def test_source_first_added_causal_forensics_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_ADDED_CAUSAL_FORENSICS_2Y_V1"
    )
    assert atlas.EXPECTED_SOURCE_FIRST_MAX3 == 1118
    assert atlas.EXPECTED_ADDED_SELECTED == 719
    assert atlas.EXPECTED_DD_EPISODE_TRADES == 148
    assert atlas.EXPECTED_DD_ADDED == 87
