from qore.infrastructure.cibo_ce2i_pre_holdout_gate import (
    CiboPreHoldoutStatus,
    calibration_matrix_sha256,
    evaluate_pre_holdout_readiness,
)


def test_pre_holdout_gate_is_fail_closed_before_calibration_freeze() -> None:
    readiness = evaluate_pre_holdout_readiness()

    assert readiness.status is CiboPreHoldoutStatus.NOT_READY
    assert readiness.holdout_candidate_id == "CIBO_USD60_6M_HOLDOUT_2017H1_V1"
    assert readiness.holdout_outcomes_inspected is False
    assert readiness.holdout_market_data_read is False
    assert "PROVIDER_ECONOMICS_NOT_FROZEN" in readiness.blockers
    assert "CALIBRATION_FREEZE_MANIFEST_NOT_SEALED" in readiness.blockers
    assert any(
        item.startswith("UNRESOLVED_CAUSAL_CALIBRATIONS:")
        for item in readiness.blockers
    )


def test_matrix_digest_is_stable_and_nonempty() -> None:
    first = calibration_matrix_sha256()
    second = calibration_matrix_sha256()

    assert first == second
    assert len(first) == 64


def test_t16_t17_fail_closed_does_not_by_itself_contaminate_holdout() -> None:
    readiness = evaluate_pre_holdout_readiness(
        provider_economics_frozen=True,
        calibration_freeze_manifest_sealed=True,
    )

    assert readiness.holdout_outcomes_inspected is False
    assert readiness.holdout_market_data_read is False
    assert not any(
        item.startswith("UNRESOLVED_FAIL_CLOSED_TOOLS:T16")
        for item in readiness.blockers
    )
    assert not any(
        item.startswith("UNRESOLVED_FAIL_CLOSED_TOOLS:T17")
        for item in readiness.blockers
    )
