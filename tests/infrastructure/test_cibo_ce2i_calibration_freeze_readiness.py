from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    FrozenToolCalibration,
    FrozenToolCalibrationDisposition,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_readiness import (
    evaluate_calibration_freeze_readiness,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_COMPONENT_FREEZE_SHA256,
)

T0 = datetime(2026, 10, 1, 14, 15, tzinfo=UTC)


def _forward(*, ready: bool) -> dict[str, object]:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return {
        "manifest_sha256": "sha256:" + "1" * 64,
        "frozen_candidate_id": frozen.candidate_id,
        "frozen_code_sha": frozen.code_sha,
        "frozen_parameter_sha256": frozen.parameter_sha256(),
        "qualification_plan_id": plan.plan_id,
        "qualification_plan_sha256": phase20d_qualification_plan_sha256(),
        "baseline_policy_id": plan.baseline_policy_id,
        "ready_for_scientific_consumption": ready,
    }


def _tools() -> tuple[FrozenToolCalibration, ...]:
    provider_required = {
        row.tool_code
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.provider_economics_required
    }
    result = []
    for index in range(1, 21):
        code = f"T{index:02d}"
        disabled = code in {"T16", "T17"}
        result.append(
            FrozenToolCalibration(
                tool_code=code,
                disposition=(
                    FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED
                    if disabled
                    else FrozenToolCalibrationDisposition.CERTIFICATION_READY
                ),
                evidence_refs=(f"evidence:{code}",),
                oos_ready=not disabled,
                certification_ready=not disabled,
                structurally_disabled=disabled,
                provider_economics_bound=code in provider_required,
            )
        )
    return tuple(result)


def test_readiness_fails_closed_without_scientific_forward_manifest() -> None:
    report = evaluate_calibration_freeze_readiness(
        forward_manifest=_forward(ready=False),
        tools=_tools(),
        frozen_at=T0,
    )

    assert report.ready_to_seal is False
    assert report.calibration_manifest is None
    assert report.blockers == (
        "FORWARD_MANIFEST_NOT_SCIENTIFICALLY_CONSUMABLE",
    )
    assert report.holdout_market_data_read is False
    assert report.holdout_outcomes_used is False
    assert report.productive_authority is False


def test_readiness_reports_missing_tool_evidence_without_imputation() -> None:
    report = evaluate_calibration_freeze_readiness(
        forward_manifest=_forward(ready=True),
        tools=_tools()[:-2],
        frozen_at=T0,
    )

    assert report.ready_to_seal is False
    assert report.missing_tool_codes == ("T19", "T20")
    assert report.blockers == ("MISSING_TOOL_EVIDENCE:T19,T20",)


def test_readiness_seals_only_complete_bound_evidence() -> None:
    report = evaluate_calibration_freeze_readiness(
        forward_manifest=_forward(ready=True),
        tools=_tools(),
        frozen_at=T0,
    )

    assert report.ready_to_seal is True
    assert report.blockers == ()
    assert report.missing_tool_codes == ()
    assert report.calibration_manifest is not None
    assert report.calibration_manifest.sealed is True
    assert (
        report.calibration_manifest.provider_economics_freeze_sha256
        == PROVIDER_COMPONENT_FREEZE_SHA256
    )
    assert (
        report.calibration_manifest.phase20d_forward_manifest_sha256
        == _forward(ready=True)["manifest_sha256"]
    )
    assert report.calibration_manifest.holdout_market_data_read is False
    assert report.calibration_manifest.holdout_outcomes_used is False
