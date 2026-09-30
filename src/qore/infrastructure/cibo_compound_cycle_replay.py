"""Single chronological runner for the integrated CIBO compound cycle.

The runner orchestrates existing accounting/protection/GEN-C6/T19 operations.
It does not define a new capital policy. Events must already contain causal
pre-outcome decisions where applicable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TypeAlias

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementState
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_cycle_audit import (
    CompoundCycleReconciliation,
    reconcile_compound_cycle,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    CiboCompoundCycleState,
    classify_compound_capital,
    ingest_base_settlement,
    policy_protect_floor,
    protect_compound_capital,
)
from qore.infrastructure.cibo_compound_market_cycle import (
    apply_internal_capital_market_decision,
    settle_compound_deployment,
)
from qore.infrastructure.cibo_internal_capital_market import (
    CapitalScarcityEvent,
    Genc6InternalCapitalMarketDecision,
)


@dataclass(frozen=True, slots=True)
class BaseSettlementEvent:
    event_id: str
    occurred_at: datetime
    trader_id: TraderLineage
    settlement: CmaSettlementState


@dataclass(frozen=True, slots=True)
class ClassificationEvent:
    event_id: str
    occurred_at: datetime
    source_lot_id: str
    to_state: CompoundCapitalState
    amount_usd: Decimal


@dataclass(frozen=True, slots=True)
class ProtectProfitEvent:
    event_id: str
    occurred_at: datetime
    source_lot_id: str
    amount_usd: Decimal


@dataclass(frozen=True, slots=True)
class PolicyProtectFloorEvent:
    event_id: str
    occurred_at: datetime
    tranche_id: str
    policy_id: str
    policy_sha256: str


@dataclass(frozen=True, slots=True)
class InternalCapitalMarketEvent:
    event_id: str
    scarcity_event: CapitalScarcityEvent
    decision: Genc6InternalCapitalMarketDecision
    source_lot_id: str | None = None

    @property
    def occurred_at(self) -> datetime:
        return self.decision.decision_at


@dataclass(frozen=True, slots=True)
class CompoundDeploymentSettlementEvent:
    event_id: str
    occurred_at: datetime
    deployment_id: str
    settlement: CmaSettlementState


CompoundCycleEvent: TypeAlias = (
    BaseSettlementEvent
    | ClassificationEvent
    | ProtectProfitEvent
    | PolicyProtectFloorEvent
    | InternalCapitalMarketEvent
    | CompoundDeploymentSettlementEvent
)


@dataclass(frozen=True, slots=True)
class CompoundCycleReplayResult:
    final_state: CiboCompoundCycleState
    reconciliation: CompoundCycleReconciliation
    event_count: int
    chronological: bool = True
    future_leakage_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.final_state, CiboCompoundCycleState):
            raise CiboCompoundCapitalError(
                "compound replay result state is invalid"
            )
        if not isinstance(
            self.reconciliation,
            CompoundCycleReconciliation,
        ):
            raise CiboCompoundCapitalError(
                "compound replay result reconciliation is invalid"
            )
        if (
            not isinstance(self.event_count, int)
            or isinstance(self.event_count, bool)
            or self.event_count <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound replay event count must be positive"
            )
        if (
            not self.chronological
            or self.future_leakage_used
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "compound replay governance/causality drift"
            )


def replay_compound_cycle(
    *,
    initial_state: CiboCompoundCycleState,
    events: tuple[CompoundCycleEvent, ...],
) -> CompoundCycleReplayResult:
    """Apply one exact ordered event stream and reconcile the resulting capital."""

    if not isinstance(initial_state, CiboCompoundCycleState):
        raise CiboCompoundCapitalError(
            "compound replay requires canonical initial state"
        )
    if not isinstance(events, tuple) or not events:
        raise CiboCompoundCapitalError(
            "compound replay requires non-empty event tuple"
        )

    state = initial_state
    previous_at = initial_state.last_event_at
    seen: set[str] = set()
    for event in events:
        if not isinstance(
            event,
            (
                BaseSettlementEvent,
                ClassificationEvent,
                ProtectProfitEvent,
                PolicyProtectFloorEvent,
                InternalCapitalMarketEvent,
                CompoundDeploymentSettlementEvent,
            ),
        ):
            raise CiboCompoundCapitalError(
                "compound replay event type is invalid"
            )
        if not event.event_id or event.event_id in seen:
            raise CiboCompoundCapitalError(
                "compound replay event id is missing or duplicated"
            )
        occurred_at = event.occurred_at
        if previous_at is not None and occurred_at < previous_at:
            raise CiboCompoundCapitalError(
                "compound replay input chronology is reversed"
            )
        seen.add(event.event_id)
        previous_at = occurred_at
        state = _apply(state, event)

    return CompoundCycleReplayResult(
        final_state=state,
        reconciliation=reconcile_compound_cycle(state),
        event_count=len(events),
        chronological=True,
        future_leakage_used=False,
        productive_authority=False,
    )


def _apply(
    state: CiboCompoundCycleState,
    event: CompoundCycleEvent,
) -> CiboCompoundCycleState:
    if isinstance(event, BaseSettlementEvent):
        return ingest_base_settlement(
            state,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            trader_id=event.trader_id,
            settlement=event.settlement,
        )
    if isinstance(event, ClassificationEvent):
        return classify_compound_capital(
            state,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            source_lot_id=event.source_lot_id,
            to_state=event.to_state,
            amount_usd=event.amount_usd,
        )
    if isinstance(event, ProtectProfitEvent):
        return protect_compound_capital(
            state,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            source_lot_id=event.source_lot_id,
            amount_usd=event.amount_usd,
        )
    if isinstance(event, PolicyProtectFloorEvent):
        return policy_protect_floor(
            state,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            tranche_id=event.tranche_id,
            policy_id=event.policy_id,
            policy_sha256=event.policy_sha256,
        )
    if isinstance(event, InternalCapitalMarketEvent):
        return apply_internal_capital_market_decision(
            state,
            event_id=event.event_id,
            scarcity_event=event.scarcity_event,
            decision=event.decision,
            source_lot_id=event.source_lot_id,
        )
    if isinstance(event, CompoundDeploymentSettlementEvent):
        return settle_compound_deployment(
            state,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            deployment_id=event.deployment_id,
            settlement=event.settlement,
        )
    raise CiboCompoundCapitalError("compound replay event is unsupported")
