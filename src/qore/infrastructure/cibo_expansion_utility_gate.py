"""Non-compensatory economic utility gate for CIBO T06/T07 expansion.

The gate evaluates already-materialized provider-valid summaries. It does not
choose expansion size, invent a funding source, replace QORE Risk, or promote a
runtime policy. Safety deterioration cannot be purchased with more return.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

EXPANSION_UTILITY_GATE_ID = "CIBO_T06_T07_NONCOMPENSATORY_EXPANSION_UTILITY_GATE_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ExpansionUtilityKind(StrEnum):
    T06_PROFIT_FUNDED = "T06_PROFIT_FUNDED"
    T07_PROTECTED_CAPACITY = "T07_PROTECTED_CAPACITY"


class ExpansionCandidateRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class ExpansionUtilityStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT = (
        "REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT"
    )


@dataclass(frozen=True, slots=True)
class ExpansionUtilitySummary:
    candidate_id: str
    kind: ExpansionUtilityKind
    role: ExpansionCandidateRole
    population_sha256: str
    provider_economics_sha256: str
    realized_net_delta_usd: Decimal
    capital_productivity_usd_per_risk_minute: Decimal
    peak_plausible_loss_usd: Decimal
    max_settlement_drawdown_usd: Decimal
    peak_margin_occupancy_usd: Decimal
    capital_lockup_minutes: Decimal
    max_recovery_minutes: Decimal
    minimum_realized_capital_usd: Decimal
    optionality_preserved_rate: Decimal
    provider_failure_incidence: Decimal
    protected_capacity_accounting_only: bool = False
    broker_guarantee_claimed: bool = False
    broker_guarantee_evidence_sha256: str | None = None
    future_leakage_used: bool = False
    synthetic_values_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "expansion utility candidate identity is required"
            )
        if type(self.kind) is not ExpansionUtilityKind:
            raise CiboCompoundCapitalError("expansion utility kind is invalid")
        if type(self.role) is not ExpansionCandidateRole:
            raise CiboCompoundCapitalError("expansion utility role is invalid")
        _sha(self.population_sha256, "population_sha256")
        _sha(self.provider_economics_sha256, "provider_economics_sha256")
        for name in (
            "peak_plausible_loss_usd",
            "max_settlement_drawdown_usd",
            "peak_margin_occupancy_usd",
            "capital_lockup_minutes",
            "max_recovery_minutes",
            "minimum_realized_capital_usd",
            "provider_failure_incidence",
        ):
            _nonnegative(getattr(self, name), name)
        _finite(
            self.realized_net_delta_usd,
            "realized_net_delta_usd",
        )
        _finite(
            self.capital_productivity_usd_per_risk_minute,
            "capital_productivity_usd_per_risk_minute",
        )
        _rate(self.optionality_preserved_rate, "optionality_preserved_rate")
        _rate(self.provider_failure_incidence, "provider_failure_incidence")
        for name in (
            "protected_capacity_accounting_only",
            "broker_guarantee_claimed",
            "future_leakage_used",
            "synthetic_values_used",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"expansion utility {name} must be bool"
                )
        if self.kind is ExpansionUtilityKind.T06_PROFIT_FUNDED:
            if (
                self.protected_capacity_accounting_only
                or self.broker_guarantee_claimed
                or self.broker_guarantee_evidence_sha256 is not None
            ):
                raise CiboCompoundCapitalError(
                    "T06 profit-funded expansion cannot claim protected/broker capacity"
                )
        else:
            if not self.protected_capacity_accounting_only:
                raise CiboCompoundCapitalError(
                    "T07 must identify protected capacity as accounting protection"
                )
            if self.broker_guarantee_claimed:
                if self.broker_guarantee_evidence_sha256 is None:
                    raise CiboCompoundCapitalError(
                        "T07 broker guarantee claim requires canonical evidence"
                    )
                _sha(
                    self.broker_guarantee_evidence_sha256,
                    "broker_guarantee_evidence_sha256",
                )
            elif self.broker_guarantee_evidence_sha256 is not None:
                raise CiboCompoundCapitalError(
                    "T07 broker evidence cannot exist without guarantee claim"
                )
        if (
            self.future_leakage_used
            or self.synthetic_values_used
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "expansion utility summary governance drift"
            )


@dataclass(frozen=True, slots=True)
class ExpansionUtilityGateRow:
    candidate_id: str
    status: ExpansionUtilityStatus
    safety_no_worse: bool
    strict_economic_improvement: bool
    failed_dimensions: tuple[str, ...]
    weighted_score_used: bool = False
    production_promotion: bool = False


@dataclass(frozen=True, slots=True)
class ExpansionUtilityGateReport:
    gate_id: str
    kind: ExpansionUtilityKind
    control_candidate_id: str
    population_sha256: str
    provider_economics_sha256: str
    rows: tuple[ExpansionUtilityGateRow, ...]
    weighted_score_used: bool = False
    production_policy_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != EXPANSION_UTILITY_GATE_ID:
            raise CiboCompoundCapitalError("expansion utility gate identity drift")
        _sha(self.population_sha256, "gate population_sha256")
        _sha(
            self.provider_economics_sha256,
            "gate provider_economics_sha256",
        )
        ids = tuple(row.candidate_id for row in self.rows)
        if len(ids) != len(set(ids)) or self.control_candidate_id not in ids:
            raise CiboCompoundCapitalError(
                "expansion utility gate candidate identity drift"
            )
        if (
            self.weighted_score_used
            or self.production_policy_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "expansion utility gate governance drift"
            )


def evaluate_expansion_utility_gate(
    summaries: tuple[ExpansionUtilitySummary, ...],
) -> ExpansionUtilityGateReport:
    """Evaluate same-population expansion treatments against one control."""

    if not summaries:
        raise CiboCompoundCapitalError(
            "expansion utility gate requires summaries"
        )
    kinds = {item.kind for item in summaries}
    populations = {item.population_sha256 for item in summaries}
    economics = {item.provider_economics_sha256 for item in summaries}
    if len(kinds) != 1:
        raise CiboCompoundCapitalError(
            "expansion utility gate cannot mix T06 and T07"
        )
    if len(populations) != 1 or len(economics) != 1:
        raise CiboCompoundCapitalError(
            "expansion utility gate requires identical population/provider economics"
        )
    controls = tuple(
        item for item in summaries
        if item.role is ExpansionCandidateRole.CONTROL
    )
    if len(controls) != 1:
        raise CiboCompoundCapitalError(
            "expansion utility gate requires exactly one control"
        )
    ids = tuple(item.candidate_id for item in summaries)
    if len(ids) != len(set(ids)):
        raise CiboCompoundCapitalError(
            "expansion utility candidate ids must be unique"
        )
    control = controls[0]
    rows = tuple(
        _evaluate_candidate(control=control, candidate=item)
        for item in summaries
    )
    return ExpansionUtilityGateReport(
        gate_id=EXPANSION_UTILITY_GATE_ID,
        kind=control.kind,
        control_candidate_id=control.candidate_id,
        population_sha256=control.population_sha256,
        provider_economics_sha256=control.provider_economics_sha256,
        rows=rows,
    )


def _evaluate_candidate(
    *,
    control: ExpansionUtilitySummary,
    candidate: ExpansionUtilitySummary,
) -> ExpansionUtilityGateRow:
    if candidate.candidate_id == control.candidate_id:
        return ExpansionUtilityGateRow(
            candidate_id=candidate.candidate_id,
            status=ExpansionUtilityStatus.CONTROL,
            safety_no_worse=True,
            strict_economic_improvement=False,
            failed_dimensions=(),
        )

    failed: list[str] = []
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
        "CAPITAL_LOCKUP_MINUTES",
        candidate.capital_lockup_minutes,
        control.capital_lockup_minutes,
    )
    _no_more(
        failed,
        "MAX_RECOVERY_MINUTES",
        candidate.max_recovery_minutes,
        control.max_recovery_minutes,
    )
    _no_more(
        failed,
        "PROVIDER_FAILURE_INCIDENCE",
        candidate.provider_failure_incidence,
        control.provider_failure_incidence,
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
    safety_no_worse = not failed

    strict = (
        candidate.realized_net_delta_usd > control.realized_net_delta_usd
        or candidate.capital_productivity_usd_per_risk_minute
        > control.capital_productivity_usd_per_risk_minute
        or candidate.minimum_realized_capital_usd
        > control.minimum_realized_capital_usd
        or candidate.optionality_preserved_rate
        > control.optionality_preserved_rate
    )

    if not safety_no_worse:
        status = ExpansionUtilityStatus.REJECTED_SAFETY_DETERIORATION
    elif not strict:
        status = (
            ExpansionUtilityStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
        )
    else:
        status = ExpansionUtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH

    return ExpansionUtilityGateRow(
        candidate_id=candidate.candidate_id,
        status=status,
        safety_no_worse=safety_no_worse,
        strict_economic_improvement=strict,
        failed_dimensions=tuple(failed),
    )


def _finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCompoundCapitalError(
            f"expansion utility {name} must be finite Decimal"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    _finite(value, name)
    if value < 0:
        raise CiboCompoundCapitalError(
            f"expansion utility {name} must be non-negative"
        )


def _rate(value: Decimal, name: str) -> None:
    _nonnegative(value, name)
    if value > 1:
        raise CiboCompoundCapitalError(
            f"expansion utility {name} must be in [0,1]"
        )


def _sha(value: str | None, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"expansion utility {name} must be canonical SHA-256"
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
