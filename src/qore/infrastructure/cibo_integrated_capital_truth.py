"""Cross-ledger capital truth for the integrated CIBO compound program.

CapitalSourceLedger and GEN-C1 can both represent realized profit. They are
therefore not additive. This module proves when they are two representations of
the same economic value and refuses consolidation when lineage is incomplete.

No sizing, Risk, execution, LIVE, broker or real-capital authority is granted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_compound_capital import CompoundCapitalLot
from qore.infrastructure.cibo_compound_cycle_audit import (
    compound_cycle_state_sha256,
)
from qore.infrastructure.cibo_compound_cycle_state import CiboCompoundCycleState
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioEventType,
)


class CiboIntegratedCapitalTruthError(ValueError):
    """Cross-ledger economic truth is incomplete or duplicated."""


@dataclass(frozen=True, slots=True)
class RealizedProfitEquivalenceBinding:
    source_id: str
    admission_lot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_id:
            raise CiboIntegratedCapitalTruthError(
                "realized-profit binding source_id is required"
            )
        if (
            not self.admission_lot_ids
            or len(self.admission_lot_ids)
            != len(set(self.admission_lot_ids))
            or any(not item for item in self.admission_lot_ids)
        ):
            raise CiboIntegratedCapitalTruthError(
                "realized-profit binding requires unique admission lot ids"
            )


@dataclass(frozen=True, slots=True)
class IntegratedCapitalTruth:
    account_identity: CiboAccountCapitalIdentity
    source_ledger_sha256: str
    compound_cycle_state_sha256: str
    realized_profit_source_ids: tuple[str, ...]
    admission_lot_ids: tuple[str, ...]
    realized_profit_proven_usd: Decimal
    realized_profit_nonconsumed_usd: Decimal
    compound_admitted_realized_profit_usd: Decimal
    compound_current_economic_value_usd: Decimal
    equivalence_residual_usd: Decimal
    nonconsumed_residual_usd: Decimal
    settlement_provenance_pass: bool
    admission_coverage_pass: bool
    no_double_counting_pass: bool
    fungible_cross_dimension_total_computed: bool = False
    runtime_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboIntegratedCapitalTruthError(
                "integrated capital truth account identity is invalid"
            )
        for value in (
            self.source_ledger_sha256,
            self.compound_cycle_state_sha256,
        ):
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboIntegratedCapitalTruthError(
                    "integrated capital truth digest is invalid"
                )
        if (
            len(self.realized_profit_source_ids)
            != len(set(self.realized_profit_source_ids))
            or len(self.admission_lot_ids)
            != len(set(self.admission_lot_ids))
        ):
            raise CiboIntegratedCapitalTruthError(
                "integrated capital truth identities must be unique"
            )
        for name in (
            "realized_profit_proven_usd",
            "realized_profit_nonconsumed_usd",
            "compound_admitted_realized_profit_usd",
            "compound_current_economic_value_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboIntegratedCapitalTruthError(
                    f"integrated capital truth {name} must be non-negative"
                )
        if self.equivalence_residual_usd != 0:
            raise CiboIntegratedCapitalTruthError(
                "realized-profit equivalence residual must be zero"
            )
        if self.nonconsumed_residual_usd != 0:
            raise CiboIntegratedCapitalTruthError(
                "nonconsumed realized-profit residual must be zero"
            )
        for name in (
            "settlement_provenance_pass",
            "admission_coverage_pass",
            "no_double_counting_pass",
        ):
            if getattr(self, name) is not True:
                raise CiboIntegratedCapitalTruthError(
                    f"integrated capital truth required gate failed: {name}"
                )
        if self.fungible_cross_dimension_total_computed:
            raise CiboIntegratedCapitalTruthError(
                "non-fungible capital dimensions must not be summed"
            )
        if any(
            (
                self.runtime_authority,
                self.sizing_authority,
                self.risk_authority,
                self.execution_authority,
            )
        ):
            raise CiboIntegratedCapitalTruthError(
                "integrated capital truth has no productive authority"
            )


def build_integrated_capital_truth(
    *,
    account_identity: CiboAccountCapitalIdentity,
    source_ledger: CapitalSourceLedger,
    compound_state: CiboCompoundCycleState,
    realized_profit_bindings: tuple[
        RealizedProfitEquivalenceBinding, ...
    ],
) -> IntegratedCapitalTruth:
    """Prove source-ledger realized profit equals GEN-C admitted profit."""

    if not isinstance(
        account_identity,
        CiboAccountCapitalIdentity,
    ):
        raise CiboIntegratedCapitalTruthError(
            "integrated capital truth account identity is invalid"
        )
    if not isinstance(source_ledger, CapitalSourceLedger):
        raise CiboIntegratedCapitalTruthError(
            "integrated capital truth requires canonical source ledger"
        )
    if not isinstance(compound_state, CiboCompoundCycleState):
        raise CiboIntegratedCapitalTruthError(
            "integrated capital truth requires canonical compound state"
        )
    if compound_state.account_identity != account_identity:
        raise CiboIntegratedCapitalTruthError(
            "integrated capital truth account domains differ"
        )
    if not isinstance(realized_profit_bindings, tuple):
        raise CiboIntegratedCapitalTruthError(
            "realized-profit bindings must be tuple"
        )
    if any(
        not isinstance(item, RealizedProfitEquivalenceBinding)
        for item in realized_profit_bindings
    ):
        raise CiboIntegratedCapitalTruthError(
            "realized-profit binding is not canonical"
        )

    protected_sources = tuple(
        item.source_id
        for item in source_ledger.accounts
        if item.source is CapitalSource.PROTECTED_ECONOMIC_FLOOR
    )
    if protected_sources:
        raise CiboIntegratedCapitalTruthError(
            "PROTECTED_ECONOMIC_FLOOR source requires explicit lineage "
            "before cross-ledger consolidation"
        )

    realized_accounts = tuple(
        item
        for item in source_ledger.accounts
        if item.source is CapitalSource.REALIZED_PROFIT
    )
    realized_ids = tuple(item.source_id for item in realized_accounts)
    binding_ids = tuple(item.source_id for item in realized_profit_bindings)
    if len(binding_ids) != len(set(binding_ids)):
        raise CiboIntegratedCapitalTruthError(
            "realized-profit source cannot have duplicate bindings"
        )
    if set(binding_ids) != set(realized_ids):
        raise CiboIntegratedCapitalTruthError(
            "realized-profit source binding coverage is incomplete"
        )

    all_lots = {
        item.lot_id: item
        for item in (
            compound_state.compound_ledger.active_lots
            + compound_state.compound_ledger.archived_lots
        )
    }
    admission_ids = _admission_lot_ids(compound_state)
    bound_lot_ids = tuple(
        lot_id
        for binding in realized_profit_bindings
        for lot_id in binding.admission_lot_ids
    )
    if len(bound_lot_ids) != len(set(bound_lot_ids)):
        raise CiboIntegratedCapitalTruthError(
            "compound admission lot cannot bind to multiple profit sources"
        )
    if set(bound_lot_ids) != set(admission_ids):
        raise CiboIntegratedCapitalTruthError(
            "compound admission binding coverage is incomplete"
        )

    accounts_by_id = {item.source_id: item for item in realized_accounts}
    for binding in realized_profit_bindings:
        account = accounts_by_id[binding.source_id]
        amount = sum(
            (
                _root_lot(all_lots, lot_id).amount_usd
                for lot_id in binding.admission_lot_ids
            ),
            Decimal(0),
        )
        if amount != account.proven_amount_usd:
            raise CiboIntegratedCapitalTruthError(
                "realized-profit source amount differs from bound admissions"
            )

    for lot_id in admission_ids:
        _require_settlement_provenance(
            compound_state,
            _root_lot(all_lots, lot_id),
        )

    proven = sum(
        (item.proven_amount_usd for item in realized_accounts),
        Decimal(0),
    )
    nonconsumed = sum(
        (
            item.proven_amount_usd - item.consumed_usd
            for item in realized_accounts
        ),
        Decimal(0),
    )
    admitted = compound_state.compound_ledger.admitted_realized_profit_usd
    current = compound_state.compound_ledger.current_economic_value_usd
    equivalence_residual = proven - admitted
    nonconsumed_residual = nonconsumed - current
    if equivalence_residual != 0:
        raise CiboIntegratedCapitalTruthError(
            "source-ledger and GEN-C admitted realized profit diverge"
        )
    if nonconsumed_residual != 0:
        raise CiboIntegratedCapitalTruthError(
            "source-ledger and GEN-C nonconsumed profit diverge"
        )

    return IntegratedCapitalTruth(
        account_identity=account_identity,
        source_ledger_sha256=_source_ledger_sha256(source_ledger),
        compound_cycle_state_sha256=compound_cycle_state_sha256(
            compound_state
        ),
        realized_profit_source_ids=tuple(sorted(realized_ids)),
        admission_lot_ids=tuple(sorted(admission_ids)),
        realized_profit_proven_usd=proven,
        realized_profit_nonconsumed_usd=nonconsumed,
        compound_admitted_realized_profit_usd=admitted,
        compound_current_economic_value_usd=current,
        equivalence_residual_usd=equivalence_residual,
        nonconsumed_residual_usd=nonconsumed_residual,
        settlement_provenance_pass=True,
        admission_coverage_pass=True,
        no_double_counting_pass=True,
        fungible_cross_dimension_total_computed=False,
        runtime_authority=False,
        sizing_authority=False,
        risk_authority=False,
        execution_authority=False,
    )


def _admission_lot_ids(state: CiboCompoundCycleState) -> tuple[str, ...]:
    ids: list[str] = []
    for event in state.compound_ledger.events:
        if (
            event.event_type
            is CompoundPortfolioEventType.ADMIT_REALIZED_PROFIT
        ):
            ids.extend(event.target_lot_ids)
    return tuple(ids)


def _root_lot(
    lots: dict[str, CompoundCapitalLot],
    lot_id: str,
) -> CompoundCapitalLot:
    lot = lots.get(lot_id)
    if lot is None:
        raise CiboIntegratedCapitalTruthError(
            "bound compound admission lot is missing"
        )
    return lot


def _require_settlement_provenance(
    state: CiboCompoundCycleState,
    lot: CompoundCapitalLot,
) -> None:
    matches = tuple(
        item
        for item in state.settlements
        if item.trader_id is lot.origin_trader
        and item.signal_fingerprint == lot.origin_signal_fingerprint
        and item.position_id == lot.origin_position_id
        and item.realized_net_pnl_usd == lot.amount_usd
        and item.realized_net_pnl_usd > 0
    )
    if len(matches) != 1:
        raise CiboIntegratedCapitalTruthError(
            "compound admission lacks unique settlement provenance"
        )


def _source_ledger_sha256(ledger: CapitalSourceLedger) -> str:
    payload = {
        "accounts": [
            {
                "source_id": item.source_id,
                "source": item.source.value,
                "proven_amount_usd": format(item.proven_amount_usd, "f"),
                "reserved_usd": format(item.reserved_usd, "f"),
                "deployed_usd": format(item.deployed_usd, "f"),
                "consumed_usd": format(item.consumed_usd, "f"),
                "cumulative_released_usd": format(
                    item.cumulative_released_usd,
                    "f",
                ),
            }
            for item in sorted(
                ledger.accounts,
                key=lambda row: row.source_id,
            )
        ],
        "reservations": [
            {
                "reservation_id": item.reservation_id,
                "source_id": item.source_id,
                "amount_usd": format(item.amount_usd, "f"),
                "state": item.state.value,
                "returned_capacity_usd": format(
                    item.returned_capacity_usd,
                    "f",
                ),
                "consumed_capacity_usd": format(
                    item.consumed_capacity_usd,
                    "f",
                ),
            }
            for item in sorted(
                ledger.reservations,
                key=lambda row: row.reservation_id,
            )
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()
