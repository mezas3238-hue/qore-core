"""Supplemental non-compensatory scarcity safety gate for CE2I T09/T18.

The existing T09/T18 fresh-OOS scarcity utility contract proves population
coverage, four-fold realized utility, drawdown and capital productivity. The
CE2I closure protocol also makes starvation and concentration mandatory safety
dimensions under true scarcity. This additive preregistered gate evaluates
those dimensions without rewriting or weakening the frozen scarcity utility
contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

GATE_ID = "CIBO_T09_T18_NONCOMPENSATORY_SCARCITY_SAFETY_GATE_V1"
GATE_FROZEN_AT = datetime(2026, 9, 30, 22, 45, tzinfo=UTC)
GATE_SHA256 = (
    "sha256:6db2f83fb17a8b9f3f90864cbb18fcd02a36709b"
    "068693436014d3d5e2056abe"
)
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class T09T18ScarcityTool(StrEnum):
    T09 = "T09"
    T18 = "T18"


class T09T18ScarcityRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class T09T18ScarcityStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NOT_STRICT_4_OF_4 = "REJECTED_NOT_STRICT_4_OF_4"


@dataclass(frozen=True, slots=True)
class T09T18ScarcityFoldObservation:
    candidate_id: str
    tool: T09T18ScarcityTool
    role: T09T18ScarcityRole
    fold_id: str
    population_sha256: str
    opportunity_set_sha256: str
    strategy_surface_sha256: str
    provider_surface_sha256: str
    risk_boundary_sha256: str
    capital_truth_sha256: str
    causal_horizon_sha256: str
    protocol_binding_sha256: str
    realized_net_delta_usd: Decimal
    maximum_drawdown_usd: Decimal
    p99_drawdown_usd: Decimal
    peak_plausible_loss_usd: Decimal
    peak_margin_occupancy_usd: Decimal
    minimum_liquid_reserve_usd: Decimal
    minimum_optionality_usd: Decimal
    p95_recovery_minutes: Decimal
    capital_productivity: Decimal
    concentration_rate: Decimal
    starvation_rate: Decimal
    provider_failure_count: int
    true_scarcity_observed: bool
    simultaneous_opportunity_set_verified: bool
    trader_sovereignty_preserved: bool
    causal_effect_identified: bool
    treatment_preregistered_before_outcomes: bool
    provider_economics_complete: bool
    outcome_coverage_complete: bool
    future_outcome_used: bool = False
    weighted_score_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity candidate identity is required"
            )
        if type(self.tool) is not T09T18ScarcityTool:
            raise CiboCompoundCapitalError("T09/T18 scarcity tool is invalid")
        if type(self.role) is not T09T18ScarcityRole:
            raise CiboCompoundCapitalError("T09/T18 scarcity role is invalid")
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity fold must be WF1..WF4"
            )

        for name in (
            "population_sha256",
            "opportunity_set_sha256",
            "strategy_surface_sha256",
            "provider_surface_sha256",
            "risk_boundary_sha256",
            "capital_truth_sha256",
            "causal_horizon_sha256",
            "protocol_binding_sha256",
        ):
            _sha(getattr(self, name), name)

        for name in (
            "maximum_drawdown_usd",
            "p99_drawdown_usd",
            "peak_plausible_loss_usd",
            "peak_margin_occupancy_usd",
            "minimum_liquid_reserve_usd",
            "minimum_optionality_usd",
            "p95_recovery_minutes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"T09/T18 scarcity {name} must be finite non-negative"
                )

        for name in ("realized_net_delta_usd", "capital_productivity"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCompoundCapitalError(
                    f"T09/T18 scarcity {name} must be finite Decimal"
                )

        for name in ("concentration_rate", "starvation_rate"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCompoundCapitalError(
                    f"T09/T18 scarcity {name} must be Decimal in [0,1]"
                )

        if (
            type(self.provider_failure_count) is not int
            or self.provider_failure_count < 0
        ):
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity provider_failure_count must be non-negative int"
            )

        for name in (
            "true_scarcity_observed",
            "simultaneous_opportunity_set_verified",
            "trader_sovereignty_preserved",
            "causal_effect_identified",
            "treatment_preregistered_before_outcomes",
            "provider_economics_complete",
            "outcome_coverage_complete",
            "future_outcome_used",
            "weighted_score_used",
            "productive_authority",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"T09/T18 scarcity {name} must be bool"
                )

        if (
            not self.true_scarcity_observed
            or not self.simultaneous_opportunity_set_verified
            or not self.causal_effect_identified
            or not self.treatment_preregistered_before_outcomes
            or not self.provider_economics_complete
            or not self.outcome_coverage_complete
            or self.future_outcome_used
            or self.weighted_score_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity observation governance/causal drift"
            )

        if (
            self.tool is T09T18ScarcityTool.T18
            and not self.trader_sovereignty_preserved
        ):
            raise CiboCompoundCapitalError(
                "T18 scarcity allocation must preserve Trader sovereignty"
            )


@dataclass(frozen=True, slots=True)
class T09T18ScarcityCandidateVerdict:
    tool: T09T18ScarcityTool
    candidate_id: str
    status: T09T18ScarcityStatus
    passed_fold_ids: tuple[str, ...]
    failed_fold_ids: tuple[str, ...]
    failed_dimensions: tuple[str, ...]
    winner_selected: bool = False
    production_promotion: bool = False


@dataclass(frozen=True, slots=True)
class T09T18ScarcityGateReport:
    gate_id: str
    gate_sha256: str
    gate_frozen_at: datetime
    verdicts: tuple[T09T18ScarcityCandidateVerdict, ...]
    weighted_score_used: bool = False
    winner_selected: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity gate identity drift"
            )
        if self.gate_sha256 != GATE_SHA256:
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity gate digest drift"
            )
        if self.gate_frozen_at != GATE_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity gate freeze drift"
            )
        keys = tuple((item.tool, item.candidate_id) for item in self.verdicts)
        if len(keys) != len(set(keys)):
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity verdict identities must be unique"
            )
        if (
            self.weighted_score_used
            or self.winner_selected
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "T09/T18 scarcity gate cannot score/promote/certify"
            )


def evaluate_t09_t18_scarcity_gate(
    observations: tuple[T09T18ScarcityFoldObservation, ...],
) -> T09T18ScarcityGateReport:
    """Require strict 4/4 value with no starvation/concentration deterioration."""

    if not observations:
        raise CiboCompoundCapitalError(
            "T09/T18 scarcity observations are required"
        )

    verdicts: list[T09T18ScarcityCandidateVerdict] = []
    for tool in sorted({item.tool for item in observations}, key=lambda x: x.value):
        rows = tuple(item for item in observations if item.tool is tool)
        controls = {
            item.candidate_id
            for item in rows
            if item.role is T09T18ScarcityRole.CONTROL
        }
        if len(controls) != 1:
            raise CiboCompoundCapitalError(
                f"{tool.value} scarcity gate requires one control candidate"
            )
        control_id = next(iter(controls))
        control_rows = _four_fold_rows(
            tuple(item for item in rows if item.candidate_id == control_id)
        )
        verdicts.append(
            T09T18ScarcityCandidateVerdict(
                tool=tool,
                candidate_id=control_id,
                status=T09T18ScarcityStatus.CONTROL,
                passed_fold_ids=_CANONICAL_FOLDS,
                failed_fold_ids=(),
                failed_dimensions=(),
            )
        )

        treatment_ids = sorted(
            {
                item.candidate_id
                for item in rows
                if item.role is T09T18ScarcityRole.TREATMENT
            }
        )
        if not treatment_ids:
            raise CiboCompoundCapitalError(
                f"{tool.value} scarcity gate requires treatment candidate"
            )
        for candidate_id in treatment_ids:
            treatment_rows = _four_fold_rows(
                tuple(item for item in rows if item.candidate_id == candidate_id)
            )
            verdicts.append(
                _evaluate_candidate(
                    tool=tool,
                    candidate_id=candidate_id,
                    control_rows=control_rows,
                    treatment_rows=treatment_rows,
                )
            )

    return T09T18ScarcityGateReport(
        gate_id=GATE_ID,
        gate_sha256=GATE_SHA256,
        gate_frozen_at=GATE_FROZEN_AT,
        verdicts=tuple(verdicts),
    )


def _four_fold_rows(
    rows: tuple[T09T18ScarcityFoldObservation, ...],
) -> dict[str, T09T18ScarcityFoldObservation]:
    by_fold = {item.fold_id: item for item in rows}
    if len(rows) != 4 or tuple(sorted(by_fold)) != _CANONICAL_FOLDS:
        raise CiboCompoundCapitalError(
            "T09/T18 scarcity candidate requires exactly WF1..WF4"
        )
    if len({item.candidate_id for item in rows}) != 1:
        raise CiboCompoundCapitalError(
            "T09/T18 scarcity candidate identity drift across folds"
        )
    return by_fold


def _evaluate_candidate(
    *,
    tool: T09T18ScarcityTool,
    candidate_id: str,
    control_rows: dict[str, T09T18ScarcityFoldObservation],
    treatment_rows: dict[str, T09T18ScarcityFoldObservation],
) -> T09T18ScarcityCandidateVerdict:
    passed: list[str] = []
    failed: list[str] = []
    failed_dimensions: list[str] = []
    safety_failed = False

    for fold_id in _CANONICAL_FOLDS:
        control = control_rows[fold_id]
        treatment = treatment_rows[fold_id]
        _require_comparable(control, treatment)

        dimensions: list[str] = []
        for name, treatment_value, control_value in (
            (
                "maximum_drawdown_usd",
                treatment.maximum_drawdown_usd,
                control.maximum_drawdown_usd,
            ),
            (
                "p99_drawdown_usd",
                treatment.p99_drawdown_usd,
                control.p99_drawdown_usd,
            ),
            (
                "peak_plausible_loss_usd",
                treatment.peak_plausible_loss_usd,
                control.peak_plausible_loss_usd,
            ),
            (
                "peak_margin_occupancy_usd",
                treatment.peak_margin_occupancy_usd,
                control.peak_margin_occupancy_usd,
            ),
            (
                "p95_recovery_minutes",
                treatment.p95_recovery_minutes,
                control.p95_recovery_minutes,
            ),
            (
                "concentration_rate",
                treatment.concentration_rate,
                control.concentration_rate,
            ),
            (
                "starvation_rate",
                treatment.starvation_rate,
                control.starvation_rate,
            ),
            (
                "provider_failure_count",
                treatment.provider_failure_count,
                control.provider_failure_count,
            ),
        ):
            if treatment_value > control_value:
                dimensions.append(name)

        for name, treatment_value, control_value in (
            (
                "minimum_liquid_reserve_usd",
                treatment.minimum_liquid_reserve_usd,
                control.minimum_liquid_reserve_usd,
            ),
            (
                "minimum_optionality_usd",
                treatment.minimum_optionality_usd,
                control.minimum_optionality_usd,
            ),
            (
                "realized_net_delta_usd",
                treatment.realized_net_delta_usd,
                control.realized_net_delta_usd,
            ),
        ):
            if treatment_value < control_value:
                dimensions.append(name)

        if dimensions:
            safety_failed = True
            failed.append(fold_id)
            failed_dimensions.extend(
                f"{fold_id}:{name}" for name in dimensions
            )
            continue

        strict_improvement = (
            treatment.realized_net_delta_usd > control.realized_net_delta_usd
            or treatment.capital_productivity > control.capital_productivity
        )
        if strict_improvement:
            passed.append(fold_id)
        else:
            failed.append(fold_id)
            failed_dimensions.append(f"{fold_id}:NO_STRICT_IMPROVEMENT")

    if safety_failed:
        status = T09T18ScarcityStatus.REJECTED_SAFETY_DETERIORATION
    elif tuple(passed) != _CANONICAL_FOLDS:
        status = T09T18ScarcityStatus.REJECTED_NOT_STRICT_4_OF_4
    else:
        status = T09T18ScarcityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH

    return T09T18ScarcityCandidateVerdict(
        tool=tool,
        candidate_id=candidate_id,
        status=status,
        passed_fold_ids=tuple(passed),
        failed_fold_ids=tuple(dict.fromkeys(failed)),
        failed_dimensions=tuple(failed_dimensions),
    )


def _require_comparable(
    control: T09T18ScarcityFoldObservation,
    treatment: T09T18ScarcityFoldObservation,
) -> None:
    if (
        control.tool is not treatment.tool
        or control.fold_id != treatment.fold_id
        or control.role is not T09T18ScarcityRole.CONTROL
        or treatment.role is not T09T18ScarcityRole.TREATMENT
    ):
        raise CiboCompoundCapitalError(
            "T09/T18 scarcity comparison role/fold/tool drift"
        )
    comparable = (
        "population_sha256",
        "opportunity_set_sha256",
        "strategy_surface_sha256",
        "provider_surface_sha256",
        "risk_boundary_sha256",
        "capital_truth_sha256",
        "causal_horizon_sha256",
        "protocol_binding_sha256",
    )
    if any(getattr(control, name) != getattr(treatment, name) for name in comparable):
        raise CiboCompoundCapitalError(
            "T09/T18 scarcity gate requires identical causal comparison surface"
        )


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"T09/T18 scarcity {name} must be sha256:<64 lowercase hex>"
        )
