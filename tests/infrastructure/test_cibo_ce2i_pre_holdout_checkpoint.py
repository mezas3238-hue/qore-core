from qore.infrastructure.cibo_ce2i_pre_holdout_checkpoint import (
    build_pre_holdout_checkpoint,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze import (
    CiboHoldoutSealState,
)


def test_pre_holdout_checkpoint_fails_closed_before_full_calibration() -> None:
    checkpoint = build_pre_holdout_checkpoint()

    assert checkpoint.holdout_state is CiboHoldoutSealState.SEALED_UNTOUCHED
    assert checkpoint.holdout_2017h1_read is False
    assert checkpoint.pre_holdout_freeze_active is False
    assert checkpoint.calibrated_tools == (
        "T02",
        "T04",
        "T05",
        "T06",
        "T07",
        "T10",
        "T19",
        "T20",
    )
    assert checkpoint.oos_ready_tools == ()
    assert checkpoint.certification_ready_tools == ()
    assert checkpoint.ready_to_freeze is False
    assert len(checkpoint.matrix_sha256) == 64
