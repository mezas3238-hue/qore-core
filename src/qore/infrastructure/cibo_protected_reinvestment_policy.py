"""Frozen Trader Lab policy for protected-capital reinvestment.

Derived only in NON_CERTIFYING_REUSED_HOLDOUT Trader Lab calibration.
The policy is then consumed as a fixed predecision rule. It never inspects the
current candidate outcome and grants no Risk, sizing, broker, LIVE, Production,
real-capital, certification, deployment, or merge authority.
"""

from __future__ import annotations

from decimal import Decimal

POLICY_ID = "CIBO_PROTECTED_REINVESTMENT_TRADER_LAB_V1"
CALIBRATION_MODE = "NON_CERTIFYING_REUSED_HOLDOUT"
ELIGIBLE_SIDE = "long"
MAX_CAPITAL_NEED_TO_BASE_RATIO = Decimal(
    "0.030069491001082367274812335331333333333333333333333"
)
USD60_MAX_CAPITAL_NEED_USD = Decimal(
    "1.80416946006494203648874011988"
)

POPULATION_GATE_USED = False
OUTCOME_USED_AT_DECISION = False
FORWARD_GENERALIZATION_CLAIMED = False
RUNTIME_AUTHORITY = False


def maximum_reinvestment_capital_need_usd(
    opening_base_capital_usd: Decimal,
) -> Decimal:
    if (
        not isinstance(opening_base_capital_usd, Decimal)
        or not opening_base_capital_usd.is_finite()
        or opening_base_capital_usd <= 0
    ):
        raise ValueError("opening base capital must be finite positive Decimal")
    return opening_base_capital_usd * MAX_CAPITAL_NEED_TO_BASE_RATIO


def protected_reinvestment_candidate_allowed(
    *,
    side: str,
    capital_need_usd: Decimal,
    opening_base_capital_usd: Decimal,
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
        <= maximum_reinvestment_capital_need_usd(opening_base_capital_usd)
    )
