"""Durable mutation fence for FundedNext Stellar Instant MT5 execution.

The ledger is committed before any provider mutation.  A process restart after
that fence converts an in-flight attempt to OUTCOME_UNKNOWN so recovery may only
reconcile/discover the original order; it can never blindly resubmit it.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Protocol

from qore.infrastructure.execution_boundary import ExecutionBoundaryError, ExecutionSubmission


class FundedNextMt5MutationLedgerError(ExecutionBoundaryError):
    """Durable MT5 mutation evidence could not be read or committed safely."""

    __slots__ = ()


class FundedNextMt5MutationState(StrEnum):
    ATTEMPT_STARTED = "attempt_started"
    OUTCOME_UNKNOWN = "outcome_unknown"
    NOT_SUBMITTED = "not_submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


def fundednext_submission_digest(submission: ExecutionSubmission) -> str:
    if not isinstance(submission, ExecutionSubmission):
        raise FundedNextMt5MutationLedgerError(
            "submission digest requires canonical ExecutionSubmission"
        )
    canonical = json.dumps(
        submission.logical_values(),
        default=str,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


@dataclass(frozen=True, slots=True)
class FundedNextMt5MutationRecord:
    idempotency_key: str
    receipt_id: str
    submission_digest: str
    client_order_id: str
    state: FundedNextMt5MutationState
    transitioned_at: datetime
    risk_authorization_id: str
    risk_authorization_fingerprint: str
    risk_reservation_id: str
    provider_order_ref: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.idempotency_key, "idempotency_key"),
            (self.receipt_id, "receipt_id"),
            (self.submission_digest, "submission_digest"),
            (self.client_order_id, "client_order_id"),
            (self.risk_authorization_id, "risk_authorization_id"),
            (self.risk_authorization_fingerprint, "risk_authorization_fingerprint"),
            (self.risk_reservation_id, "risk_reservation_id"),
        ):
            if not isinstance(value, str) or not value:
                raise FundedNextMt5MutationLedgerError(f"{name} must be non-empty")
        if not self.submission_digest.startswith("sha256:"):
            raise FundedNextMt5MutationLedgerError("submission_digest must be SHA-256")
        if len(self.risk_authorization_fingerprint) != 64:
            raise FundedNextMt5MutationLedgerError(
                "risk_authorization_fingerprint must be raw SHA-256 hex"
            )
        if type(self.state) is not FundedNextMt5MutationState:
            raise FundedNextMt5MutationLedgerError("state must be canonical")
        if self.transitioned_at.tzinfo is None or self.transitioned_at.utcoffset() is None:
            raise FundedNextMt5MutationLedgerError("transitioned_at must be timezone-aware")
        if self.provider_order_ref is not None and not self.provider_order_ref:
            raise FundedNextMt5MutationLedgerError(
                "provider_order_ref must be non-empty or None"
            )
        if self.reason is not None and not self.reason:
            raise FundedNextMt5MutationLedgerError("reason must be non-empty or None")

    def transition(
        self,
        *,
        state: FundedNextMt5MutationState,
        transitioned_at: datetime,
        provider_order_ref: str | None = None,
        reason: str | None = None,
    ) -> FundedNextMt5MutationRecord:
        return replace(
            self,
            state=state,
            transitioned_at=transitioned_at,
            provider_order_ref=(
                provider_order_ref
                if provider_order_ref is not None
                else self.provider_order_ref
            ),
            reason=reason,
        )

    def as_json(self) -> dict[str, object]:
        return {
            "client_order_id": self.client_order_id,
            "idempotency_key": self.idempotency_key,
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
    def from_json(cls, value: object) -> FundedNextMt5MutationRecord:
        if not isinstance(value, dict):
            raise FundedNextMt5MutationLedgerError("ledger record must be an object")
        try:
            return cls(
                idempotency_key=value["idempotency_key"],
                receipt_id=value["receipt_id"],
                submission_digest=value["submission_digest"],
                client_order_id=value["client_order_id"],
                state=FundedNextMt5MutationState(value["state"]),
                transitioned_at=datetime.fromisoformat(value["transitioned_at"]),
                risk_authorization_id=value["risk_authorization_id"],
                risk_authorization_fingerprint=value[
                    "risk_authorization_fingerprint"
                ],
                risk_reservation_id=value["risk_reservation_id"],
                provider_order_ref=value.get("provider_order_ref"),
                reason=value.get("reason"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise FundedNextMt5MutationLedgerError(
                "invalid durable FundedNext MT5 mutation record"
            ) from error


class FundedNextMt5MutationLedger(Protocol):
    def records(self) -> tuple[FundedNextMt5MutationRecord, ...]: ...

    def upsert(self, record: FundedNextMt5MutationRecord) -> None: ...


class InMemoryFundedNextMt5MutationLedger:
    """Deterministic test ledger; operational wiring must use durable storage."""

    def __init__(self) -> None:
        self._records: dict[str, FundedNextMt5MutationRecord] = {}

    def records(self) -> tuple[FundedNextMt5MutationRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def upsert(self, record: FundedNextMt5MutationRecord) -> None:
        if not isinstance(record, FundedNextMt5MutationRecord):
            raise FundedNextMt5MutationLedgerError(
                "upsert requires FundedNextMt5MutationRecord"
            )
        self._records[record.idempotency_key] = record


class JsonFileFundedNextMt5MutationLedger:
    """Single-file journal committed with fsync plus atomic replace."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or not path.name:
            raise FundedNextMt5MutationLedgerError("ledger path must be concrete")
        self._path = path
        self._lock = Lock()
        self._records = self._load()

    def _load(self) -> dict[str, FundedNextMt5MutationRecord]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if raw.get("schema_version") != self.SCHEMA_VERSION:
                raise FundedNextMt5MutationLedgerError(
                    "unsupported FundedNext MT5 mutation-ledger schema"
                )
            parsed = tuple(
                FundedNextMt5MutationRecord.from_json(item)
                for item in raw.get("records", ())
            )
        except (OSError, AttributeError, json.JSONDecodeError, TypeError) as error:
            raise FundedNextMt5MutationLedgerError(
                "FundedNext MT5 mutation ledger is unreadable"
            ) from error
        records = {record.idempotency_key: record for record in parsed}
        if len(records) != len(parsed):
            raise FundedNextMt5MutationLedgerError("mutation ledger has duplicate keys")
        return records

    def records(self) -> tuple[FundedNextMt5MutationRecord, ...]:
        with self._lock:
            return tuple(self._records[key] for key in sorted(self._records))

    def upsert(self, record: FundedNextMt5MutationRecord) -> None:
        if not isinstance(record, FundedNextMt5MutationRecord):
            raise FundedNextMt5MutationLedgerError(
                "upsert requires FundedNextMt5MutationRecord"
            )
        with self._lock:
            next_records = dict(self._records)
            next_records[record.idempotency_key] = record
            self._commit(next_records)
            self._records = next_records

    def _commit(self, records: dict[str, FundedNextMt5MutationRecord]) -> None:
        last_error: OSError | None = None
        for attempt in range(3):
            try:
                self._commit_once(records)
                return
            except OSError as error:
                last_error = error
                if attempt < 2:
                    time.sleep(0.01 * (attempt + 1))
        assert last_error is not None
        raise FundedNextMt5MutationLedgerError(
            "atomic FundedNext MT5 mutation-ledger commit failed"
        ) from last_error

    def _commit_once(
        self,
        records: dict[str, FundedNextMt5MutationRecord],
    ) -> None:
        parent = self._path.parent
        parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.", suffix=".tmp", dir=parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(
                    {
                        "records": [
                            records[key].as_json() for key in sorted(records)
                        ],
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
            _fsync_parent_directory(parent)
        finally:
            if temporary.exists():
                temporary.unlink()


def _fsync_parent_directory(parent: Path) -> None:
    if os.name == "nt":
        return
    directory_fd = os.open(parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
