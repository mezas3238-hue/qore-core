"""Pre-Risk causal opportunity-capture sensor for Maximum Capability.

This sensor uses only information available at the decision epoch:
frozen expectation, Context disposition, CE2I regime posture and allocation
disposition. Realized trade outcomes are not read.

It measures the historical baseline and the exact opportunity surface that a
single bounded RECOVERY capability-measurement probe could have exposed to the
allocator/QORE Risk. The challenger measurement does not claim that QORE Risk
would authorize the opportunity or that the trade would later win.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class CiboPreRiskCaptureReport:
    positive_context_allowed_count: int
    positive_context_allowed_expected_value_usd: Decimal
    selected_count: int
    selected_expected_value_usd: Decimal
    recovery_preserve_miss_count: int
    recovery_preserve_miss_expected_value_usd: Decimal
    baseline_count_efficiency: Decimal
    baseline_value_efficiency: Decimal
    recovery_probe_count_ceiling: Decimal
    recovery_probe_value_ceiling: Decimal
    count_efficiency_delta: Decimal
    value_efficiency_delta: Decimal
    outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "positive_context_allowed_count",
            "selected_count",
            "recovery_preserve_miss_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"pre-Risk capture {name} must be non-negative int"
                )
        for name in (
            "positive_context_allowed_expected_value_usd",
            "selected_expected_value_usd",
            "recovery_preserve_miss_expected_value_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"pre-Risk capture {name} must be finite non-negative Decimal"
                )
        for name in (
            "baseline_count_efficiency",
            "baseline_value_efficiency",
            "recovery_probe_count_ceiling",
            "recovery_probe_value_ceiling",
        ):
            value = getattr(self, name)
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"pre-Risk capture {name} outside [0,1]"
                )
        if self.outcome_used or self.productive_authority:
            raise CiboCapitalManagementError(
                "pre-Risk capture sensor cannot use outcomes or authority"
            )


def _dec(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            "pre-Risk capture expected value is invalid"
        ) from error
    if not result.is_finite():
        raise CiboCapitalManagementError(
            "pre-Risk capture expected value must be finite"
        )
    return result


def _ratio(numerator: int | Decimal, denominator: int | Decimal) -> Decimal:
    num = Decimal(numerator)
    den = Decimal(denominator)
    if den <= 0:
        return Decimal(1) if num == 0 else Decimal(0)
    return max(Decimal(0), min(Decimal(1), num / den))


def _regime_posture(row: dict[str, Any]) -> str:
    allocation = row.get("allocation")
    if isinstance(allocation, dict):
        value = allocation.get("allocator_regime_posture")
        if value:
            return str(value)

    ce2i = row.get("ce2i")
    if isinstance(ce2i, dict):
        receipts = ce2i.get("runtime_receipts")
        if isinstance(receipts, list):
            for receipt in receipts:
                if not isinstance(receipt, dict):
                    continue
                if receipt.get("engine_name") != "select_ce2i_tools_for_regime":
                    continue
                output = receipt.get("output_payload")
                if isinstance(output, dict) and output.get("posture"):
                    return str(output["posture"])
    return "<UNKNOWN>"


def measure_pre_risk_opportunity_capture(
    decision_trace: dict[str, Any],
) -> CiboPreRiskCaptureReport:
    """Measure baseline and RECOVERY-probe opportunity capture ex ante."""

    rows = decision_trace.get("opportunities")
    if not isinstance(rows, list):
        raise CiboCapitalManagementError(
            "pre-Risk capture requires decision-trace opportunities"
        )

    eligible_count = 0
    eligible_ev = Decimal(0)
    selected_count = 0
    selected_ev = Decimal(0)
    recovery_miss_count = 0
    recovery_miss_ev = Decimal(0)

    for row in rows:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "pre-Risk capture opportunity row must be object"
            )
        expectation = row.get("expectation")
        context = row.get("context_quality")
        allocation = row.get("allocation")
        if (
            not isinstance(expectation, dict)
            or not isinstance(context, dict)
            or not isinstance(allocation, dict)
        ):
            raise CiboCapitalManagementError(
                "pre-Risk capture row surfaces missing"
            )
        ev = _dec(expectation.get("expected_net_value_usd", "0"))
        if ev <= 0 or context.get("disposition") != "ALLOW":
            continue

        eligible_count += 1
        eligible_ev += ev
        selected = bool(allocation.get("selected_by_cibo_policy"))
        if selected:
            selected_count += 1
            selected_ev += ev
            continue

        if (
            allocation.get("allocator_disposition") == "PRESERVE_CAPACITY"
            and _regime_posture(row) == "RECOVERY"
        ):
            recovery_miss_count += 1
            recovery_miss_ev += ev

    challenger_count = selected_count + recovery_miss_count
    challenger_ev = selected_ev + recovery_miss_ev
    baseline_count_eff = _ratio(selected_count, eligible_count)
    baseline_value_eff = _ratio(selected_ev, eligible_ev)
    challenger_count_eff = _ratio(challenger_count, eligible_count)
    challenger_value_eff = _ratio(challenger_ev, eligible_ev)

    return CiboPreRiskCaptureReport(
        positive_context_allowed_count=eligible_count,
        positive_context_allowed_expected_value_usd=eligible_ev,
        selected_count=selected_count,
        selected_expected_value_usd=selected_ev,
        recovery_preserve_miss_count=recovery_miss_count,
        recovery_preserve_miss_expected_value_usd=recovery_miss_ev,
        baseline_count_efficiency=baseline_count_eff,
        baseline_value_efficiency=baseline_value_eff,
        recovery_probe_count_ceiling=challenger_count_eff,
        recovery_probe_value_ceiling=challenger_value_eff,
        count_efficiency_delta=challenger_count_eff - baseline_count_eff,
        value_efficiency_delta=challenger_value_eff - baseline_value_eff,
        outcome_used=False,
        productive_authority=False,
    )
