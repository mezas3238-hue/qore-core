"""Passive CIBO CMA capital observation contract.

This module combines reconciled position economics with the CMA state machine and
emits an auditable observation. It has no order, sizing, or mutation authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_capital_state_machine import derive_stage
from qore.infrastructure.cibo_economic_floor import (
    EconomicFloorResult,
    ReconciledPositionEconomics,
    evaluate_economic_floor,
)


class CmaCapitalObservationError(ValueError):
    """Invalid passive CMA capital-observation evidence."""


@dataclass(frozen=True, slots=True)
class CmaCapitalObservationInput:
    trader_id: TraderLineage
    signal_fingerprint: str
    qore_symbol: str
    position_id: int
    seed_deployed: bool
    position_open: bool
    realized_net_pnl_usd: Decimal
    remaining_stop_worst_case_pnl_usd: Decimal | None
    future_cost_reserve_usd: Decimal
    slippage_reserve_usd: Decimal
    broker_position_reconciled: bool
    protection_reconciled: bool
    mutation_outcome_unknown: bool

    def __post_init__(self) -> None:
        if type(self.trader_id) is not TraderLineage:
            raise CmaCapitalObservationError("trader_id must be TraderLineage")
        if not self.signal_fingerprint:
            raise CmaCapitalObservationError("signal_fingerprint is required")
        if not self.qore_symbol:
            raise CmaCapitalObservationError("qore_symbol is required")
        if not isinstance(self.position_id, int) or isinstance(self.position_id, bool):
            raise CmaCapitalObservationError("position_id must be int")
        if self.position_id <= 0:
            raise CmaCapitalObservationError("position_id must be positive")
        for name in ("seed_deployed", "position_open", "broker_position_reconciled",
                     "protection_reconciled", "mutation_outcome_unknown"):
            if type(getattr(self, name)) is not bool:
                raise CmaCapitalObservationError(f"{name} must be bool")
        if not isinstance(self.realized_net_pnl_usd, Decimal):
            raise CmaCapitalObservationError("realized_net_pnl_usd must be Decimal")
        if not self.realized_net_pnl_usd.is_finite():
            raise CmaCapitalObservationError("realized_net_pnl_usd must be finite")
        if self.remaining_stop_worst_case_pnl_usd is not None:
            if (
                not isinstance(self.remaining_stop_worst_case_pnl_usd, Decimal)
                or not self.remaining_stop_worst_case_pnl_usd.is_finite()
            ):
                raise CmaCapitalObservationError(
                    "remaining_stop_worst_case_pnl_usd must be finite Decimal/null"
                )
        for name in ("future_cost_reserve_usd", "slippage_reserve_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CmaCapitalObservationError(
                    f"{name} must be finite non-negative Decimal"
                )


@dataclass(frozen=True, slots=True)
class CmaCapitalObservation:
    event: str
    trader: str
    symbol: str
    signal_fingerprint: str
    position_id: int
    stage: CapitalStage
    evidence_sufficient: bool
    expansion_eligible: bool
    realized_net_pnl_usd: Decimal
    remaining_stop_worst_case_pnl_usd: Decimal | None
    net_economic_floor_usd: Decimal | None
    base_capital_at_risk_usd: Decimal | None
    protected_open_floor_usd: Decimal | None
    self_financing_capacity_usd: Decimal | None
    reason: str

    def as_payload(self) -> dict[str, object]:
        return {
            "event": self.event,
            "trader": self.trader,
            "symbol": self.symbol,
            "signal_fingerprint": self.signal_fingerprint,
            "position_id": self.position_id,
            "stage": self.stage.value,
            "evidence_sufficient": self.evidence_sufficient,
            "expansion_eligible": self.expansion_eligible,
            "realized_net_pnl_usd": format(self.realized_net_pnl_usd, "f"),
            "remaining_stop_worst_case_pnl_usd": _fmt(
                self.remaining_stop_worst_case_pnl_usd
            ),
            "net_economic_floor_usd": _fmt(self.net_economic_floor_usd),
            "base_capital_at_risk_usd": _fmt(self.base_capital_at_risk_usd),
            "protected_open_floor_usd": _fmt(self.protected_open_floor_usd),
            "self_financing_capacity_usd": _fmt(
                self.self_financing_capacity_usd
            ),
            "reason": self.reason,
            "capital_management_authority": "CIBO_CMA",
            "mutation_authority": "NONE_OBSERVATIONAL",
        }


def observe_capital_state(
    evidence: CmaCapitalObservationInput,
) -> CmaCapitalObservation:
    """Build one fail-closed passive capital observation."""

    if not isinstance(evidence, CmaCapitalObservationInput):
        raise CmaCapitalObservationError(
            "evidence must be CmaCapitalObservationInput"
        )

    floor = _floor(evidence)
    stage_decision = derive_stage(
        seed_deployed=evidence.seed_deployed,
        position_open=evidence.position_open,
        floor=floor,
    )
    expansion_eligible = (
        floor.evidence_sufficient
        and stage_decision.expansion_eligible
        and not evidence.mutation_outcome_unknown
    )

    return CmaCapitalObservation(
        event="CIBO_CMA_CAPITAL_OBSERVATION",
        trader=evidence.trader_id.value,
        symbol=evidence.qore_symbol,
        signal_fingerprint=evidence.signal_fingerprint,
        position_id=evidence.position_id,
        stage=stage_decision.stage,
        evidence_sufficient=floor.evidence_sufficient,
        expansion_eligible=expansion_eligible,
        realized_net_pnl_usd=evidence.realized_net_pnl_usd,
        remaining_stop_worst_case_pnl_usd=(
            evidence.remaining_stop_worst_case_pnl_usd
        ),
        net_economic_floor_usd=floor.net_economic_floor_usd,
        base_capital_at_risk_usd=floor.base_capital_at_risk_usd,
        protected_open_floor_usd=floor.protected_open_floor_usd,
        self_financing_capacity_usd=floor.proven_self_financing_capacity_usd,
        reason=stage_decision.reason,
    )


def _floor(evidence: CmaCapitalObservationInput) -> EconomicFloorResult:
    if evidence.position_open and evidence.remaining_stop_worst_case_pnl_usd is None:
        return EconomicFloorResult(
            trader_id=evidence.trader_id,
            signal_fingerprint=evidence.signal_fingerprint,
            evidence_sufficient=False,
            realized_net_pnl_usd=None,
            net_economic_floor_usd=None,
            base_capital_at_risk_usd=None,
            protected_open_floor_usd=None,
            proven_self_financing_capacity_usd=None,
            base_recovered=False,
            reason="remaining stop worst-case evidence unavailable",
        )

    remaining = (
        evidence.remaining_stop_worst_case_pnl_usd
        if evidence.position_open
        else Decimal(0)
    )
    assert remaining is not None
    return evaluate_economic_floor(
        ReconciledPositionEconomics(
            trader_id=evidence.trader_id,
            signal_fingerprint=evidence.signal_fingerprint,
            realized_net_pnl_usd=evidence.realized_net_pnl_usd,
            remaining_stop_worst_case_pnl_usd=remaining,
            future_cost_reserve_usd=evidence.future_cost_reserve_usd,
            slippage_reserve_usd=evidence.slippage_reserve_usd,
            broker_position_reconciled=evidence.broker_position_reconciled,
            protection_reconciled=evidence.protection_reconciled,
            mutation_outcome_unknown=evidence.mutation_outcome_unknown,
        )
    )


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")
