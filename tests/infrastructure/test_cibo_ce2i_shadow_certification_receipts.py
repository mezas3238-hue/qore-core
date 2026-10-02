from qore.infrastructure.cibo_ce2i_shadow_certification_receipts import (
    PHASE20_SHADOW_ARTIFACT_ID,
    PHASE21_FREEZE_ARTIFACT_ID,
    PHASE21_SCREEN_ARTIFACT_ID,
    SHADOW_CERTIFICATION_RECEIPTS,
    shadow_receipt_payload,
)


def test_shadow_certification_receipts_are_terminal_and_holdout_safe() -> None:
    receipts = SHADOW_CERTIFICATION_RECEIPTS
    payload = shadow_receipt_payload()

    assert receipts.phase20_shadow_passed is True
    assert receipts.phase21_screen_passed is True
    assert receipts.phase21_policy_freeze_sealed is True
    assert receipts.final_holdout_2017h1_read is False
    assert payload["phase20_shadow"]["artifact_id"] == PHASE20_SHADOW_ARTIFACT_ID
    assert payload["phase21_screen"]["artifact_id"] == PHASE21_SCREEN_ARTIFACT_ID
    assert (
        payload["phase21_policy_freeze"]["artifact_id"]
        == PHASE21_FREEZE_ARTIFACT_ID
    )
    assert payload["governance"]["final_holdout_2017h1_read"] is False
