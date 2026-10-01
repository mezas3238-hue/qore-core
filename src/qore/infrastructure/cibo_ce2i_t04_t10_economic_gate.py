"""Executable non-compensatory economic gate for CE2I T04 and T10.

T04 marginal risk efficiency and T10 capital velocity already have mechanical
and pre-outcome research components. This module is the separate preregistered
outcome-bound evaluator. It requires causally identified provider-valid
control/treatment evidence, strict WF1..WF4 replication, and never grants
runtime, Risk, execution, merge or certification authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

GATE_ID = "CIBO_CE2I_T04_T10_NONCOMPENSATORY_ECONOMIC_GATE_V1"
GATE_FROZEN_AT = datetime(2026, 9, 30, 22, 30, tzinfo=UTC)
GATE_SHA256 = (
    "sha256:45928fe4db78cb771d88891f099dab484f37d5d4"
    "ce55e0fe1d76a7345b9fe35b"
)
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Ce2iT04T10Tool(StrEnum):
    T04 = "T04"
    T10 = "T10"


class Ce2iT04T10Role(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class Ce2iT04T10Status(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NOT_STRICT_4_OF_4 = "REJECTED_NOT_STRICT_4_OF_4"


@dataclass(frozen=True, slots=True)
class Ce2iT04T10FoldObservation:
    candidate_id: str
    tool: Ce2iT04T10Tool
    role: Ce2iT04T10Role
    fold_id: str
    population_sha256: str
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
    provider_cost_usd: Decimal
    provider_failure_count: int
    capital_conservation_breach_count: int
    minimum_realized_capital_usd: Decimal
    minimum_liquid_reserve_usd: Decimal
    minimum_optionality_usd: Decimal
    p95_recovery_minutes: Decimal
    true_stop_risk_usd: Decimal
    capital_minutes: Decimal
    capital_risk_time_productivity: Decimal
    realized_output_per_true_stop_risk: Decimal
    realized_output_per_capital_minute: Decimal
    causal_effect_identified: bool
    treatment_preregistered_before_outcomes: bool
    provider_economics_complete: bool
    outcome_coverage_complete: bool
    authoritative_deployment_release_timestamps: bool = False
    future_outcome_used: bool = False
    weighted_score_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "T04/T10 economic candidate identity is required"
            )
        if type(self.tool) is not Ce2iT04T10Tool:
            raise CiboCompoundCapitalError("T04/T10 economic tool is invalid")
        if type(self.role) is not Ce2iT04T10Role:
            raise CiboCompoundCapitalError("T04/T10 economic role is invalid")
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "T04/T10 economic fold must be WF1..WF4"
            )
        for name in (
            "population_sha256",
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
            "provider_cost_usd",
            "minimum_realized_capital_usd",
            "minimum_liquid_reserve_usd",
            "minimum_optionality_usd",
            "p95_recovery_minutes",
            "true_stop_risk_usd",
            "capital_minutes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"T04/T10 economic {name} must be finite non-negative"
                )

        for name in (
            "realized_net_delta_usd",
            "capital_risk_time_productivity",
            "realized_output_per_true_stop_risk",
            "realized_output_per_capital_minute",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCompoundCapitalError(
                    f"T04/T10 economic {name} must be finite Decimal"
                )

        for name in (
            "provider_failure_count",
            "capital_conservation_breach_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCompoundCapitalError(
                    f"T04/T10 economic {name} must be non-negative int"
                )

        for name in (
            "causal_effect_identified",
            "treatment_preregistered_before_outcomes",
            "provider_economics_complete",
            "outcome_coverage_complete",
            "authoritative_deployment_release_timestamps",
            "future_outcome_used",
            "weighted_score_used",
            "productive_authority",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"T04/T10 economic {name} must be bool"
                )

        if (
            not self.causal_effect_identified
            or not self.treatment_preregistered_before_outcomes
            or not self.provider_economics_complete
            or not self.outcome_coverage_complete
            or self.future_outcome_used
            or self.weighted_score_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "T04/T10 economic observation governance/causal drift"
            )

        if self.true_stop_risk_usd <= 0:
            raise CiboCompoundCapitalError(
                "T04/T10 true stop risk must be strictly positive"
            )
        if self.capital_minutes <= 0:
            raise CiboCompoundCapitalError(
                "T04/T10 capital minutes must be strictly positive"
            )
        if (
            self.tool is Ce2iT04T10Tool.T10
            and not self.authoritative_deployment_release_timestamps
        ):
            raise CiboCompoundCapitalError(
                "T10 requires authoritative deployment/release timestamps"
            )


@dataclass(frozen=True, slots=True)
class Ce2iT04T10CandidateVerdict:
    tool: Ce2iT04T10Tool
    candidate_id: str
    status: Ce2iT04T10Status
    passed_fold_ids: tuple[str, ...]
    failed_fold_ids: tuple[str, ...]
    failed_dimensions: tuple[str, ...]
    winner_selected: bool = False
    production_promotion: bool = False

    def __post_init__(self) -> None:
        if type(self.tool) is not Ce2iT04T10Tool or not self.candidate_id:
            raise CiboCompoundCapitalError(
                "T04/T10 economic verdict identity is invalid"
            )
        if type(self.status) is not Ce2iT04T10Status:
            raise CiboCompoundCapitalError(
                "T04/T10 economic verdict status is invalid"
            )
        for values, label in (
            (self.passed_fold_ids, "passed folds"),
            (self.failed_fold_ids, "failed folds"),
            (self.failed_dimensions, "failed dimensions"),
        ):
            if not isinstance(values, tuple) or any(
                not isinstance(item, str) or not item for item in values
            ):
                raise CiboCompoundCapitalError(
                    f"T04/T10 economic verdict {label} are invalid"
                )
            if len(values) != len(set(values)):
                raise CiboCompoundCapitalError(
                    f"T04/T10 economic verdict {label} must be unique"
                )
        passed = set(self.passed_fold_ids)
        failed = set(self.failed_fold_ids)
        canonical = set(_CANONICAL_FOLDS)
        if (
            not passed <= canonical
            or not failed <= canonical
            or passed & failed
            or self.passed_fold_ids
            != tuple(item for item in _CANONICAL_FOLDS if item in passed)
            or self.failed_fold_ids
            != tuple(item for item in _CANONICAL_FOLDS if item in failed)
        ):
            raise CiboCompoundCapitalError(
                "T04/T10 economic verdict fold identity drift"
            )
        for name in ("winner_selected", "production_promotion"):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"T04/T10 economic verdict {name} must be bool"
                )
        if self.winner_selected or self.production_promotion:
            raise CiboCompoundCapitalError(
                "T04/T10 economic verdict cannot select/promote"
            )
        if self.status is Ce2iT04T10Status.CONTROL:
            if (
                self.passed_fold_ids != _CANONICAL_FOLDS
                or self.failed_fold_ids
                or self.failed_dimensions
            ):
                raise CiboCompoundCapitalError(
                    "T04/T10 CONTROL verdict fold drift"
                )
            return
        if passed | failed != canonical:
            raise CiboCompoundCapitalError(
                "T04/T10 treatment verdict requires WF1..WF4 disposition"
            )
        for dimension in self.failed_dimensions:
            fold_id, separator, _name = dimension.partition(":")
            if not separator or fold_id not in failed:
                raise CiboCompoundCapitalError(
                    "T04/T10 failed dimension/fold drift"
                )
        safety_failed = any(
            not item.endswith(":NO_STRICT_IMPROVEMENT")
            for item in self.failed_dimensions
        )
        expected_status = (
            Ce2iT04T10Status.REJECTED_SAFETY_DETERIORATION
            if safety_failed
            else (
                Ce2iT04T10Status.REJECTED_NOT_STRICT_4_OF_4
                if self.passed_fold_ids != _CANONICAL_FOLDS
                else Ce2iT04T10Status.ELIGIBLE_FOR_FURTHER_RESEARCH
            )
        )
        if self.status is not expected_status:
            raise CiboCompoundCapitalError(
                "T04/T10 economic verdict status/fold drift"
            )


@dataclass(frozen=True, slots=True)
class Ce2iT04T10EconomicGateReport:
    gate_id: str
    gate_sha256: str
    gate_frozen_at: datetime
    verdicts: tuple[Ce2iT04T10CandidateVerdict, ...]
    weighted_score_used: bool = False
    winner_selected: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "T04/T10 economic gate identity drift"
            )
        if self.gate_sha256 != GATE_SHA256:
            raise CiboCompoundCapitalError(
                "T04/T10 economic gate digest drift"
            )
        if self.gate_frozen_at != GATE_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "T04/T10 economic gate freeze drift"
            )
        if not isinstance(self.verdicts, tuple) or not self.verdicts or any(
            not isinstance(item, Ce2iT04T10CandidateVerdict)
            for item in self.verdicts
        ):
            raise CiboCompoundCapitalError(
                "T04/T10 economic gate requires canonical verdicts"
            )
        keys = tuple((item.tool, item.candidate_id) for item in self.verdicts)
        if len(keys) != len(set(keys)):
            raise CiboCompoundCapitalError(
                "T04/T10 economic verdict identities must be unique"
            )
        for tool in {item.tool for item in self.verdicts}:
            controls = tuple(
                item
                for item in self.verdicts
                if item.tool is tool and item.status is Ce2iT04T10Status.CONTROL
            )
            if len(controls) != 1:
                raise CiboCompoundCapitalError(
                    "T04/T10 economic gate requires one control verdict per tool"
                )
        if (
            self.weighted_score_used
            or self.winner_selected
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "T04/T10 economic gate cannot score/promote/certify"
            )


def evaluate_t04_t10_economic_gate(
    observations: tuple[Ce2iT04T10FoldObservation, ...],
) -> Ce2iT04T10EconomicGateReport:
    """Require non-compensatory economic improvement independently in 4/4 folds."""

    if not observations:
        raise CiboCompoundCapitalError(
            "T04/T10 economic observations are required"
        )

    verdicts: list[Ce2iT04T10CandidateVerdict] = []
    for tool in sorted({item.tool for item in observations}, key=lambda x: x.value):
        rows = tuple(item for item in observations if item.tool is tool)
        controls = {
            item.candidate_id
            for item in rows
            if item.role is Ce2iT04T10Role.CONTROL
        }
        if len(controls) != 1:
            raise CiboCompoundCapitalError(
                f"{tool.value} economic gate requires one control candidate"
            )
        control_id = next(iter(controls))
        control_rows = _four_fold_rows(
            tuple(item for item in rows if item.candidate_id == control_id)
        )
        verdicts.append(
            Ce2iT04T10CandidateVerdict(
                tool=tool,
                candidate_id=control_id,
                status=Ce2iT04T10Status.CONTROL,
                passed_fold_ids=_CANONICAL_FOLDS,
                failed_fold_ids=(),
                failed_dimensions=(),
            )
        )

        treatment_ids = sorted(
            {
                item.candidate_id
                for item in rows
                if item.role is Ce2iT04T10Role.TREATMENT
            }
        )
        if not treatment_ids:
            raise CiboCompoundCapitalError(
                f"{tool.value} economic gate requires treatment candidate"
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

    return Ce2iT04T10EconomicGateReport(
        gate_id=GATE_ID,
        gate_sha256=GATE_SHA256,
        gate_frozen_at=GATE_FROZEN_AT,
        verdicts=tuple(verdicts),
    )


def _four_fold_rows(
    rows: tuple[Ce2iT04T10FoldObservation, ...],
) -> dict[str, Ce2iT04T10FoldObservation]:
    by_fold = {item.fold_id: item for item in rows}
    if len(rows) != 4 or tuple(sorted(by_fold)) != _CANONICAL_FOLDS:
        raise CiboCompoundCapitalError(
            "T04/T10 economic candidate requires exactly WF1..WF4"
        )
    if len({item.candidate_id for item in rows}) != 1:
        raise CiboCompoundCapitalError(
            "T04/T10 economic candidate identity drift across folds"
        )
    return by_fold


def _evaluate_candidate(
    *,
    tool: Ce2iT04T10Tool,
    candidate_id: str,
    control_rows: dict[str, Ce2iT04T10FoldObservation],
    treatment_rows: dict[str, Ce2iT04T10FoldObservation],
) -> Ce2iT04T10CandidateVerdict:
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
                "provider_failure_count",
                treatment.provider_failure_count,
                control.provider_failure_count,
            ),
            (
                "capital_conservation_breach_count",
                treatment.capital_conservation_breach_count,
                control.capital_conservation_breach_count,
            ),
            (
                "p95_recovery_minutes",
                treatment.p95_recovery_minutes,
                control.p95_recovery_minutes,
            ),
        ):
            if treatment_value > control_value:
                dimensions.append(name)

        for name, treatment_value, control_value in (
            (
                "minimum_realized_capital_usd",
                treatment.minimum_realized_capital_usd,
                control.minimum_realized_capital_usd,
            ),
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

        if tool is Ce2iT04T10Tool.T04:
            strict_improvement = (
                treatment.realized_output_per_true_stop_risk
                > control.realized_output_per_true_stop_risk
                or treatment.capital_risk_time_productivity
                > control.capital_risk_time_productivity
            )
        else:
            strict_improvement = (
                treatment.realized_output_per_capital_minute
                > control.realized_output_per_capital_minute
                or treatment.capital_risk_time_productivity
                > control.capital_risk_time_productivity
            )

        if strict_improvement:
            passed.append(fold_id)
        else:
            failed.append(fold_id)
            failed_dimensions.append(f"{fold_id}:NO_STRICT_IMPROVEMENT")

    if safety_failed:
        status = Ce2iT04T10Status.REJECTED_SAFETY_DETERIORATION
    elif tuple(passed) != _CANONICAL_FOLDS:
        status = Ce2iT04T10Status.REJECTED_NOT_STRICT_4_OF_4
    else:
        status = Ce2iT04T10Status.ELIGIBLE_FOR_FURTHER_RESEARCH

    return Ce2iT04T10CandidateVerdict(
        tool=tool,
        candidate_id=candidate_id,
        status=status,
        passed_fold_ids=tuple(passed),
        failed_fold_ids=tuple(dict.fromkeys(failed)),
        failed_dimensions=tuple(failed_dimensions),
    )


def _require_comparable(
    control: Ce2iT04T10FoldObservation,
    treatment: Ce2iT04T10FoldObservation,
) -> None:
    if (
        control.tool is not treatment.tool
        or control.fold_id != treatment.fold_id
        or control.role is not Ce2iT04T10Role.CONTROL
        or treatment.role is not Ce2iT04T10Role.TREATMENT
    ):
        raise CiboCompoundCapitalError(
            "T04/T10 economic comparison role/fold/tool drift"
        )

    comparable = (
        "population_sha256",
        "strategy_surface_sha256",
        "provider_surface_sha256",
        "risk_boundary_sha256",
        "capital_truth_sha256",
        "causal_horizon_sha256",
        "protocol_binding_sha256",
    )
    if any(getattr(control, name) != getattr(treatment, name) for name in comparable):
        raise CiboCompoundCapitalError(
            "T04/T10 economic gate requires identical causal comparison surface"
        )


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"T04/T10 economic {name} must be sha256:<64 lowercase hex>"
        )
