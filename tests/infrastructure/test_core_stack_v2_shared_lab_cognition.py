from qore.infrastructure.core_stack_v2.shared_lab_cognition import (
    CalibrationBin,
    ContradictionDisposition,
    ContradictionEvidence,
    ContradictionResolutionReceipt,
    UncertaintyCalibrationReceipt,
)


def test_uncertainty_calibration_detects_overconfidence():
    receipt = UncertaintyCalibrationReceipt(
        capability_id="MC09",
        bins=(
            CalibrationBin(0.9, 100, 0.5),
            CalibrationBin(0.6, 100, 0.58),
        ),
        max_allowed_weighted_error=0.15,
        max_high_confidence_wrong_rate=0.25,
    )
    assert receipt.passed is False


def test_good_calibration_passes():
    receipt = UncertaintyCalibrationReceipt(
        capability_id="MC09",
        bins=(
            CalibrationBin(0.8, 100, 0.78),
            CalibrationBin(0.6, 100, 0.62),
        ),
        max_allowed_weighted_error=0.05,
        max_high_confidence_wrong_rate=0.25,
    )
    assert receipt.passed is True


def test_contradiction_requires_physics_rejection_and_uncertainty_update():
    receipt = ContradictionResolutionReceipt(
        capability_id="ARBITER",
        evidence=(
            ContradictionEvidence("MC09", "RISK_OFF", 0.8, True, 0.8),
            ContradictionEvidence("MC18", "RISK_ON", 0.7, False, 0.6),
        ),
        disposition=ContradictionDisposition.RESOLVED,
        selected_claim="RISK_OFF",
        uncertainty_increased=True,
        impossible_world_rejected=True,
    )
    assert receipt.passed is True


def test_simple_unresolved_conflict_fails():
    receipt = ContradictionResolutionReceipt(
        capability_id="ARBITER",
        evidence=(
            ContradictionEvidence("MC09", "A", 0.8, True, 0.8),
            ContradictionEvidence("MC10", "B", 0.8, True, 0.8),
        ),
        disposition=ContradictionDisposition.UNRESOLVED,
        selected_claim=None,
        uncertainty_increased=False,
        impossible_world_rejected=False,
    )
    assert receipt.passed is False
