"""Preregistered causal efficiency guard for RECOVERY capability probes.

This guard was derived on burned/reused-holdout adaptive research and is not a
fresh-OOS or certification claim. Runtime inputs are strictly predecision:
expected value, candidate stop risk and current hard-risk headroom.

The guard has no sizing, Risk, execution or broker authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

RECOVERY_PROBE_EFFICIENCY_GUARD_ID = "CIBO_RECOVERY_PROBE_EFFICIENCY_GUARD_V1"
MIN_EXPECTED_VALUE_PER_STOP_RISK = Decimal("0.15")
MAX_STOP_RISK_FRACTION_OF_HEADROOM = Decimal("0.04")


@dataclass(frozen=True, slots=True)
class CiboRecoveryProbeEfficiencyDecision:
    guard_id: str
    expected_value_per_stop_risk: Decimal
    stop_risk_fraction_of_headroom: Decimal
    admitted: bool
    reason: str
    reused_holdout_derived: bool = True
    scientific_freshness_claimed: bool = False
    certification_claimed: bool = False
    outcome_used: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.guard_id != RECOVERY_PROBE_EFFICIENCY_GUARD_ID:
            raise CiboCapitalManagementError("RECOVERY probe guard identity drift")
        for name in (
            "expected_value_per_stop_risk",
            "stop_risk_fraction_of_headroom",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"RECOVERY probe guard {name} must be finite Decimal"
                )
        if self.stop_risk_fraction_of_headroom < 0:
            raise CiboCapitalManagementError(
                "RECOVERY probe headroom fraction cannot be negative"
            )
        if not self.reason:
            raise CiboCapitalManagementError("RECOVERY probe guard reason required")
        if (
            not self.reused_holdout_derived
            or self.scientific_freshness_claimed
            or self.certification_claimed
            or self.outcome_used
            or self.risk_authority
            or self.execution_authority
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "RECOVERY probe guard governance contamination"
            )


def evaluate_recovery_probe_efficiency(
    *,
    expected_net_value_usd: Decimal,
    stop_risk_usd: Decimal,
    hard_risk_headroom_usd: Decimal,
) -> CiboRecoveryProbeEfficiencyDecision:
    """Evaluate the preregistered RECOVERY probe surface, fail closed."""

    for name, value in (
        ("expected_net_value_usd", expected_net_value_usd),
        ("stop_risk_usd", stop_risk_usd),
        ("hard_risk_headroom_usd", hard_risk_headroom_usd),
    ):
        if not isinstance(value, Decimal) or not value.is_finite():
            raise CiboCapitalManagementError(
                f"RECOVERY probe guard {name} must be finite Decimal"
            )

    if stop_risk_usd <= 0 or hard_risk_headroom_usd <= 0:
        return CiboRecoveryProbeEfficiencyDecision(
            guard_id=RECOVERY_PROBE_EFFICIENCY_GUARD_ID,
            expected_value_per_stop_risk=Decimal(0),
            stop_risk_fraction_of_headroom=Decimal(1),
            admitted=False,
            reason="INVALID_OR_ZERO_RISK_HEADROOM_FAIL_CLOSED",
        )

    value_per_risk = expected_net_value_usd / stop_risk_usd
    risk_fraction = stop_risk_usd / hard_risk_headroom_usd
    admitted = (
        value_per_risk >= MIN_EXPECTED_VALUE_PER_STOP_RISK
        and risk_fraction <= MAX_STOP_RISK_FRACTION_OF_HEADROOM
    )
    if value_per_risk < MIN_EXPECTED_VALUE_PER_STOP_RISK:
        reason = "EXPECTED_VALUE_PER_STOP_RISK_BELOW_FROZEN_FLOOR"
    elif risk_fraction > MAX_STOP_RISK_FRACTION_OF_HEADROOM:
        reason = "STOP_RISK_FRACTION_OF_HEADROOM_ABOVE_FROZEN_CAP"
    else:
        reason = "RECOVERY_PROBE_EFFICIENCY_GUARD_PASS"

    return CiboRecoveryProbeEfficiencyDecision(
        guard_id=RECOVERY_PROBE_EFFICIENCY_GUARD_ID,
        expected_value_per_stop_risk=value_per_risk,
        stop_risk_fraction_of_headroom=risk_fraction,
        admitted=admitted,
        reason=reason,
    )
