"""Terminal disposition semantics for frozen CE2I external utility gates.

This module closes the gap between "eligible for further research" gate outputs
and the master-ledger terminal vocabulary.  It does not create observations and
cannot certify a gate on synthetic or reused evidence.

A gate report is terminalizable only when its upstream adapter separately proves:
- fresh post-freeze/OOS population;
- current provider-bound economics;
- causal control/treatment identity;
- frozen and complete preregistered candidate universe;
- no outcome refit and no holdout rerun.

For a frozen candidate universe:
- >=1 eligible treatment => COMPLETED_AND_PROVEN;
- all treatment candidates rejected => FALSIFIED_AND_CLOSED.

No ranking, pooled rescue, parameter search, canonical-ledger mutation, or
productive authority is introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t04_t10_economic_gate import (
    Ce2iT04T10EconomicGateReport,
    Ce2iT04T10Status,
    Ce2iT04T10Tool,
)
from qore.infrastructure.cibo_expansion_utility_gate import (
    ExpansionUtilityGateReport,
    ExpansionUtilityKind,
    ExpansionUtilityStatus,
)
from qore.infrastructure.cibo_t09_t18_scarcity_safety_gate import (
    T09T18ScarcityGateReport,
    T09T18ScarcityStatus,
    T09T18ScarcityTool,
)
from qore.infrastructure.cibo_t14_t15_utility_gate import (
    T14T15UtilityGateReport,
    T14T15UtilityKind,
    T14T15UtilityStatus,
)

COMPLETED = "COMPLETED_AND_PROVEN"
FALSIFIED = "FALSIFIED_AND_CLOSED"


@dataclass(frozen=True, slots=True)
class Ce2iExternalGateProvenance:
    evidence_id: str
    source_receipt_sha256: str
    fresh_post_freeze_oos: bool
    provider_bound: bool
    causal_control_treatment_bound: bool
    candidate_universe_frozen_complete: bool
    outcome_refit_performed: bool = False
    holdout_rerun_performed: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise CiboCapitalManagementError(
                "CE2I external gate provenance evidence id required"
            )
        if (
            not self.source_receipt_sha256.startswith("sha256:")
            or len(self.source_receipt_sha256) != 71
            or any(
                char not in "0123456789abcdef"
                for char in self.source_receipt_sha256[7:]
            )
        ):
            raise CiboCapitalManagementError(
                "CE2I external gate provenance receipt SHA invalid"
            )
        required = (
            self.fresh_post_freeze_oos,
            self.provider_bound,
            self.causal_control_treatment_bound,
            self.candidate_universe_frozen_complete,
        )
        prohibited = (
            self.outcome_refit_performed,
            self.holdout_rerun_performed,
            self.canonical_ledger_modified,
            self.productive_authority,
        )
        if not all(required) or any(prohibited):
            raise CiboCapitalManagementError(
                "CE2I external gate provenance is not terminal-safe"
            )


@dataclass(frozen=True, slots=True)
class Ce2iExternalGateTerminalResult:
    workstream_id: str
    source_receipt_sha256: str
    treatment_candidate_count: int
    eligible_candidate_ids: tuple[str, ...]
    rejected_candidate_ids: tuple[str, ...]
    terminal_recommendation: str
    pooled_rescue_used: bool = False
    winner_selected: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id not in {
            "T04",
            "T06",
            "T07",
            "T09",
            "T10",
            "T14",
            "T15",
            "T18",
        }:
            raise CiboCapitalManagementError(
                "CE2I external gate workstream unsupported"
            )
        if self.treatment_candidate_count <= 0:
            raise CiboCapitalManagementError(
                "CE2I external gate requires treatment candidates"
            )
        if (
            len(self.eligible_candidate_ids) + len(self.rejected_candidate_ids)
            != self.treatment_candidate_count
        ):
            raise CiboCapitalManagementError(
                "CE2I external gate treatment disposition count drift"
            )
        if set(self.eligible_candidate_ids) & set(self.rejected_candidate_ids):
            raise CiboCapitalManagementError(
                "CE2I external gate candidate disposition overlap"
            )
        expected = COMPLETED if self.eligible_candidate_ids else FALSIFIED
        if self.terminal_recommendation != expected:
            raise CiboCapitalManagementError(
                "CE2I external gate terminal recommendation drift"
            )
        if (
            self.pooled_rescue_used
            or self.winner_selected
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "CE2I external terminal result exceeded authority"
            )


def terminalize_t04_t10(
    *,
    report: Ce2iT04T10EconomicGateReport,
    provenance: Ce2iExternalGateProvenance,
) -> tuple[Ce2iExternalGateTerminalResult, Ce2iExternalGateTerminalResult]:
    if not isinstance(report, Ce2iT04T10EconomicGateReport):
        raise CiboCapitalManagementError(
            "T04/T10 terminalization requires canonical gate report"
        )
    _require_provenance(provenance)
    tools = {item.tool for item in report.verdicts}
    if tools != {Ce2iT04T10Tool.T04, Ce2iT04T10Tool.T10}:
        raise CiboCapitalManagementError(
            "T04/T10 terminalization requires both frozen tool surfaces"
        )
    return (
        _from_verdicts(
            workstream_id="T04",
            rows=tuple(
                (item.candidate_id, item.status)
                for item in report.verdicts
                if item.tool is Ce2iT04T10Tool.T04
            ),
            control_status=Ce2iT04T10Status.CONTROL,
            eligible_status=Ce2iT04T10Status.ELIGIBLE_FOR_FURTHER_RESEARCH,
            provenance=provenance,
        ),
        _from_verdicts(
            workstream_id="T10",
            rows=tuple(
                (item.candidate_id, item.status)
                for item in report.verdicts
                if item.tool is Ce2iT04T10Tool.T10
            ),
            control_status=Ce2iT04T10Status.CONTROL,
            eligible_status=Ce2iT04T10Status.ELIGIBLE_FOR_FURTHER_RESEARCH,
            provenance=provenance,
        ),
    )


def terminalize_expansion(
    *,
    report: ExpansionUtilityGateReport,
    provenance: Ce2iExternalGateProvenance,
) -> Ce2iExternalGateTerminalResult:
    if not isinstance(report, ExpansionUtilityGateReport):
        raise CiboCapitalManagementError(
            "T06/T07 terminalization requires canonical expansion report"
        )
    _require_provenance(provenance)
    workstream_id = (
        "T06"
        if report.kind is ExpansionUtilityKind.T06_PROFIT_FUNDED
        else "T07"
    )
    return _from_verdicts(
        workstream_id=workstream_id,
        rows=tuple((item.candidate_id, item.status) for item in report.rows),
        control_status=ExpansionUtilityStatus.CONTROL,
        eligible_status=ExpansionUtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
        provenance=provenance,
    )


def terminalize_t09_t18(
    *,
    report: T09T18ScarcityGateReport,
    provenance: Ce2iExternalGateProvenance,
) -> tuple[Ce2iExternalGateTerminalResult, Ce2iExternalGateTerminalResult]:
    if not isinstance(report, T09T18ScarcityGateReport):
        raise CiboCapitalManagementError(
            "T09/T18 terminalization requires canonical scarcity report"
        )
    _require_provenance(provenance)
    tools = {item.tool for item in report.verdicts}
    if tools != {T09T18ScarcityTool.T09, T09T18ScarcityTool.T18}:
        raise CiboCapitalManagementError(
            "T09/T18 terminalization requires both frozen tool surfaces"
        )
    return (
        _from_verdicts(
            workstream_id="T09",
            rows=tuple(
                (item.candidate_id, item.status)
                for item in report.verdicts
                if item.tool is T09T18ScarcityTool.T09
            ),
            control_status=T09T18ScarcityStatus.CONTROL,
            eligible_status=T09T18ScarcityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
            provenance=provenance,
        ),
        _from_verdicts(
            workstream_id="T18",
            rows=tuple(
                (item.candidate_id, item.status)
                for item in report.verdicts
                if item.tool is T09T18ScarcityTool.T18
            ),
            control_status=T09T18ScarcityStatus.CONTROL,
            eligible_status=T09T18ScarcityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
            provenance=provenance,
        ),
    )


def terminalize_t14_t15(
    *,
    report: T14T15UtilityGateReport,
    provenance: Ce2iExternalGateProvenance,
) -> Ce2iExternalGateTerminalResult:
    if not isinstance(report, T14T15UtilityGateReport):
        raise CiboCapitalManagementError(
            "T14/T15 terminalization requires canonical utility report"
        )
    _require_provenance(provenance)
    workstream_id = (
        "T14"
        if report.kind is T14T15UtilityKind.T14_DYNAMIC_DERISKING
        else "T15"
    )
    return _from_verdicts(
        workstream_id=workstream_id,
        rows=tuple((item.candidate_id, item.status) for item in report.rows),
        control_status=T14T15UtilityStatus.CONTROL,
        eligible_status=T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
        provenance=provenance,
    )


def _require_provenance(value: Ce2iExternalGateProvenance) -> None:
    if not isinstance(value, Ce2iExternalGateProvenance):
        raise CiboCapitalManagementError(
            "CE2I external gate requires canonical terminal-safe provenance"
        )


def _from_verdicts(
    *,
    workstream_id: str,
    rows: tuple[tuple[str, StrEnum], ...],
    control_status: StrEnum,
    eligible_status: StrEnum,
    provenance: Ce2iExternalGateProvenance,
) -> Ce2iExternalGateTerminalResult:
    controls = tuple(candidate for candidate, status in rows if status is control_status)
    treatments = tuple(
        (candidate, status)
        for candidate, status in rows
        if status is not control_status
    )
    if len(controls) != 1 or not treatments:
        raise CiboCapitalManagementError(
            f"{workstream_id} terminalization requires one control and treatment"
        )
    eligible = tuple(
        candidate for candidate, status in treatments if status is eligible_status
    )
    rejected = tuple(
        candidate for candidate, status in treatments if status is not eligible_status
    )
    if len(eligible) + len(rejected) != len(treatments):
        raise CiboCapitalManagementError(
            f"{workstream_id} terminalization candidate accounting drift"
        )
    return Ce2iExternalGateTerminalResult(
        workstream_id=workstream_id,
        source_receipt_sha256=provenance.source_receipt_sha256,
        treatment_candidate_count=len(treatments),
        eligible_candidate_ids=eligible,
        rejected_candidate_ids=rejected,
        terminal_recommendation=COMPLETED if eligible else FALSIFIED,
        pooled_rescue_used=False,
        winner_selected=False,
        canonical_ledger_modified=False,
        productive_authority=False,
    )
