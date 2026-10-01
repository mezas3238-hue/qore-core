from qore.infrastructure.cibo_ce2i_pre_holdout_freeze import (
    ACTIVE_PRE_HOLDOUT_FREEZE,
    CALIBRATION_FREEZE_ARTIFACT_ID,
    CALIBRATION_MANIFEST_FINGERPRINT,
    CURRENT_HOLDOUT_SEAL_STATE,
    PRE_HOLDOUT_CHECKPOINT_ARTIFACT_ID,
    CiboHoldoutSealState,
    pre_holdout_freeze_ready,
    pre_holdout_freeze_receipt_payload,
    require_pre_holdout_freeze_before_2017h1_access,
)


def test_pre_holdout_freeze_is_explicitly_active_and_receipted() -> None:
    assert CURRENT_HOLDOUT_SEAL_STATE is CiboHoldoutSealState.PRE_HOLDOUT_FROZEN
    assert ACTIVE_PRE_HOLDOUT_FREEZE is not None
    assert pre_holdout_freeze_ready() is True
    require_pre_holdout_freeze_before_2017h1_access()

    payload = pre_holdout_freeze_receipt_payload()
    assert payload["ready"] is True
    assert payload["checkpoint"]["artifact_id"] == PRE_HOLDOUT_CHECKPOINT_ARTIFACT_ID
    assert (
        payload["calibration_freeze"]["artifact_id"]
        == CALIBRATION_FREEZE_ARTIFACT_ID
    )
    assert (
        payload["calibration_freeze"]["manifest_fingerprint"]
        == CALIBRATION_MANIFEST_FINGERPRINT
    )
    assert payload["governance"]["holdout_outcomes_inspected"] is False
    assert payload["governance"]["holdout_market_data_read_before_freeze"] is False
