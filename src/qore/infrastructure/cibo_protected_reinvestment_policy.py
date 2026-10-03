"""Frozen Trader Lab policy for protected-capital reinvestment.

Derived only in NON_CERTIFYING_REUSED_HOLDOUT Trader Lab calibration.
The policy consumes only facts known before the candidate outcome. It grants no
Risk, sizing, broker, LIVE, Production, real-capital, certification, deployment,
or merge authority.

Trader Lab V2 selected the first preregistered candidate that passed LONG,
SHORT and BOTH on both CIBO_COMPOUND and COMPOUND_PORTFOLIO with:
- 4/4 positive chronological folds;
- positive Monte Carlo median and p05;
- zero Monte Carlo protected-pool breaches;
- all adversarial stresses except WINNER_DROUGHT positive;
- zero protected-pool breach in every stress.

The capital limit scales with causally-known CURRENT realized account capital.
"""

from __future__ import annotations

from decimal import Decimal

POLICY_ID = "CIBO_PROTECTED_REINVESTMENT_TRADER_LAB_V2"
CALIBRATION_MODE = "NON_CERTIFYING_REUSED_HOLDOUT"

ELIGIBLE_SIDES = ("long", "short")
# Compatibility alias only. New code must use ELIGIBLE_SIDES.
ELIGIBLE_SIDE = "long"

MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO = Decimal("0.04")
MAX_CAPITAL_NEED_TO_BASE_RATIO = MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO
USD60_MAX_CAPITAL_NEED_USD = Decimal("2.40")

LONG_REQUIRED_ENTRY_TYPE = "market"
LONG_MIN_EXPECTED_NET_VALUE_USD = Decimal("-0.075")
LONG_MAX_EXPECTED_CAPITAL_MINUTES = Decimal("55")

SHORT_REQUIRED_ENTRY_TYPE = "market"
SHORT_MIN_EXPECTED_NET_VALUE_USD = Decimal("0.045")
SHORT_MAX_EXPECTED_CAPITAL_MINUTES = Decimal("45")

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
    entry_type: str | None = None,
    expected_net_value_usd: Decimal | None = None,
    expected_capital_minutes: Decimal | None = None,
) -> bool:
    """Apply the frozen V2 causal admission rule.

    Missing causal inputs fail closed rather than falling back to the old
    LONG-only policy.
    """

    if not isinstance(side, str) or not side:
        raise ValueError("side is required")
    if (
        not isinstance(capital_need_usd, Decimal)
        or not capital_need_usd.is_finite()
        or capital_need_usd < 0
    ):
        raise ValueError("capital need must be finite non-negative Decimal")
    if entry_type is not None and not isinstance(entry_type, str):
        raise ValueError("entry type must be str or None")
    for name, value in (
        ("expected net value", expected_net_value_usd),
        ("expected capital minutes", expected_capital_minutes),
    ):
        if value is not None and (
            not isinstance(value, Decimal) or not value.is_finite()
        ):
            raise ValueError(f"{name} must be finite Decimal or None")

    if side not in ELIGIBLE_SIDES:
        return False
    if entry_type != "market":
        return False
    if expected_net_value_usd is None or expected_capital_minutes is None:
        return False
    if expected_capital_minutes <= 0:
        return False
    if capital_need_usd > maximum_reinvestment_capital_need_usd(
        eligible_current_capital_usd
    ):
        return False

    if side == "long":
        return (
            expected_net_value_usd >= LONG_MIN_EXPECTED_NET_VALUE_USD
            and expected_capital_minutes <= LONG_MAX_EXPECTED_CAPITAL_MINUTES
        )
    return (
        expected_net_value_usd >= SHORT_MIN_EXPECTED_NET_VALUE_USD
        and expected_capital_minutes <= SHORT_MAX_EXPECTED_CAPITAL_MINUTES
    )
