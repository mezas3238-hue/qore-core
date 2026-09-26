"""Durable reservation ledger for FundedNext account-wide Risk.

The base Risk engine is intentionally pure/in-memory.  This operational wrapper
persists every capital reservation transition before exposing the new state and
requires an explicit fresh broker/account reconciliation after restart before it
will authorize another order.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import RLock
from typing import Protocol

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    AccountWideRiskError,
    CiboCapitalProvenanceLot,
    CiboRiskRequest,
    ReservationState,
    RiskAuthorization,
    RiskCapitalConstraintEnvelope,
    RiskDecision,
    RiskReservation,
    TraderLineage,
)

_SCHEMA = "qore.account-wide-risk-ledger.v1"


class AccountWideRiskLedger(Protocol):
    def load(self) -> tuple[RiskReservation, ...]: ...

    def store(self, reservations: tuple[RiskReservation, ...]) -> None: ...


class InMemoryAccountWideRiskLedger:
    def __init__(self) -> None:
        self._items: tuple[RiskReservation, ...] = ()

    def load(self) -> tuple[RiskReservation, ...]:
        return self._items

    def store(self, reservations: tuple[RiskReservation, ...]) -> None:
        self._items = tuple(reservations)


class DurableAccountWideRiskLedger:
    """Atomic JSON snapshot store; credentials/account secrets are never persisted."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise AccountWideRiskError("risk ledger path must be pathlib.Path")
        self._path = path
        self._lock = RLock()

    def load(self) -> tuple[RiskReservation, ...]:
        with self._lock:
            if not self._path.exists():
                return ()
            try:
                payload = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise AccountWideRiskError("durable risk ledger is unreadable") from error
            if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
                raise AccountWideRiskError("durable risk ledger schema mismatch")
            raw_items = payload.get("reservations")
            if not isinstance(raw_items, list):
                raise AccountWideRiskError("durable risk ledger reservations missing")
            return tuple(_reservation_from_payload(item) for item in raw_items)

    def store(self, reservations: tuple[RiskReservation, ...]) -> None:
        with self._lock:
            payload = {
                "schema": _SCHEMA,
                "reservations": [
                    _reservation_payload(item)
                    for item in sorted(
                        reservations,
                        key=lambda item: item.authorization.authorization_id,
                    )
                ],
            }
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_name(f".{self._path.name}.tmp")
            encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
            try:
                with temporary.open("w", encoding="utf-8") as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self._path)
            except OSError as error:
                raise AccountWideRiskError("durable risk ledger write failed") from error
            finally:
                if temporary.exists():
                    temporary.unlink()


class DurableAccountWideRiskEngine(AccountWideRiskEngine):
    """Account-wide Risk with durable reservations and a restart recovery fence."""

    def __init__(self, ledger: AccountWideRiskLedger) -> None:
        if not callable(getattr(ledger, "load", None)) or not callable(
            getattr(ledger, "store", None)
        ):
            raise AccountWideRiskError("durable account-wide Risk ledger is required")
        super().__init__()
        self._durable_ledger = ledger
        restored = ledger.load()
        for item in restored:
            auth_id = item.authorization.authorization_id
            if auth_id in self._reservations:
                raise AccountWideRiskError("duplicate durable Risk authorization")
            self._reservations[auth_id] = item
            self._signal_to_authorization[item.authorization.signal_fingerprint] = auth_id
        self._recovery_required = any(
            item.state not in {ReservationState.RELEASED, ReservationState.EXPIRED}
            for item in restored
        )

    @property
    def recovery_required(self) -> bool:
        return self._recovery_required

    def complete_boot_reconciliation(
        self,
        snapshot: AccountRiskSnapshot,
        *,
        now: datetime,
        max_snapshot_age: timedelta = timedelta(seconds=10),
    ) -> None:
        if not isinstance(snapshot, AccountRiskSnapshot):
            raise AccountWideRiskError("boot reconciliation requires account snapshot")
        _aware(now, "now")
        if max_snapshot_age <= timedelta(0):
            raise AccountWideRiskError("max_snapshot_age must be positive")
        if snapshot.reconciled_at > now or now - snapshot.reconciled_at > max_snapshot_age:
            raise AccountWideRiskError("boot reconciliation snapshot is stale")
        active_accounts = {
            item.authorization.account_binding_id
            for item in self._reservations.values()
            if item.state not in {ReservationState.RELEASED, ReservationState.EXPIRED}
        }
        if active_accounts and active_accounts != {snapshot.account_binding_id}:
            raise AccountWideRiskError("boot reconciliation account binding mismatch")
        self._recovery_required = False

    def capital_constraint_envelope(
        self,
        snapshot: AccountRiskSnapshot,
        *,
        now: datetime,
    ) -> RiskCapitalConstraintEnvelope:
        if self._recovery_required:
            raise AccountWideRiskError(
                "restart-reconciliation-required-before-capital-envelope"
            )
        return super().capital_constraint_envelope(snapshot, now=now)

    def authorize(
        self,
        request: CiboRiskRequest,
        snapshot: AccountRiskSnapshot,
        *,
        now: datetime,
    ) -> RiskAuthorization:
        if self._recovery_required:
            raise AccountWideRiskError(
                "restart-reconciliation-required-before-new-risk-authorization"
            )
        result = super().authorize(request, snapshot, now=now)
        self._persist()
        return result

    def cancel(self, authorization_id: str) -> None:
        super().cancel(authorization_id)
        self._persist()

    def record_partial_fill(
        self,
        authorization_id: str,
        *,
        filled_volume: Decimal,
    ) -> None:
        super().record_partial_fill(
            authorization_id,
            filled_volume=filled_volume,
        )
        self._persist()

    def record_full_fill(self, authorization_id: str) -> None:
        super().record_full_fill(authorization_id)
        self._persist()

    def reconcile_fill(self, authorization_id: str) -> None:
        super().reconcile_fill(authorization_id)
        self._persist()

    def expire(self, *, now: datetime) -> None:
        super().expire(now=now)
        self._persist()

    def _persist(self) -> None:
        self._durable_ledger.store(tuple(self._reservations.values()))


