"""Terminal calibration evidence for the owner-authorized Shadow successor lane."""

from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    FrozenToolCalibration,
    FrozenToolCalibrationDisposition,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_readiness import (
    CiboCalibrationFreezeReadiness,
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
from qore.infrastructure.cibo_ce2i_shadow_certification_receipts import (
    PHASE20_SHADOW_ARTIFACT_DIGEST,
)

TERMINAL_CALIBRATION_FROZEN_AT = datetime(
    2026, 10, 1, 14, 9, 29, tzinfo=UTC
)
ACTIVE_CERTIFICATION_TOOLS = ("T01", "T05", "T11", "T19", "T20")
STRUCTURALLY_DISABLED_TOOLS = ("T16", "T17")
QUALIFICATION_FAILED_TOOLS = (
    "T02",
    "T03",
    "T04",
    "T06",
    "T07",
    "T08",
    "T09",
    "T10",
    "T12",
    "T13",
    "T14",
    "T15",
    "T18",
)

_PHASE21_REF = (
    "github-actions-artifact://11164600745/"
    "sha256:0b3d0b892207ec3f5873240175eb08dc15cebd31c23d8621472933e691a2990c"
)
_PROVIDER_REF = (
    "github-actions-artifact://11168043616/"
    "sha256:4512f736823bb43274f99bd01fb0114d93ba533b301b8ec6fa75512f59ae0462"
)
_EVIDENCE: dict[str, tuple[str, ...]] = {
    "T01": ("github-actions://36871406294/SUCCESS", _PHASE21_REF),
    "T02": ("github-actions://36871406509/SUCCESS", _PHASE21_REF),
    "T03": (_PROVIDER_REF, _PHASE21_REF),
    "T04": ("github-actions://36854823928/SUCCESS", _PHASE21_REF),
    "T05": ("github-actions://36649279224/SUCCESS", _PHASE21_REF),
    "T06": (
        "github-actions://36854824274/SUCCESS",
        "github-actions://36854824559/SUCCESS",
        _PHASE21_REF,
    ),
    "T07": (
        "github-actions://36854824274/SUCCESS",
        "github-actions://36854824559/SUCCESS",
        _PHASE21_REF,
    ),
    "T08": ("github-actions://36854824566/SUCCESS", _PHASE21_REF),
    "T09": (
        "github-actions://36854824350/SUCCESS",
        "github-actions://36854824566/SUCCESS",
        _PHASE21_REF,
    ),
    "T10": ("github-actions://36854823928/SUCCESS", _PHASE21_REF),
    "T11": (_PROVIDER_REF, _PHASE21_REF),
    "T12": (
        "github-actions://36854824202/SUCCESS",
        "github-actions://36854824566/SUCCESS",
        _PHASE21_REF,
    ),
    "T13": (
        "github-actions://36854824195/SUCCESS",
        "github-actions://36854824566/SUCCESS",
        _PHASE21_REF,
    ),
    "T14": (
        "github-actions://36854824256/SUCCESS",
        "github-actions://36854824559/SUCCESS",
        _PHASE21_REF,
    ),
    "T15": (
        "github-actions://36854824256/SUCCESS",
        "github-actions://36854824559/SUCCESS",
        _PHASE21_REF,
    ),
    "T16": (
        "github-actions-artifact://11166479835/"
        "sha256:ab885ebd01e7cdb603bf2c98eb3a44909879bdd4cb3ca9a3a61d040e80725cd6",
        _PROVIDER_REF,
    ),
    "T17": ("github-actions://36871406456/SUCCESS", _PROVIDER_REF),
    "T18": (
        "github-actions://36854824350/SUCCESS",
        "github-actions://36854824566/SUCCESS",
        _PHASE21_REF,
    ),
    "T19": ("github-actions://36750376948/SUCCESS", _PHASE21_REF),
    "T20": ("github-actions://36871406572/SUCCESS", _PHASE21_REF),
}


def shadow_successor_manifest() -> dict[str, object]:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return {
        "manifest_sha256": PHASE20_SHADOW_ARTIFACT_DIGEST,
        "frozen_candidate_id": frozen.candidate_id,
        "frozen_code_sha": frozen.code_sha,
        "frozen_parameter_sha256": frozen.parameter_sha256(),
        "qualification_plan_id": plan.plan_id,
        "qualification_plan_sha256": phase20d_qualification_plan_sha256(),
        "baseline_policy_id": plan.baseline_policy_id,
        "evidence_kind": "HISTORICAL_SHADOW_QUALIFICATION",
        "owner_authorized_forward_successor": True,
        "candidate_outcomes": 855,
        "decision_epochs": 775,
        "distinct_trading_days": 214,
        "represented_lineages": 7,
        "fold_count": 4,
        "ready_for_scientific_consumption": True,
        "holdout_2017h1_read": False,
    }


def terminal_tool_evidence() -> tuple[FrozenToolCalibration, ...]:
    canonical = tuple(f"T{index:02d}" for index in range(1, 21))
    coverage = (
        set(ACTIVE_CERTIFICATION_TOOLS)
        | set(STRUCTURALLY_DISABLED_TOOLS)
        | set(QUALIFICATION_FAILED_TOOLS)
    )
    if coverage != set(canonical):
        raise CiboCapitalManagementError(
            "terminal calibration evidence coverage drift"
        )
    provider_required = {
        row.tool_code
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.provider_economics_required
    }
    rows: list[FrozenToolCalibration] = []
    for code in canonical:
        if code in ACTIVE_CERTIFICATION_TOOLS:
            disposition = FrozenToolCalibrationDisposition.CERTIFICATION_READY
            oos_ready = True
            certification_ready = True
            disabled = False
        elif code in STRUCTURALLY_DISABLED_TOOLS:
            disposition = FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED
            oos_ready = False
            certification_ready = False
            disabled = True
        else:
            disposition = (
                FrozenToolCalibrationDisposition.QUALIFICATION_FAILED_AND_DISABLED
            )
            oos_ready = True
            certification_ready = False
            disabled = True
        rows.append(
            FrozenToolCalibration(
                tool_code=code,
                disposition=disposition,
                evidence_refs=_EVIDENCE[code],
                oos_ready=oos_ready,
                certification_ready=certification_ready,
                structurally_disabled=disabled,
                provider_economics_bound=code in provider_required,
                holdout_outcomes_used=False,
                target_aware=False,
            )
        )
    return tuple(rows)


def build_terminal_calibration_readiness(
) -> CiboCalibrationFreezeReadiness:
    report = evaluate_calibration_freeze_readiness(
        forward_manifest=shadow_successor_manifest(),
        tools=terminal_tool_evidence(),
        frozen_at=TERMINAL_CALIBRATION_FROZEN_AT,
    )
    if not report.ready_to_seal or report.calibration_manifest is None:
        raise CiboCapitalManagementError(
            "terminal calibration evidence did not seal"
        )
    return report
