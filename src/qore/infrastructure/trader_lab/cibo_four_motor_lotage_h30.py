"""Shared capital-aware lotage for CIBO's four economic authorities (H30).

One causal account ledger, NOT four independent risk purses. SIZING requests
stop dollars, CIBO_COMPOUND checks BANK-funded MEDIUM custody, PORTFOLIO_COMPOUND
checks shared open capacity/cushion, ADAPTIVE_LEVERAGE converts the joint
approval into legal volume. No outcome/SL change; no fabricated liquidity.
Research-only until broker's live tick-value and margin service are verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D, ROUND_FLOOR


@dataclass(frozen=True)
class LotageContext:
    mode: str
    equity_usd: D
    initial_capital_usd: D
    initial_stop_target_usd: D
    min_lots: D
    step_lots: D
    max_multiplier: int
    native_cap: int
    stop_usd_per_min_lot: D
    margin_usd_per_min_lot: D
    fee_usd_per_min_lot: D
    risk_left_usd: D
    margin_left_usd: D
    bank_free_usd: D
    cushion_free_usd: D
    portfolio_credit_free_usd: D
    strict_account_cash_margin: bool = True
    already_committed_margin_usd: D = D(0)


@dataclass(frozen=True)
class MotorQuote:
    motor: str
    requested_lots: D
    approved_lots: D
    approved_stop_usd: D
    free_cash_usd: D
    binding_reason: str


@dataclass(frozen=True)
class CoordinatedLotage:
    selected_lots: D
    selected_multiplier: int
    selected_stop_usd: D
    selected_margin_usd: D
    selected_fees_usd: D
    requested_stop_usd: D
    target_attained: bool
    all_stages: tuple[MotorQuote, ...]
    binding_reason: str
    funded: bool
    minimum_lot_fundable: bool


def _amount_ok(x: D, allow_zero: bool = True) -> bool:
    return isinstance(x, D) and x.is_finite() and (x >= 0 if allow_zero else x > 0)


def _check(x: LotageContext) -> None:
    if x.mode not in ("MEDIUM","ATTACK"):
        raise ValueError("lotage cannot assign BANK trade")
    vals=(x.equity_usd,x.initial_capital_usd,x.initial_stop_target_usd,
          x.min_lots,x.step_lots,x.stop_usd_per_min_lot,
          x.margin_usd_per_min_lot,x.fee_usd_per_min_lot,x.risk_left_usd,
          x.margin_left_usd,x.bank_free_usd,x.cushion_free_usd,
          x.portfolio_credit_free_usd,x.already_committed_margin_usd)
    if not all(_amount_ok(a) for a in vals):
        raise ValueError("negative/nonfinite lotage economic input")
    if any(a<=0 for a in (x.equity_usd,x.initial_capital_usd,
                           x.initial_stop_target_usd,x.min_lots,x.step_lots,
                           x.stop_usd_per_min_lot)):
        raise ValueError("zero/negative volume or seed risk")
    if x.max_multiplier < 1 or x.native_cap < 1:
        raise ValueError("invalid volume multiplier cap")
    if (x.min_lots/x.step_lots).to_integral_value() != x.min_lots/x.step_lots:
        raise ValueError("min volume must align with broker step")
    if x.step_lots != x.min_lots:
        # This old engine still represents positions by integers of min_volume;
        # its exact active set must match legal increments for faithful sizing.
        raise ValueError("min_volume != volume_step requires broker adapter upgrade")


def _quote(motor: str, requested: D, lots: D, ctx: LotageContext, reason: str, cash: D) -> MotorQuote:
    return MotorQuote(
        motor=motor,requested_lots=requested,approved_lots=lots,
        approved_stop_usd=(lots/ctx.min_lots)*ctx.stop_usd_per_min_lot,
        free_cash_usd=cash,binding_reason=reason,
    )


def _floor_int(value: D) -> int:
    return max(0,int(value.to_integral_value(rounding=ROUND_FLOOR)))


def _cap(request: int, other: int) -> int:
    return max(0,min(request,other))


def sizing_lotage(ctx: LotageContext) -> MotorQuote:
    """Economic Sizing: grow the original $2.95 with realized account capital.

    This is a target, NOT permission to use dollars locked by open trades.
    """
    target=min(
        ctx.equity_usd*ctx.initial_stop_target_usd/ctx.initial_capital_usd,
        ctx.equity_usd*D("0.05"),ctx.risk_left_usd
    )
    wished=_floor_int(target/ctx.stop_usd_per_min_lot)
    permitted=_cap(wished,ctx.max_multiplier)
    reason="SIZING_STOP_BUDGET" if permitted<wished else "SIZING_TARGET"
    return _quote("SIZING",D(wished)*ctx.min_lots,D(permitted)*ctx.min_lots,ctx,reason,ctx.risk_left_usd)


def cibo_compound_lotage(ctx: LotageContext, prior: MotorQuote) -> MotorQuote:
    """BANK for MEDIUM only; Portfolio cushion owns ATTACK, never borrow BANK."""
    source=ctx.bank_free_usd if ctx.mode=="MEDIUM" else ctx.cushion_free_usd
    unit=ctx.stop_usd_per_min_lot+ctx.fee_usd_per_min_lot
    maxunits=_floor_int(source/unit)
    wanted=_floor_int(prior.approved_lots/ctx.min_lots)
    amount=_cap(wanted,maxunits)
    return _quote("CIBO_COMPOUND",prior.approved_lots,D(amount)*ctx.min_lots,
                  ctx,"BANK_CUSTODY_CAP" if amount<wanted else "COMPOUND_FUNDABLE",
                  source)


def portfolio_compound_lotage(ctx: LotageContext, prior: MotorQuote) -> MotorQuote:
    """Shared portfolio: total open-risk budget once; ATTACK cushion credit once."""
    available=(min(ctx.cushion_free_usd,ctx.portfolio_credit_free_usd)
               if ctx.mode=="ATTACK" else ctx.bank_free_usd)
    perunit=ctx.stop_usd_per_min_lot+ctx.fee_usd_per_min_lot
    max_source=_floor_int(available/perunit)
    max_total=_floor_int(ctx.risk_left_usd/ctx.stop_usd_per_min_lot)
    requested=_floor_int(prior.approved_lots/ctx.min_lots)
    approved=min(requested,max_source,max_total)
    reason="PORTFOLIO_SHARED_RISK_OR_CREDIT_CAP" if approved<requested else "PORTFOLIO_AVAILABLE"
    return _quote("COMPOUND_PORTFOLIO",prior.approved_lots,D(approved)*ctx.min_lots,ctx,reason,available)


def adaptive_leverage_lotage(ctx: LotageContext, prior: MotorQuote) -> MotorQuote:
    """Last authorization: broker min/max lot, native leverage cap, cash margin."""
    basecap=min(ctx.max_multiplier,ctx.native_cap)
    # An exchange requires funded margin in actual free funds. In H30 the
    # historical manifest is treated as a provider-model approximation only.
    cashmargin=(max(D(0),ctx.equity_usd-ctx.already_committed_margin_usd)
                if ctx.strict_account_cash_margin else ctx.margin_left_usd)
    feasible_margin=min(cashmargin,ctx.margin_left_usd)
    units_from_margin=(
        _floor_int(feasible_margin/ctx.margin_usd_per_min_lot)
        if ctx.margin_usd_per_min_lot>0 else basecap
    )
    wanted=_floor_int(prior.approved_lots/ctx.min_lots)
    approved=min(wanted,basecap,units_from_margin)
    reason=("MARGIN_FREE_CASH" if units_from_margin<min(wanted,basecap)
            else "NATIVE_OR_PROVIDER_CAP" if basecap<wanted
            else "LEVERAGE_APPROVED")
    return _quote("ADAPTIVE_LEVERAGE",prior.approved_lots,D(approved)*ctx.min_lots,ctx,reason,feasible_margin)


def coordinate_four_motor_lotage(ctx: LotageContext) -> CoordinatedLotage:
    _check(ctx)
    a=sizing_lotage(ctx)
    b=cibo_compound_lotage(ctx,a)
    c=portfolio_compound_lotage(ctx,b)
    d=adaptive_leverage_lotage(ctx,c)
    k=_floor_int(d.approved_lots/ctx.min_lots)
    target=min(ctx.equity_usd*ctx.initial_stop_target_usd/ctx.initial_capital_usd,
               ctx.equity_usd*D("0.05"))
    stop=D(k)*ctx.stop_usd_per_min_lot
    margin=D(k)*ctx.margin_usd_per_min_lot
    fees=D(k)*ctx.fee_usd_per_min_lot
    target_met=abs(stop-target)<=D("0.005")
    stages=(a,b,c,d)
    bindings=[x.binding_reason for x in stages
              if x.binding_reason not in ("SIZING_TARGET","COMPOUND_FUNDABLE",
                                          "PORTFOLIO_AVAILABLE","LEVERAGE_APPROVED")]
    # Fail closed; don't invent a nonzero position if source/margin unavailable.
    return CoordinatedLotage(
        selected_lots=d.approved_lots, selected_multiplier=k,
        selected_stop_usd=stop,selected_margin_usd=margin,selected_fees_usd=fees,
        requested_stop_usd=target,target_attained=target_met,
        all_stages=stages,binding_reason=";".join(bindings) if bindings else "FUNDED",
        funded=k>=1,minimum_lot_fundable=(
            ctx.stop_usd_per_min_lot+ctx.fee_usd_per_min_lot
            <= (ctx.bank_free_usd if ctx.mode=="MEDIUM" else min(ctx.cushion_free_usd,ctx.portfolio_credit_free_usd))
            and ctx.margin_usd_per_min_lot<=ctx.margin_left_usd
            and (not ctx.strict_account_cash_margin or ctx.margin_usd_per_min_lot<=max(D(0),ctx.equity_usd-ctx.already_committed_margin_usd))
        ),
    )
