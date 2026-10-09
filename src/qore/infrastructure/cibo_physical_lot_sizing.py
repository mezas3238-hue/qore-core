"""CIBO per-entry physical lot sizing (research, no order authority).

All four economic engines share one Decimal lot grid. The Trader supplies entry
geometry; CIBO sizes post-decision, subject to explicit, real broker constraints.
This pure module never mutates a broker or represents an unfundable position as
executed. Net stop loss includes provider costs and adverse-fill allowance.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext


class CiboLotSizingError(ValueError):
    """Invalid physical contract or money source: fail closed."""


def _value(name: str, value: Decimal, *, allow_zero: bool = False) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboLotSizingError(f"{name} must be finite Decimal")
    if value < 0 or (value == 0 and not allow_zero):
        raise CiboLotSizingError(
            f"{name} must be {'nonnegative' if allow_zero else 'positive'}"
        )
    return value


def stop_loss_usd_per_lot(
    *, entry_price: Decimal, stop_price: Decimal,
    tick_size: Decimal, tick_value_usd_per_lot: Decimal,
) -> Decimal:
    """Convert broker-confirmed price/tick economics to USD per whole lot.

    Tick value must already be in account USD at the evaluated instant; never
    reuse a different symbol's or a stale quote's tick value.
    """
    _value("entry_price", entry_price)
    _value("stop_price", stop_price)
    _value("tick_size", tick_size)
    _value("tick_value_usd_per_lot", tick_value_usd_per_lot)
    if entry_price == stop_price:
        raise CiboLotSizingError("entry and stop cannot coincide")
    with localcontext() as ctx:
        ctx.prec = 100
        return abs(entry_price - stop_price) / tick_size * tick_value_usd_per_lot


@dataclass(frozen=True, slots=True)
class CiboLotSizingInput:
    requested_loss_budget_usd: Decimal
    stop_risk_usd_per_lot: Decimal
    provider_cost_usd_per_lot: Decimal
    margin_usd_per_lot: Decimal
    broker_min_lot: Decimal
    broker_max_lot: Decimal
    broker_lot_step: Decimal
    sizing_risk_cap_usd: Decimal
    cibo_compound_risk_cap_usd: Decimal
    portfolio_unreserved_cash_usd: Decimal
    sovereign_unreserved_cash_usd: Decimal
    source_lane: str
    leverage_available_margin_usd: Decimal
    sovereign_unreserved_risk_usd: Decimal
    leverage_max_lots: Decimal
    requested_target_lots: Decimal | None = None

    def __post_init__(self) -> None:
        for name in (
            "requested_loss_budget_usd", "stop_risk_usd_per_lot",
            "margin_usd_per_lot", "broker_min_lot", "broker_max_lot",
            "broker_lot_step", "leverage_max_lots",
        ):
            _value(name, getattr(self, name))
        for name in (
            "provider_cost_usd_per_lot", "sizing_risk_cap_usd",
            "cibo_compound_risk_cap_usd", "portfolio_unreserved_cash_usd",
            "sovereign_unreserved_cash_usd", "leverage_available_margin_usd",
            "sovereign_unreserved_risk_usd",
        ):
            _value(name, getattr(self, name), allow_zero=True)
        if self.requested_target_lots is not None:
            _value("requested_target_lots", self.requested_target_lots)
        if self.source_lane not in {"SOVEREIGN_BANK", "PORTFOLIO_CUSHION"}:
            raise CiboLotSizingError("source_lane must be a physical treasury source")
        if self.broker_min_lot > self.broker_max_lot:
            raise CiboLotSizingError("broker minimum lot exceeds maximum lot")


@dataclass(frozen=True, slots=True)
class CiboLotSizingDecision:
    status: str
    lots: Decimal
    requested_loss_budget_usd: Decimal
    stop_risk_usd: Decimal
    all_in_loss_if_stopped_usd: Decimal
    provider_cost_usd: Decimal
    margin_required_usd: Decimal
    physical_min_lots: Decimal
    engine_max_lots: tuple[tuple[str, Decimal], ...]
    binding_constraints: tuple[str, ...]


def compute_cibo_lot_sizing(spec: CiboLotSizingInput) -> CiboLotSizingDecision:
    """Quantize every engine's independent physical ceiling to broker steps.

    SIZING and CIBO_COMPOUND propose *risk USD*; PORTFOLIO provides unreserved
    money for stop+cost; ADAPTIVE_LEVERAGE provides actual free margin and its
    authorized maximum volume; QORE_RISK provides a hard stop-risk ceiling.
    MEDIUM chooses the actual sovereign bank, ATTACK the actual cushion;
    unused money in another lane is NOT fungible without authorized atomic
    transfer. These are upper bounds, not balances to sum.
    """
    if not isinstance(spec, CiboLotSizingInput):
        raise CiboLotSizingError("CiboLotSizingInput required")
    with localcontext() as ctx:
        ctx.prec = 100
        effective_loss_per_lot = (
            spec.stop_risk_usd_per_lot + spec.provider_cost_usd_per_lot
        )
        step = spec.broker_lot_step
        minimum_lots = (
            (spec.broker_min_lot / step).to_integral_value(rounding=ROUND_CEILING)
            * step
        )

        def quantized(amount: Decimal) -> Decimal:
            return max(
                Decimal(0),
                (amount / step).to_integral_value(rounding=ROUND_FLOOR) * step,
            )

        source_usd = (
            spec.sovereign_unreserved_cash_usd
            if spec.source_lane == "SOVEREIGN_BANK"
            else spec.portfolio_unreserved_cash_usd
        )
        source_code = (
            "SOVEREIGN_BANK"
            if spec.source_lane == "SOVEREIGN_BANK"
            else "COMPOUND_PORTFOLIO"
        )
        caps = (
            ("REQUESTED_USD", quantized(
                spec.requested_loss_budget_usd / effective_loss_per_lot
            )),
            ("SIZING", quantized(
                spec.sizing_risk_cap_usd / effective_loss_per_lot
            )),
            ("CIBO_COMPOUND", quantized(
                spec.cibo_compound_risk_cap_usd / effective_loss_per_lot
            )),
            (source_code, quantized(
                source_usd / effective_loss_per_lot
            )),
            ("ADAPTIVE_LEVERAGE_MARGIN", quantized(
                spec.leverage_available_margin_usd / spec.margin_usd_per_lot
            )),
            ("ADAPTIVE_LEVERAGE_MAX", quantized(spec.leverage_max_lots)),
            ("QORE_RISK", quantized(
                spec.sovereign_unreserved_risk_usd / effective_loss_per_lot
            )),
            ("BROKER_MAX", quantized(spec.broker_max_lot)),
        )
        if spec.requested_target_lots is not None:
            # A target is a ceiling, not permission to evade risk or margin.
            caps += (("REQUESTED_TARGET_LOTS", quantized(spec.requested_target_lots)),)
        candidate = min(v for _, v in caps)
        binding = tuple(name for name, limit in caps if limit == candidate)
        if candidate < minimum_lots:
            return CiboLotSizingDecision(
                status="UNFUNDABLE_BROKER_MINIMUM",
                lots=Decimal(0),
                requested_loss_budget_usd=spec.requested_loss_budget_usd,
                stop_risk_usd=Decimal(0),
                all_in_loss_if_stopped_usd=Decimal(0),
                provider_cost_usd=Decimal(0),
                margin_required_usd=Decimal(0),
                physical_min_lots=minimum_lots,
                engine_max_lots=caps,
                binding_constraints=binding,
            )
        stop_loss = candidate * spec.stop_risk_usd_per_lot
        cost = candidate * spec.provider_cost_usd_per_lot
        all_in_loss = stop_loss + cost
        margin = candidate * spec.margin_usd_per_lot
        if (
            all_in_loss > spec.requested_loss_budget_usd
            or all_in_loss > spec.sizing_risk_cap_usd
            or all_in_loss > spec.cibo_compound_risk_cap_usd
            or all_in_loss > source_usd
            or all_in_loss > spec.sovereign_unreserved_risk_usd
            or margin > spec.leverage_available_margin_usd
            or candidate > spec.leverage_max_lots
            or candidate > spec.broker_max_lot
        ):
            raise CiboLotSizingError("lot-grid sizing physical invariant failed")
        return CiboLotSizingDecision(
            status="FUNDED_PROPOSAL_NOT_EXECUTION",
            lots=candidate,
            requested_loss_budget_usd=spec.requested_loss_budget_usd,
            stop_risk_usd=stop_loss,
            all_in_loss_if_stopped_usd=all_in_loss,
            provider_cost_usd=cost,
            margin_required_usd=margin,
            physical_min_lots=minimum_lots,
            engine_max_lots=caps,
            binding_constraints=binding,
        )


def quote_cibo_trader_opportunity_lots(
    opportunity: object,
    *,
    requested_loss_budget_usd: Decimal,
    provider_cost_usd_per_lot: Decimal,
    sizing_risk_cap_usd: Decimal,
    cibo_compound_risk_cap_usd: Decimal,
    portfolio_unreserved_cash_usd: Decimal,
    sovereign_unreserved_cash_usd: Decimal,
    source_lane: str,
    leverage_available_margin_usd: Decimal,
    sovereign_unreserved_risk_usd: Decimal,
    leverage_max_lots: Decimal,
    requested_target_lots: Decimal | None = None,
) -> CiboLotSizingDecision:
    """Bridge actual TraderOpportunityEnvelope economics to shared calculator.

    Every input reflects a causal, contemporary preexecution account snapshot;
    no historical profit, implicit bank/cushion loan or unverified tick value.
    It honors methodology minimum_execution_steps from the Trader envelope.
    """
    from qore.infrastructure.cibo_capital_management_authority import (
        TraderOpportunityEnvelope,
        minimum_seed_volume,
    )

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboLotSizingError("a verified TraderOpportunityEnvelope is required")
    return compute_cibo_lot_sizing(
        CiboLotSizingInput(
            requested_loss_budget_usd=requested_loss_budget_usd,
            stop_risk_usd_per_lot=opportunity.stop_loss_per_volume,
            provider_cost_usd_per_lot=provider_cost_usd_per_lot,
            margin_usd_per_lot=opportunity.margin_per_volume,
            broker_min_lot=minimum_seed_volume(opportunity),
            broker_max_lot=opportunity.maximum_volume,
            broker_lot_step=opportunity.volume_step,
            sizing_risk_cap_usd=sizing_risk_cap_usd,
            cibo_compound_risk_cap_usd=cibo_compound_risk_cap_usd,
            portfolio_unreserved_cash_usd=portfolio_unreserved_cash_usd,
            sovereign_unreserved_cash_usd=sovereign_unreserved_cash_usd,
            source_lane=source_lane,
            leverage_available_margin_usd=leverage_available_margin_usd,
            sovereign_unreserved_risk_usd=sovereign_unreserved_risk_usd,
            leverage_max_lots=leverage_max_lots,
            requested_target_lots=requested_target_lots,
        )
    )
