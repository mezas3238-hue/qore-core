"""Economic-floor and base-capital recovery engine for CIBO CMA.

The engine converts reconciled position economics into conservative capital facts.
It never treats positive floating PnL as protected capacity unless that PnL is
already guaranteed by a broker-confirmed protection state expressed through the
remaining worst-case PnL input.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import CiboCapitalState


class EconomicFloorError(ValueError):
    """Position-economic evidence is invalid or unreconciled."""


@dataclass(frozen=True, slots=True)
class ReconciledPositionEconomics:
    trader_id: TraderLineage
    signal_fingerprint: str
    realized_net_pnl_usd: Decimal
    remaining_stop_worst_case_pnl_usd: Decimal
    future_cost_reserve_usd: Decimal
    slippage_reserve_usd: Decimal
    broker_position_reconciled: bool
    protection_reconciled: bool
    mutation_outcome_unknown: bool = False

    def __post_init__(self) -> None:
        if type(self.trader_id) is not TraderLineage:
            raise EconomicFloorError("trader_id must be TraderLineage")
        if not self.signal_fingerprint:
            raise EconomicFloorError("signal_fingerprint is required")
        for name in (
            "realized_net_pnl_usd",
            "remaining_stop_worst_case_pnl_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise EconomicFloorError(f"{name} must be finite Decimal")
        for name in ("future_cost_reserve_usd", "slippage_reserve_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise EconomicFloorError(f"{name} must be finite non-negative")
        for name in (
            "broker_position_reconciled",
            "protection_reconciled",
            "mutation_outcome_unknown",
        ):
            if type(getattr(self, name)) is not bool:
                raise EconomicFloorError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class EconomicFloorResult:
    trader_id: TraderLineage
    signal_fingerprint: str
    evidence_sufficient: bool
    realized_net_pnl_usd: Decimal | None
    net_economic_floor_usd: Decimal | None
    base_capital_at_risk_usd: Decimal | None
    protected_open_floor_usd: Decimal | None
    proven_self_financing_capacity_usd: Decimal | None
    base_recovered: bool
    reason: str


def evaluate_economic_floor(
    economics: ReconciledPositionEconomics,
) -> EconomicFloorResult:
    """Return conservative floor; fail closed when position/protection is unreconciled."""

    if not isinstance(economics, ReconciledPositionEconomics):
        raise EconomicFloorError("economics must be ReconciledPositionEconomics")

    if economics.mutation_outcome_unknown:
        return _insufficient(economics, "mutation outcome unknown")
    if not economics.broker_position_reconciled:
        return _insufficient(economics, "broker position not reconciled")
    if not economics.protection_reconciled:
        return _insufficient(economics, "protection state not reconciled")

    reserves = economics.future_cost_reserve_usd + economics.slippage_reserve_usd
    net_floor = (
        economics.realized_net_pnl_usd
        + economics.remaining_stop_worst_case_pnl_usd
        - reserves
    )
    base_at_risk = max(Decimal(0), -net_floor)
    protected_open = max(
        Decimal(0),
        economics.remaining_stop_worst_case_pnl_usd,
    )
    self_financing = max(Decimal(0), net_floor)

    return EconomicFloorResult(
        trader_id=economics.trader_id,
        signal_fingerprint=economics.signal_fingerprint,
        evidence_sufficient=True,
        realized_net_pnl_usd=economics.realized_net_pnl_usd,
        net_economic_floor_usd=net_floor,
        base_capital_at_risk_usd=base_at_risk,
        protected_open_floor_usd=protected_open,
        proven_self_financing_capacity_usd=self_financing,
        base_recovered=net_floor >= 0,
        reason=(
            "base capital economically recovered"
            if net_floor >= 0
            else "base capital remains exposed at reconciled worst-case floor"
        ),
    )


def _insufficient(
    economics: ReconciledPositionEconomics,
    reason: str,
) -> EconomicFloorResult:
    return EconomicFloorResult(
        trader_id=economics.trader_id,
        signal_fingerprint=economics.signal_fingerprint,
        evidence_sufficient=False,
        realized_net_pnl_usd=None,
        net_economic_floor_usd=None,
        base_capital_at_risk_usd=None,
        protected_open_floor_usd=None,
        proven_self_financing_capacity_usd=None,
        base_recovered=False,
        reason=reason,
    )



def build_cibo_capital_state(
    result: EconomicFloorResult,
    *,
    assigned_capital_usd: Decimal,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    reserved_expansion_risk_usd: Decimal = Decimal(0),
    cost_reserve_usd: Decimal = Decimal(0),
) -> CiboCapitalState:
    """Promote only sufficient reconciled floor evidence into CMA capital state."""

    if not isinstance(result, EconomicFloorResult):
        raise EconomicFloorError("result must be EconomicFloorResult")
    if not result.evidence_sufficient:
        raise EconomicFloorError("insufficient floor evidence cannot create capital state")
    if (
        result.base_capital_at_risk_usd is None
        or result.protected_open_floor_usd is None
        or result.proven_self_financing_capacity_usd is None
        or result.realized_net_pnl_usd is None
    ):
        raise EconomicFloorError("sufficient floor result missing required economics")

    return CiboCapitalState(
        assigned_capital_usd=assigned_capital_usd,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        base_capital_at_risk_usd=result.base_capital_at_risk_usd,
        realized_net_profit_usd=max(Decimal(0), result.realized_net_pnl_usd),
        protected_open_economic_floor_usd=result.protected_open_floor_usd,
        proven_self_financing_capacity_usd=result.proven_self_financing_capacity_usd,
        reserved_expansion_risk_usd=reserved_expansion_risk_usd,
        cost_reserve_usd=cost_reserve_usd,
    )
