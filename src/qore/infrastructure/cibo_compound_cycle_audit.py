"""Deterministic reconciliation audit for the integrated CIBO compound cycle.

The audit derives accounting integrity from the replay state.  It does not
infer profitability, certify economic utility or grant productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalLot,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    CiboCompoundCycleState,
)


@dataclass(frozen=True, slots=True)
class CompoundGenerationLineageEdge:
    child_lot_id: str
    child_generation: int
    child_origin_trader: TraderLineage
    direct_parent_lot_id: str
    parent_generation: int
    parent_origin_trader: TraderLineage
    amount_usd: Decimal

    def __post_init__(self) -> None:
        if not self.child_lot_id or not self.direct_parent_lot_id:
            raise CiboCompoundCapitalError(
                "compound audit generation edge identity is required"
            )
        if (
            self.child_generation <= self.parent_generation
            or self.child_generation < 2
        ):
            raise CiboCompoundCapitalError(
                "compound audit generation edge must advance generation"
            )
        if type(self.child_origin_trader) is not TraderLineage:
            raise CiboCompoundCapitalError(
                "compound audit child Trader is invalid"
            )
        if type(self.parent_origin_trader) is not TraderLineage:
            raise CiboCompoundCapitalError(
                "compound audit parent Trader is invalid"
            )
        if (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound audit generation amount must be positive"
            )


@dataclass(frozen=True, slots=True)
class CompoundCycleReconciliation:
    state_sha256: str
    opening_original_base_usd: Decimal
    current_original_base_usd: Decimal
    admitted_realized_profit_usd: Decimal
    cumulative_realized_gains_usd: Decimal
    cumulative_realized_losses_usd: Decimal
    consumed_compound_capital_usd: Decimal
    base_capital_loss_usd: Decimal
    closing_realized_capital_usd: Decimal
    accounting_identity_usd: Decimal
    accounting_residual_usd: Decimal
    protected_floor_usd: Decimal
    compoundable_usd: Decimal
    strategic_reserve_usd: Decimal
    opportunity_reserve_usd: Decimal
    active_compound_capacity_usd: Decimal
    deployed_compound_capital_usd: Decimal
    active_t19_reservation_count: int
    market_decision_count: int
    deployment_count: int
    settled_deployment_count: int
    highest_generation: int
    original_capital_dependence_ratio: Decimal
    generation_edges: tuple[CompoundGenerationLineageEdge, ...]
    accounting_integrity_pass: bool
    provenance_pass: bool
    no_double_counting_pass: bool
    no_unexplained_creation_pass: bool
    no_unexplained_destruction_pass: bool
    path_dependence_mechanics_pass: bool
    economic_value_demonstrated: bool = False
    fresh_oos_pass: bool = False
    stress_pass: bool = False
    temporal_replication_pass: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.state_sha256, str)
            or not self.state_sha256.startswith("sha256:")
            or len(self.state_sha256) != 71
            or any(
                char not in "0123456789abcdef"
                for char in self.state_sha256[7:]
            )
        ):
            raise CiboCompoundCapitalError(
                "compound audit state digest is invalid"
            )
        for name in (
            "opening_original_base_usd",
            "current_original_base_usd",
            "admitted_realized_profit_usd",
            "cumulative_realized_gains_usd",
            "cumulative_realized_losses_usd",
            "consumed_compound_capital_usd",
            "base_capital_loss_usd",
            "closing_realized_capital_usd",
            "accounting_identity_usd",
            "accounting_residual_usd",
            "protected_floor_usd",
            "compoundable_usd",
            "strategic_reserve_usd",
            "opportunity_reserve_usd",
            "active_compound_capacity_usd",
            "deployed_compound_capital_usd",
            "original_capital_dependence_ratio",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCompoundCapitalError(
                    f"compound audit {name} must be finite Decimal"
                )
        for name in (
            "active_t19_reservation_count",
            "market_decision_count",
            "deployment_count",
            "settled_deployment_count",
            "highest_generation",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCompoundCapitalError(
                    f"compound audit {name} must be non-negative int"
                )
        if self.settled_deployment_count > self.deployment_count:
            raise CiboCompoundCapitalError(
                "compound audit settled deployments exceed deployments"
            )
        if (
            not isinstance(self.generation_edges, tuple)
            or any(
                not isinstance(item, CompoundGenerationLineageEdge)
                for item in self.generation_edges
            )
        ):
            raise CiboCompoundCapitalError(
                "compound audit generation edges must be canonical"
            )
        edge_ids = tuple(
            (item.child_lot_id, item.direct_parent_lot_id)
            for item in self.generation_edges
        )
        if len(edge_ids) != len(set(edge_ids)):
            raise CiboCompoundCapitalError(
                "compound audit generation edges must be unique"
            )
        highest_edge_generation = max(
            (item.child_generation for item in self.generation_edges),
            default=0,
        )
        if (
            (self.highest_generation < 2 and self.generation_edges)
            or (
                self.highest_generation >= 2
                and highest_edge_generation != self.highest_generation
            )
        ):
            raise CiboCompoundCapitalError(
                "compound audit generation lineage/highest-generation drift"
            )
        if self.accounting_residual_usd != Decimal(0):
            raise CiboCompoundCapitalError(
                "compound audit accounting residual must be zero"
            )
        for name in (
            "accounting_integrity_pass",
            "provenance_pass",
            "no_double_counting_pass",
            "no_unexplained_creation_pass",
            "no_unexplained_destruction_pass",
            "path_dependence_mechanics_pass",
        ):
            if getattr(self, name) is not True:
                raise CiboCompoundCapitalError(
                    f"compound audit required mechanical gate failed: {name}"
                )
        for name in (
            "economic_value_demonstrated",
            "fresh_oos_pass",
            "stress_pass",
            "temporal_replication_pass",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"compound audit {name} must be bool"
                )
        if (
            self.economic_value_demonstrated
            or self.fresh_oos_pass
            or self.stress_pass
            or self.temporal_replication_pass
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "compound mechanical audit cannot claim scientific certification"
            )


def reconcile_compound_cycle(
    state: CiboCompoundCycleState,
) -> CompoundCycleReconciliation:
    """Prove conservation/provenance mechanics without claiming economic value."""

    if not isinstance(state, CiboCompoundCycleState):
        raise CiboCompoundCapitalError(
            "compound audit requires canonical cycle state"
        )

    gains = sum(
        (
            max(Decimal(0), item.realized_net_pnl_usd)
            for item in state.settlements
        ),
        Decimal(0),
    )
    losses = sum(
        (
            max(Decimal(0), -item.realized_net_pnl_usd)
            for item in state.settlements
        ),
        Decimal(0),
    )
    if gains != state.cumulative_realized_gains_usd:
        raise CiboCompoundCapitalError(
            "compound audit gain ledger/replay mismatch"
        )
    if losses != state.cumulative_realized_losses_usd:
        raise CiboCompoundCapitalError(
            "compound audit loss ledger/replay mismatch"
        )

    admitted = state.compound_ledger.admitted_realized_profit_usd
    if admitted != gains:
        raise CiboCompoundCapitalError(
            "compound audit realized gains are not fully admitted exactly once"
        )

    consumed = state.compound_ledger.balance(
        CompoundCapitalState.CONSUMED
    )
    base_loss = (
        state.opening_original_base_usd
        - state.current_original_base_usd
    )
    if base_loss < 0:
        raise CiboCompoundCapitalError(
            "compound audit original base cannot grow from compound accounting"
        )
    if base_loss + consumed != losses:
        raise CiboCompoundCapitalError(
            "compound audit realized loss destruction is unexplained"
        )

    closing = state.closing_realized_capital_usd
    identity = state.accounting_identity_usd
    residual = closing - identity
    if residual != 0:
        raise CiboCompoundCapitalError(
            "compound audit closing-capital reconciliation failed"
        )

    edges = _generation_edges(state)
    all_lots = (
        state.compound_ledger.active_lots
        + state.compound_ledger.archived_lots
    )
    lot_ids = tuple(item.lot_id for item in all_lots)
    provenance_pass = (
        len(lot_ids) == len(set(lot_ids))
        and all(
            parent in set(lot_ids)
            for lot in all_lots
            for parent in lot.parent_lot_ids
        )
    )
    if not provenance_pass:
        raise CiboCompoundCapitalError(
            "compound audit lot provenance is incomplete"
        )

    settled_count = sum(1 for item in state.deployments if item.settled)
    settled_shas = {
        item.settlement_sha256
        for item in state.settlements
        if item.source_kind == "COMPOUND_CAPITAL"
    }
    path_mechanics = (
        state.last_event_at is not None
        and all(
            (
                item.settlement_sha256 in settled_shas
                if item.settled
                else item.settlement_sha256 is None
            )
            for item in state.deployments
        )
    )

    return CompoundCycleReconciliation(
        state_sha256=compound_cycle_state_sha256(state),
        opening_original_base_usd=state.opening_original_base_usd,
        current_original_base_usd=state.current_original_base_usd,
        admitted_realized_profit_usd=admitted,
        cumulative_realized_gains_usd=gains,
        cumulative_realized_losses_usd=losses,
        consumed_compound_capital_usd=consumed,
        base_capital_loss_usd=base_loss,
        closing_realized_capital_usd=closing,
        accounting_identity_usd=identity,
        accounting_residual_usd=residual,
        protected_floor_usd=state.floor_ledger.total_floor_usd,
        compoundable_usd=state.compound_ledger.balance(
            CompoundCapitalState.COMPOUNDABLE
        ),
        strategic_reserve_usd=state.compound_ledger.balance(
            CompoundCapitalState.STRATEGIC_RESERVE
        ),
        opportunity_reserve_usd=state.compound_ledger.balance(
            CompoundCapitalState.OPPORTUNITY_RESERVE
        ),
        active_compound_capacity_usd=state.compound_ledger.balance(
            CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY
        ),
        deployed_compound_capital_usd=state.compound_ledger.balance(
            CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL
        ),
        active_t19_reservation_count=len(
            state.t19_ledger.active_reservations
        ),
        market_decision_count=len(state.market_records),
        deployment_count=len(state.deployments),
        settled_deployment_count=settled_count,
        highest_generation=state.highest_generation,
        original_capital_dependence_ratio=(
            state.original_capital_dependence_ratio
        ),
        generation_edges=edges,
        accounting_integrity_pass=True,
        provenance_pass=True,
        no_double_counting_pass=True,
        no_unexplained_creation_pass=True,
        no_unexplained_destruction_pass=True,
        path_dependence_mechanics_pass=path_mechanics,
        economic_value_demonstrated=False,
        fresh_oos_pass=False,
        stress_pass=False,
        temporal_replication_pass=False,
        certification_ready=False,
    )


def compound_cycle_state_sha256(state: CiboCompoundCycleState) -> str:
    payload = {
        "account": {
            "provider_key": state.account_identity.provider_key,
            "account_ref": state.account_identity.account_ref,
            "environment": state.account_identity.environment.value,
            "provider_program": state.account_identity.provider_program,
        },
        "opening_original_base_usd": format(
            state.opening_original_base_usd,
            "f",
        ),
        "current_original_base_usd": format(
            state.current_original_base_usd,
            "f",
        ),
        "gains": format(state.cumulative_realized_gains_usd, "f"),
        "losses": format(state.cumulative_realized_losses_usd, "f"),
        "events": list(state.event_ids),
        "settlements": [
            {
                "event_id": item.event_id,
                "sha256": item.settlement_sha256,
                "pnl": format(item.realized_net_pnl_usd, "f"),
                "source": item.source_kind,
                "deployment_id": item.deployment_id,
            }
            for item in state.settlements
        ],
        "markets": [
            {
                "event_id": item.event_id,
                "decision_id": item.decision_id,
                "action": item.action,
                "candidate_id": item.candidate_id,
                "amount": format(item.amount_usd, "f"),
                "portfolio_sha256": item.portfolio_state_sha256,
                "t19_sha256": item.t19_ledger_sha256,
            }
            for item in state.market_records
        ],
        "deployments": [
            {
                "deployment_id": item.deployment_id,
                "candidate_id": item.candidate_id,
                "signal": item.signal_fingerprint,
                "source_lot": item.source_lot_id,
                "deployed_lot": item.deployed_lot_id,
                "amount": format(item.amount_usd, "f"),
                "source_generation": item.source_generation,
                "settled": item.settled,
                "settlement_sha256": item.settlement_sha256,
            }
            for item in state.deployments
        ],
        "active_lots": [_lot_payload(item) for item in state.compound_ledger.active_lots],
        "archived_lots": [
            _lot_payload(item) for item in state.compound_ledger.archived_lots
        ],
        "floor": [
            {
                "tranche_id": item.tranche_id,
                "source_lot_id": item.source_compound_lot_id,
                "amount": format(item.amount_usd, "f"),
                "protection_class": item.protection_class.value,
            }
            for item in state.floor_ledger.tranches
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _generation_edges(
    state: CiboCompoundCycleState,
) -> tuple[CompoundGenerationLineageEdge, ...]:
    lots = {
        item.lot_id: item
        for item in (
            state.compound_ledger.active_lots
            + state.compound_ledger.archived_lots
        )
    }
    edges: list[CompoundGenerationLineageEdge] = []
    for child in lots.values():
        if child.generation < 2 or not child.parent_lot_ids:
            continue
        parent_id = child.parent_lot_ids[-1]
        parent = lots.get(parent_id)
        if parent is None:
            raise CiboCompoundCapitalError(
                "compound audit generation parent is missing"
            )
        if parent.generation > child.generation:
            raise CiboCompoundCapitalError(
                "compound audit generation parent cannot exceed child generation"
            )
        if parent.generation == child.generation:
            continue
        edges.append(
            CompoundGenerationLineageEdge(
                child_lot_id=child.lot_id,
                child_generation=child.generation,
                child_origin_trader=child.origin_trader,
                direct_parent_lot_id=parent.lot_id,
                parent_generation=parent.generation,
                parent_origin_trader=parent.origin_trader,
                amount_usd=child.amount_usd,
            )
        )
    return tuple(
        sorted(
            edges,
            key=lambda item: (
                item.child_generation,
                item.child_lot_id,
            ),
        )
    )


def _lot_payload(lot: CompoundCapitalLot) -> dict[str, object]:
    return {
        "lot_id": lot.lot_id,
        "amount": format(lot.amount_usd, "f"),
        "state": lot.state.value,
        "generation": lot.generation,
        "origin_trader": lot.origin_trader.value,
        "origin_signal": lot.origin_signal_fingerprint,
        "parent_lot_ids": list(lot.parent_lot_ids),
    }
