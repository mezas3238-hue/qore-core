"""Bind reconciled live broker positions to CIBO CMA capital observations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_cma_capital_observation import (
    CmaCapitalObservation,
    CmaCapitalObservationInput,
    observe_capital_state,
)
from qore.infrastructure.cibo_cma_position_floor import (
    OpenPositionStopEvidence,
    evaluate_remaining_stop_floor,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementState


class CmaRealPositionBindingError(ValueError):
    """Live broker/settlement evidence is contradictory or unsafe."""


@dataclass(frozen=True, slots=True)
class CmaOpenPositionEvidence:
    trader_id: TraderLineage
    signal_fingerprint: str
    qore_symbol: str
    position_id: int
    side: str
    entry_price: Decimal
    current_stop: Decimal | None
    initial_volume: Decimal
    remaining_volume: Decimal
    tick_size: Decimal
    tick_value: Decimal
    broker_position_reconciled: bool
    broker_stop_reconciled: bool
    mutation_outcome_unknown: bool
    settlement_state: CmaSettlementState | None = None
    future_cost_reserve_usd: Decimal = Decimal(0)
    slippage_reserve_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if type(self.trader_id) is not TraderLineage:
            raise CmaRealPositionBindingError("trader_id must be TraderLineage")
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CmaRealPositionBindingError(
                "signal_fingerprint/qore_symbol required"
            )
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise CmaRealPositionBindingError("position_id must be positive int")
        if self.side not in {"long", "short"}:
            raise CmaRealPositionBindingError("side must be long/short")
        for name in (
            "entry_price",
            "initial_volume",
            "remaining_volume",
            "tick_size",
            "tick_value",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CmaRealPositionBindingError(
                    f"{name} must be finite positive Decimal"
                )
        if self.remaining_volume > self.initial_volume:
            raise CmaRealPositionBindingError(
                "remaining volume cannot exceed initial CMA seed volume"
            )
        if self.current_stop is not None and (
            not isinstance(self.current_stop, Decimal)
            or not self.current_stop.is_finite()
            or self.current_stop < 0
        ):
            raise CmaRealPositionBindingError(
                "current_stop must be finite non-negative Decimal/null"
            )
        for name in (
            "future_cost_reserve_usd",
            "slippage_reserve_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CmaRealPositionBindingError(
                    f"{name} must be finite non-negative Decimal"
                )
        for name in (
            "broker_position_reconciled",
            "broker_stop_reconciled",
            "mutation_outcome_unknown",
        ):
            if type(getattr(self, name)) is not bool:
                raise CmaRealPositionBindingError(f"{name} must be bool")
        if self.settlement_state is not None:
            if (
                self.settlement_state.signal_fingerprint
                != self.signal_fingerprint
                or self.settlement_state.position_id != self.position_id
            ):
                raise CmaRealPositionBindingError(
                    "settlement state identity mismatch"
                )
            if self.settlement_state.position_closed:
                raise CmaRealPositionBindingError(
                    "open position cannot use terminal settlement state"
                )


def observe_open_position(
    evidence: CmaOpenPositionEvidence,
) -> CmaCapitalObservation:
    """Produce one conservative CMA observation from live broker evidence."""

    if not isinstance(evidence, CmaOpenPositionEvidence):
        raise CmaRealPositionBindingError(
            "evidence must be CmaOpenPositionEvidence"
        )

    realized = (
        Decimal(0)
        if evidence.settlement_state is None
        else evidence.settlement_state.realized_net_pnl_usd
    )
    settlement_reconciled = not (
        evidence.remaining_volume < evidence.initial_volume
        and evidence.settlement_state is None
    )

    remaining_stop: Decimal | None = None
    protection_reconciled = False
    if evidence.current_stop is not None and evidence.current_stop > 0:
        stop_floor = evaluate_remaining_stop_floor(
            OpenPositionStopEvidence(
                side=evidence.side,
                entry_price=evidence.entry_price,
                current_stop=evidence.current_stop,
                remaining_volume=evidence.remaining_volume,
                tick_size=evidence.tick_size,
                tick_value=evidence.tick_value,
                broker_position_reconciled=evidence.broker_position_reconciled,
                broker_stop_reconciled=evidence.broker_stop_reconciled,
            )
        )
        if stop_floor.evidence_sufficient:
            remaining_stop = stop_floor.remaining_stop_worst_case_pnl_usd
            protection_reconciled = True

    return observe_capital_state(
        CmaCapitalObservationInput(
            trader_id=evidence.trader_id,
            signal_fingerprint=evidence.signal_fingerprint,
            qore_symbol=evidence.qore_symbol,
            position_id=evidence.position_id,
            seed_deployed=True,
            position_open=True,
            realized_net_pnl_usd=realized,
            remaining_stop_worst_case_pnl_usd=remaining_stop,
            future_cost_reserve_usd=evidence.future_cost_reserve_usd,
            slippage_reserve_usd=evidence.slippage_reserve_usd,
            broker_position_reconciled=evidence.broker_position_reconciled,
            protection_reconciled=protection_reconciled,
            mutation_outcome_unknown=evidence.mutation_outcome_unknown,
            settlement_reconciled=settlement_reconciled,
        )
    )


def observe_closed_position(
    *,
    trader_id: TraderLineage,
    qore_symbol: str,
    settlement_state: CmaSettlementState,
    future_cost_reserve_usd: Decimal = Decimal(0),
    slippage_reserve_usd: Decimal = Decimal(0),
    mutation_outcome_unknown: bool = False,
) -> CmaCapitalObservation:
    """Close the CMA lifecycle only from a terminal reconciled settlement."""

    if not isinstance(settlement_state, CmaSettlementState):
        raise CmaRealPositionBindingError(
            "settlement_state must be CmaSettlementState"
        )
    if not settlement_state.position_closed:
        raise CmaRealPositionBindingError(
            "closed position requires terminal exit settlement"
        )

    return observe_capital_state(
        CmaCapitalObservationInput(
            trader_id=trader_id,
            signal_fingerprint=settlement_state.signal_fingerprint,
            qore_symbol=qore_symbol,
            position_id=settlement_state.position_id,
            seed_deployed=True,
            position_open=False,
            realized_net_pnl_usd=settlement_state.realized_net_pnl_usd,
            remaining_stop_worst_case_pnl_usd=None,
            future_cost_reserve_usd=future_cost_reserve_usd,
            slippage_reserve_usd=slippage_reserve_usd,
            broker_position_reconciled=True,
            protection_reconciled=True,
            mutation_outcome_unknown=mutation_outcome_unknown,
            settlement_reconciled=True,
        )
    )
