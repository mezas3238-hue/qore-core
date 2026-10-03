"""Frozen Trader Lab policy for protected-capital reinvestment.

Derived only in NON_CERTIFYING_REUSED_HOLDOUT Trader Lab calibration.
The policy is then consumed as a fixed predecision rule. It never inspects the
current candidate outcome and grants no Risk, sizing, broker, LIVE, Production,
real-capital, certification, deployment, or merge authority.

The calibrated ratio is applied to causally-known CURRENT realized economic
capital at decision time. It is not frozen to the account's opening balance.
Protected-capital availability, QORE Risk and provider/margin constraints remain
independent hard ceilings.
"""

from __future__ import annotations

from decimal import Decimal

POLICY_ID = "CIBO_PROTECTED_REINVESTMENT_TRADER_LAB_V1"
CALIBRATION_MODE = "NON_CERTIFYING_REUSED_HOLDOUT"
ELIGIBLE_SIDE = "long"
MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO = Decimal(
    "0.030069491001082367274812335331333333333333333333333"
)
# Compatibility alias for retained reports. New code must use the CURRENT-capital
# name and must never interpret this ratio as permanently bound to opening capital.
MAX_CAPITAL_NEED_TO_BASE_RATIO = MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO
USD60_MAX_CAPITAL_NEED_USD = Decimal(
    "1.80416946006494203648874011988"
)

POPULATION_GATE_USED = False
OUTCOME_USED_AT_DECISION = False
FORWARD_GENERALIZATION_CLAIMED = False
RUNTIME_AUTHORITY = False
DYNAMIC_CURRENT_CAPITAL_SCALING = True
# Predecision reserve only: this capital remains protected and is not deployed.
# The ratio matches the preregistered GAP_AND_SLIPPAGE_25PCT_RISK stress family.
PROTECTED_LOSS_RESERVE_STOP_RISK_RATIO = Decimal("0.25")


def protected_loss_reserve_usd(stop_risk_usd: Decimal) -> Decimal:
    if (
        not isinstance(stop_risk_usd, Decimal)
        or not stop_risk_usd.is_finite()
        or stop_risk_usd < 0
    ):
        raise ValueError("stop risk must be finite non-negative Decimal")
    return stop_risk_usd * PROTECTED_LOSS_RESERVE_STOP_RISK_RATIO


def maximum_reinvestment_capital_need_usd(
    eligible_current_capital_usd: Decimal,
) -> Decimal:
    if (
        not isinstance(eligible_current_capital_usd, Decimal)
        or not eligible_current_capital_usd.is_finite()
        or eligible_current_capital_usd <= 0
    ):
        raise ValueError("eligible current capital must be finite positive Decimal")
    return (
        eligible_current_capital_usd
        * MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO
    )


def protected_reinvestment_candidate_allowed(
    *,
    side: str,
    capital_need_usd: Decimal,
    eligible_current_capital_usd: Decimal,
) -> bool:
    if not isinstance(side, str) or not side:
        raise ValueError("side is required")
    if (
        not isinstance(capital_need_usd, Decimal)
        or not capital_need_usd.is_finite()
        or capital_need_usd < 0
    ):
        raise ValueError("capital need must be finite non-negative Decimal")
    return (
        side == ELIGIBLE_SIDE
        and capital_need_usd
        <= maximum_reinvestment_capital_need_usd(
            eligible_current_capital_usd
        )
    )
