"""H10: causal micro-account stop sizing and funded account risk custody.

Research only. No authority to veto an already executed Trader entry or
pretend a broker minimum is fundable when cash/margin are insufficient.
State is entry-time only; no hindsight outcome or instrument blacklists.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

D = Decimal
ZERO = D("0")
AccountMode = Literal["micro_research", "stellar_instant"]


@dataclass(frozen=True, slots=True)
class MicroAccountState:
    balance_usd: Decimal
    settled_peak_usd: Decimal
    trailing_floor_usd: Decimal
    reserved_open_stop_and_exit_fees_usd: Decimal
    day_open_balance_usd: Decimal
    daily_internal_cap_usd: Decimal
    already_committed_margin_usd: Decimal


@dataclass(frozen=True, slots=True)
class MicroBudget:
    # Causal desired STOP allocation, not a guaranteed broker executable fill.
    desired_stop_risk_usd: Decimal
    maximum_fundable_stop_risk_usd: Decimal
    minimum_roundtrip_fee_usd: Decimal
    entry_stop_and_roundtrip_fee_ceiling_usd: Decimal
    aggregate_risk_ceiling_usd: Decimal
    drawdown_fraction: Decimal
    scale_multiplier: Decimal
    can_fund_broker_minimum: bool
    shortfall_to_broker_minimum_usd: Decimal
    hard_fail_reason: str | None


def micro_stop_target(balance_usd: Decimal) -> Decimal:
    """Gentle monotonic scaling: $60->$3, $100->$3.32, $500->$6.52.

    5% is a target at $60, NOT a promise of 5% risk on a $2k funded
    account. At small balance, a loss at stop PLUS fees can exceed $3.
    """
    if balance_usd <= ZERO:
        raise ValueError("positive balance required")
    return min(
        balance_usd * D(".05"),
        D("3") + max(ZERO, balance_usd - D("60")) * D(".008"),
    )


def plan_microcapital_entry(
    state: MicroAccountState,
    *,
    broker_minimum_stop_plus_roundtrip_fees_usd: Decimal,
    broker_minimum_margin_usd: Decimal,
    broker_minimum_roundtrip_fee_usd: Decimal = ZERO,
    absolute_per_trade_ceiling_usd: Decimal = D("999999"),
    account_mode: AccountMode = "micro_research",
) -> MicroBudget:
    """Budget intended $3 STOP at $60, and explicit roundtrip fees.

    Micro-research uses 10% aggregate maximum and its own daily budget,
    NOT FundedNext's mandatory rules. Stellar Instant is constrained to
    <=3% aggregate, its real trailing-floor headroom and user $60/day
    plan at $2k. A stop+fees reservation is NOT protection against gaps.
    No capacity -> scientific FAIL, never fictional funding.
    """
    values = (
        state.balance_usd, state.settled_peak_usd, state.trailing_floor_usd,
        state.reserved_open_stop_and_exit_fees_usd, state.day_open_balance_usd,
        state.daily_internal_cap_usd, state.already_committed_margin_usd,
        broker_minimum_stop_plus_roundtrip_fees_usd,
        broker_minimum_margin_usd, broker_minimum_roundtrip_fee_usd,
        absolute_per_trade_ceiling_usd,
    )
    if any(not isinstance(x, D) or not x.is_finite() for x in values):
        raise ValueError("finite Decimal inputs required")
    if state.balance_usd <= ZERO or state.settled_peak_usd <= ZERO:
        raise ValueError("positive balance and historical peak required")
    if account_mode not in ("micro_research", "stellar_instant"):
        raise ValueError("unknown account mode")
    if any(x < ZERO for x in (
        state.reserved_open_stop_and_exit_fees_usd,
        state.daily_internal_cap_usd,
        state.already_committed_margin_usd,
        broker_minimum_stop_plus_roundtrip_fees_usd,
        broker_minimum_margin_usd, broker_minimum_roundtrip_fee_usd,
        absolute_per_trade_ceiling_usd,
    )):
        raise ValueError("negative risk, margin, fee or limit")
    if broker_minimum_roundtrip_fee_usd > broker_minimum_stop_plus_roundtrip_fees_usd:
        raise ValueError("minimum fees cannot exceed complete minimum loss")
    dd = max(ZERO, (state.settled_peak_usd - state.balance_usd)
             / state.settled_peak_usd)
    slowdown = (
        D("1") if dd < D(".01") else
        D(".75") if dd < D(".02") else
        D(".50") if dd < D(".03") else D(".25")
    )
    base_stop = micro_stop_target(state.balance_usd)
    if account_mode == "stellar_instant":
        # Never allow the voluntary micro curriculum to override the
        # funded account's stricter simultaneous 3% risk and daily cap.
        base_stop = min(base_stop, state.balance_usd * D(".01"))
        aggregate_ceiling = min(
            state.balance_usd * D(".03"),
            state.day_open_balance_usd * D(".03"),
        )
    else:
        aggregate_ceiling = min(
            state.balance_usd * D(".10"),
            state.day_open_balance_usd * D(".10"),
        )
    desired_stop = base_stop * slowdown
    open_risk = state.reserved_open_stop_and_exit_fees_usd
    day_left = max(ZERO, state.daily_internal_cap_usd
                   - (state.day_open_balance_usd - state.balance_usd)
                   - open_risk)
    trailing_left = max(ZERO, state.balance_usd
                        - state.trailing_floor_usd - open_risk)
    available_all_in = max(ZERO, min(
        absolute_per_trade_ceiling_usd,
        day_left, trailing_left, aggregate_ceiling - open_risk,
    ))
    fee = broker_minimum_roundtrip_fee_usd
    # Desired SL risk stays separate from the roundtrip cost.
    funded_stop = max(ZERO, min(desired_stop, available_all_in - fee))
    funded_all_in = funded_stop + fee if available_all_in >= fee else ZERO
    physically_possible = (
        broker_minimum_stop_plus_roundtrip_fees_usd <= funded_all_in
        and broker_minimum_margin_usd <= max(
            ZERO, state.balance_usd - state.already_committed_margin_usd
        )
    )
    margin_fail = broker_minimum_margin_usd > max(
        ZERO, state.balance_usd - state.already_committed_margin_usd
    )
    return MicroBudget(
        desired_stop_risk_usd=desired_stop,
        maximum_fundable_stop_risk_usd=funded_stop,
        minimum_roundtrip_fee_usd=fee,
        entry_stop_and_roundtrip_fee_ceiling_usd=funded_all_in,
        aggregate_risk_ceiling_usd=aggregate_ceiling,
        drawdown_fraction=dd, scale_multiplier=slowdown,
        can_fund_broker_minimum=physically_possible,
        shortfall_to_broker_minimum_usd=max(
            ZERO, broker_minimum_stop_plus_roundtrip_fees_usd - funded_all_in,
        ),
        hard_fail_reason=(
            None if physically_possible else "BROKER_MIN_MARGIN_UNFUNDED"
            if margin_fail else "BROKER_MIN_STOP_PLUS_FEES_ABOVE_MICRO_BUDGET"
        ),
    )
