"""Identity-safe durable stores for Phase22 V2 historical replay.

Phase22 is an empirically calibrated counterfactual historical replay. It must
not fabricate broker order, deal, fill or position identifiers for 2015-2016.
This module therefore stores deterministic research evidence with explicit
counterfactual identity while rejecting broker-shaped identity fields.

The store is append-only, generation-CAS protected and atomically persisted.
It has no broker mutation, Risk, sizing or productive authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from threading import RLock
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_SCHEMA = "CIBO_PHASE22_COUNTERFACTUAL_HISTORICAL_STORE_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ROLES = {
    "HOLDOUT_FORWARD_EVIDENCE",
    "HOLDOUT_POLICY",
    "EXECUTED_RISK",
    "CMA_SETTLEMENT",
    "T20_RELEASE",
}
_FORBIDDEN_IDENTITY_KEYS = {
    "position_id",
    "provider_order_ref",
    "settlement_deal_id",
    "settlement_deal_ids",
    "broker_order_id",
    "broker_deal_id",
    "broker_position_id",
    "order_id",
    "deal_id",
    "fill_id",
    "fill_evidence_refs",
}


class DurablePhase22HistoricalStoreError(CiboCapitalManagementError):
    """Phase22 historical evidence cannot be trusted or persisted safely."""


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DurablePhase22HistoricalStoreError(
            f"{name} must be timezone-aware"
        )


def _normalize(value: object) -> object:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise DurablePhase22HistoricalStoreError(
                "historical payload Decimal must be finite"
            )
        return format(value, "f")
    if isinstance(value, datetime):
        _aware(value, "historical payload datetime")
        return value.isoformat()
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key in sorted(value):
            if not isinstance(key, str) or not key:
                raise DurablePhase22HistoricalStoreError(
                    "historical payload keys must be non-empty strings"
                )
            if key in _FORBIDDEN_IDENTITY_KEYS:
                raise DurablePhase22HistoricalStoreError(
                    f"historical payload cannot contain broker identity field {key}"
                )
            normalized[key] = _normalize(value[key])
        return normalized
    if isinstance(value, (tuple, list)):
        return [_normalize(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise DurablePhase22HistoricalStoreError(
        f"historical payload type {type(value).__name__} is not supported"
    )


@dataclass(frozen=True, slots=True)
class Phase22HistoricalEvidenceRecord:
    """One deterministic counterfactual historical replay fact."""

    role: str
    signal_fingerprint: str
    trader_id: str
    qore_symbol: str
    market_event_at: datetime
    replay_sealed_at: datetime
    provider_model_sha256: str
    payload: dict[str, object]
    source_refs: tuple[str, ...]
    counterfactual_historical_replay: bool = True
    broker_identity_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.role not in _ROLES:
            raise DurablePhase22HistoricalStoreError(
                "historical evidence role invalid"
            )
        if _SHA256_RE.fullmatch(self.signal_fingerprint) is None:
            raise DurablePhase22HistoricalStoreError(
                "historical signal fingerprint invalid"
            )
        if _SHA256_RE.fullmatch(self.provider_model_sha256) is None:
            raise DurablePhase22HistoricalStoreError(
                "historical provider model digest invalid"
            )
        if not self.trader_id or not self.qore_symbol:
            raise DurablePhase22HistoricalStoreError(
                "historical Trader and symbol identities are required"
            )
        _aware(self.market_event_at, "market_event_at")
        _aware(self.replay_sealed_at, "replay_sealed_at")
        if self.replay_sealed_at <= self.market_event_at:
            raise DurablePhase22HistoricalStoreError(
                "historical replay seal must follow market event"
            )
        normalized = _normalize(self.payload)
        if not isinstance(normalized, dict):
            raise DurablePhase22HistoricalStoreError(
                "historical payload must normalize to object"
            )
        if not self.source_refs or any(not item for item in self.source_refs):
            raise DurablePhase22HistoricalStoreError(
                "historical source refs are required"
            )
        if len(self.source_refs) != len(set(self.source_refs)):
            raise DurablePhase22HistoricalStoreError(
                "historical source refs cannot duplicate"
            )
        if (
            not self.counterfactual_historical_replay
            or self.broker_identity_used
            or self.productive_authority
        ):
            raise DurablePhase22HistoricalStoreError(
                "historical evidence governance contamination"
            )

    def payload_for_hash(self) -> dict[str, object]:
        normalized = _normalize(self.payload)
        assert isinstance(normalized, dict)
        return {
            "role": self.role,
            "signal_fingerprint": self.signal_fingerprint,
            "trader_id": self.trader_id,
            "qore_symbol": self.qore_symbol,
            "market_event_at": self.market_event_at.isoformat(),
            "replay_sealed_at": self.replay_sealed_at.isoformat(),
            "provider_model_sha256": self.provider_model_sha256,
            "payload": normalized,
            "source_refs": list(self.source_refs),
            "counterfactual_historical_replay": True,
            "broker_identity_used": False,
            "productive_authority": False,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload_for_hash(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class VersionedPhase22HistoricalBook:
    role: str
    generation: int
    records: tuple[Phase22HistoricalEvidenceRecord, ...] = ()

    def __post_init__(self) -> None:
        if self.role not in _ROLES:
            raise DurablePhase22HistoricalStoreError(
                "historical book role invalid"
            )
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurablePhase22HistoricalStoreError(
                "historical generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise DurablePhase22HistoricalStoreError(
                "historical generation/record count drift"
            )
        if any(item.role != self.role for item in self.records):
            raise DurablePhase22HistoricalStoreError(
                "historical book contains foreign role"
            )
        ids = tuple(item.fingerprint() for item in self.records)
        if len(ids) != len(set(ids)):
            raise DurablePhase22HistoricalStoreError(
                "historical book contains duplicate record"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            {
                "schema": _SCHEMA,
                "role": self.role,
                "generation": self.generation,
                "record_sha256s": [
                    item.fingerprint() for item in self.records
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


class DurablePhase22HistoricalStore:
    """Append-only Phase22 store that cannot encode fake broker identity."""

    def __init__(self, path: Path, *, role: str) -> None:
        if not isinstance(path, Path):
            raise DurablePhase22HistoricalStoreError(
                "historical store path must be pathlib.Path"
            )
        if role not in _ROLES:
            raise DurablePhase22HistoricalStoreError(
                "historical store role invalid"
            )
        self._path = path
        self._role = role
        self._lock = RLock()

    def load(self) -> VersionedPhase22HistoricalBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        record: Phase22HistoricalEvidenceRecord,
        *,
        expected_generation: int,
    ) -> VersionedPhase22HistoricalBook:
        if not isinstance(record, Phase22HistoricalEvidenceRecord):
            raise DurablePhase22HistoricalStoreError(
                "historical store requires canonical record"
            )
        if record.role != self._role:
            raise DurablePhase22HistoricalStoreError(
                "historical record/store role drift"
            )
        with self._lock:
            current = self._load_unlocked()
            if current.generation != expected_generation:
                raise DurablePhase22HistoricalStoreError(
                    "stale historical store generation"
                )
            digest = record.fingerprint()
            for existing in current.records:
                if existing.fingerprint() == digest:
                    return current
            next_book = VersionedPhase22HistoricalBook(
                role=self._role,
                generation=current.generation + 1,
                records=current.records + (record,),
            )
            self._write_unlocked(next_book)
            return next_book

    def _load_unlocked(self) -> VersionedPhase22HistoricalBook:
        if not self._path.exists():
            return VersionedPhase22HistoricalBook(
                role=self._role,
                generation=0,
            )
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurablePhase22HistoricalStoreError(
                "historical store is unreadable"
            ) from error
        if (
            not isinstance(raw, dict)
            or raw.get("schema") != _SCHEMA
            or raw.get("role") != self._role
        ):
            raise DurablePhase22HistoricalStoreError(
                "historical store schema/role mismatch"
            )
        rows = raw.get("records")
        if not isinstance(rows, list):
            raise DurablePhase22HistoricalStoreError(
                "historical store records invalid"
            )
        try:
            records = tuple(
                Phase22HistoricalEvidenceRecord(
                    role=str(row["role"]),
                    signal_fingerprint=str(row["signal_fingerprint"]),
                    trader_id=str(row["trader_id"]),
                    qore_symbol=str(row["qore_symbol"]),
                    market_event_at=datetime.fromisoformat(
                        str(row["market_event_at"])
                    ),
                    replay_sealed_at=datetime.fromisoformat(
                        str(row["replay_sealed_at"])
                    ),
                    provider_model_sha256=str(
                        row["provider_model_sha256"]
                    ),
                    payload=dict(row["payload"]),
                    source_refs=tuple(
                        str(item) for item in row["source_refs"]
                    ),
                    counterfactual_historical_replay=bool(
                        row["counterfactual_historical_replay"]
                    ),
                    broker_identity_used=bool(row["broker_identity_used"]),
                    productive_authority=bool(row["productive_authority"]),
                )
                for row in rows
            )
            generation = int(raw["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise DurablePhase22HistoricalStoreError(
                "historical store record payload invalid"
            ) from error
        return VersionedPhase22HistoricalBook(
            role=self._role,
            generation=generation,
            records=records,
        )

    def _write_unlocked(self, book: VersionedPhase22HistoricalBook) -> None:
        payload: dict[str, Any] = {
            "schema": _SCHEMA,
            "role": self._role,
            "generation": book.generation,
            "records": [item.payload_for_hash() for item in book.records],
            "counterfactual_historical_replay": True,
            "broker_identity_used": False,
            "productive_authority": False,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            temporary.write_text(
                json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, self._path)
        except OSError as error:
            raise DurablePhase22HistoricalStoreError(
                "historical store write failed"
            ) from error
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
