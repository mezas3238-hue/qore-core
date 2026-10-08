"""H10 causal microcapital sizing contract — research-only, non-authoritative.

Never veto an already-executed Trader entry; if broker minimum cannot fit,
report an infeasible custody/execution contract, NOT a fabricated PnL.
No future R/outcome, trader ID, year, symbol blacklist or return labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

D = Decimal
ZERO = D("0")


@dataclass(frozen=True, slots=True)
class MicroAccountState:
    """All inputs known at order time, without future settlement labels."""

    balance_usd: Decimal
    settled_peak_usd: Decimal
    trailing_floor_usd: Decimal
    reserved_open_stop_and_exit_fees_usd: Decimal
    day_open_balance_usd: Decimal
    daily_internal_cap_usd: Decimal
    already_committed_margin_usd: Decimal


@dataclass(frozen=True, slots=True)
class MicroBudget:
    entry_stop_and_roundtrip_fee_ceiling_usd: Decimal
    aggregate_risk_ceiling_usd: Decimal
    drawdown_fraction: Decimal
    scale_multiplier: Decimal
    can_fund_broker_minimum: bool
    shortfall_to_broker_minimum_usd: Decimal
    hard_fail_reason: str | None


def plan_microcapital_entry(
    state: MicroAccountState,
    *,
    broker_minimum_stop_plus_roundtrip_fees_usd: Decimal,
    broker_minimum_margin_usd: Decimal,
    absolute_per_trade_ceiling_usd: Decimal = D("999999"),
) -> MicroBudget:
    """Budget 0.25% of present capital (incl. roundtrip fees), taper in DD.

    Harder limits: <=10% of remaining trailing headroom, <=10% of
    unconsumed internal daily loss budget and <=1% total concurrent
    declared stop-risk including committed fees. Risk budget is not
    evidence of execution or a guarantee against gaps/slippage.
    """
    values = (
        state.balance_usd, state.settled_peak_usd, state.trailing_floor_usd,
        state.reserved_open_stop_and_exit_fees_usd,
        state.day_open_balance_usd, state.daily_internal_cap_usd,
        state.already_committed_margin_usd,
        broker_minimum_stop_plus_roundtrip_fees_usd,
        broker_minimum_margin_usd, absolute_per_trade_ceiling_usd,
    )
    if any(not isinstance(x, D) or not x.is_finite() for x in values):
        raise ValueError("finite Decimal inputs required")
    if state.balance_usd <= ZERO or state.settled_peak_usd <= ZERO:
        raise ValueError("positive balance and historical peak required")
    if any(x < ZERO for x in (
        state.reserved_open_stop_and_exit_fees_usd,
        state.daily_internal_cap_usd,
        state.already_committed_margin_usd,
        broker_minimum_stop_plus_roundtrip_fees_usd,
        broker_minimum_margin_usd,
        absolute_per_trade_ceiling_usd,
    )):
        raise ValueError("negative risk, margin, fee or limit")
    dd = max(ZERO, (state.settled_peak_usd-state.balance_usd)
             / state.settled_peak_usd)
    slowdown = (D("1") if dd < D(".01") else
                D(".75") if dd < D(".02") else
                D(".50") if dd < D(".03") else D(".25"))
    open_risk = state.reserved_open_stop_and_exit_fees_usd
    aggregate_ceiling = max(ZERO, min(
        state.balance_usd*D(".01"),
        state.day_open_balance_usd*D(".03"),
    ))
    unspent_daily = max(ZERO, (
        state.daily_internal_cap_usd
        - (state.day_open_balance_usd-state.balance_usd) - open_risk
    ))
    unspent_trailing = max(
        ZERO,state.balance_usd-state.trailing_floor_usd-open_risk
    )
    cap = max(ZERO,min(
        absolute_per_trade_ceiling_usd,
        state.balance_usd*D(".0025")*slowdown,
        unspent_trailing*D(".10"),
        unspent_daily*D(".10"),
        aggregate_ceiling-open_risk,
    ))
    feasible_risk = broker_minimum_stop_plus_roundtrip_fees_usd <= cap
    feasible_margin = (
        broker_minimum_margin_usd <=
        max(ZERO, state.balance_usd - state.already_committed_margin_usd)
    )
    feasible = feasible_risk and feasible_margin
    return MicroBudget(
        entry_stop_and_roundtrip_fee_ceiling_usd=cap,
        aggregate_risk_ceiling_usd=aggregate_ceiling,
        drawdown_fraction=dd,
        scale_multiplier=slowdown,
        can_fund_broker_minimum=feasible,
        shortfall_to_broker_minimum_usd=max(
            ZERO,broker_minimum_stop_plus_roundtrip_fees_usd-cap
        ),
        hard_fail_reason=(
            None if feasible else "BROKER_MIN_MARGIN_UNFUNDED"
            if not feasible_margin else "BROKER_MIN_STOP_PLUS_FEES_ABOVE_MICRO_BUDGET"
        ),
    )
