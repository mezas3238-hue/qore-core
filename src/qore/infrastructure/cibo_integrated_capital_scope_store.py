"""Durable account-scope companion ledger for legacy CIBO capital stores.

The legacy Source Ledger, T19 allocation store and CMA settlement store schemas
do not embed CiboAccountCapitalIdentity. Track B must not mutate those frozen
schemas retrospectively. This companion ledger binds their exact durable
component refs to one account identity using a hash-chained CAS store.

Any legacy component mutation makes the scope stale until an explicit reseal.
No productive authority is granted.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_integrated_capital_transaction_store import (
    IntegratedCapitalComponent,
    IntegratedCapitalComponentRef,
    IntegratedCapitalTransactionError,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

_SCHEMA = "CIBO_LEGACY_CAPITAL_STORE_SCOPE_BOOK_V1"
_GENESIS = "sha256:" + "0" * 64
_LEGACY_COMPONENTS = frozenset(
    {
        IntegratedCapitalComponent.SOURCE_LEDGER,
        IntegratedCapitalComponent.T19_ALLOCATION,
        IntegratedCapitalComponent.CMA_SETTLEMENT,
    }
)


@dataclass(frozen=True, slots=True)
class LegacyCapitalStoreScopeRecord:
    sequence: int
    account_identity: CiboAccountCapitalIdentity
    component_refs: tuple[IntegratedCapitalComponentRef, ...]
    sealed_at: datetime
    previous_chain_sha256: str
    chain_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence <= 0
        ):
            raise IntegratedCapitalTransactionError(
                "legacy scope sequence must be positive int"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise IntegratedCapitalTransactionError(
                "legacy scope account identity is invalid"
            )
        _validate_legacy_refs(self.component_refs)
        _aware(self.sealed_at)
        _sha(self.previous_chain_sha256, "previous chain")
        _sha(self.chain_sha256, "chain")
        expected = _chain_sha(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            account_identity=self.account_identity,
            refs=self.component_refs,
            sealed_at=self.sealed_at,
        )
        if self.chain_sha256 != expected:
            raise IntegratedCapitalTransactionError(
                "legacy scope chain digest mismatch"
            )


@dataclass(frozen=True, slots=True)
class VersionedLegacyCapitalStoreScopeBook:
    generation: int
    account_identity: CiboAccountCapitalIdentity
    records: tuple[LegacyCapitalStoreScopeRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise IntegratedCapitalTransactionError(
                "legacy scope generation is invalid"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise IntegratedCapitalTransactionError(
                "legacy scope book account identity is invalid"
            )
        if self.generation != len(self.records):
            raise IntegratedCapitalTransactionError(
                "legacy scope generation/record count drift"
            )
        previous = _GENESIS
        for sequence, record in enumerate(self.records, start=1):
            if record.sequence != sequence:
                raise IntegratedCapitalTransactionError(
                    "legacy scope sequence drift"
                )
            if record.account_identity != self.account_identity:
                raise IntegratedCapitalTransactionError(
                    "legacy scope crossed account domain"
                )
            if record.previous_chain_sha256 != previous:
                raise IntegratedCapitalTransactionError(
                    "legacy scope previous-chain drift"
                )
            previous = record.chain_sha256

    @property
    def current_refs(self) -> tuple[IntegratedCapitalComponentRef, ...] | None:
        return self.records[-1].component_refs if self.records else None

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS


class DurableLegacyCapitalStoreScopeStore:
    """Account-local hash-chain companion for legacy store scope."""

    def __init__(
        self,
        path: Path,
        *,
        account_identity: CiboAccountCapitalIdentity,
    ) -> None:
        if not isinstance(path, Path):
            raise IntegratedCapitalTransactionError(
                "legacy scope path must be pathlib.Path"
            )
        if not isinstance(
            account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise IntegratedCapitalTransactionError(
                "legacy scope account identity is invalid"
            )
        self._path = path
        self._account_identity = account_identity
        self._lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedLegacyCapitalStoreScopeBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        refs: tuple[IntegratedCapitalComponentRef, ...],
        *,
        sealed_at: datetime,
        expected_generation: int,
    ) -> VersionedLegacyCapitalStoreScopeBook:
        _validate_legacy_refs(refs)
        _aware(sealed_at)
        _expected_generation(expected_generation)
        with self._lock:
            self._acquire_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise IntegratedCapitalTransactionError(
                        "stale legacy scope generation"
                    )
                if current.current_refs == refs:
                    return current
                record = LegacyCapitalStoreScopeRecord(
                    sequence=current.generation + 1,
                    account_identity=self._account_identity,
                    component_refs=refs,
                    sealed_at=sealed_at,
                    previous_chain_sha256=current.chain_sha256,
                    chain_sha256=_chain_sha(
                        previous=current.chain_sha256,
                        sequence=current.generation + 1,
                        account_identity=self._account_identity,
                        refs=refs,
                        sealed_at=sealed_at,
                    ),
                )
                updated = VersionedLegacyCapitalStoreScopeBook(
                    generation=current.generation + 1,
                    account_identity=self._account_identity,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_lock()

    def verify(
        self,
        refs: tuple[IntegratedCapitalComponentRef, ...],
    ) -> VersionedLegacyCapitalStoreScopeBook:
        _validate_legacy_refs(refs)
        book = self.load()
        if book.generation <= 0 or book.current_refs is None:
            raise IntegratedCapitalTransactionError(
                "legacy capital store scope is not sealed"
            )
        if book.current_refs != refs:
            raise IntegratedCapitalTransactionError(
                "legacy capital store scope is stale"
            )
        return book

    def _load_unlocked(self) -> VersionedLegacyCapitalStoreScopeBook:
        if not self._path.exists():
            return VersionedLegacyCapitalStoreScopeBook(
                generation=0,
                account_identity=self._account_identity,
            )
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegratedCapitalTransactionError(
                "legacy scope store is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise IntegratedCapitalTransactionError(
                "legacy scope store schema mismatch"
            )
        try:
            generation = _payload_int(raw["generation"], "generation")
            identity = _identity_from_payload(raw["account_identity"])
            rows = raw["records"]
            if not isinstance(rows, list):
                raise TypeError("legacy scope records must be list")
            records = tuple(_record_from_payload(item) for item in rows)
        except (KeyError, TypeError, ValueError) as error:
            raise IntegratedCapitalTransactionError(
                "legacy scope store payload is invalid"
            ) from error
        if identity != self._account_identity:
            raise IntegratedCapitalTransactionError(
                "legacy scope store account identity drift"
            )
        return VersionedLegacyCapitalStoreScopeBook(
            generation=generation,
            account_identity=identity,
            records=records,
        )

    def _write_unlocked(
        self,
        book: VersionedLegacyCapitalStoreScopeBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "account_identity": _identity_payload(book.account_identity),
            "records": [_record_payload(item) for item in book.records],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError as error:
            raise IntegratedCapitalTransactionError(
                "legacy scope store write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_lock(self) -> None:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._lock_path.mkdir()
        except FileExistsError as error:
            raise IntegratedCapitalTransactionError(
                "legacy scope writer lock already held"
            ) from error
        except OSError as error:
            raise IntegratedCapitalTransactionError(
                "legacy scope writer lock unavailable"
            ) from error

    def _release_lock(self) -> None:
        try:
            self._lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise IntegratedCapitalTransactionError(
                "legacy scope writer lock release failed"
            ) from error


def _validate_legacy_refs(
    refs: tuple[IntegratedCapitalComponentRef, ...],
) -> None:
    if not isinstance(refs, tuple) or any(
        not isinstance(item, IntegratedCapitalComponentRef)
        for item in refs
    ):
        raise IntegratedCapitalTransactionError(
            "legacy scope refs must be canonical tuple"
        )
    components = tuple(item.component for item in refs)
    if len(components) != len(set(components)):
        raise IntegratedCapitalTransactionError(
            "legacy scope components are duplicated"
        )
    if set(components) != set(_LEGACY_COMPONENTS):
        raise IntegratedCapitalTransactionError(
            "legacy scope component coverage is incomplete"
        )


def _chain_sha(
    *,
    previous: str,
    sequence: int,
    account_identity: CiboAccountCapitalIdentity,
    refs: tuple[IntegratedCapitalComponentRef, ...],
    sealed_at: datetime,
) -> str:
    payload = {
        "previous": previous,
        "sequence": sequence,
        "account_identity": _identity_payload(account_identity),
        "refs": [_ref_payload(item) for item in refs],
        "sealed_at": sealed_at.isoformat(),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _record_payload(
    record: LegacyCapitalStoreScopeRecord,
) -> dict[str, object]:
    return {
        "sequence": record.sequence,
        "account_identity": _identity_payload(record.account_identity),
        "component_refs": [
            _ref_payload(item) for item in record.component_refs
        ],
        "sealed_at": record.sealed_at.isoformat(),
        "previous_chain_sha256": record.previous_chain_sha256,
        "chain_sha256": record.chain_sha256,
    }


def _record_from_payload(value: object) -> LegacyCapitalStoreScopeRecord:
    if not isinstance(value, dict):
        raise TypeError("legacy scope record must be object")
    identity = _identity_from_payload(value["account_identity"])
    refs_raw = value["component_refs"]
    if not isinstance(refs_raw, list):
        raise TypeError("legacy scope refs must be list")
    refs = tuple(_ref_from_payload(item) for item in refs_raw)
    return LegacyCapitalStoreScopeRecord(
        sequence=_payload_int(value["sequence"], "record sequence"),
        account_identity=identity,
        component_refs=refs,
        sealed_at=datetime.fromisoformat(str(value["sealed_at"])),
        previous_chain_sha256=str(value["previous_chain_sha256"]),
        chain_sha256=str(value["chain_sha256"]),
    )


def _ref_payload(
    ref: IntegratedCapitalComponentRef,
) -> dict[str, object]:
    return {
        "component": ref.component.value,
        "generation": ref.generation,
        "sha256": ref.sha256,
    }


def _ref_from_payload(value: object) -> IntegratedCapitalComponentRef:
    if not isinstance(value, dict):
        raise TypeError("legacy scope ref must be object")
    return IntegratedCapitalComponentRef(
        component=IntegratedCapitalComponent(str(value["component"])),
        generation=_payload_int(
            value["generation"],
            "component generation",
        ),
        sha256=str(value["sha256"]),
    )


def _identity_payload(
    identity: CiboAccountCapitalIdentity,
) -> dict[str, object]:
    return {
        "provider_key": identity.provider_key,
        "account_ref": identity.account_ref,
        "environment": identity.environment.value,
        "provider_program": identity.provider_program,
    }


def _identity_from_payload(value: object) -> CiboAccountCapitalIdentity:
    if not isinstance(value, dict):
        raise TypeError("legacy scope account identity must be object")
    provider_program_raw = value["provider_program"]
    provider_program = (
        None
        if provider_program_raw is None
        else str(provider_program_raw)
    )
    return CiboAccountCapitalIdentity(
        provider_key=str(value["provider_key"]),
        account_ref=str(value["account_ref"]),
        environment=MarketRuntimeEnvironment(str(value["environment"])),
        provider_program=provider_program,
    )


def _aware(value: datetime) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise IntegratedCapitalTransactionError(
            "legacy scope sealed_at must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise IntegratedCapitalTransactionError(
            f"legacy scope {name} is invalid"
        )


def _expected_generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise IntegratedCapitalTransactionError(
            "legacy scope expected_generation is invalid"
        )


def _payload_int(value: object, name: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise TypeError(f"legacy scope {name} must be non-negative int")
    return value
