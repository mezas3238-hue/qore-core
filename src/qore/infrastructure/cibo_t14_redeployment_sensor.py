"""T14 release-to-redeployment diagnostic sensor.

Evaluation-only. Uses only T14 release geometry plus later causal expectations,
Context and allocation state. It never reads realized P/L to decide whether a
release was good or bad.

The sensor separates:
1. natural opportunity wait: release -> first later positive Context-ALLOW
   opportunity that fits the released risk/margin capacity;
2. allocator wait: first fitting opportunity -> first fitting opportunity that
   CIBO actually selected.

This prevents natural market scarcity from being misclassified as T14 or
allocator inefficiency.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from statistics import median
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class CiboT14RedeploymentReport:
    changed_release_count: int
    released_stop_risk_usd: Decimal
    released_margin_usd: Decimal
    later_fitting_opportunity_count: int
    later_selected_fitting_count: int
    no_later_fit_count: int
    fit_not_selected_count: int
    fitting_coverage: Decimal
    first_fit_selected_immediately_rate: Decimal
    natural_opportunity_wait_median_minutes: Decimal
    natural_opportunity_wait_p90_minutes: Decimal
    allocator_wait_median_minutes: Decimal
    allocator_wait_p90_minutes: Decimal
    outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "changed_release_count",
            "later_fitting_opportunity_count",
            "later_selected_fitting_count",
            "no_later_fit_count",
            "fit_not_selected_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"T14 redeployment {name} must be non-negative int"
                )
        for name in (
            "released_stop_risk_usd",
            "released_margin_usd",
            "natural_opportunity_wait_median_minutes",
            "natural_opportunity_wait_p90_minutes",
            "allocator_wait_median_minutes",
            "allocator_wait_p90_minutes",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"T14 redeployment {name} must be finite non-negative Decimal"
                )
        for name in ("fitting_coverage", "first_fit_selected_immediately_rate"):
            value = getattr(self, name)
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"T14 redeployment {name} outside [0,1]"
                )
        if self.outcome_used or self.productive_authority:
            raise CiboCapitalManagementError(
                "T14 redeployment sensor cannot use outcomes or authority"
            )


def _dec(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            "T14 redeployment numeric evidence invalid"
        ) from error
    if not result.is_finite():
        raise CiboCapitalManagementError(
            "T14 redeployment numeric evidence must be finite"
        )
    return result


def _dt(value: object) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(
            "T14 redeployment time must be ISO string"
        )
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CiboCapitalManagementError(
            "T14 redeployment time must be timezone-aware"
        )
    return parsed


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal(1) if numerator == 0 else Decimal(0)
    return Decimal(numerator) / Decimal(denominator)


def _quantile(values: list[Decimal], q: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * Decimal(len(ordered) - 1)
    lo = int(position)
    hi = min(len(ordered) - 1, lo + 1)
    fraction = position - Decimal(lo)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * fraction


def measure_t14_redeployment(
    *,
    t14_decisions: list[dict[str, Any]],
    decision_trace: dict[str, Any],
) -> CiboT14RedeploymentReport:
    """Separate natural opportunity scarcity from allocator redeployment delay."""

    changed = []
    for item in t14_decisions:
        if not isinstance(item, dict):
            raise CiboCapitalManagementError(
                "T14 redeployment decision must be object"
            )
        risk = _dec(item.get("released_stop_risk_usd", "0"))
        margin = _dec(item.get("released_margin_usd", "0"))
        if item.get("action") in {"REDUCE", "RELEASE_ALL"} and (
            risk > 0 or margin > 0
        ):
            if item.get("outcome_used") is True:
                raise CiboCapitalManagementError(
                    "T14 redeployment cannot consume outcome-aware release"
                )
            changed.append((item, risk, margin))

    raw_rows = decision_trace.get("opportunities")
    if not isinstance(raw_rows, list):
        raise CiboCapitalManagementError(
            "T14 redeployment requires decision-trace opportunities"
        )

    opportunities: list[
        tuple[datetime, Decimal, Decimal, bool]
    ] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "T14 redeployment opportunity must be object"
            )
        expectation = row.get("expectation")
        context = row.get("context_quality")
        cma = row.get("cma")
        allocation = row.get("allocation")
        if not all(
            isinstance(item, dict)
            for item in (expectation, context, cma, allocation)
        ):
            continue
        expected_value = _dec(
            expectation.get("expected_net_value_usd", "0")
        )
        if expected_value <= 0 or context.get("disposition") != "ALLOW":
            continue
        risk = _dec(cma.get("candidate_stop_risk_usd", "0"))
        margin = _dec(cma.get("candidate_margin_usd", "0"))
        if risk <= 0 or margin <= 0:
            continue
        opportunities.append(
            (
                _dt(row.get("market_decision_at")),
                risk,
                margin,
                bool(allocation.get("selected_by_cibo_policy")),
            )
        )
    opportunities.sort(key=lambda item: item[0])

    natural_waits: list[Decimal] = []
    allocator_waits: list[Decimal] = []
    fitting = 0
    selected_fitting = 0
    immediate = 0

    for item, released_risk, released_margin in changed:
        release_at = _dt(item.get("decision_at"))
        first_fit = None
        first_selected_fit = None
        for opportunity in opportunities:
            when, required_risk, required_margin, selected = opportunity
            if when <= release_at:
                continue
            if (
                required_risk <= released_risk
                and required_margin <= released_margin
            ):
                if first_fit is None:
                    first_fit = opportunity
                if selected and first_selected_fit is None:
                    first_selected_fit = opportunity
                if first_fit is not None and first_selected_fit is not None:
                    break

        if first_fit is None:
            continue
        fitting += 1
        natural_wait = Decimal(
            str((first_fit[0] - release_at).total_seconds() / 60)
        )
        natural_waits.append(natural_wait)

        if first_selected_fit is None:
            continue
        selected_fitting += 1
        allocator_wait = Decimal(
            str(
                (
                    first_selected_fit[0] - first_fit[0]
                ).total_seconds()
                / 60
            )
        )
        allocator_waits.append(allocator_wait)
        if allocator_wait == 0:
            immediate += 1

    changed_count = len(changed)
    no_fit = changed_count - fitting
    fit_not_selected = fitting - selected_fitting

    return CiboT14RedeploymentReport(
        changed_release_count=changed_count,
        released_stop_risk_usd=sum(
            (risk for _, risk, _ in changed),
            Decimal(0),
        ),
        released_margin_usd=sum(
            (margin for _, _, margin in changed),
            Decimal(0),
        ),
        later_fitting_opportunity_count=fitting,
        later_selected_fitting_count=selected_fitting,
        no_later_fit_count=no_fit,
        fit_not_selected_count=fit_not_selected,
        fitting_coverage=_ratio(fitting, changed_count),
        first_fit_selected_immediately_rate=_ratio(
            immediate,
            selected_fitting,
        ),
        natural_opportunity_wait_median_minutes=(
            Decimal(str(median(natural_waits)))
            if natural_waits
            else Decimal(0)
        ),
        natural_opportunity_wait_p90_minutes=_quantile(
            natural_waits,
            Decimal("0.90"),
        ),
        allocator_wait_median_minutes=(
            Decimal(str(median(allocator_waits)))
            if allocator_waits
            else Decimal(0)
        ),
        allocator_wait_p90_minutes=_quantile(
            allocator_waits,
            Decimal("0.90"),
        ),
        outcome_used=False,
        productive_authority=False,
    )
