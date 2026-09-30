"""Read exact durable component refs for integrated CIBO capital truth.

This adapter binds the two-phase transaction journal to the five existing
durable stores using only their public load/state APIs. It never calls private
serializers and never assumes that non-fungible capital dimensions are
interchangeable.

The Source/T19/Settlement legacy schemas do not encode account identity. Their
paths therefore remain caller-scoped until those schemas are upgraded; this
adapter does not falsely claim otherwise.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_store import (
    DurablePortfolioAllocationStore,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    DurableCmaSettlementStore,
    VersionedCmaSettlementBook,
)
from qore.infrastructure.cibo_compound_floor_store import (
    DurableProtectedCapitalFloorStore,
)
from qore.infrastructure.cibo_compound_portfolio_store import (
    DurableCompoundPortfolioStore,
)
from qore.infrastructure.cibo_integrated_capital_transaction_store import (
    IntegratedCapitalComponent,
    IntegratedCapitalComponentRef,
    IntegratedCapitalTransactionError,
)
from qore.infrastructure.cibo_protected_base_overlay import (
    capital_source_ledger_sha256,
)


@dataclass(frozen=True, slots=True)
class IntegratedCapitalStoreSet:
    account_identity: CiboAccountCapitalIdentity
    source_store: DurableCapitalSourceLedgerStore
    compound_store: DurableCompoundPortfolioStore
    floor_store: DurableProtectedCapitalFloorStore
    t19_store: DurablePortfolioAllocationStore
    settlement_store: DurableCmaSettlementStore
    legacy_path_scope_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise IntegratedCapitalTransactionError(
                "integrated component account identity is invalid"
            )
        expected = (
            (self.source_store, DurableCapitalSourceLedgerStore),
            (self.compound_store, DurableCompoundPortfolioStore),
            (self.floor_store, DurableProtectedCapitalFloorStore),
            (self.t19_store, DurablePortfolioAllocationStore),
            (self.settlement_store, DurableCmaSettlementStore),
        )
        if any(not isinstance(value, kind) for value, kind in expected):
            raise IntegratedCapitalTransactionError(
                "integrated component store set is invalid"
            )
        if type(self.legacy_path_scope_verified) is not bool:
            raise IntegratedCapitalTransactionError(
                "legacy path-scope flag must be bool"
            )
        if not self.legacy_path_scope_verified:
            raise IntegratedCapitalTransactionError(
                "legacy Source/T19/Settlement paths require explicit "
                "account-scope verification"
            )


def read_integrated_component_refs(
    stores: IntegratedCapitalStoreSet,
) -> tuple[IntegratedCapitalComponentRef, ...]:
    """Read the exact durable generations and canonical component digests."""

    if not isinstance(stores, IntegratedCapitalStoreSet):
        raise IntegratedCapitalTransactionError(
            "integrated component adapter requires canonical store set"
        )

    source = stores.source_store.load()
    compound = stores.compound_store.load()
    floor = stores.floor_store.load()
    t19 = stores.t19_store.load()
    settlement = stores.settlement_store.load()

    if source.generation <= 0:
        raise IntegratedCapitalTransactionError(
            "source ledger is not durably persisted"
        )
    if compound.generation <= 0:
        raise IntegratedCapitalTransactionError(
            "compound portfolio is not durably persisted"
        )
    if floor.generation <= 0:
        raise IntegratedCapitalTransactionError(
            "protected floor is not durably persisted"
        )
    if t19 is None or t19.generation <= 0:
        raise IntegratedCapitalTransactionError(
            "T19 allocation ledger is not durably initialized"
        )
    if settlement.generation <= 0:
        raise IntegratedCapitalTransactionError(
            "CMA settlement book is not durably persisted"
        )
    if compound.account_identity != stores.account_identity:
        raise IntegratedCapitalTransactionError(
            "compound portfolio account scope differs from adapter account"
        )
    if floor.account_identity != stores.account_identity:
        raise IntegratedCapitalTransactionError(
            "protected floor account scope differs from adapter account"
        )

    refs = (
        IntegratedCapitalComponentRef(
            component=IntegratedCapitalComponent.SOURCE_LEDGER,
            generation=source.generation,
            sha256=capital_source_ledger_sha256(source.ledger),
        ),
        IntegratedCapitalComponentRef(
            component=IntegratedCapitalComponent.COMPOUND_PORTFOLIO,
            generation=compound.generation,
            sha256=compound.chain_sha256,
        ),
        IntegratedCapitalComponentRef(
            component=IntegratedCapitalComponent.PROTECTED_FLOOR,
            generation=floor.generation,
            sha256=floor.chain_sha256,
        ),
        IntegratedCapitalComponentRef(
            component=IntegratedCapitalComponent.T19_ALLOCATION,
            generation=t19.generation,
            sha256=portfolio_allocation_ledger_sha256(t19.ledger),
        ),
        IntegratedCapitalComponentRef(
            component=IntegratedCapitalComponent.CMA_SETTLEMENT,
            generation=settlement.generation,
            sha256=settlement_book_sha256(settlement),
        ),
    )
    return tuple(sorted(refs, key=lambda item: item.component.value))


def portfolio_allocation_ledger_sha256(ledger) -> str:
    """Canonical public-state digest for the T19 ledger."""

    payload = {
        "total_stop_risk_capacity_usd": _fmt(
            ledger.total_stop_risk_capacity_usd
        ),
        "total_margin_capacity_usd": _fmt(
            ledger.total_margin_capacity_usd
        ),
        "concentration_limit_by_group": [
            [name, _fmt(limit)]
            for name, limit in sorted(ledger.concentration_limit_by_group)
        ],
        "reservations": [
            {
                "signal_fingerprint": item.signal_fingerprint,
                "trader_id": item.trader_id.value,
                "qore_symbol": item.qore_symbol,
                "stop_risk_usd": _fmt(item.stop_risk_usd),
                "margin_usd": _fmt(item.margin_usd),
                "concentration_group": item.concentration_group,
                "concentration_risk_usd": _fmt(
                    item.concentration_risk_usd
                ),
                "state": item.state.value,
            }
            for item in sorted(
                ledger.reservations,
                key=lambda row: (
                    row.signal_fingerprint,
                    row.trader_id.value,
                    row.qore_symbol,
                ),
            )
        ],
    }
    return _payload_sha256(payload)


def settlement_book_sha256(book: VersionedCmaSettlementBook) -> str:
    """Canonical public-state digest for the durable settlement book."""

    if not isinstance(book, VersionedCmaSettlementBook):
        raise IntegratedCapitalTransactionError(
            "settlement digest requires canonical versioned book"
        )
    payload = {
        "states": [
            {
                "signal_fingerprint": state.signal_fingerprint,
                "position_id": state.position_id,
                "position_closed": state.position_closed,
                "records": [
                    {
                        "event": record.event,
                        "deal_id": record.deal_id,
                        "signal_fingerprint": record.signal_fingerprint,
                        "position_id": record.position_id,
                        "net_profit_usd": _fmt(record.net_profit_usd),
                        "position_open_after": record.position_open_after,
                    }
                    for record in state.records
                ],
            }
            for state in sorted(
                book.states,
                key=lambda row: (
                    row.signal_fingerprint,
                    row.position_id,
                ),
            )
        ]
    }
    return _payload_sha256(payload)


def _payload_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _fmt(value: Decimal) -> str:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
    ):
        raise IntegratedCapitalTransactionError(
            "integrated component Decimal must be finite"
        )
    return format(value, "f")
