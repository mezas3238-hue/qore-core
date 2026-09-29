"""Durable hash-chain store for the GEN-C2 protected capital floor.

The store persists account-local floor snapshots with generation CAS, a
cross-process writer lock and atomic replace. It has no sizing, Risk, execution,
broker, DEMO-governed, LIVE or real-capital authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundProtectionClass,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
    ProtectedFloorEvent,
    ProtectedFloorEventType,
    ProtectedFloorTranche,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

_SCHEMA = "QORE_CIBO_PROTECTED_CAPITAL_FLOOR_STORE_V1"
_GENESIS = "sha256:" + ("0" * 64)


@dataclass(frozen=True, slots=True)
class ProtectedFloorStoreRecord:
    sequence: int
    payload_json: str
    payload_sha256: str
    previous_chain_sha256: str
    chain_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence < 1
        ):
            raise CiboCompoundCapitalError(
                "protected floor store sequence must be positive int"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            _require_sha(getattr(self, name), name)
        digest = "sha256:" + hashlib.sha256(
            self.payload_json.encode()
        ).hexdigest()
        if digest != self.payload_sha256:
            raise CiboCompoundCapitalError(
                "protected floor payload digest mismatch"
            )
        expected = _chain_sha(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            payload_sha256=self.payload_sha256,
        )
        if expected != self.chain_sha256:
            raise CiboCompoundCapitalError(
                "protected floor chain digest mismatch"
            )
        _ledger_from_json(self.payload_json)


@dataclass(frozen=True, slots=True)
class VersionedProtectedFloorBook:
    generation: int
    account_identity: CiboAccountCapitalIdentity
    records: tuple[ProtectedFloorStoreRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCompoundCapitalError(
                "protected floor generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise CiboCompoundCapitalError(
                "protected floor generation/record count drift"
            )
        previous = _GENESIS
        prior_floor = Decimal(0)
        for expected_sequence, record in enumerate(self.records, start=1):
            if record.sequence != expected_sequence:
                raise CiboCompoundCapitalError(
                    "protected floor record sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise CiboCompoundCapitalError(
                    "protected floor previous-chain drift"
                )
            ledger = _ledger_from_json(record.payload_json)
            if ledger.account_identity != self.account_identity:
                raise CiboCompoundCapitalError(
                    "protected floor store crossed account domain"
                )
            if ledger.total_floor_usd < prior_floor:
                raise CiboCompoundCapitalError(
                    "protected floor durable history ratcheted downward"
                )
            prior_floor = ledger.total_floor_usd
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    @property
    def ledger(self) -> ProtectedCapitalFloorLedger:
        if not self.records:
            return ProtectedCapitalFloorLedger(
                account_identity=self.account_identity
            )
        return _ledger_from_json(self.records[-1].payload_json)


class DurableProtectedCapitalFloorStore:
    """Atomic account-local durable floor store."""

    def __init__(
        self,
        path: Path,
        *,
        account_identity: CiboAccountCapitalIdentity,
    ) -> None:
        if not isinstance(path, Path):
            raise CiboCompoundCapitalError(
                "protected floor store path must be pathlib.Path"
            )
        if not isinstance(
            account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "protected floor store account identity is invalid"
            )
        self._path = path
        self._account_identity = account_identity
        self._writer_lock_path = path.with_name(
            f".{path.name}.writer-lock"
        )
        self._lock = RLock()

    def load(self) -> VersionedProtectedFloorBook:
        with self._lock:
            return self._load_unlocked()

    def store(
        self,
        ledger: ProtectedCapitalFloorLedger,
        *,
        expected_generation: int,
    ) -> VersionedProtectedFloorBook:
        if not isinstance(ledger, ProtectedCapitalFloorLedger):
            raise CiboCompoundCapitalError(
                "protected floor store requires canonical ledger"
            )
        if ledger.account_identity != self._account_identity:
            raise CiboCompoundCapitalError(
                "protected floor store cannot cross account domains"
            )
        _expected_generation(expected_generation)

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise CiboCompoundCapitalError(
                        "protected floor store generation conflict"
                    )
                if current.generation and current.ledger == ledger:
                    return current
                if ledger.total_floor_usd < current.ledger.total_floor_usd:
                    raise CiboCompoundCapitalError(
                        "protected floor cannot ratchet downward"
                    )

                payload_json = _ledger_json(ledger)
                payload_sha = "sha256:" + hashlib.sha256(
                    payload_json.encode()
                ).hexdigest()
                record = ProtectedFloorStoreRecord(
                    sequence=current.generation + 1,
                    payload_json=payload_json,
                    payload_sha256=payload_sha,
                    previous_chain_sha256=current.chain_sha256,
                    chain_sha256=_chain_sha(
                        previous=current.chain_sha256,
                        sequence=current.generation + 1,
                        payload_sha256=payload_sha,
                    ),
                )
                updated = VersionedProtectedFloorBook(
                    generation=current.generation + 1,
                    account_identity=self._account_identity,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedProtectedFloorBook:
        if not self._path.exists():
            return VersionedProtectedFloorBook(
                generation=0,
                account_identity=self._account_identity,
            )
        try:
            payload = json.loads(
                self._path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise CiboCompoundCapitalError(
                "protected floor store unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != _SCHEMA
        ):
            raise CiboCompoundCapitalError(
                "protected floor store schema mismatch"
            )
        identity = _identity_from_payload(
            payload.get("account_identity")
        )
        if identity != self._account_identity:
            raise CiboCompoundCapitalError(
                "protected floor store account identity mismatch"
            )
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise CiboCompoundCapitalError(
                "protected floor store records must be list"
            )
        try:
            records = tuple(
                ProtectedFloorStoreRecord(
                    sequence=int(row["sequence"]),
                    payload_json=str(row["payload_json"]),
                    payload_sha256=str(row["payload_sha256"]),
                    previous_chain_sha256=str(
                        row["previous_chain_sha256"]
                    ),
                    chain_sha256=str(row["chain_sha256"]),
                )
                for row in raw_records
                if isinstance(row, dict)
            )
            if len(records) != len(raw_records):
                raise TypeError("protected floor record must be object")
            generation = int(payload["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise CiboCompoundCapitalError(
                "protected floor store payload invalid"
            ) from error
        book = VersionedProtectedFloorBook(
            generation=generation,
            account_identity=identity,
            records=records,
        )
        if payload.get("chain_sha256") != book.chain_sha256:
            raise CiboCompoundCapitalError(
                "protected floor terminal chain mismatch"
            )
        return book

    def _write_unlocked(
        self,
        book: VersionedProtectedFloorBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "account_identity": _identity_payload(
                book.account_identity
            ),
            "generation": book.generation,
            "chain_sha256": book.chain_sha256,
            "records": [
                {
                    "sequence": row.sequence,
                    "payload_json": row.payload_json,
                    "payload_sha256": row.payload_sha256,
                    "previous_chain_sha256": (
                        row.previous_chain_sha256
                    ),
                    "chain_sha256": row.chain_sha256,
                }
                for row in book.records
            ],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temp.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        payload,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self._path)
        except OSError as error:
            raise CiboCompoundCapitalError(
                "protected floor store write failed"
            ) from error
        finally:
            temp.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise CiboCompoundCapitalError(
                "protected floor writer lock already held"
            ) from error
        except OSError as error:
            raise CiboCompoundCapitalError(
                "protected floor writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise CiboCompoundCapitalError(
                "protected floor writer lock release failed"
            ) from error


def _ledger_json(ledger: ProtectedCapitalFloorLedger) -> str:
    return json.dumps(
        {
            "account_identity": _identity_payload(
                ledger.account_identity
            ),
            "tranches": [
                _tranche_payload(item) for item in ledger.tranches
            ],
            "events": [
                _event_payload(item) for item in ledger.events
            ],
            "runtime_authority": ledger.runtime_authority,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _ledger_from_json(value: str) -> ProtectedCapitalFloorLedger:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            "protected floor ledger JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            "protected floor ledger payload must be object"
        )
    try:
        raw_tranches = payload["tranches"]
        raw_events = payload["events"]
        runtime_authority = payload["runtime_authority"]
        if (
            not isinstance(raw_tranches, list)
            or not isinstance(raw_events, list)
            or type(runtime_authority) is not bool
        ):
            raise TypeError("protected floor ledger collections invalid")
        return ProtectedCapitalFloorLedger(
            account_identity=_identity_from_payload(
                payload["account_identity"]
            ),
            tranches=tuple(
                _tranche_from_payload(row) for row in raw_tranches
            ),
            events=tuple(
                _event_from_payload(row) for row in raw_events
            ),
            runtime_authority=runtime_authority,
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "protected floor ledger payload invalid"
        ) from error


def _identity_payload(
    identity: CiboAccountCapitalIdentity,
) -> dict[str, object]:
    return {
        "provider_key": identity.provider_key,
        "account_ref": identity.account_ref,
        "environment": identity.environment.value,
        "provider_program": identity.provider_program,
    }


def _identity_from_payload(
    value: object,
) -> CiboAccountCapitalIdentity:
    if not isinstance(value, dict):
        raise CiboCompoundCapitalError(
            "protected floor identity payload invalid"
        )
    try:
        program = value.get("provider_program")
        if program is not None:
            program = str(program)
        return CiboAccountCapitalIdentity(
            provider_key=str(value["provider_key"]),
            account_ref=str(value["account_ref"]),
            environment=MarketRuntimeEnvironment(
                str(value["environment"])
            ),
            provider_program=program,
        )
    except (KeyError, ValueError) as error:
        raise CiboCompoundCapitalError(
            "protected floor identity payload invalid"
        ) from error


def _tranche_payload(
    tranche: ProtectedFloorTranche,
) -> dict[str, object]:
    return {
        "tranche_id": tranche.tranche_id,
        "account_identity": _identity_payload(
            tranche.account_identity
        ),
        "source_compound_lot_id": tranche.source_compound_lot_id,
        "amount_usd": str(tranche.amount_usd),
        "protection_class": tranche.protection_class.value,
        "admitted_at": tranche.admitted_at.isoformat(),
        "policy_id": tranche.policy_id,
        "policy_sha256": tranche.policy_sha256,
        "broker_guarantee_evidence_id": (
            tranche.broker_guarantee_evidence_id
        ),
        "broker_guarantee_sha256": (
            tranche.broker_guarantee_sha256
        ),
        "runtime_authority": tranche.runtime_authority,
    }


def _tranche_from_payload(value: object) -> ProtectedFloorTranche:
    if not isinstance(value, dict):
        raise CiboCompoundCapitalError(
            "protected floor tranche payload invalid"
        )
    try:
        policy_id = value.get("policy_id")
        policy_sha = value.get("policy_sha256")
        broker_id = value.get("broker_guarantee_evidence_id")
        broker_sha = value.get("broker_guarantee_sha256")
        runtime_authority = value["runtime_authority"]
        if type(runtime_authority) is not bool:
            raise TypeError("protected floor authority flag invalid")
        return ProtectedFloorTranche(
            tranche_id=str(value["tranche_id"]),
            account_identity=_identity_from_payload(
                value["account_identity"]
            ),
            source_compound_lot_id=str(
                value["source_compound_lot_id"]
            ),
            amount_usd=Decimal(str(value["amount_usd"])),
            protection_class=CompoundProtectionClass(
                str(value["protection_class"])
            ),
            admitted_at=datetime.fromisoformat(
                str(value["admitted_at"])
            ),
            policy_id=None if policy_id is None else str(policy_id),
            policy_sha256=(
                None if policy_sha is None else str(policy_sha)
            ),
            broker_guarantee_evidence_id=(
                None if broker_id is None else str(broker_id)
            ),
            broker_guarantee_sha256=(
                None if broker_sha is None else str(broker_sha)
            ),
            runtime_authority=runtime_authority,
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "protected floor tranche payload invalid"
        ) from error


def _event_payload(event: ProtectedFloorEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "tranche_id": event.tranche_id,
        "occurred_at": event.occurred_at.isoformat(),
        "floor_before_usd": str(event.floor_before_usd),
        "floor_after_usd": str(event.floor_after_usd),
        "from_class": (
            None if event.from_class is None else event.from_class.value
        ),
        "to_class": event.to_class.value,
        "evidence_ref": event.evidence_ref,
    }


def _event_from_payload(value: object) -> ProtectedFloorEvent:
    if not isinstance(value, dict):
        raise CiboCompoundCapitalError(
            "protected floor event payload invalid"
        )
    try:
        from_class = value.get("from_class")
        return ProtectedFloorEvent(
            event_id=str(value["event_id"]),
            event_type=ProtectedFloorEventType(
                str(value["event_type"])
            ),
            tranche_id=str(value["tranche_id"]),
            occurred_at=datetime.fromisoformat(
                str(value["occurred_at"])
            ),
            floor_before_usd=Decimal(
                str(value["floor_before_usd"])
            ),
            floor_after_usd=Decimal(
                str(value["floor_after_usd"])
            ),
            from_class=(
                None
                if from_class is None
                else CompoundProtectionClass(str(from_class))
            ),
            to_class=CompoundProtectionClass(
                str(value["to_class"])
            ),
            evidence_ref=str(value["evidence_ref"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "protected floor event payload invalid"
        ) from error


def _chain_sha(
    *,
    previous: str,
    sequence: int,
    payload_sha256: str,
) -> str:
    raw = f"{previous}|{sequence}|{payload_sha256}".encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _require_sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"protected floor {name} must be canonical SHA-256"
        )


def _expected_generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            "protected floor expected generation must be non-negative int"
        )
