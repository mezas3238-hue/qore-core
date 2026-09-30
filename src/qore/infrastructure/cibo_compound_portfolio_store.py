"""Durable append-only store for the GEN-C1 Core Compound Portfolio.

Each write appends a canonical full-ledger snapshot to a SHA-256 hash chain.
The store uses generation CAS, a cross-process writer lock and atomic replace.
It is research-only and grants no sizing, Risk, execution or broker authority.
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

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalLot,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioEvent,
    CompoundPortfolioEventType,
    CompoundPortfolioLedger,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

_SCHEMA = "QORE_CIBO_COMPOUND_PORTFOLIO_STORE_V1"
_GENESIS = "sha256:" + ("0" * 64)


@dataclass(frozen=True, slots=True)
class CompoundPortfolioStoreRecord:
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
                "compound store sequence must be positive int"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            _require_sha(getattr(self, name), name)
        expected_payload = "sha256:" + hashlib.sha256(
            self.payload_json.encode("utf-8")
        ).hexdigest()
        if self.payload_sha256 != expected_payload:
            raise CiboCompoundCapitalError(
                "compound store payload digest mismatch"
            )
        expected_chain = _chain_sha(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            payload_sha256=self.payload_sha256,
        )
        if self.chain_sha256 != expected_chain:
            raise CiboCompoundCapitalError(
                "compound store chain digest mismatch"
            )
        _ledger_from_json(self.payload_json)


@dataclass(frozen=True, slots=True)
class VersionedCompoundPortfolioBook:
    generation: int
    account_identity: CiboAccountCapitalIdentity
    records: tuple[CompoundPortfolioStoreRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCompoundCapitalError(
                "compound store generation must be non-negative int"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "compound store account identity is invalid"
            )
        if self.generation != len(self.records):
            raise CiboCompoundCapitalError(
                "compound store generation/record count drift"
            )
        previous = _GENESIS
        for sequence, record in enumerate(self.records, start=1):
            if record.sequence != sequence:
                raise CiboCompoundCapitalError(
                    "compound store record sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise CiboCompoundCapitalError(
                    "compound store previous-chain drift"
                )
            ledger = _ledger_from_json(record.payload_json)
            if ledger.account_identity != self.account_identity:
                raise CiboCompoundCapitalError(
                    "compound store record crossed account domain"
                )
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    @property
    def ledger(self) -> CompoundPortfolioLedger:
        if not self.records:
            return CompoundPortfolioLedger(
                account_identity=self.account_identity,
            )
        return _ledger_from_json(self.records[-1].payload_json)


class DurableCompoundPortfolioStore:
    """Atomic account-scoped hash-chain store with generation CAS."""

    def __init__(
        self,
        path: Path,
        *,
        account_identity: CiboAccountCapitalIdentity,
    ) -> None:
        if not isinstance(path, Path):
            raise CiboCompoundCapitalError(
                "compound store path must be pathlib.Path"
            )
        if not isinstance(
            account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "compound store account identity is invalid"
            )
        self._path = path
        self._account_identity = account_identity
        self._writer_lock_path = path.with_name(
            f".{path.name}.writer-lock"
        )
        self._lock = RLock()

    def load(self) -> VersionedCompoundPortfolioBook:
        with self._lock:
            return self._load_unlocked()

    def store(
        self,
        ledger: CompoundPortfolioLedger,
        *,
        expected_generation: int,
    ) -> VersionedCompoundPortfolioBook:
        if not isinstance(ledger, CompoundPortfolioLedger):
            raise CiboCompoundCapitalError(
                "compound store requires canonical ledger"
            )
        if ledger.account_identity != self._account_identity:
            raise CiboCompoundCapitalError(
                "compound store cannot cross account domains"
            )
        _expected_generation(expected_generation)

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise CiboCompoundCapitalError(
                        "compound store generation conflict"
                    )
                if (
                    current.generation > 0
                    and current.ledger == ledger
                ):
                    return current

                payload_json = _ledger_json(ledger)
                payload_sha = "sha256:" + hashlib.sha256(
                    payload_json.encode("utf-8")
                ).hexdigest()
                record = CompoundPortfolioStoreRecord(
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
                updated = VersionedCompoundPortfolioBook(
                    generation=current.generation + 1,
                    account_identity=self._account_identity,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedCompoundPortfolioBook:
        if not self._path.exists():
            return VersionedCompoundPortfolioBook(
                generation=0,
                account_identity=self._account_identity,
            )
        try:
            payload = json.loads(
                self._path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise CiboCompoundCapitalError(
                "compound store is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != _SCHEMA
        ):
            raise CiboCompoundCapitalError(
                "compound store schema mismatch"
            )
        stored_identity = _identity_from_payload(
            payload.get("account_identity")
        )
        if stored_identity != self._account_identity:
            raise CiboCompoundCapitalError(
                "compound store account identity mismatch"
            )
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise CiboCompoundCapitalError(
                "compound store records must be list"
            )
        try:
            records = tuple(
                CompoundPortfolioStoreRecord(
                    sequence=int(item["sequence"]),
                    payload_json=str(item["payload_json"]),
                    payload_sha256=str(item["payload_sha256"]),
                    previous_chain_sha256=str(
                        item["previous_chain_sha256"]
                    ),
                    chain_sha256=str(item["chain_sha256"]),
                )
                for item in raw_records
                if isinstance(item, dict)
            )
            if len(records) != len(raw_records):
                raise TypeError("compound store record must be object")
            generation = int(payload["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise CiboCompoundCapitalError(
                "compound store payload invalid"
            ) from error
        book = VersionedCompoundPortfolioBook(
            generation=generation,
            account_identity=stored_identity,
            records=records,
        )
        if payload.get("chain_sha256") != book.chain_sha256:
            raise CiboCompoundCapitalError(
                "compound store terminal chain mismatch"
            )
        return book

    def _write_unlocked(
        self,
        book: VersionedCompoundPortfolioBook,
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
                    "sequence": item.sequence,
                    "payload_json": item.payload_json,
                    "payload_sha256": item.payload_sha256,
                    "previous_chain_sha256": (
                        item.previous_chain_sha256
                    ),
                    "chain_sha256": item.chain_sha256,
                }
                for item in book.records
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
                "compound store write failed"
            ) from error
        finally:
            temp.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise CiboCompoundCapitalError(
                "compound store writer lock already held"
            ) from error
        except OSError as error:
            raise CiboCompoundCapitalError(
                "compound store writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise CiboCompoundCapitalError(
                "compound store writer lock release failed"
            ) from error


def _ledger_json(ledger: CompoundPortfolioLedger) -> str:
    payload = {
        "account_identity": _identity_payload(
            ledger.account_identity
        ),
        "active_lots": [
            _lot_payload(item) for item in ledger.active_lots
        ],
        "archived_lots": [
            _lot_payload(item) for item in ledger.archived_lots
        ],
        "events": [
            _event_payload(item) for item in ledger.events
        ],
        "runtime_authority": ledger.runtime_authority,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )


def _ledger_from_json(value: str) -> CompoundPortfolioLedger:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            "compound ledger JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            "compound ledger payload must be object"
        )
    try:
        active_raw = payload["active_lots"]
        archived_raw = payload["archived_lots"]
        events_raw = payload["events"]
        if (
            not isinstance(active_raw, list)
            or not isinstance(archived_raw, list)
            or not isinstance(events_raw, list)
        ):
            raise TypeError("compound ledger lists invalid")
        runtime_authority = payload["runtime_authority"]
        if type(runtime_authority) is not bool:
            raise TypeError("compound runtime authority invalid")
        return CompoundPortfolioLedger(
            account_identity=_identity_from_payload(
                payload["account_identity"]
            ),
            active_lots=tuple(
                _lot_from_payload(item) for item in active_raw
            ),
            archived_lots=tuple(
                _lot_from_payload(item) for item in archived_raw
            ),
            events=tuple(
                _event_from_payload(item) for item in events_raw
            ),
            runtime_authority=runtime_authority,
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "compound ledger payload invalid"
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
            "compound account identity payload invalid"
        )
    try:
        provider_program = value.get("provider_program")
        if provider_program is not None:
            provider_program = str(provider_program)
        return CiboAccountCapitalIdentity(
            provider_key=str(value["provider_key"]),
            account_ref=str(value["account_ref"]),
            environment=MarketRuntimeEnvironment(
                str(value["environment"])
            ),
            provider_program=provider_program,
        )
    except (KeyError, ValueError) as error:
        raise CiboCompoundCapitalError(
            "compound account identity payload invalid"
        ) from error


def _lot_payload(lot: CompoundCapitalLot) -> dict[str, object]:
    return {
        "lot_id": lot.lot_id,
        "account_identity": _identity_payload(
            lot.account_identity
        ),
        "amount_usd": str(lot.amount_usd),
        "state": lot.state.value,
        "generation": lot.generation,
        "origin_evidence_id": lot.origin_evidence_id,
        "origin_trader": lot.origin_trader.value,
        "origin_signal_fingerprint": (
            lot.origin_signal_fingerprint
        ),
        "origin_position_id": lot.origin_position_id,
        "origin_deal_ids": list(lot.origin_deal_ids),
        "realized_at": lot.realized_at.isoformat(),
        "created_at": lot.created_at.isoformat(),
        "parent_lot_ids": list(lot.parent_lot_ids),
        "core_owned": lot.core_owned,
        "runtime_authority": lot.runtime_authority,
    }


def _lot_from_payload(value: object) -> CompoundCapitalLot:
    if not isinstance(value, dict):
        raise CiboCompoundCapitalError(
            "compound lot payload invalid"
        )
    try:
        deal_ids = value["origin_deal_ids"]
        parent_ids = value["parent_lot_ids"]
        if not isinstance(deal_ids, list) or not isinstance(
            parent_ids,
            list,
        ):
            raise TypeError("compound lot lists invalid")
        core_owned = value["core_owned"]
        runtime_authority = value["runtime_authority"]
        if (
            type(core_owned) is not bool
            or type(runtime_authority) is not bool
        ):
            raise TypeError("compound lot authority flags invalid")
        return CompoundCapitalLot(
            lot_id=str(value["lot_id"]),
            account_identity=_identity_from_payload(
                value["account_identity"]
            ),
            amount_usd=Decimal(str(value["amount_usd"])),
            state=CompoundCapitalState(str(value["state"])),
            generation=int(value["generation"]),
            origin_evidence_id=str(value["origin_evidence_id"]),
            origin_trader=TraderLineage(
                str(value["origin_trader"])
            ),
            origin_signal_fingerprint=str(
                value["origin_signal_fingerprint"]
            ),
            origin_position_id=int(value["origin_position_id"]),
            origin_deal_ids=tuple(int(item) for item in deal_ids),
            realized_at=datetime.fromisoformat(
                str(value["realized_at"])
            ),
            created_at=datetime.fromisoformat(
                str(value["created_at"])
            ),
            parent_lot_ids=tuple(str(item) for item in parent_ids),
            core_owned=core_owned,
            runtime_authority=runtime_authority,
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "compound lot payload invalid"
        ) from error


def _event_payload(
    event: CompoundPortfolioEvent,
) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "occurred_at": event.occurred_at.isoformat(),
        "source_lot_ids": list(event.source_lot_ids),
        "target_lot_ids": list(event.target_lot_ids),
        "source_total_usd": str(event.source_total_usd),
        "target_total_usd": str(event.target_total_usd),
        "detail": event.detail,
    }


def _event_from_payload(value: object) -> CompoundPortfolioEvent:
    if not isinstance(value, dict):
        raise CiboCompoundCapitalError(
            "compound event payload invalid"
        )
    try:
        sources = value["source_lot_ids"]
        targets = value["target_lot_ids"]
        if not isinstance(sources, list) or not isinstance(
            targets,
            list,
        ):
            raise TypeError("compound event lot lists invalid")
        return CompoundPortfolioEvent(
            event_id=str(value["event_id"]),
            event_type=CompoundPortfolioEventType(
                str(value["event_type"])
            ),
            occurred_at=datetime.fromisoformat(
                str(value["occurred_at"])
            ),
            source_lot_ids=tuple(str(item) for item in sources),
            target_lot_ids=tuple(str(item) for item in targets),
            source_total_usd=Decimal(
                str(value["source_total_usd"])
            ),
            target_total_usd=Decimal(
                str(value["target_total_usd"])
            ),
            detail=str(value["detail"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "compound event payload invalid"
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
            f"compound store {name} must be canonical SHA-256"
        )


def _expected_generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            "compound store expected generation must be non-negative int"
        )
