"""Durable mutation fence for certified H4 containment exits."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.fundednext.position-exit-ledger.v1"


class FundedNextPositionExitError(InfrastructureError):
    __slots__ = ()


class PositionExitState(StrEnum):
    ATTEMPT_STARTED = "attempt_started"
    OUTCOME_UNKNOWN = "outcome_unknown"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class PositionExitRecord:
    source_client_order_id: str
    provider_position_ref: str
    symbol: str
    magic: int
    due_at: datetime
    state: PositionExitState
    transitioned_at: datetime
    provider_deal_ref: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("source_client_order_id", self.source_client_order_id),
            ("provider_position_ref", self.provider_position_ref),
            ("symbol", self.symbol),
        ):
            if not value:
                raise FundedNextPositionExitError(f"{name} required")
        if self.magic <= 0:
            raise FundedNextPositionExitError("magic must be positive")
        for timestamp_name, timestamp_value in (
            ("due_at", self.due_at),
            ("transitioned_at", self.transitioned_at),
        ):
            if timestamp_value.tzinfo is None or timestamp_value.utcoffset() is None:
                raise FundedNextPositionExitError(
                    f"{timestamp_name} must be timezone-aware"
                )
        if type(self.state) is not PositionExitState:
            raise FundedNextPositionExitError("exit state must be canonical")

    @property
    def key(self) -> str:
        return f"{self.source_client_order_id}|{self.provider_position_ref}"

    def transition(
        self,
        *,
        state: PositionExitState,
        transitioned_at: datetime,
        provider_deal_ref: str | None = None,
        reason: str | None = None,
    ) -> PositionExitRecord:
        return replace(
            self,
            state=state,
            transitioned_at=transitioned_at,
            provider_deal_ref=(provider_deal_ref or self.provider_deal_ref),
            reason=reason,
        )


class JsonFileFundedNextPositionExitLedger:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._records = self._load()

    def records(self) -> tuple[PositionExitRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    @property
    def has_unresolved(self) -> bool:
        return any(
            record.state in {PositionExitState.ATTEMPT_STARTED, PositionExitState.OUTCOME_UNKNOWN}
            for record in self._records.values()
        )

    def upsert(self, record: PositionExitRecord) -> None:
        if not isinstance(record, PositionExitRecord):
            raise FundedNextPositionExitError("canonical exit record required")
        next_records = dict(self._records)
        next_records[record.key] = record
        self._commit(next_records)
        self._records = next_records

    def mark_interrupted_unknown(self, *, now: datetime) -> None:
        for record in self.records():
            if record.state is PositionExitState.ATTEMPT_STARTED:
                self.upsert(
                    record.transition(
                        state=PositionExitState.OUTCOME_UNKNOWN,
                        transitioned_at=now,
                        reason="runtime-restart-after-exit-fence",
                    )
                )

    def _load(self) -> dict[str, PositionExitRecord]:
        if not self._path.exists():
            return {}
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
                raise FundedNextPositionExitError("position exit ledger schema mismatch")
            raw_records = payload.get("records")
            if not isinstance(raw_records, list):
                raise FundedNextPositionExitError("position exit records missing")
            records = tuple(_from_payload(item) for item in raw_records)
        except (OSError, json.JSONDecodeError) as error:
            raise FundedNextPositionExitError("position exit ledger unreadable") from error
        mapped = {record.key: record for record in records}
        if len(mapped) != len(records):
            raise FundedNextPositionExitError("duplicate position exit records")
        return mapped

    def _commit(self, records: dict[str, PositionExitRecord]) -> None:
        payload = {
            "schema": _SCHEMA,
            "records": [_payload(records[key]) for key in sorted(records)],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.", suffix=".tmp", dir=self._path.parent
        )
        temp = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self._path)
        finally:
            if temp.exists():
                temp.unlink()


def _payload(record: PositionExitRecord) -> dict[str, object]:
    return {
        "source_client_order_id": record.source_client_order_id,
        "provider_position_ref": record.provider_position_ref,
        "symbol": record.symbol,
        "magic": record.magic,
        "due_at": record.due_at.isoformat(),
        "state": record.state.value,
        "transitioned_at": record.transitioned_at.isoformat(),
        "provider_deal_ref": record.provider_deal_ref,
        "reason": record.reason,
    }


def _from_payload(value: object) -> PositionExitRecord:
    if not isinstance(value, dict):
        raise FundedNextPositionExitError("exit record must be object")
    try:
        return PositionExitRecord(
            source_client_order_id=str(value["source_client_order_id"]),
            provider_position_ref=str(value["provider_position_ref"]),
            symbol=str(value["symbol"]),
            magic=int(value["magic"]),
            due_at=datetime.fromisoformat(str(value["due_at"])),
            state=PositionExitState(str(value["state"])),
            transitioned_at=datetime.fromisoformat(str(value["transitioned_at"])),
            provider_deal_ref=(
                None if value.get("provider_deal_ref") is None else str(value["provider_deal_ref"])
            ),
            reason=None if value.get("reason") is None else str(value["reason"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise FundedNextPositionExitError("invalid position exit record") from error
