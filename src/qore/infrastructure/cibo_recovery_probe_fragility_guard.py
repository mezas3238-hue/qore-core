"""Causal fragility guard for RECOVERY capability probes.

Research-only guard derived on reused/burned holdout diagnostics. It uses only
predecision decision-context state and owns no sizing, Risk, execution, broker,
or certification authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

RECOVERY_PROBE_FRAGILITY_GUARD_ID = "CIBO_RECOVERY_PROBE_FRAGILITY_GUARD_V1"
_BLOCKED_M5_VOLATILITY_STATES = frozenset({"extreme"})


@dataclass(frozen=True, slots=True)
class CiboRecoveryProbeFragilityDecision:
    guard_id: str
    m5_volatility_state: str | None
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
        if self.guard_id != RECOVERY_PROBE_FRAGILITY_GUARD_ID:
            raise CiboCapitalManagementError(
                "RECOVERY fragility guard identity drift"
            )
        if self.m5_volatility_state is not None and not isinstance(
            self.m5_volatility_state, str
        ):
            raise CiboCapitalManagementError(
                "RECOVERY fragility guard M5 state must be string or None"
            )
        if not self.reason:
            raise CiboCapitalManagementError(
                "RECOVERY fragility guard reason required"
            )
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
                "RECOVERY fragility guard governance contamination"
            )


def evaluate_recovery_probe_fragility(
    *,
    decision_context: tuple[tuple[str, str], ...],
) -> CiboRecoveryProbeFragilityDecision:
    """Reject only preregistered fragile predecision states, fail transparent."""

    if not isinstance(decision_context, tuple):
        raise CiboCapitalManagementError(
            "RECOVERY fragility guard requires tuple decision_context"
        )
    context: dict[str, str] = {}
    for item in decision_context:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
        ):
            raise CiboCapitalManagementError(
                "RECOVERY fragility guard decision_context row invalid"
            )
        context[item[0]] = item[1]

    state = context.get("reg_m5_volatility_state")
    blocked = (
        state is not None
        and state.strip().lower() in _BLOCKED_M5_VOLATILITY_STATES
    )
    return CiboRecoveryProbeFragilityDecision(
        guard_id=RECOVERY_PROBE_FRAGILITY_GUARD_ID,
        m5_volatility_state=state,
        admitted=not blocked,
        reason=(
            "M5_EXTREME_VOLATILITY_FRAGILITY_REJECT"
            if blocked
            else "RECOVERY_PROBE_FRAGILITY_GUARD_PASS"
        ),
    )
