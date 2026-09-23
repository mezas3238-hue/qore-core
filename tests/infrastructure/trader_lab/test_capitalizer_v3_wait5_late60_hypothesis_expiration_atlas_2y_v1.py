from qore.infrastructure.trader_lab import (
    capitalizer_v3_wait5_late60_hypothesis_expiration_atlas_2y_v1 as atlas,
)


def test_hypothesis_expiration_atlas_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_WAIT5_LATE60_HYPOTHESIS_EXPIRATION_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_SUPERSESSION_ROWS == 376
    assert atlas.EXPECTED_CARRY_ROWS == 365


def test_continuity_state_is_structural_only() -> None:
    assert atlas._continuity_state({"new_state": "NO_NEW_SWEEP"}) == (
        atlas.NO_NEW_H1_SWEEP
    )
    assert atlas._continuity_state({"new_state": "NEW_SWEEP_ONLY"}) == (
        atlas.NEW_H1_SWEEP_PENDING
    )
    assert atlas._continuity_state({"new_state": "NEW_CLOSEBACK_NO_MSS"}) == (
        atlas.NEW_H1_CLOSEBACK_PENDING
    )
    assert atlas._continuity_state(
        {
            "new_state": "NEW_MSS",
            "new_mss_side_relation": "OPPOSED_SIDE",
        }
    ) == atlas.OPPOSED_NEW_H1_MSS
    assert atlas._continuity_state(
        {
            "new_state": "NEW_MSS",
            "new_mss_side_relation": "SAME_SIDE",
        }
    ) == atlas.SAME_SIDE_NEW_H1_MSS
