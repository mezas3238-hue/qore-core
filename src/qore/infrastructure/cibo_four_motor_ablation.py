"""Five-arm four-motor leave-one-out *capacity* ablation, SHADOW research only.

Same signal, QORE NAV, broker costs, broker minimum and account epoch for
control + 4 ablations. This is NOT realized PnL, MT5 execution or a DD study;
those require authenticated fills and a chronological broker market replay.
No credit is given to a motor with a tied/nonbinding limit.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from qore.infrastructure.cibo_four_motor_policy import (
    FourMotorObservation, FourMotorProposal, FourMotorPolicyError, ZERO, positive,
)
from qore.infrastructure.cibo_account_sizing_authority import propose_p0_sizing_vote
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote

NAMES = ("SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND")


@dataclass(frozen=True, slots=True)
class ShadowCapacityArm:
    removed_motor: str | None
    potential_lots: Decimal
    potential_risk_usd: Decimal
    funding_state: str
    binding_constraints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ShadowMotorAblation:
    request_id: str
    arms: tuple[ShadowCapacityArm, ...]
    incremental_lots_if_disabled: tuple[tuple[str, Decimal], ...]
    # No profit/DD attribution until full broker-causal outcome replay exists.
    pnl_attributed: bool = False
    drawdown_attributed: bool = False


def ablate_four_motors(
    observation: FourMotorObservation, *,
    minimum_lot: Decimal, lot_step: Decimal,
) -> ShadowMotorAblation:
    if not isinstance(observation, FourMotorObservation):
        raise FourMotorPolicyError("causal observation required")
    positive("minimum_lot", minimum_lot)
    positive("lot_step", lot_step)
    # No broker quote/cost or market sequence is manufactured here.
    all_in = observation.full_stop_cost_per_lot_usd
    positive("all_in_loss_per_lot", all_in)
    proposals = {
        v.producer: v for v in (
            propose_p0_sizing_vote(observation),
            propose_p0_compound_vote(observation),
            propose_p0_adaptive_leverage_vote(observation),
            propose_p0_portfolio_vote(observation),
        )
    }
    legal_min = (minimum_lot / lot_step).to_integral_value(rounding=ROUND_CEILING) * lot_step
    margin_free = max(ZERO, observation.broker_free_margin_usd -
                      observation.broker_margin_reservations_usd)
    directional = max(ZERO, min(observation.symbol_max_lots,
                               observation.provider_direction_max_lots)
                      - observation.open_and_reserved_direction_lots)
    arms: list[ShadowCapacityArm] = []
    for removed in (None, *NAMES):
        risk_caps = {
            "QORE_5PCT": observation.base_entry_budget_usd,
            "UNPROTECTED_CAPITAL": observation.risk_cash_remaining_usd,
            "SOURCE_UNRESERVED": observation.source_available_usd,
            "SIZING": Decimal(proposals["SIZING"].limits["approved_risk_usd"])
                      if removed != "SIZING" else observation.base_entry_budget_usd,
            "CIBO_COMPOUND": Decimal(proposals["CIBO_COMPOUND"].limits["approved_risk_usd"])
                             if removed != "CIBO_COMPOUND" else observation.base_entry_budget_usd,
            "PORTFOLIO_COMPOUND": Decimal(proposals["PORTFOLIO_COMPOUND"].limits["approved_source_funds_usd"])
                                  if removed != "PORTFOLIO_COMPOUND" else observation.source_available_usd,
        }
        margin = (Decimal(proposals["ADAPTIVE_LEVERAGE"].limits["approved_margin_usd"])
                  if removed != "ADAPTIVE_LEVERAGE" else margin_free)
        lots = (Decimal(proposals["ADAPTIVE_LEVERAGE"].limits["approved_max_lots"])
                if removed != "ADAPTIVE_LEVERAGE" else directional)
        physical_caps = {
            "BROKER_DIRECTIONAL": directional,
            "BROKER_UNRESERVED_MARGIN": margin_free / observation.broker_margin_usd_per_lot,
            "ADAPTIVE_MARGIN": margin / observation.broker_margin_usd_per_lot,
            "ADAPTIVE_LOTS": lots,
        }
        caps = {**{k: v / all_in for k, v in risk_caps.items()}, **physical_caps}
        limiting = min(caps.values())
        quantized = max(ZERO, (limiting / lot_step).to_integral_value(rounding=ROUND_FLOOR) * lot_step)
        funded = quantized >= legal_min
        binding = tuple(sorted(k for k, v in caps.items() if v == limiting))
        arms.append(ShadowCapacityArm(
            removed_motor=removed, potential_lots=quantized if funded else ZERO,
            potential_risk_usd=quantized * all_in if funded else ZERO,
            funding_state="SYNTHETIC_POTENTIAL" if funded else "SYNTHETIC_UNFUNDABLE",
            binding_constraints=binding,
        ))
    baseline = arms[0].potential_lots
    deltas = tuple((name, arms[i+1].potential_lots - baseline)
                   for i, name in enumerate(NAMES))
    if any(delta < ZERO for _, delta in deltas):
        raise FourMotorPolicyError("removing an economic cap cannot decrease potential size")
    return ShadowMotorAblation(observation.request_id, tuple(arms), deltas)
