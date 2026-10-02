"""Reconcile durable QORE Risk reservations against cTrader DEMO truth.

This module never mutates the broker. It releases only QORE's internal
in-flight reservation shadow after authoritative provider evidence proves that
risk has moved into broker-observed state, was cancelled, or reached a terminal
settlement. Ambiguous state remains reserved and therefore fail-closed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountWideRiskEngine,
    AccountWideRiskError,
    ReservationState,
)
from qore.infrastructure.ctrader_demo_mutation_ledger import (
    CTraderDemoMutationLedgerRecord,
)
from qore.infrastructure.ctrader_demo_trade_registry import (
    DemoTradeRegistryEntry,
)

_ACTIVE_ORDER_STATUSES = frozenset({1, 2})
_TERMINAL_ORDER_STATUSES = frozenset({3, 4, 5})


@dataclass(frozen=True, slots=True)
class DemoRiskReservationReconciliation:
    inspected: int
    broker_pending: int
    open_fill_reconciled: int
    terminal_settlement_released: int
    terminal_order_cancelled: int
    awaiting_fill_evidence: int
    awaiting_terminal_settlement: int
    blockers: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "inspected",
            "broker_pending",
            "open_fill_reconciled",
            "terminal_settlement_released",
            "terminal_order_cancelled",
            "awaiting_fill_evidence",
            "awaiting_terminal_settlement",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise AccountWideRiskError(
                    f"DEMO Risk reconciliation {name} must be non-negative int"
                )
        if self.productive_authority:
            raise AccountWideRiskError(
                "DEMO Risk reconciliation grants no productive authority"
            )

    @property
    def safe_to_clear_boot_fence(self) -> bool:
        return not self.blockers


def confirmed_fill_authorization_ids(
    *,
    registry_entries: tuple[DemoTradeRegistryEntry, ...],
    mutation_records: tuple[CTraderDemoMutationLedgerRecord, ...],
) -> frozenset[str]:
    """Return Risk authorizations with exact terminal provider fill evidence."""

    if any(
        not isinstance(item, DemoTradeRegistryEntry)
        for item in registry_entries
    ):
        raise AccountWideRiskError(
            "DEMO Risk reconciliation requires canonical registry entries"
        )
    if any(
        not isinstance(item, CTraderDemoMutationLedgerRecord)
        for item in mutation_records
    ):
        raise AccountWideRiskError(
            "DEMO Risk reconciliation requires canonical mutation records"
        )

    confirmed: set[str] = set()
    for entry in registry_entries:
        authorization_id = entry.risk_authorization_id
        if authorization_id is None or entry.position_id is None:
            continue
        required = (
            entry.receipt_id,
            entry.idempotency_key,
            entry.authorized_source_volume,
            entry.source_contract_size_units,
        )
        if any(value is None for value in required):
            continue
        matches = tuple(
            item
            for item in mutation_records
            if (
                item.risk_authorization_id == authorization_id
                and item.receipt_id == entry.receipt_id
                and item.idempotency_key == entry.idempotency_key
                and item.provider_order_ref == entry.provider_order_ref
            )
        )
        if len(matches) > 1:
            raise AccountWideRiskError(
                "DEMO Risk reconciliation found ambiguous mutation lineage"
            )
        if not matches:
            continue
        mutation = matches[0]
        if not mutation.is_complete:
            continue
        try:
            expected_provider_quantity = (
                Decimal(str(entry.authorized_source_volume))
                * Decimal(str(entry.source_contract_size_units))
            )
            observed_provider_quantity = Decimal(
                str(mutation.cumulative_quantity)
            )
        except Exception as error:
            raise AccountWideRiskError(
                "DEMO Risk reconciliation fill quantity is invalid"
            ) from error
        if (
            expected_provider_quantity <= 0
            or observed_provider_quantity != expected_provider_quantity
        ):
            continue
        confirmed.add(authorization_id)
    return frozenset(confirmed)


def reconcile_demo_risk_reservations(
    *,
    risk: AccountWideRiskEngine,
    registry_entries: tuple[DemoTradeRegistryEntry, ...],
    confirmed_fill_authorization_ids: frozenset[str],
    terminal_settlement_keys: frozenset[tuple[str, int]],
    broker_open_position_ids: frozenset[int],
    provider_order_status: Callable[[str], int],
    observed_at: datetime,
) -> DemoRiskReservationReconciliation:
    """Reconcile internal Risk shadow without inferring provider lifecycle."""

    if not isinstance(risk, AccountWideRiskEngine):
        raise AccountWideRiskError(
            "DEMO Risk reconciliation requires AccountWideRiskEngine"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise AccountWideRiskError(
            "DEMO Risk reconciliation observed_at must be timezone-aware"
        )
    if not callable(provider_order_status):
        raise AccountWideRiskError(
            "DEMO Risk reconciliation requires provider order status"
        )

    by_authorization: dict[str, list[DemoTradeRegistryEntry]] = {}
    for entry in registry_entries:
        if not isinstance(entry, DemoTradeRegistryEntry):
            raise AccountWideRiskError(
                "DEMO Risk reconciliation registry entry is invalid"
            )
        if entry.risk_authorization_id is not None:
            by_authorization.setdefault(
                entry.risk_authorization_id,
                [],
            ).append(entry)

    pending = open_reconciled = released = cancelled = 0
    awaiting_fill = awaiting_terminal = 0
    blockers: list[str] = []
    reservations = risk.reservations()

    for reservation in reservations:
        if reservation.state in {
            ReservationState.RELEASED,
            ReservationState.EXPIRED,
        }:
            continue
        authorization = reservation.authorization
        rows = tuple(
            by_authorization.get(authorization.authorization_id, ())
        )
        if len(rows) != 1:
            blockers.append(
                "RISK_AUTHORIZATION_REGISTRY_BINDING_"
                f"{authorization.authorization_id}_COUNT_{len(rows)}"
            )
            continue
        entry = rows[0]
        if (
            entry.signal_fingerprint != authorization.signal_fingerprint
            or entry.request_id != authorization.request_id
        ):
            blockers.append(
                "RISK_AUTHORIZATION_REGISTRY_IDENTITY_DRIFT_"
                f"{authorization.authorization_id}"
            )
            continue

        if entry.position_id is None:
            try:
                status = provider_order_status(entry.provider_order_ref)
            except Exception as error:
                blockers.append(
                    "RISK_PROVIDER_ORDER_STATUS_UNAVAILABLE_"
                    f"{authorization.authorization_id}:"
                    f"{type(error).__name__}"
                )
                continue
            if status in _TERMINAL_ORDER_STATUSES:
                risk.cancel(authorization.authorization_id)
                cancelled += 1
            elif status in _ACTIVE_ORDER_STATUSES:
                pending += 1
            else:
                blockers.append(
                    "RISK_PROVIDER_ORDER_STATUS_UNSUPPORTED_"
                    f"{authorization.authorization_id}:{status}"
                )
            continue

        key = (entry.signal_fingerprint, entry.position_id)
        fill_confirmed = (
            authorization.authorization_id
            in confirmed_fill_authorization_ids
        )
        if entry.position_id in broker_open_position_ids:
            if not fill_confirmed:
                awaiting_fill += 1
                continue
            current = risk.reservation_for(
                authorization.authorization_id
            )
            if current is None:
                blockers.append(
                    "RISK_RESERVATION_DISAPPEARED_"
                    f"{authorization.authorization_id}"
                )
                continue
            if current.state in {
                ReservationState.RESERVED,
                ReservationState.PARTIALLY_FILLED,
            }:
                risk.record_full_fill(authorization.authorization_id)
                current = risk.reservation_for(
                    authorization.authorization_id
                )
            if (
                current is not None
                and current.state is ReservationState.FILLED_UNRECONCILED
            ):
                risk.reconcile_fill(authorization.authorization_id)
            open_reconciled += 1
            continue

        if key not in terminal_settlement_keys or not fill_confirmed:
            awaiting_terminal += 1
            continue
        risk.reconcile_terminal_release(
            authorization.authorization_id
        )
        released += 1

    return DemoRiskReservationReconciliation(
        inspected=sum(
            1
            for item in reservations
            if item.state
            not in {ReservationState.RELEASED, ReservationState.EXPIRED}
        ),
        broker_pending=pending,
        open_fill_reconciled=open_reconciled,
        terminal_settlement_released=released,
        terminal_order_cancelled=cancelled,
        awaiting_fill_evidence=awaiting_fill,
        awaiting_terminal_settlement=awaiting_terminal,
        blockers=tuple(blockers),
    )
