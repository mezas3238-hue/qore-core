from qore.infrastructure.trader_lab.capitalizer_joint_state_ablation import (
    _is_blocked,
)


def test_exact_weak_joint_state_is_blocked() -> None:
    assert _is_blocked(
        ablation="DROP_OLDER_PRIOR_STRICT_RECLAIM",
        state_family="RECLAIM_ALL_FRESH",
        source_age_state="OLDER_H1_SOURCE",
        boundary_type_state="PRIOR_HIGH_LOW_ONLY",
        reclaim_phase="RECLAIM_STRICTLY_BEFORE",
    )


def test_exact_ablation_does_not_block_swing_source() -> None:
    assert not _is_blocked(
        ablation="DROP_OLDER_PRIOR_STRICT_RECLAIM",
        state_family="RECLAIM_ALL_FRESH",
        source_age_state="OLDER_H1_SOURCE",
        boundary_type_state="SWING_HIGH_LOW_ONLY",
        reclaim_phase="RECLAIM_STRICTLY_BEFORE",
    )


def test_broader_nonswing_group_is_still_categorical() -> None:
    assert _is_blocked(
        ablation="DROP_OLDER_NONSWING_STRICT_RECLAIM",
        state_family="RECLAIM_ALL_FRESH",
        source_age_state="OLDER_H1_SOURCE",
        boundary_type_state="MIXED_BOUNDARY_TYPE",
        reclaim_phase="RECLAIM_STRICTLY_BEFORE",
    )
