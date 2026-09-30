from qore.infrastructure.trader_lab.capitalizer_joint_state_forensics import (
    _joint_state_key,
)


def test_joint_state_key_is_stable_and_explicit() -> None:
    assert _joint_state_key(
        state_family="RECLAIM_ALL_FRESH",
        source_age_state="OLDER_H1_SOURCE",
        boundary_type_state="SWING_HIGH_LOW_ONLY",
        reclaim_phase="RECLAIM_STRICTLY_BEFORE",
    ) == (
        "RECLAIM_ALL_FRESH|OLDER_H1_SOURCE|SWING_HIGH_LOW_ONLY|"
        "RECLAIM_STRICTLY_BEFORE"
    )