def _reservation_payload(item: RiskReservation) -> dict[str, object]:
    auth = item.authorization
    return {
        "authorization": {
            "authorization_id": auth.authorization_id,
            "account_binding_id": auth.account_binding_id,
            "trader_id": auth.trader_id.value,
            "request_id": auth.request_id,
            "signal_fingerprint": auth.signal_fingerprint,
            "qore_symbol": auth.qore_symbol,
            "provider_symbol": auth.provider_symbol,
            "side": auth.side,
            "entry_type": auth.entry_type,
            "intended_entry": str(auth.intended_entry),
            "stop_loss": str(auth.stop_loss),
            "take_profit": str(auth.take_profit),
            "requested_volume": str(auth.requested_volume),
            "authorized_volume": str(auth.authorized_volume),
            "monetary_stop_loss": str(auth.monetary_stop_loss),
            "aggregate_pre_order_worst_case": str(auth.aggregate_pre_order_worst_case),
            "aggregate_post_order_worst_case": str(auth.aggregate_post_order_worst_case),
            "provider_headroom": str(auth.provider_headroom),
            "internal_qore_headroom": str(auth.internal_qore_headroom),
            "margin_reserved": str(auth.margin_reserved),
            "decision": auth.decision.value,
            "reason": auth.reason,
            "issued_at": auth.issued_at.isoformat(),
            "expires_at": auth.expires_at.isoformat(),
            "authorization_fingerprint": auth.authorization_fingerprint,
            "capital_provenance": [
                {
                    "source_kind": item.source_kind,
                    "source_id": item.source_id,
                    "amount_usd": str(item.amount_usd),
                }
                for item in auth.capital_provenance
            ],
        },
        "pending_stop_risk": str(item.pending_stop_risk),
        "pending_margin": str(item.pending_margin),
        "filled_unreconciled_stop_risk": str(item.filled_unreconciled_stop_risk),
        "state": item.state.value,
    }


def _reservation_from_payload(value: object) -> RiskReservation:
    if not isinstance(value, dict):
        raise AccountWideRiskError("durable Risk reservation must be object")
    raw_auth = value.get("authorization")
    if not isinstance(raw_auth, dict):
        raise AccountWideRiskError("durable Risk authorization missing")
    try:
        auth = RiskAuthorization(
            authorization_id=str(raw_auth["authorization_id"]),
            account_binding_id=str(raw_auth["account_binding_id"]),
            trader_id=TraderLineage(str(raw_auth["trader_id"])),
            request_id=str(raw_auth["request_id"]),
            signal_fingerprint=str(raw_auth["signal_fingerprint"]),
            qore_symbol=str(raw_auth["qore_symbol"]),
            provider_symbol=str(raw_auth["provider_symbol"]),
            side=str(raw_auth["side"]),
            entry_type=str(raw_auth["entry_type"]),
            intended_entry=Decimal(str(raw_auth["intended_entry"])),
            stop_loss=Decimal(str(raw_auth["stop_loss"])),
            take_profit=Decimal(str(raw_auth["take_profit"])),
            requested_volume=Decimal(str(raw_auth["requested_volume"])),
            authorized_volume=Decimal(str(raw_auth["authorized_volume"])),
            monetary_stop_loss=Decimal(str(raw_auth["monetary_stop_loss"])),
            aggregate_pre_order_worst_case=Decimal(
                str(raw_auth["aggregate_pre_order_worst_case"])
            ),
            aggregate_post_order_worst_case=Decimal(
                str(raw_auth["aggregate_post_order_worst_case"])
            ),
            provider_headroom=Decimal(str(raw_auth["provider_headroom"])),
            internal_qore_headroom=Decimal(str(raw_auth["internal_qore_headroom"])),
            margin_reserved=Decimal(str(raw_auth["margin_reserved"])),
            decision=RiskDecision(str(raw_auth["decision"])),
            reason=str(raw_auth["reason"]),
            issued_at=datetime.fromisoformat(str(raw_auth["issued_at"])),
            expires_at=datetime.fromisoformat(str(raw_auth["expires_at"])),
            authorization_fingerprint=str(raw_auth["authorization_fingerprint"]),
            capital_provenance=tuple(
                CiboCapitalProvenanceLot(
                    source_kind=str(item["source_kind"]),
                    source_id=str(item["source_id"]),
                    amount_usd=Decimal(str(item["amount_usd"])),
                )
                for item in raw_auth.get("capital_provenance", [])
                if isinstance(item, dict)
            ),
        )
        return RiskReservation(
            authorization=auth,
            pending_stop_risk=Decimal(str(value["pending_stop_risk"])),
            pending_margin=Decimal(str(value["pending_margin"])),
            filled_unreconciled_stop_risk=Decimal(
                str(value["filled_unreconciled_stop_risk"])
            ),
            state=ReservationState(str(value["state"])),
        )
    except (KeyError, ValueError) as error:
        raise AccountWideRiskError("durable Risk reservation is invalid") from error


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AccountWideRiskError(f"{name} must be timezone-aware")
