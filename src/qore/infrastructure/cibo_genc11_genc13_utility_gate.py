"""Executable GEN-C11 / GEN-C13 utility wrapper over the frozen GEN-C9 law.

GEN-C11 MPC and GEN-C13 prospective memory use deliberately reuse the same
non-compensatory safety/economic law instead of inventing weighted scores.
This module makes that reuse executable while enforcing each workstream's
specific causal prerequisites.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_genc9_economic_gate import (
    GENC9_ECONOMIC_GATE_ID,
    Genc9EconomicGateStatus,
    evaluate_genc9_economic_gate,
)
from qore.infrastructure.cibo_genc10_transition_uncertainty_calibration import (
    Genc10TransitionCalibrationReport,
)
from qore.infrastructure.cibo_robust_growth_ruin_capacity import (
    Genc9CandidateRole,
    Genc9ResearchReport,
)

GATE_ID = "CIBO_GENC11_GENC13_NONCOMPENSATORY_UTILITY_WRAPPER_V1"
GATE_SHA256 = (
    "sha256:97f9b42b8843d5aa1483a387c8df87dff7f3c5e9"
    "7206c98970673769bcc7e9d7"
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Genc11Genc13Workstream(StrEnum):
    GENC11 = "GEN-C11"
    GENC13 = "GEN-C13"


@dataclass(frozen=True, slots=True)
class Genc11Genc13UtilityInput:
    evaluation_id: str
    workstream: Genc11Genc13Workstream
    control_candidate_id: str
    treatment_candidate_id: str
    population_sha256: str
    provider_surface_sha256: str
    protocol_binding_sha256: str
    research_report: Genc9ResearchReport
    causal_effect_identified: bool
    treatment_preregistered_before_outcomes: bool
    temporal_separation_proven: bool
    transition_uncertainty_calibrated: bool = False
    transition_calibration_sha256: str | None = None
    transition_calibration_population_sha256: str | None = None
    transition_calibration_report: Genc10TransitionCalibrationReport | None = None
    prospective_memory_use_ablation: bool = False
    memory_hypothesis_sha256: str | None = None
    retrospective_counterfactual_used_as_causal: bool = False
    future_outcome_used: bool = False
    weighted_score_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.evaluation_id:
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility evaluation identity is required"
            )
        if type(self.workstream) is not Genc11Genc13Workstream:
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility workstream is invalid"
            )
        if (
            not self.control_candidate_id
            or not self.treatment_candidate_id
            or self.control_candidate_id == self.treatment_candidate_id
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 control/treatment identities are invalid"
            )
        for name in (
            "population_sha256",
            "provider_surface_sha256",
            "protocol_binding_sha256",
        ):
            _sha(getattr(self, name), name)
        if not isinstance(self.research_report, Genc9ResearchReport):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility requires canonical GEN-C9 research report"
            )

        summaries = self.research_report.summaries
        if {item.candidate_id for item in summaries} != {
            self.control_candidate_id,
            self.treatment_candidate_id,
        }:
            raise CiboCompoundCapitalError(
                "GEN-C11/13 report candidate identity drift"
            )
        controls = tuple(
            item
            for item in summaries
            if item.role is Genc9CandidateRole.CONTROL
        )
        treatments = tuple(
            item
            for item in summaries
            if item.role is Genc9CandidateRole.TREATMENT
        )
        if (
            len(controls) != 1
            or len(treatments) != 1
            or controls[0].candidate_id != self.control_candidate_id
            or treatments[0].candidate_id != self.treatment_candidate_id
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 report role binding drift"
            )

        for name in (
            "causal_effect_identified",
            "treatment_preregistered_before_outcomes",
            "temporal_separation_proven",
            "transition_uncertainty_calibrated",
            "prospective_memory_use_ablation",
            "retrospective_counterfactual_used_as_causal",
            "future_outcome_used",
            "weighted_score_used",
            "productive_authority",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C11/13 utility {name} must be bool"
                )

        if (
            not self.causal_effect_identified
            or not self.treatment_preregistered_before_outcomes
            or not self.temporal_separation_proven
            or self.retrospective_counterfactual_used_as_causal
            or self.future_outcome_used
            or self.weighted_score_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility governance/causal drift"
            )

        if self.workstream is Genc11Genc13Workstream.GENC11:
            if (
                not self.transition_uncertainty_calibrated
                or self.transition_calibration_sha256 is None
                or self.transition_calibration_population_sha256 is None
                or not isinstance(
                    self.transition_calibration_report,
                    Genc10TransitionCalibrationReport,
                )
                or self.prospective_memory_use_ablation
                or self.memory_hypothesis_sha256 is not None
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C11 utility requires calibrated GEN-C10 transition evidence"
                )
            _sha(
                self.transition_calibration_sha256,
                "transition_calibration_sha256",
            )
            _sha(
                self.transition_calibration_population_sha256,
                "transition_calibration_population_sha256",
            )
            report = self.transition_calibration_report
            if report.report_sha256 != self.transition_calibration_sha256:
                raise CiboCompoundCapitalError(
                    "GEN-C11 transition calibration digest drift"
                )
            if (
                report.source_population_sha256
                != self.transition_calibration_population_sha256
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C11 transition calibration population lineage drift"
                )
        else:
            if (
                not self.prospective_memory_use_ablation
                or self.memory_hypothesis_sha256 is None
                or self.transition_uncertainty_calibrated
                or self.transition_calibration_sha256 is not None
                or self.transition_calibration_population_sha256 is not None
                or self.transition_calibration_report is not None
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C13 utility requires prospective memory-use ablation"
                )
            _sha(self.memory_hypothesis_sha256, "memory_hypothesis_sha256")


@dataclass(frozen=True, slots=True)
class Genc11Genc13UtilityReport:
    gate_id: str
    reused_economic_gate_id: str
    evaluation_id: str
    workstream: Genc11Genc13Workstream
    treatment_candidate_id: str
    status: Genc9EconomicGateStatus
    failed_dimensions: tuple[str, ...]
    research_eligible: bool
    temporal_replication_claimed: bool = False
    stress_pass_claimed: bool = False
    winner_selected: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility wrapper identity drift"
            )
        if self.reused_economic_gate_id != GENC9_ECONOMIC_GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility wrapper reused gate drift"
            )
        if not self.evaluation_id or not self.treatment_candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility wrapper result identity is required"
            )
        if type(self.workstream) is not Genc11Genc13Workstream:
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility wrapper workstream is invalid"
            )
        if (
            type(self.status) is not Genc9EconomicGateStatus
            or self.status is Genc9EconomicGateStatus.CONTROL
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility wrapper treatment status is invalid"
            )
        if (
            not isinstance(self.failed_dimensions, tuple)
            or any(
                not isinstance(item, str) or not item
                for item in self.failed_dimensions
            )
            or len(self.failed_dimensions) != len(set(self.failed_dimensions))
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility wrapper failed dimensions are invalid"
            )
        for name in (
            "research_eligible",
            "temporal_replication_claimed",
            "stress_pass_claimed",
            "winner_selected",
            "productive_authority",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C11/13 utility wrapper {name} must be bool"
                )
        if self.research_eligible != (
            self.status is Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility wrapper status/eligibility drift"
            )
        if self.research_eligible and self.failed_dimensions:
            raise CiboCompoundCapitalError(
                "GEN-C11/13 eligible result cannot carry failed dimensions"
            )
        if (
            self.status
            is Genc9EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
            and not self.failed_dimensions
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 safety rejection requires failed dimensions"
            )
        if (
            self.status
            is Genc9EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
            and self.failed_dimensions
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 no-improvement rejection cannot carry safety failures"
            )
        if (
            self.temporal_replication_claimed
            or self.stress_pass_claimed
            or self.winner_selected
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C11/13 utility wrapper cannot overclaim closure/authority"
            )


def evaluate_genc11_genc13_utility(
    evidence: Genc11Genc13UtilityInput,
) -> Genc11Genc13UtilityReport:
    """Reuse the frozen GEN-C9 law after GEN-C11/13 causal prerequisites."""

    if not isinstance(evidence, Genc11Genc13UtilityInput):
        raise CiboCompoundCapitalError(
            "GEN-C11/13 utility requires canonical input"
        )
    economic = evaluate_genc9_economic_gate(evidence.research_report)
    treatment = next(
        row
        for row in economic.rows
        if row.candidate_id == evidence.treatment_candidate_id
    )
    return Genc11Genc13UtilityReport(
        gate_id=GATE_ID,
        reused_economic_gate_id=GENC9_ECONOMIC_GATE_ID,
        evaluation_id=evidence.evaluation_id,
        workstream=evidence.workstream,
        treatment_candidate_id=evidence.treatment_candidate_id,
        status=treatment.status,
        failed_dimensions=treatment.failed_dimensions,
        research_eligible=(
            treatment.status
            is Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        ),
    )


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"GEN-C11/13 utility {name} must be canonical SHA-256"
        )
