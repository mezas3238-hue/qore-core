"""Causal Pareto utility gate for CE2I T14/T15.

T14 dynamic de-risking and T15 optionality have different causal questions but
share one comparison law: same legal population/provider economics, no weighted
score, no future leakage, no runtime promotion, no economic deterioration hidden
by one attractive metric.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

T14_T15_UTILITY_GATE_ID = "CIBO_T14_T15_CAUSAL_PARETO_UTILITY_GATE_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class T14T15UtilityKind(StrEnum):
    T14_DYNAMIC_DERISKING = "T14_DYNAMIC_DERISKING"
    T15_OPTIONALITY = "T15_OPTIONALITY"


class T14T15CandidateRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class T14T15UtilityStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_CAUSAL_IDENTIFICATION = "REJECTED_CAUSAL_IDENTIFICATION"
    REJECTED_GOVERNANCE = "REJECTED_GOVERNANCE"
    REJECTED_PARETO_DETERIORATION = "REJECTED_PARETO_DETERIORATION"
    REJECTED_NO_STRICT_UTILITY_IMPROVEMENT = (
        "REJECTED_NO_STRICT_UTILITY_IMPROVEMENT"
    )


@dataclass(frozen=True, slots=True)
class T14T15UtilitySummary:
    candidate_id: str
    kind: T14T15UtilityKind
    role: T14T15CandidateRole
    population_sha256: str
    provider_economics_sha256: str
    causal_horizon_sha256: str
    realized_net_delta_usd: Decimal
    capital_productivity_usd_per_risk_minute: Decimal
    peak_plausible_loss_usd: Decimal
    max_settlement_drawdown_usd: Decimal
    peak_margin_occupancy_usd: Decimal
    minimum_realized_capital_usd: Decimal
    max_recovery_minutes: Decimal
    optionality_preserved_rate: Decimal
    released_stop_risk_minutes_usd: Decimal
    materialized_known_options_executable: int
    known_option_set_sha256: str | None = None
    causal_effect_identified: bool = False
    structural_stop_changed_by_cibo: bool = False
    trader_methodology_overridden: bool = False
    risk_authority_overridden: bool = False
    recovery_sizing_used: bool = False
    future_opportunity_oracle_used: bool = False
    synthetic_values_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "T14/T15 utility candidate identity is required"
            )
        if type(self.kind) is not T14T15UtilityKind:
            raise CiboCompoundCapitalError("T14/T15 utility kind is invalid")
        if type(self.role) is not T14T15CandidateRole:
            raise CiboCompoundCapitalError("T14/T15 utility role is invalid")
        for name in (
            "population_sha256",
            "provider_economics_sha256",
            "causal_horizon_sha256",
        ):
            _sha(getattr(self, name), name)
        for name in (
            "peak_plausible_loss_usd",
            "max_settlement_drawdown_usd",
            "peak_margin_occupancy_usd",
            "minimum_realized_capital_usd",
            "max_recovery_minutes",
            "released_stop_risk_minutes_usd",
        ):
            _nonnegative(getattr(self, name), name)
        _finite(self.realized_net_delta_usd, "realized_net_delta_usd")
        _finite(
            self.capital_productivity_usd_per_risk_minute,
            "capital_productivity_usd_per_risk_minute",
        )
        _rate(self.optionality_preserved_rate, "optionality_preserved_rate")
        if (
            not isinstance(self.materialized_known_options_executable, int)
            or isinstance(self.materialized_known_options_executable, bool)
            or self.materialized_known_options_executable < 0
        ):
            raise CiboCompoundCapitalError(
                "T14/T15 materialized known options must be non-negative int"
            )
        for name in (
            "causal_effect_identified",
            "structural_stop_changed_by_cibo",
            "trader_methodology_overridden",
            "risk_authority_overridden",
            "recovery_sizing_used",
            "future_opportunity_oracle_used",
            "synthetic_values_used",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"T14/T15 utility {name} must be bool"
                )
        if self.kind is T14T15UtilityKind.T14_DYNAMIC_DERISKING:
            if self.known_option_set_sha256 is not None:
                raise CiboCompoundCapitalError(
                    "T14 cannot carry a T15 known-option set"
                )
        else:
            if self.known_option_set_sha256 is None:
                raise CiboCompoundCapitalError(
                    "T15 utility requires frozen known-option set digest"
                )
            _sha(self.known_option_set_sha256, "known_option_set_sha256")


@dataclass(frozen=True, slots=True)
class T14T15UtilityGateRow:
    candidate_id: str
    status: T14T15UtilityStatus
    causal_identification_pass: bool
    governance_pass: bool
    pareto_no_worse: bool
    strict_utility_improvement: bool
    failed_dimensions: tuple[str, ...]
    weighted_score_used: bool = False
    production_promotion: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id or type(self.status) is not T14T15UtilityStatus:
            raise CiboCompoundCapitalError(
                "T14/T15 utility row identity/status drift"
            )
        for name in (
            "causal_identification_pass",
            "governance_pass",
            "pareto_no_worse",
            "strict_utility_improvement",
            "weighted_score_used",
            "production_promotion",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"T14/T15 utility row {name} must be bool"
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
                "T14/T15 utility row failed dimensions are invalid"
            )
        if self.weighted_score_used or self.production_promotion:
            raise CiboCompoundCapitalError(
                "T14/T15 utility row cannot score/promote"
            )
        if self.status is T14T15UtilityStatus.CONTROL:
            if (
                not self.causal_identification_pass
                or not self.governance_pass
                or not self.pareto_no_worse
                or self.strict_utility_improvement
                or self.failed_dimensions
            ):
                raise CiboCompoundCapitalError(
                    "T14/T15 CONTROL row drift"
                )
            return
        expected_status = (
            T14T15UtilityStatus.REJECTED_CAUSAL_IDENTIFICATION
            if not self.causal_identification_pass
            else (
                T14T15UtilityStatus.REJECTED_GOVERNANCE
                if not self.governance_pass
                else (
                    T14T15UtilityStatus.REJECTED_PARETO_DETERIORATION
                    if not self.pareto_no_worse
                    else (
                        T14T15UtilityStatus.REJECTED_NO_STRICT_UTILITY_IMPROVEMENT
                        if not self.strict_utility_improvement
                        else T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
                    )
                )
            )
        )
        if self.status is not expected_status:
            raise CiboCompoundCapitalError(
                "T14/T15 utility row status/metric drift"
            )
        if (
            self.status
            in {
                T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
                T14T15UtilityStatus.REJECTED_NO_STRICT_UTILITY_IMPROVEMENT,
            }
            and self.failed_dimensions
        ):
            raise CiboCompoundCapitalError(
                "T14/T15 utility row unexpected failed dimensions"
            )
        if (
            self.status
            in {
                T14T15UtilityStatus.REJECTED_GOVERNANCE,
                T14T15UtilityStatus.REJECTED_PARETO_DETERIORATION,
            }
            and not self.failed_dimensions
        ):
            raise CiboCompoundCapitalError(
                "T14/T15 utility row missing failed dimensions"
            )


@dataclass(frozen=True, slots=True)
class T14T15UtilityGateReport:
    gate_id: str
    kind: T14T15UtilityKind
    control_candidate_id: str
    population_sha256: str
    provider_economics_sha256: str
    causal_horizon_sha256: str
    rows: tuple[T14T15UtilityGateRow, ...]
    weighted_score_used: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != T14_T15_UTILITY_GATE_ID:
            raise CiboCompoundCapitalError("T14/T15 utility gate identity drift")
        for name in (
            "population_sha256",
            "provider_economics_sha256",
            "causal_horizon_sha256",
        ):
            _sha(getattr(self, name), name)
        if type(self.kind) is not T14T15UtilityKind:
            raise CiboCompoundCapitalError(
                "T14/T15 utility gate kind is invalid"
            )
        if not isinstance(self.rows, tuple) or not self.rows or any(
            not isinstance(row, T14T15UtilityGateRow) for row in self.rows
        ):
            raise CiboCompoundCapitalError(
                "T14/T15 utility gate requires canonical rows"
            )
        ids = tuple(row.candidate_id for row in self.rows)
        if len(ids) != len(set(ids)) or self.control_candidate_id not in ids:
            raise CiboCompoundCapitalError(
                "T14/T15 utility gate candidate identity drift"
            )
        controls = tuple(
            row for row in self.rows if row.status is T14T15UtilityStatus.CONTROL
        )
        if (
            len(controls) != 1
            or controls[0].candidate_id != self.control_candidate_id
        ):
            raise CiboCompoundCapitalError(
                "T14/T15 utility gate control row drift"
            )
        if (
            self.weighted_score_used
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "T14/T15 utility gate governance drift"
            )


def evaluate_t14_t15_utility_gate(
    summaries: tuple[T14T15UtilitySummary, ...],
) -> T14T15UtilityGateReport:
    """Evaluate one T14 or T15 family against exactly one frozen control."""

    if not summaries:
        raise CiboCompoundCapitalError(
            "T14/T15 utility gate requires summaries"
        )
    kinds = {item.kind for item in summaries}
    populations = {item.population_sha256 for item in summaries}
    economics = {item.provider_economics_sha256 for item in summaries}
    horizons = {item.causal_horizon_sha256 for item in summaries}
    if len(kinds) != 1:
        raise CiboCompoundCapitalError(
            "T14/T15 utility gate cannot mix workstreams"
        )
    if len(populations) != 1 or len(economics) != 1 or len(horizons) != 1:
        raise CiboCompoundCapitalError(
            "T14/T15 utility gate requires identical causal comparison surface"
        )
    if next(iter(kinds)) is T14T15UtilityKind.T15_OPTIONALITY:
        option_sets = {item.known_option_set_sha256 for item in summaries}
        if len(option_sets) != 1:
            raise CiboCompoundCapitalError(
                "T15 utility gate requires identical frozen known-option set"
            )
    controls = tuple(
        item for item in summaries
        if item.role is T14T15CandidateRole.CONTROL
    )
    if len(controls) != 1:
        raise CiboCompoundCapitalError(
            "T14/T15 utility gate requires exactly one control"
        )
    ids = tuple(item.candidate_id for item in summaries)
    if len(ids) != len(set(ids)):
        raise CiboCompoundCapitalError(
            "T14/T15 utility candidate ids must be unique"
        )
    control = controls[0]
    rows = tuple(
        _evaluate(control=control, candidate=item)
        for item in summaries
    )
    return T14T15UtilityGateReport(
        gate_id=T14_T15_UTILITY_GATE_ID,
        kind=control.kind,
        control_candidate_id=control.candidate_id,
        population_sha256=control.population_sha256,
        provider_economics_sha256=control.provider_economics_sha256,
        causal_horizon_sha256=control.causal_horizon_sha256,
        rows=rows,
    )


def _evaluate(
    *,
    control: T14T15UtilitySummary,
    candidate: T14T15UtilitySummary,
) -> T14T15UtilityGateRow:
    if candidate.candidate_id == control.candidate_id:
        return T14T15UtilityGateRow(
            candidate_id=candidate.candidate_id,
            status=T14T15UtilityStatus.CONTROL,
            causal_identification_pass=True,
            governance_pass=True,
            pareto_no_worse=True,
            strict_utility_improvement=False,
            failed_dimensions=(),
        )

    causal_pass = (
        candidate.causal_effect_identified
        if candidate.kind is T14T15UtilityKind.T15_OPTIONALITY
        else True
    )
    governance_failures: list[str] = []
    for name in (
        "structural_stop_changed_by_cibo",
        "trader_methodology_overridden",
        "risk_authority_overridden",
        "recovery_sizing_used",
        "future_opportunity_oracle_used",
        "synthetic_values_used",
        "productive_authority",
    ):
        if getattr(candidate, name):
            governance_failures.append(name.upper())
    governance_pass = not governance_failures

    failed = list(governance_failures)
    _no_less(
        failed,
        "REALIZED_NET_DELTA_USD",
        candidate.realized_net_delta_usd,
        control.realized_net_delta_usd,
    )
    _no_more(
        failed,
        "PEAK_PLAUSIBLE_LOSS_USD",
        candidate.peak_plausible_loss_usd,
        control.peak_plausible_loss_usd,
    )
    _no_more(
        failed,
        "MAX_SETTLEMENT_DRAWDOWN_USD",
        candidate.max_settlement_drawdown_usd,
        control.max_settlement_drawdown_usd,
    )
    _no_more(
        failed,
        "PEAK_MARGIN_OCCUPANCY_USD",
        candidate.peak_margin_occupancy_usd,
        control.peak_margin_occupancy_usd,
    )
    _no_more(
        failed,
        "MAX_RECOVERY_MINUTES",
        candidate.max_recovery_minutes,
        control.max_recovery_minutes,
    )
    _no_less(
        failed,
        "MINIMUM_REALIZED_CAPITAL_USD",
        candidate.minimum_realized_capital_usd,
        control.minimum_realized_capital_usd,
    )
    _no_less(
        failed,
        "OPTIONALITY_PRESERVED_RATE",
        candidate.optionality_preserved_rate,
        control.optionality_preserved_rate,
    )
    pareto_no_worse = not failed

    strict = (
        candidate.realized_net_delta_usd > control.realized_net_delta_usd
        or candidate.capital_productivity_usd_per_risk_minute
        > control.capital_productivity_usd_per_risk_minute
        or candidate.peak_plausible_loss_usd
        < control.peak_plausible_loss_usd
        or candidate.max_settlement_drawdown_usd
        < control.max_settlement_drawdown_usd
        or candidate.peak_margin_occupancy_usd
        < control.peak_margin_occupancy_usd
        or candidate.minimum_realized_capital_usd
        > control.minimum_realized_capital_usd
        or candidate.max_recovery_minutes < control.max_recovery_minutes
        or candidate.optionality_preserved_rate
        > control.optionality_preserved_rate
        or candidate.released_stop_risk_minutes_usd
        > control.released_stop_risk_minutes_usd
        or (
            candidate.kind is T14T15UtilityKind.T15_OPTIONALITY
            and candidate.materialized_known_options_executable
            > control.materialized_known_options_executable
        )
    )

    if not causal_pass:
        status = T14T15UtilityStatus.REJECTED_CAUSAL_IDENTIFICATION
    elif not governance_pass:
        status = T14T15UtilityStatus.REJECTED_GOVERNANCE
    elif not pareto_no_worse:
        status = T14T15UtilityStatus.REJECTED_PARETO_DETERIORATION
    elif not strict:
        status = T14T15UtilityStatus.REJECTED_NO_STRICT_UTILITY_IMPROVEMENT
    else:
        status = T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH

    return T14T15UtilityGateRow(
        candidate_id=candidate.candidate_id,
        status=status,
        causal_identification_pass=causal_pass,
        governance_pass=governance_pass,
        pareto_no_worse=pareto_no_worse,
        strict_utility_improvement=strict,
        failed_dimensions=tuple(failed),
    )


def _finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCompoundCapitalError(
            f"T14/T15 utility {name} must be finite Decimal"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    _finite(value, name)
    if value < 0:
        raise CiboCompoundCapitalError(
            f"T14/T15 utility {name} must be non-negative"
        )


def _rate(value: Decimal, name: str) -> None:
    _nonnegative(value, name)
    if value > 1:
        raise CiboCompoundCapitalError(
            f"T14/T15 utility {name} must be in [0,1]"
        )


def _sha(value: str | None, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"T14/T15 utility {name} must be canonical SHA-256"
        )


def _no_more(
    failed: list[str],
    name: str,
    treatment: Decimal,
    control: Decimal,
) -> None:
    if treatment > control:
        failed.append(name)


def _no_less(
    failed: list[str],
    name: str,
    treatment: Decimal,
    control: Decimal,
) -> None:
    if treatment < control:
        failed.append(name)
