"""Atomic durable ledger for cTrader DEMO mutation fences and reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Protocol

from qore.infrastructure.ctrader_demo_execution_contracts import CTraderDemoAttemptState
from qore.infrastructure.execution_boundary import ExecutionBoundaryError, ExecutionSubmission


class CTraderDemoMutationLedgerError(ExecutionBoundaryError):
    """The durable mutation fence could not be read or committed safely."""

    __slots__ = ()


def ctrader_submission_digest(submission: ExecutionSubmission) -> str:
    """Return a stable digest without persisting credentials or account identifiers."""
    if not isinstance(submission, ExecutionSubmission):
        raise CTraderDemoMutationLedgerError("submission digest requires ExecutionSubmission")
    canonical = json.dumps(
        submission.logical_values(),
        default=str,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


@dataclass(frozen=True, slots=True)
class CTraderDemoMutationLedgerRecord:
    """Recoverable evidence for one and only one provider mutation."""

    idempotency_key: str
    receipt_id: str
    submission_digest: str
    client_order_id: str
    state: CTraderDemoAttemptState
    transitioned_at: datetime
    provider_order_ref: str | None = None
    reason: str | None = None
    outcome: str | None = None
    fill_refs: tuple[str, ...] = ()
    fill_identities: tuple[tuple[str, str], ...] = ()
    cumulative_quantity: str = "0"
    is_complete: bool = False
    risk_authorization_id: str | None = None
    risk_authorization_fingerprint: str | None = None
    risk_reservation_id: str | None = None

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.idempotency_key, "idempotency_key"),
            (self.receipt_id, "receipt_id"),
            (self.submission_digest, "submission_digest"),
            (self.client_order_id, "client_order_id"),
            (self.cumulative_quantity, "cumulative_quantity"),
        ):
            if not isinstance(value, str) or not value:
                raise CTraderDemoMutationLedgerError(f"{field_name} must be non-empty")
        if not self.submission_digest.startswith("sha256:"):
            raise CTraderDemoMutationLedgerError("submission_digest must be SHA-256")
        if not isinstance(self.state, CTraderDemoAttemptState):
            raise CTraderDemoMutationLedgerError("state must be CTraderDemoAttemptState")
        if self.transitioned_at.tzinfo is None or self.transitioned_at.utcoffset() is None:
            raise CTraderDemoMutationLedgerError("transitioned_at must be timezone-aware")
        if type(self.is_complete) is not bool:
            raise CTraderDemoMutationLedgerError("is_complete must be a strict bool")
        if not isinstance(self.fill_refs, tuple) or any(
            not isinstance(item, str) or not item for item in self.fill_refs
        ):
            raise CTraderDemoMutationLedgerError("fill_refs must contain non-empty strings")
        if not isinstance(self.fill_identities, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or any(not isinstance(part, str) or not part for part in item)
            for item in self.fill_identities
        ):
            raise CTraderDemoMutationLedgerError(
                "fill_identities must contain reference/digest pairs"
            )

    def with_risk(
        self,
        *,
        authorization_id: str,
        authorization_fingerprint: str,
        reservation_id: str,
    ) -> CTraderDemoMutationLedgerRecord:
        return replace(
            self,
            risk_authorization_id=authorization_id,
            risk_authorization_fingerprint=authorization_fingerprint,
            risk_reservation_id=reservation_id,
        )

    def as_json(self) -> dict[str, object]:
        return {
            "client_order_id": self.client_order_id,
            "cumulative_quantity": self.cumulative_quantity,
            "fill_refs": list(self.fill_refs),
            "fill_identities": [list(item) for item in self.fill_identities],
            "idempotency_key": self.idempotency_key,
            "is_complete": self.is_complete,
            "outcome": self.outcome,
            "provider_order_ref": self.provider_order_ref,
            "reason": self.reason,
            "receipt_id": self.receipt_id,
            "risk_authorization_fingerprint": self.risk_authorization_fingerprint,
            "risk_authorization_id": self.risk_authorization_id,
            "risk_reservation_id": self.risk_reservation_id,
            "state": self.state.value,
            "submission_digest": self.submission_digest,
            "transitioned_at": self.transitioned_at.isoformat(),
        }

    @classmethod
    def from_json(cls, value: object) -> CTraderDemoMutationLedgerRecord:
        if not isinstance(value, dict):
            raise CTraderDemoMutationLedgerError("ledger record must be an object")
        try:
            return cls(
                idempotency_key=value["idempotency_key"],
                receipt_id=value["receipt_id"],
                submission_digest=value["submission_digest"],
                client_order_id=value["client_order_id"],
                state=CTraderDemoAttemptState(value["state"]),
                transitioned_at=datetime.fromisoformat(value["transitioned_at"]),
                provider_order_ref=value.get("provider_order_ref"),
                reason=value.get("reason"),
                outcome=value.get("outcome"),
                fill_refs=tuple(value.get("fill_refs", ())),
                fill_identities=tuple(
                    tuple(item) for item in value.get("fill_identities", ())
                ),
                cumulative_quantity=value.get("cumulative_quantity", "0"),
                is_complete=value.get("is_complete", False),
                risk_authorization_id=value.get("risk_authorization_id"),
                risk_authorization_fingerprint=value.get("risk_authorization_fingerprint"),
                risk_reservation_id=value.get("risk_reservation_id"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise CTraderDemoMutationLedgerError("invalid durable mutation record") from error


class CTraderDemoMutationLedger(Protocol):
    """Durability port whose upsert must complete before a broker mutation."""

    def records(self) -> tuple[CTraderDemoMutationLedgerRecord, ...]: ...

    def upsert(self, record: CTraderDemoMutationLedgerRecord) -> None: ...


class InMemoryCTraderDemoMutationLedger:
    """Deterministic unit-test implementation; operational wiring uses the file ledger."""

    def __init__(self) -> None:
        self._records: dict[str, CTraderDemoMutationLedgerRecord] = {}

    def records(self) -> tuple[CTraderDemoMutationLedgerRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def upsert(self, record: CTraderDemoMutationLedgerRecord) -> None:
        self._records[record.idempotency_key] = record


class JsonFileCTraderDemoMutationLedger:
    """Single-file journal committed with fsync + atomic replace in one directory."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or not path.name:
            raise CTraderDemoMutationLedgerError("ledger path must be a concrete Path")
        self._path = path
        self._lock = Lock()
        self._records = self._load()

    def _load(self) -> dict[str, CTraderDemoMutationLedgerRecord]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if raw.get("schema_version") != self.SCHEMA_VERSION:
                raise CTraderDemoMutationLedgerError("unsupported mutation ledger schema")
            parsed = tuple(
                CTraderDemoMutationLedgerRecord.from_json(item)
                for item in raw.get("records", ())
            )
        except (OSError, AttributeError, json.JSONDecodeError, TypeError) as error:
            raise CTraderDemoMutationLedgerError("mutation ledger is unreadable") from error
        records = {item.idempotency_key: item for item in parsed}
        if len(records) != len(parsed):
            raise CTraderDemoMutationLedgerError("mutation ledger has duplicate keys")
        return records

    def records(self) -> tuple[CTraderDemoMutationLedgerRecord, ...]:
        with self._lock:
            return tuple(self._records[key] for key in sorted(self._records))

    def upsert(self, record: CTraderDemoMutationLedgerRecord) -> None:
        if not isinstance(record, CTraderDemoMutationLedgerRecord):
            raise CTraderDemoMutationLedgerError("upsert requires a mutation ledger record")
        with self._lock:
            next_records = dict(self._records)
            next_records[record.idempotency_key] = record
            self._commit(next_records)
            self._records = next_records

    def _commit(self, records: dict[str, CTraderDemoMutationLedgerRecord]) -> None:
        parent = self._path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self._path.name}.", suffix=".tmp", dir=parent
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    json.dump(
                        {
                            "records": [records[key].as_json() for key in sorted(records)],
                            "schema_version": self.SCHEMA_VERSION,
                        },
                        stream,
                        ensure_ascii=True,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self._path)
                directory_fd = os.open(parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if temporary.exists():
                    temporary.unlink()
        except OSError as error:
            raise CTraderDemoMutationLedgerError("atomic mutation ledger commit failed") from error
