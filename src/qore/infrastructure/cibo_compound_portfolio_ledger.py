"""Account-local Core Compound Portfolio ledger for CIBO GEN-C1.

The ledger is research-only. It models current compound-capital ownership as an
exact partition of admitted realized profit lots. Transitions archive the source
lot and create immutable child lots, preventing the same economic unit from
being deployable, reserved and protected simultaneously.

Consumed capital remains an explicit terminal accounting state so losses never
make provenance disappear.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalLot,
    CompoundCapitalState,
)


class CompoundPortfolioEventType(StrEnum):
    ADMIT_REALIZED_PROFIT = "ADMIT_REALIZED_PROFIT"
    TRANSITION = "TRANSITION"
    SETTLE_DEPLOYMENT = "SETTLE_DEPLOYMENT"


@dataclass(frozen=True, slots=True)
class CompoundPortfolioEvent:
    event_id: str
    event_type: CompoundPortfolioEventType
    occurred_at: datetime
    source_lot_ids: tuple[str, ...]
    target_lot_ids: tuple[str, ...]
    source_total_usd: Decimal
    target_total_usd: Decimal
    detail: str

    def __post_init__(self) -> None:
        if not self.event_id or not self.detail:
            raise CiboCompoundCapitalError(
                "compound portfolio event identity/detail is required"
            )
        if type(self.event_type) is not CompoundPortfolioEventType:
            raise CiboCompoundCapitalError(
                "compound portfolio event type is invalid"
            )
        _aware(self.occurred_at, "event occurred_at")
        for name in ("source_lot_ids", "target_lot_ids"):
            values = getattr(self, name)
            if len(values) != len(set(values)) or any(
                not isinstance(item, str) or not item
                for item in values
            ):
                raise CiboCompoundCapitalError(
                    f"compound portfolio {name} must be unique/non-empty"
                )
        for name in ("source_total_usd", "target_total_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"compound portfolio {name} must be finite non-negative"
                )
        if self.event_type is CompoundPortfolioEventType.ADMIT_REALIZED_PROFIT:
            if self.source_lot_ids or self.source_total_usd != 0:
                raise CiboCompoundCapitalError(
                    "compound admission cannot consume an existing lot"
                )
            if len(self.target_lot_ids) != 1 or self.target_total_usd <= 0:
                raise CiboCompoundCapitalError(
                    "compound admission requires one positive target"
                )
        elif (
            not self.source_lot_ids
            or not self.target_lot_ids
            or self.source_total_usd <= 0
            or self.source_total_usd != self.target_total_usd
        ):
            raise CiboCompoundCapitalError(
                "compound transition must conserve source/target value"
            )


_ALLOWED_TRANSITIONS: dict[
    CompoundCapitalState,
    frozenset[CompoundCapitalState],
] = {
    CompoundCapitalState.REALIZED_PROFIT: frozenset(
        {
            CompoundCapitalState.PROTECTED_PROFIT,
            CompoundCapitalState.COMPOUNDABLE,
            CompoundCapitalState.STRATEGIC_RESERVE,
            CompoundCapitalState.OPPORTUNITY_RESERVE,
            CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        }
    ),
    CompoundCapitalState.PROTECTED_PROFIT: frozenset(
        {
            CompoundCapitalState.COMPOUNDABLE,
            CompoundCapitalState.STRATEGIC_RESERVE,
            CompoundCapitalState.OPPORTUNITY_RESERVE,
            CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        }
    ),
    CompoundCapitalState.COMPOUNDABLE: frozenset(
        {
            CompoundCapitalState.PROTECTED_PROFIT,
            CompoundCapitalState.STRATEGIC_RESERVE,
            CompoundCapitalState.OPPORTUNITY_RESERVE,
            CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
            CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        }
    ),
    CompoundCapitalState.STRATEGIC_RESERVE: frozenset(
        {
            CompoundCapitalState.COMPOUNDABLE,
            CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        }
    ),
    CompoundCapitalState.OPPORTUNITY_RESERVE: frozenset(
        {
            CompoundCapitalState.COMPOUNDABLE,
            CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
            CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        }
    ),
    CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY: frozenset(
        {
            CompoundCapitalState.COMPOUNDABLE,
            CompoundCapitalState.STRATEGIC_RESERVE,
            CompoundCapitalState.OPPORTUNITY_RESERVE,
            CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL,
            CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        }
    ),
    CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL: frozenset(),
    CompoundCapitalState.RELEASED_COMPOUND_CAPITAL: frozenset(
        {
            CompoundCapitalState.COMPOUNDABLE,
            CompoundCapitalState.STRATEGIC_RESERVE,
            CompoundCapitalState.OPPORTUNITY_RESERVE,
            CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        }
    ),
    CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR: frozenset(),
    CompoundCapitalState.CONSUMED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class CompoundPortfolioLedger:
    account_identity: CiboAccountCapitalIdentity
    active_lots: tuple[CompoundCapitalLot, ...] = ()
    archived_lots: tuple[CompoundCapitalLot, ...] = ()
    events: tuple[CompoundPortfolioEvent, ...] = ()
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "compound portfolio account identity is invalid"
            )
        if type(self.runtime_authority) is not bool:
            raise CiboCompoundCapitalError(
                "compound portfolio runtime_authority must be bool"
            )
        if self.runtime_authority:
            raise CiboCompoundCapitalError(
                "GEN-C1 compound portfolio has no runtime authority"
            )

        all_lots = self.active_lots + self.archived_lots
        lot_ids = tuple(item.lot_id for item in all_lots)
        if len(lot_ids) != len(set(lot_ids)):
            raise CiboCompoundCapitalError(
                "compound portfolio lot ids must be globally unique"
            )
        if any(
            item.account_identity != self.account_identity
            for item in all_lots
        ):
            raise CiboCompoundCapitalError(
                "compound portfolio cannot mix account domains"
            )
        event_ids = tuple(item.event_id for item in self.events)
        if len(event_ids) != len(set(event_ids)):
            raise CiboCompoundCapitalError(
                "compound portfolio event ids must be unique"
            )

        known_lots = set(lot_ids)
        lots_by_id = {item.lot_id: item for item in all_lots}
        for event in self.events:
            if not set(event.source_lot_ids).issubset(known_lots):
                raise CiboCompoundCapitalError(
                    "compound event source lot is not in portfolio history"
                )
            if not set(event.target_lot_ids).issubset(known_lots):
                raise CiboCompoundCapitalError(
                    "compound event target lot is not in portfolio history"
                )
            sources = tuple(
                lots_by_id[item] for item in event.source_lot_ids
            )
            targets = tuple(
                lots_by_id[item] for item in event.target_lot_ids
            )
            if sum(
                (item.amount_usd for item in sources),
                Decimal(0),
            ) != event.source_total_usd:
                raise CiboCompoundCapitalError(
                    "compound event source total does not match source lots"
                )
            if sum(
                (item.amount_usd for item in targets),
                Decimal(0),
            ) != event.target_total_usd:
                raise CiboCompoundCapitalError(
                    "compound event target total does not match target lots"
                )
            if any(
                item.created_at > event.occurred_at
                for item in targets
            ):
                raise CiboCompoundCapitalError(
                    "compound event cannot predate target lot creation"
                )
            if (
                event.event_type
                is not CompoundPortfolioEventType.ADMIT_REALIZED_PROFIT
                and any(
                    source_id not in target.parent_lot_ids
                    for source_id in event.source_lot_ids
                    for target in targets
                )
            ):
                raise CiboCompoundCapitalError(
                    "compound event target ancestry does not bind source lot"
                )

        admitted = sum(
            (
                event.target_total_usd
                for event in self.events
                if event.event_type
                is CompoundPortfolioEventType.ADMIT_REALIZED_PROFIT
            ),
            Decimal(0),
        )
        current_partition = sum(
            (item.amount_usd for item in self.active_lots),
            Decimal(0),
        )
        if current_partition != admitted:
            raise CiboCompoundCapitalError(
                "compound current partition must equal admitted realized profit"
            )

    @property
    def admitted_realized_profit_usd(self) -> Decimal:
        return sum(
            (
                item.target_total_usd
                for item in self.events
                if item.event_type
                is CompoundPortfolioEventType.ADMIT_REALIZED_PROFIT
            ),
            Decimal(0),
        )

    @property
    def current_partition_usd(self) -> Decimal:
        return sum(
            (item.amount_usd for item in self.active_lots),
            Decimal(0),
        )

    @property
    def current_economic_value_usd(self) -> Decimal:
        return sum(
            (
                item.amount_usd
                for item in self.active_lots
                if item.state is not CompoundCapitalState.CONSUMED
            ),
            Decimal(0),
        )

    def balance(self, state: CompoundCapitalState) -> Decimal:
        if type(state) is not CompoundCapitalState:
            raise CiboCompoundCapitalError(
                "compound balance state is invalid"
            )
        return sum(
            (
                item.amount_usd
                for item in self.active_lots
                if item.state is state
            ),
            Decimal(0),
        )

    def lot(self, lot_id: str) -> CompoundCapitalLot:
        matches = tuple(
            item for item in self.active_lots if item.lot_id == lot_id
        )
        if len(matches) != 1:
            raise CiboCompoundCapitalError(
                "active compound lot not found"
            )
        return matches[0]

    def admit_realized_profit(
        self,
        lot: CompoundCapitalLot,
        *,
        event_id: str,
        occurred_at: datetime,
    ) -> CompoundPortfolioLedger:
        """Admit one terminal realized-profit lot exactly once."""

        if not isinstance(lot, CompoundCapitalLot):
            raise CiboCompoundCapitalError(
                "compound admission requires canonical lot"
            )
        _aware(occurred_at, "admission occurred_at")
        if lot.account_identity != self.account_identity:
            raise CiboCompoundCapitalError(
                "compound admission cannot cross account domains"
            )
        if lot.state is not CompoundCapitalState.REALIZED_PROFIT:
            raise CiboCompoundCapitalError(
                "only realized-profit lot can enter compound portfolio"
            )
        if occurred_at < lot.created_at:
            raise CiboCompoundCapitalError(
                "compound admission cannot predate lot creation"
            )
        history = self.active_lots + self.archived_lots
        if any(
            item.origin_evidence_id == lot.origin_evidence_id
            for item in history
        ):
            raise CiboCompoundCapitalError(
                "compound settlement evidence already admitted"
            )
        if lot.generation == 1:
            if lot.parent_lot_ids:
                raise CiboCompoundCapitalError(
                    "GEN-1 compound lot cannot carry parent lineage"
                )
        else:
            if not lot.parent_lot_ids:
                raise CiboCompoundCapitalError(
                    "GEN-N compound lot requires parent lineage"
                )
            history_by_id = {item.lot_id: item for item in history}
            missing_parents = tuple(
                item for item in lot.parent_lot_ids
                if item not in history_by_id
            )
            if missing_parents:
                raise CiboCompoundCapitalError(
                    "GEN-N compound lot parent lineage is missing from portfolio history"
                )
            expected_generation = 1 + max(
                history_by_id[item].generation
                for item in lot.parent_lot_ids
            )
            if lot.generation != expected_generation:
                raise CiboCompoundCapitalError(
                    "GEN-N compound lot generation does not match parent lineage"
                )
        self._require_new_lot_id(lot.lot_id)
        self._require_new_event_id(event_id)

        event = CompoundPortfolioEvent(
            event_id=event_id,
            event_type=(
                CompoundPortfolioEventType.ADMIT_REALIZED_PROFIT
            ),
            occurred_at=occurred_at,
            source_lot_ids=(),
            target_lot_ids=(lot.lot_id,),
            source_total_usd=Decimal(0),
            target_total_usd=lot.amount_usd,
            detail="reconciled terminal profit admitted to Core",
        )
        return CompoundPortfolioLedger(
            account_identity=self.account_identity,
            active_lots=self.active_lots + (lot,),
            archived_lots=self.archived_lots,
            events=self.events + (event,),
            runtime_authority=False,
        )

    def transition(
        self,
        *,
        source_lot_id: str,
        to_state: CompoundCapitalState,
        amount_usd: Decimal,
        moved_lot_id: str,
        event_id: str,
        occurred_at: datetime,
        remainder_lot_id: str | None = None,
    ) -> CompoundPortfolioLedger:
        """Move all or part of one active lot without creating value."""

        source = self.lot(source_lot_id)
        if type(to_state) is not CompoundCapitalState:
            raise CiboCompoundCapitalError(
                "compound target state is invalid"
            )
        if to_state not in _ALLOWED_TRANSITIONS[source.state]:
            raise CiboCompoundCapitalError(
                f"illegal compound transition "
                f"{source.state.value}->{to_state.value}"
            )
        _positive(amount_usd, "transition amount_usd")
        if amount_usd > source.amount_usd:
            raise CiboCompoundCapitalError(
                "compound transition exceeds source lot"
            )
        _aware(occurred_at, "transition occurred_at")
        if occurred_at < source.created_at:
            raise CiboCompoundCapitalError(
                "compound transition cannot predate source lot"
            )
        self._require_new_event_id(event_id)
        self._require_new_lot_id(moved_lot_id)

        remainder = source.amount_usd - amount_usd
        if remainder == 0 and remainder_lot_id is not None:
            raise CiboCompoundCapitalError(
                "full compound transition cannot create remainder"
            )
        if remainder > 0:
            if remainder_lot_id is None:
                raise CiboCompoundCapitalError(
                    "partial compound transition requires remainder lot id"
                )
            self._require_new_lot_id(remainder_lot_id)
            if remainder_lot_id == moved_lot_id:
                raise CiboCompoundCapitalError(
                    "compound child lot ids must be distinct"
                )

        lineage = source.parent_lot_ids + (source.lot_id,)
        moved = replace(
            source,
            lot_id=moved_lot_id,
            amount_usd=amount_usd,
            state=to_state,
            created_at=occurred_at,
            parent_lot_ids=lineage,
        )
        children: tuple[CompoundCapitalLot, ...] = (moved,)
        if remainder > 0:
            assert remainder_lot_id is not None
            children += (
                replace(
                    source,
                    lot_id=remainder_lot_id,
                    amount_usd=remainder,
                    created_at=occurred_at,
                    parent_lot_ids=lineage,
                ),
            )

        event = CompoundPortfolioEvent(
            event_id=event_id,
            event_type=CompoundPortfolioEventType.TRANSITION,
            occurred_at=occurred_at,
            source_lot_ids=(source.lot_id,),
            target_lot_ids=tuple(item.lot_id for item in children),
            source_total_usd=source.amount_usd,
            target_total_usd=sum(
                (item.amount_usd for item in children),
                Decimal(0),
            ),
            detail=f"compound state transition to {to_state.value}",
        )
        return self._replace_source_with_children(
            source=source,
            children=children,
            event=event,
        )

    def settle_deployment(
        self,
        *,
        source_lot_id: str,
        returned_capacity_usd: Decimal,
        event_id: str,
        occurred_at: datetime,
        returned_lot_id: str | None,
        consumed_lot_id: str | None,
    ) -> CompoundPortfolioLedger:
        """Settle deployed compound capital into returned and consumed parts."""

        source = self.lot(source_lot_id)
        if (
            source.state
            is not CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL
        ):
            raise CiboCompoundCapitalError(
                "only deployed compound capital can settle"
            )
        if (
            not isinstance(returned_capacity_usd, Decimal)
            or not returned_capacity_usd.is_finite()
            or returned_capacity_usd < 0
            or returned_capacity_usd > source.amount_usd
        ):
            raise CiboCompoundCapitalError(
                "returned compound capacity is outside deployment"
            )
        _aware(occurred_at, "deployment settlement occurred_at")
        if occurred_at < source.created_at:
            raise CiboCompoundCapitalError(
                "compound settlement cannot predate deployment"
            )
        self._require_new_event_id(event_id)

        consumed = source.amount_usd - returned_capacity_usd
        if returned_capacity_usd > 0:
            if returned_lot_id is None:
                raise CiboCompoundCapitalError(
                    "returned compound capacity requires lot id"
                )
            self._require_new_lot_id(returned_lot_id)
        elif returned_lot_id is not None:
            raise CiboCompoundCapitalError(
                "zero returned compound capacity cannot create returned lot"
            )
        if consumed > 0:
            if consumed_lot_id is None:
                raise CiboCompoundCapitalError(
                    "consumed compound capacity requires lot id"
                )
            self._require_new_lot_id(consumed_lot_id)
        elif consumed_lot_id is not None:
            raise CiboCompoundCapitalError(
                "zero consumed compound capacity cannot create consumed lot"
            )
        if (
            returned_lot_id is not None
            and consumed_lot_id is not None
            and returned_lot_id == consumed_lot_id
        ):
            raise CiboCompoundCapitalError(
                "compound settlement child lot ids must be distinct"
            )

        lineage = source.parent_lot_ids + (source.lot_id,)
        children: tuple[CompoundCapitalLot, ...] = ()
        if returned_capacity_usd > 0:
            assert returned_lot_id is not None
            children += (
                replace(
                    source,
                    lot_id=returned_lot_id,
                    amount_usd=returned_capacity_usd,
                    state=(
                        CompoundCapitalState.RELEASED_COMPOUND_CAPITAL
                    ),
                    created_at=occurred_at,
                    parent_lot_ids=lineage,
                ),
            )
        if consumed > 0:
            assert consumed_lot_id is not None
            children += (
                replace(
                    source,
                    lot_id=consumed_lot_id,
                    amount_usd=consumed,
                    state=CompoundCapitalState.CONSUMED,
                    created_at=occurred_at,
                    parent_lot_ids=lineage,
                ),
            )

        event = CompoundPortfolioEvent(
            event_id=event_id,
            event_type=CompoundPortfolioEventType.SETTLE_DEPLOYMENT,
            occurred_at=occurred_at,
            source_lot_ids=(source.lot_id,),
            target_lot_ids=tuple(item.lot_id for item in children),
            source_total_usd=source.amount_usd,
            target_total_usd=sum(
                (item.amount_usd for item in children),
                Decimal(0),
            ),
            detail="deployed compound capital reconciled",
        )
        return self._replace_source_with_children(
            source=source,
            children=children,
            event=event,
        )

    def _replace_source_with_children(
        self,
        *,
        source: CompoundCapitalLot,
        children: tuple[CompoundCapitalLot, ...],
        event: CompoundPortfolioEvent,
    ) -> CompoundPortfolioLedger:
        active = tuple(
            item for item in self.active_lots if item.lot_id != source.lot_id
        )
        return CompoundPortfolioLedger(
            account_identity=self.account_identity,
            active_lots=active + children,
            archived_lots=self.archived_lots + (source,),
            events=self.events + (event,),
            runtime_authority=False,
        )

    def _require_new_lot_id(self, lot_id: str) -> None:
        if not isinstance(lot_id, str) or not lot_id:
            raise CiboCompoundCapitalError(
                "compound lot id must be non-empty"
            )
        if any(
            item.lot_id == lot_id
            for item in self.active_lots + self.archived_lots
        ):
            raise CiboCompoundCapitalError(
                "compound lot id already exists"
            )

    def _require_new_event_id(self, event_id: str) -> None:
        if not isinstance(event_id, str) or not event_id:
            raise CiboCompoundCapitalError(
                "compound event id must be non-empty"
            )
        if any(item.event_id == event_id for item in self.events):
            raise CiboCompoundCapitalError(
                "compound event id already exists"
            )


def _positive(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        raise CiboCompoundCapitalError(
            f"compound {name} must be finite positive Decimal"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"compound {name} must be timezone-aware"
        )
