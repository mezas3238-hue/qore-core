"""Research-only CIBO capital-efficiency sizing laboratory.

This module studies how much economically meaningful exposure a frozen strategy
geometry can obtain from a bounded stop-risk and margin budget. It has no broker
adapter, no execution authority, no Risk authority, and no runtime side effects.

The laboratory deliberately refuses unverified structural stops. Increasing
volume by inventing a tighter stop is not capital efficiency; it is a strategy
mutation and belongs to Trader research/certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum


class CapitalEfficiencySizingError(ValueError):
    """Invalid or unsafe capital-efficiency research input."""


class CapitalEfficiencyFeasibility(StrEnum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"


RISK_BUDGET = "RISK_BUDGET"
MARGIN_BUDGET = "MARGIN_BUDGET"
BROKER_MAX_VOLUME = "BROKER_MAX_VOLUME"
BROKER_MINIMUM_VOLUME = "BROKER_MINIMUM_VOLUME"


@dataclass(frozen=True, slots=True)
class CapitalEfficiencySizingInput:
    """One frozen sizing experiment.

    exposure_per_volume is intentionally generic. The caller must provide a
    consistent economic exposure unit for the experiment family. The lab never
    infers contract economics.
    """

    experiment_id: str
    qore_symbol: str
    geometry_provenance: str
    structural_stop_verified: bool
    assigned_capital: Decimal
    risk_budget_usd: Decimal
    margin_budget_usd: Decimal
    stop_loss_per_volume: Decimal
    margin_per_volume: Decimal
    exposure_per_volume: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    baseline_volume: Decimal | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("experiment_id", self.experiment_id),
            ("qore_symbol", self.qore_symbol),
            ("geometry_provenance", self.geometry_provenance),
        ):
            if not isinstance(value, str) or not value.strip():
                raise CapitalEfficiencySizingError(f"{name} must be non-empty")
        if type(self.structural_stop_verified) is not bool:
            raise CapitalEfficiencySizingError(
                "structural_stop_verified must be bool"
            )
        for name, value in (
            ("assigned_capital", self.assigned_capital),
            ("risk_budget_usd", self.risk_budget_usd),
            ("margin_budget_usd", self.margin_budget_usd),
            ("stop_loss_per_volume", self.stop_loss_per_volume),
            ("margin_per_volume", self.margin_per_volume),
            ("exposure_per_volume", self.exposure_per_volume),
            ("minimum_volume", self.minimum_volume),
            ("maximum_volume", self.maximum_volume),
            ("volume_step", self.volume_step),
        ):
            _positive_decimal(value, name)
        if self.maximum_volume < self.minimum_volume:
            raise CapitalEfficiencySizingError(
                "maximum_volume cannot be below minimum_volume"
            )
        if self.minimum_volume < self.volume_step:
            raise CapitalEfficiencySizingError(
                "minimum_volume cannot be below volume_step"
            )
        if self.risk_budget_usd > self.assigned_capital:
            raise CapitalEfficiencySizingError(
                "risk_budget_usd cannot exceed assigned_capital"
            )
        if self.baseline_volume is not None:
            _positive_decimal(self.baseline_volume, "baseline_volume")
            if self.baseline_volume > self.maximum_volume:
                raise CapitalEfficiencySizingError(
                    "baseline_volume cannot exceed maximum_volume"
                )
            if not _is_step_aligned(self.baseline_volume, self.volume_step):
                raise CapitalEfficiencySizingError(
                    "baseline_volume must align to volume_step"
                )


@dataclass(frozen=True, slots=True)
class CapitalEfficiencySizingResult:
    experiment_id: str
    qore_symbol: str
    status: CapitalEfficiencyFeasibility
    raw_volume_by_risk: Decimal
    raw_volume_by_margin: Decimal
    raw_feasible_volume: Decimal
    authorized_volume: Decimal
    stop_risk_usd: Decimal
    margin_committed_usd: Decimal
    exposure: Decimal
    exposure_per_stop_risk_dollar: Decimal
    exposure_per_margin_dollar: Decimal
    risk_budget_utilization: Decimal
    margin_budget_utilization: Decimal
    assigned_capital_risk_fraction: Decimal
    assigned_capital_margin_fraction: Decimal
    baseline_volume: Decimal | None
    baseline_stop_risk_usd: Decimal | None
    baseline_margin_committed_usd: Decimal | None
    baseline_exposure: Decimal | None
    exposure_gain_multiple: Decimal | None
    binding_constraints: tuple[str, ...]
    reason: str

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.experiment_id,
            self.qore_symbol,
            self.status.value,
            self.raw_volume_by_risk,
            self.raw_volume_by_margin,
            self.raw_feasible_volume,
            self.authorized_volume,
            self.stop_risk_usd,
            self.margin_committed_usd,
            self.exposure,
            self.exposure_per_stop_risk_dollar,
            self.exposure_per_margin_dollar,
            self.risk_budget_utilization,
            self.margin_budget_utilization,
            self.assigned_capital_risk_fraction,
            self.assigned_capital_margin_fraction,
            self.baseline_volume,
            self.baseline_stop_risk_usd,
            self.baseline_margin_committed_usd,
            self.baseline_exposure,
            self.exposure_gain_multiple,
            self.binding_constraints,
            self.reason,
        )


def evaluate_capital_efficiency_sizing(
    spec: CapitalEfficiencySizingInput,
) -> CapitalEfficiencySizingResult:
    """Find maximum step-aligned volume inside the frozen risk/margin envelope."""

    if not isinstance(spec, CapitalEfficiencySizingInput):
        raise CapitalEfficiencySizingError(
            "spec must be CapitalEfficiencySizingInput"
        )
    if not spec.structural_stop_verified:
        raise CapitalEfficiencySizingError(
            "structural stop must be verified before leverage-efficiency research"
        )

    by_risk = spec.risk_budget_usd / spec.stop_loss_per_volume
    by_margin = spec.margin_budget_usd / spec.margin_per_volume
    raw_feasible = min(by_risk, by_margin, spec.maximum_volume)
    binding = _binding_constraints(
        raw_feasible=raw_feasible,
        by_risk=by_risk,
        by_margin=by_margin,
        maximum_volume=spec.maximum_volume,
    )
    volume = _floor_to_step(raw_feasible, spec.volume_step)

    baseline = _baseline_metrics(spec)

    if volume < spec.minimum_volume:
        return CapitalEfficiencySizingResult(
            experiment_id=spec.experiment_id,
            qore_symbol=spec.qore_symbol,
            status=CapitalEfficiencyFeasibility.INFEASIBLE,
            raw_volume_by_risk=by_risk,
            raw_volume_by_margin=by_margin,
            raw_feasible_volume=raw_feasible,
            authorized_volume=Decimal(0),
            stop_risk_usd=Decimal(0),
            margin_committed_usd=Decimal(0),
            exposure=Decimal(0),
            exposure_per_stop_risk_dollar=Decimal(0),
            exposure_per_margin_dollar=Decimal(0),
            risk_budget_utilization=Decimal(0),
            margin_budget_utilization=Decimal(0),
            assigned_capital_risk_fraction=Decimal(0),
            assigned_capital_margin_fraction=Decimal(0),
            baseline_volume=spec.baseline_volume,
            baseline_stop_risk_usd=baseline[0],
            baseline_margin_committed_usd=baseline[1],
            baseline_exposure=baseline[2],
            exposure_gain_multiple=None,
            binding_constraints=tuple(
                sorted((*binding, BROKER_MINIMUM_VOLUME))
            ),
            reason=(
                "risk/margin envelope maps below broker minimum volume; "
                "no research size is feasible"
            ),
        )

    stop_risk = volume * spec.stop_loss_per_volume
    margin = volume * spec.margin_per_volume
    exposure = volume * spec.exposure_per_volume
    baseline_exposure = baseline[2]
    gain = exposure / baseline_exposure if baseline_exposure is not None else None

    return CapitalEfficiencySizingResult(
        experiment_id=spec.experiment_id,
        qore_symbol=spec.qore_symbol,
        status=CapitalEfficiencyFeasibility.FEASIBLE,
        raw_volume_by_risk=by_risk,
        raw_volume_by_margin=by_margin,
        raw_feasible_volume=raw_feasible,
        authorized_volume=volume,
        stop_risk_usd=stop_risk,
        margin_committed_usd=margin,
        exposure=exposure,
        exposure_per_stop_risk_dollar=exposure / stop_risk,
        exposure_per_margin_dollar=exposure / margin,
        risk_budget_utilization=stop_risk / spec.risk_budget_usd,
        margin_budget_utilization=margin / spec.margin_budget_usd,
        assigned_capital_risk_fraction=stop_risk / spec.assigned_capital,
        assigned_capital_margin_fraction=margin / spec.assigned_capital,
        baseline_volume=spec.baseline_volume,
        baseline_stop_risk_usd=baseline[0],
        baseline_margin_committed_usd=baseline[1],
        baseline_exposure=baseline_exposure,
        exposure_gain_multiple=gain,
        binding_constraints=binding,
        reason=(
            "maximum step-aligned exposure inside verified structural stop-risk "
            "and margin budgets"
        ),
    )


def capital_efficiency_pareto_frontier(
    results: tuple[CapitalEfficiencySizingResult, ...],
) -> tuple[CapitalEfficiencySizingResult, ...]:
    """Return feasible experiments not dominated on exposure, stop risk and margin."""

    if not isinstance(results, tuple):
        raise CapitalEfficiencySizingError("results must be a tuple")
    if any(not isinstance(item, CapitalEfficiencySizingResult) for item in results):
        raise CapitalEfficiencySizingError(
            "results must contain CapitalEfficiencySizingResult values"
        )
    feasible = tuple(
        item
        for item in results
        if item.status is CapitalEfficiencyFeasibility.FEASIBLE
    )
    frontier = [
        candidate
        for candidate in feasible
        if not any(
            _dominates(other, candidate)
            for other in feasible
            if other is not candidate
        )
    ]
    return tuple(sorted(frontier, key=lambda item: item.experiment_id))


def _dominates(
    left: CapitalEfficiencySizingResult,
    right: CapitalEfficiencySizingResult,
) -> bool:
    no_worse = (
        left.exposure >= right.exposure
        and left.stop_risk_usd <= right.stop_risk_usd
        and left.margin_committed_usd <= right.margin_committed_usd
    )
    strictly_better = (
        left.exposure > right.exposure
        or left.stop_risk_usd < right.stop_risk_usd
        or left.margin_committed_usd < right.margin_committed_usd
    )
    return no_worse and strictly_better


def _baseline_metrics(
    spec: CapitalEfficiencySizingInput,
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    volume = spec.baseline_volume
    if volume is None:
        return (None, None, None)
    return (
        volume * spec.stop_loss_per_volume,
        volume * spec.margin_per_volume,
        volume * spec.exposure_per_volume,
    )


def _binding_constraints(
    *,
    raw_feasible: Decimal,
    by_risk: Decimal,
    by_margin: Decimal,
    maximum_volume: Decimal,
) -> tuple[str, ...]:
    constraints: list[str] = []
    if by_risk == raw_feasible:
        constraints.append(RISK_BUDGET)
    if by_margin == raw_feasible:
        constraints.append(MARGIN_BUDGET)
    if maximum_volume == raw_feasible:
        constraints.append(BROKER_MAX_VOLUME)
    return tuple(sorted(constraints))


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def _is_step_aligned(value: Decimal, step: Decimal) -> bool:
    units = value / step
    return units == units.to_integral_value()


def _positive_decimal(value: object, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        raise CapitalEfficiencySizingError(
            f"{name} must be positive finite Decimal"
        )
