from qore.infrastructure.cibo_ce2i_burned_calibration import (
    CIBO_BURNED_T04_T10_CALIBRATION,
    SOURCE_PHASE19_ARTIFACT_ID,
    SOURCE_PHASE19_ARTIFACT_SHA256,
    burned_t04_t10_calibration_payload,
    burned_t04_t10_calibration_sha256,
)


def test_burned_t04_t10_calibration_is_seven_lineage_and_holdout_clean() -> None:
    payload = burned_t04_t10_calibration_payload()

    assert len(CIBO_BURNED_T04_T10_CALIBRATION) == 7
    assert payload["source"]["phase19_artifact_id"] == SOURCE_PHASE19_ARTIFACT_ID
    assert (
        payload["source"]["phase19_artifact_sha256"]
        == SOURCE_PHASE19_ARTIFACT_SHA256
    )
    assert payload["governance"]["holdout_2017h1_used"] is False
    assert payload["governance"]["phase19j_validation_used_for_fit"] is False
    assert payload["governance"]["provider_usd_economics_claimed"] is False
    assert payload["governance"]["target_aware"] is False
    assert payload["governance"]["oos_ready"] is False
    assert payload["governance"]["certification_ready"] is False


def test_burned_calibration_hash_is_stable_and_nonempty() -> None:
    first = burned_t04_t10_calibration_sha256()
    second = burned_t04_t10_calibration_sha256()

    assert first == second
    assert len(first) == 64
