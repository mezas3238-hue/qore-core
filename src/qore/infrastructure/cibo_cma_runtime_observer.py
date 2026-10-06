"""Passive runtime coordinator for CIBO CMA Phase 7/8.

This module binds one broker-reconciled position to:
- durable realized-settlement evidence;
- the real-position economic-floor engine; and
- the durable CMA lifecycle state machine.

It emits observations only. It never creates expansion orders or mutates broker state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.cibo_cma_lifecycle_store import DurableCmaLifecycleStore
from qore.infrastructure.cibo_cma_real_position_binding import (
    CmaOpenPositionEvidence,
    observe_open_position,
)
from qore.infrastructure.cibo_cma_settlement_store import DurableCmaSettlementStore


class CmaRuntimeObserverError(ValueError):
    """Runtime evidence cannot be bound safely to one CMA capital journey."""


@dataclass(frozen=True, slots=True)
class CmaRuntimePositionSnapshot:
    trader_id: TraderLineage
    signal_fingerprint: str
    qore_symbol: str
    position_id: int
    registry_leg_count: int
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
    observed_at: datetime
    future_cost_reserve_usd: Decimal = Decimal(0)
    slippage_reserve_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if type(self.trader_id) is not TraderLineage:
            raise CmaRuntimeObserverError("trader_id must be TraderLineage")
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CmaRuntimeObserverError(
                "signal_fingerprint/qore_symbol required"
            )
        if (
            not isinstance(self.registry_leg_count, int)
            or isinstance(self.registry_leg_count, bool)
            or self.registry_leg_count < 1
        ):
            raise CmaRuntimeObserverError(
                "registry_leg_count must be positive int"
            )
        if (
            not isinstance(self.observed_at, datetime)
            or self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CmaRuntimeObserverError(
                "observed_at must be timezone-aware"
            )


@dataclass(frozen=True, slots=True)
class CmaRuntimeObservationResult:
    observation: CmaCapitalObservation | None
    lifecycle_stage: CapitalStage | None
    failure_payload: dict[str, object] | None

    def __post_init__(self) -> None:
        present = sum(
            item is not None
            for item in (self.observation, self.failure_payload)
        )
        if present != 1:
            raise CmaRuntimeObserverError(
                "exactly one observation/failure payload is required"
            )


def observe_runtime_position(
    snapshot: CmaRuntimePositionSnapshot,
    *,
    settlement_store: DurableCmaSettlementStore,
    lifecycle_store: DurableCmaLifecycleStore,
) -> CmaRuntimeObservationResult:
    """Observe one open position and persist its CMA stage fail-closed."""

    if not isinstance(snapshot, CmaRuntimePositionSnapshot):
        raise CmaRuntimeObserverError(
            "snapshot must be CmaRuntimePositionSnapshot"
        )
    if not isinstance(settlement_store, DurableCmaSettlementStore):
        raise CmaRuntimeObserverError(
            "settlement_store must be DurableCmaSettlementStore"
        )
    if not isinstance(lifecycle_store, DurableCmaLifecycleStore):
        raise CmaRuntimeObserverError(
            "lifecycle_store must be DurableCmaLifecycleStore"
        )

    if snapshot.registry_leg_count != 1:
        return CmaRuntimeObservationResult(
            observation=None,
            lifecycle_stage=None,
            failure_payload={
                "event": "CIBO_CMA_CAPITAL_OBSERVATION_FAIL_CLOSED",
                "trader": snapshot.trader_id.value,
                "symbol": snapshot.qore_symbol,
                "signal_fingerprint": snapshot.signal_fingerprint,
                "position_id": snapshot.position_id,
                "reason": "NETTED_MULTI_LEG_POSITION_REQUIRES_ALLOCATION_DECOMPOSITION",
                "registry_leg_count": snapshot.registry_leg_count,
                "capital_management_authority": "CIBO_CMA",
                "mutation_authority": "NONE_OBSERVATIONAL",
            },
        )

    settlement_book = settlement_store.load()
    settlement_state = settlement_book.state_for(
        signal_fingerprint=snapshot.signal_fingerprint,
        position_id=snapshot.position_id,
    )
    observation = observe_open_position(
        CmaOpenPositionEvidence(
            trader_id=snapshot.trader_id,
            signal_fingerprint=snapshot.signal_fingerprint,
            qore_symbol=snapshot.qore_symbol,
            position_id=snapshot.position_id,
            side=snapshot.side,
            entry_price=snapshot.entry_price,
            current_stop=snapshot.current_stop,
            initial_volume=snapshot.initial_volume,
            remaining_volume=snapshot.remaining_volume,
            tick_size=snapshot.tick_size,
            tick_value=snapshot.tick_value,
            broker_position_reconciled=snapshot.broker_position_reconciled,
            broker_stop_reconciled=snapshot.broker_stop_reconciled,
            mutation_outcome_unknown=snapshot.mutation_outcome_unknown,
            settlement_state=settlement_state,
            future_cost_reserve_usd=snapshot.future_cost_reserve_usd,
            slippage_reserve_usd=snapshot.slippage_reserve_usd,
        )
    )

    lifecycle_book = lifecycle_store.load()
    lifecycle = lifecycle_book.record_for(
        signal_fingerprint=snapshot.signal_fingerprint,
        position_id=snapshot.position_id,
    )
    if lifecycle is None:
        lifecycle_book = lifecycle_store.register_seed(
            signal_fingerprint=snapshot.signal_fingerprint,
            position_id=snapshot.position_id,
            observed_at=snapshot.observed_at,
            expected_generation=lifecycle_book.generation,
        )
        lifecycle = lifecycle_book.record_for(
            signal_fingerprint=snapshot.signal_fingerprint,
            position_id=snapshot.position_id,
        )
        assert lifecycle is not None

    if lifecycle.stage is CapitalStage.MINIMAL_SEED:
        lifecycle_book = lifecycle_store.advance(
            signal_fingerprint=snapshot.signal_fingerprint,
            position_id=snapshot.position_id,
            target_stage=CapitalStage.OBSERVE,
            observed_at=snapshot.observed_at,
            expected_generation=lifecycle_book.generation,
        )
        lifecycle = lifecycle_book.record_for(
            signal_fingerprint=snapshot.signal_fingerprint,
            position_id=snapshot.position_id,
        )
        assert lifecycle is not None

    if lifecycle.stage is not observation.stage:
        lifecycle_book = lifecycle_store.advance(
            signal_fingerprint=snapshot.signal_fingerprint,
            position_id=snapshot.position_id,
            target_stage=observation.stage,
            observed_at=snapshot.observed_at,
            expected_generation=lifecycle_book.generation,
        )
        lifecycle = lifecycle_book.record_for(
            signal_fingerprint=snapshot.signal_fingerprint,
            position_id=snapshot.position_id,
        )
        assert lifecycle is not None

    return CmaRuntimeObservationResult(
        observation=observation,
        lifecycle_stage=lifecycle.stage,
        failure_payload=None,
    )
