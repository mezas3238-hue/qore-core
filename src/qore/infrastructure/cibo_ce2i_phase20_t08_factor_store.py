"""Durable delayed full-universe factor evidence for CE2I T08.

This collector contract is intentionally outside the execution-critical 2-second
path. It accepts immutable boundary opens after they have finalized, records the
actual time each fact became known, and seals a complete six-market snapshot.

Delayed observation is causal: a snapshot may be used only by decisions after
its final observed_at. No signal/candidate is required, so the sample is not
conditioned on Trader opportunity production.
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

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    FROZEN_T08_MARKET_SYMBOLS,
    T08FactorMarketSnapshot,
    T08FactorReturnObservation,
    T08MarketCollectionBasis,
    T08MarketMark,
    reconstruct_t08_factor_returns,
)

_SCHEMA = "CIBO_PHASE20_T08_FACTOR_EVIDENCE_V1"
_GENESIS = "sha256:" + ("0" * 64)


class DurableT08FactorEvidenceError(CiboCapitalManagementError):
    """T08 factor evidence cannot be trusted or updated safely."""


@dataclass(frozen=True, slots=True)
class T08FinalizedBoundaryOpen:
    qore_symbol: str
    boundary_at: datetime
    open_price: Decimal
    observed_at: datetime
    evidence_ref: str
    finalized: bool

    def __post_init__(self) -> None:
        symbol = self.qore_symbol.strip().upper()
        if symbol != self.qore_symbol or symbol not in FROZEN_T08_MARKET_SYMBOLS:
            raise DurableT08FactorEvidenceError(
                "T08 finalized boundary symbol outside frozen universe"
            )
        _aware(self.boundary_at, "T08 finalized boundary_at")
        _aware(self.observed_at, "T08 finalized observed_at")
        if self.observed_at < self.boundary_at:
            raise DurableT08FactorEvidenceError(
                "T08 finalized boundary cannot be observed before boundary"
            )
        if (
            not isinstance(self.open_price, Decimal)
            or not self.open_price.is_finite()
            or self.open_price <= 0
        ):
            raise DurableT08FactorEvidenceError(
                "T08 finalized boundary open must be positive finite Decimal"
            )
        if not self.evidence_ref:
            raise DurableT08FactorEvidenceError(
                "T08 finalized boundary evidence_ref is required"
            )
        if type(self.finalized) is not bool:
            raise DurableT08FactorEvidenceError(
                "T08 finalized flag must be bool"
            )


def build_delayed_t08_factor_snapshot(
    *,
    provider_key: str,
    boundary_opens: tuple[T08FinalizedBoundaryOpen, ...],
) -> T08FactorMarketSnapshot:
    """Seal one unbiased six-market boundary after source finalization."""

    if not provider_key:
        raise DurableT08FactorEvidenceError(
            "T08 delayed factor provider_key is required"
        )
    if len(boundary_opens) != len(FROZEN_T08_MARKET_SYMBOLS):
        raise DurableT08FactorEvidenceError(
            "T08 delayed factor snapshot requires exact frozen universe"
        )
    symbols = tuple(sorted(item.qore_symbol for item in boundary_opens))
    if symbols != FROZEN_T08_MARKET_SYMBOLS:
        raise DurableT08FactorEvidenceError(
            "T08 delayed factor snapshot requires exact frozen universe"
        )
    boundaries = {item.boundary_at for item in boundary_opens}
    if len(boundaries) != 1:
        raise DurableT08FactorEvidenceError(
            "T08 delayed factor snapshot requires one common boundary"
        )
    if not all(item.finalized for item in boundary_opens):
        raise DurableT08FactorEvidenceError(
            "T08 delayed factor snapshot requires finalized source opens"
        )

    boundary_at = next(iter(boundaries))
    observed_at = max(item.observed_at for item in boundary_opens)
    marks = tuple(
        T08MarketMark(
            qore_symbol=item.qore_symbol,
            bid=item.open_price,
            ask=item.open_price,
            price_at=boundary_at,
            observed_at=item.observed_at,
            evidence_ref=item.evidence_ref,
        )
        for item in sorted(
            boundary_opens,
            key=lambda value: value.qore_symbol,
        )
    )
    material = {
        "schema": _SCHEMA,
        "provider_key": provider_key,
        "boundary_at": boundary_at.isoformat(),
        "observed_at": observed_at.isoformat(),
        "marks": [
            {
                "qore_symbol": item.qore_symbol,
                "open_price": str(item.mid),
                "observed_at": item.observed_at.isoformat(),
                "evidence_ref": item.evidence_ref,
            }
            for item in marks
        ],
    }
    return T08FactorMarketSnapshot(
        snapshot_id="sha256:" + _sha256_json(material),
        provider_key=provider_key,
        market_at=boundary_at,
        observed_at=observed_at,
        collection_basis=T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE,
        marks=marks,
    )


@dataclass(frozen=True, slots=True)
class VersionedT08FactorEvidenceBook:
    generation: int
    snapshots: tuple[T08FactorMarketSnapshot, ...]
    chain_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence generation must be non-negative int"
            )
        if self.generation != len(self.snapshots):
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence generation/snapshot count drift"
            )
        if not _valid_sha(self.chain_sha256):
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence chain SHA invalid"
            )
        _validate_snapshot_order(self.snapshots)
        if self.chain_sha256 != _chain_sha(self.snapshots):
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence chain verification failed"
            )


class DurableT08FactorEvidenceStore:
    """Append-only atomic file store for delayed full-universe T08 snapshots."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()

    def load(self) -> VersionedT08FactorEvidenceBook:
        with self._lock:
            if not self.path.exists():
                return VersionedT08FactorEvidenceBook(
                    generation=0,
                    snapshots=(),
                    chain_sha256=_GENESIS,
                )
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise DurableT08FactorEvidenceError(
                    "T08 factor evidence store unreadable"
                ) from error
            return _book_from_payload(payload)

    def append(
        self,
        snapshot: T08FactorMarketSnapshot,
        *,
        expected_generation: int,
    ) -> VersionedT08FactorEvidenceBook:
        if not isinstance(snapshot, T08FactorMarketSnapshot):
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence append requires canonical snapshot"
            )
        if not snapshot.complete_frozen_universe:
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence append requires full-universe snapshot"
            )
        with self._lock:
            current = self.load()
            if current.generation != expected_generation:
                raise DurableT08FactorEvidenceError(
                    "T08 factor evidence generation conflict"
                )
            for prior in current.snapshots:
                if prior.snapshot_id == snapshot.snapshot_id:
                    return current
                if (
                    prior.provider_key == snapshot.provider_key
                    and prior.market_at == snapshot.market_at
                ):
                    raise DurableT08FactorEvidenceError(
                        "T08 factor evidence conflicting snapshot at boundary"
                    )
            snapshots = current.snapshots + (snapshot,)
            _validate_snapshot_order(snapshots)
            updated = VersionedT08FactorEvidenceBook(
                generation=current.generation + 1,
                snapshots=snapshots,
                chain_sha256=_chain_sha(snapshots),
            )
            self._write(updated)
            return updated

    def _write(self, book: VersionedT08FactorEvidenceBook) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        target = self.path
        temp = target.with_name(target.name + ".tmp")
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "chain_sha256": book.chain_sha256,
            "snapshots": [_snapshot_payload(item) for item in book.snapshots],
        }
        try:
            temp.write_text(
                json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()


def causal_t08_factor_return_history(
    book: VersionedT08FactorEvidenceBook,
    *,
    known_by: datetime,
) -> tuple[T08FactorReturnObservation, ...]:
    """Build adjacent return intervals using only snapshots known by cutoff."""

    if not isinstance(book, VersionedT08FactorEvidenceBook):
        raise DurableT08FactorEvidenceError(
            "T08 factor history requires canonical evidence book"
        )
    _aware(known_by, "T08 factor history known_by")
    eligible = tuple(
        item
        for item in book.snapshots
        if item.observed_at <= known_by
    )
    returns: list[T08FactorReturnObservation] = []
    for start, end in zip(eligible, eligible[1:], strict=False):
        if start.provider_key != end.provider_key:
            continue
        returns.append(
            reconstruct_t08_factor_returns(start=start, end=end)
        )
    return tuple(returns)


def _validate_snapshot_order(
    snapshots: tuple[T08FactorMarketSnapshot, ...],
) -> None:
    seen_ids: set[str] = set()
    seen_boundaries: set[tuple[str, datetime]] = set()
    previous_market_at: datetime | None = None
    for item in snapshots:
        if not item.complete_frozen_universe:
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence book contains incomplete snapshot"
            )
        if item.snapshot_id in seen_ids:
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence duplicate snapshot id"
            )
        key = (item.provider_key, item.market_at)
        if key in seen_boundaries:
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence duplicate provider boundary"
            )
        if (
            previous_market_at is not None
            and item.market_at <= previous_market_at
        ):
            raise DurableT08FactorEvidenceError(
                "T08 factor evidence market boundaries must increase"
            )
        seen_ids.add(item.snapshot_id)
        seen_boundaries.add(key)
        previous_market_at = item.market_at


def _chain_sha(
    snapshots: tuple[T08FactorMarketSnapshot, ...],
) -> str:
    state = _GENESIS
    for item in snapshots:
        state = "sha256:" + hashlib.sha256(
            (state + "|" + item.snapshot_id).encode()
        ).hexdigest()
    return state


def _snapshot_payload(snapshot: T08FactorMarketSnapshot) -> dict[str, object]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "provider_key": snapshot.provider_key,
        "market_at": snapshot.market_at.isoformat(),
        "observed_at": snapshot.observed_at.isoformat(),
        "collection_basis": snapshot.collection_basis.value,
        "marks": [
            {
                "qore_symbol": item.qore_symbol,
                "bid": str(item.bid),
                "ask": str(item.ask),
                "price_at": item.price_at.isoformat(),
                "observed_at": item.observed_at.isoformat(),
                "evidence_ref": item.evidence_ref,
            }
            for item in snapshot.marks
        ],
    }


def _book_from_payload(payload: object) -> VersionedT08FactorEvidenceBook:
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise DurableT08FactorEvidenceError(
            "T08 factor evidence store schema mismatch"
        )
    raw_snapshots = payload.get("snapshots")
    if not isinstance(raw_snapshots, list):
        raise DurableT08FactorEvidenceError(
            "T08 factor evidence snapshots must be list"
        )
    snapshots = tuple(
        _snapshot_from_payload(item)
        for item in raw_snapshots
    )
    generation = payload.get("generation")
    chain = payload.get("chain_sha256")
    if not isinstance(generation, int) or isinstance(generation, bool):
        raise DurableT08FactorEvidenceError(
            "T08 factor evidence generation invalid"
        )
    if not isinstance(chain, str):
        raise DurableT08FactorEvidenceError(
            "T08 factor evidence chain invalid"
        )
    return VersionedT08FactorEvidenceBook(
        generation=generation,
        snapshots=snapshots,
        chain_sha256=chain,
    )


def _snapshot_from_payload(payload: object) -> T08FactorMarketSnapshot:
    if not isinstance(payload, dict):
        raise DurableT08FactorEvidenceError(
            "T08 factor snapshot payload must be object"
        )
    raw_marks = payload.get("marks")
    if not isinstance(raw_marks, list):
        raise DurableT08FactorEvidenceError(
            "T08 factor snapshot marks must be list"
        )
    try:
        marks = tuple(
            T08MarketMark(
                qore_symbol=str(item["qore_symbol"]),
                bid=Decimal(str(item["bid"])),
                ask=Decimal(str(item["ask"])),
                price_at=datetime.fromisoformat(str(item["price_at"])),
                observed_at=datetime.fromisoformat(str(item["observed_at"])),
                evidence_ref=str(item["evidence_ref"]),
            )
            for item in raw_marks
            if isinstance(item, dict)
        )
        return T08FactorMarketSnapshot(
            snapshot_id=str(payload["snapshot_id"]),
            provider_key=str(payload["provider_key"]),
            market_at=datetime.fromisoformat(str(payload["market_at"])),
            observed_at=datetime.fromisoformat(str(payload["observed_at"])),
            collection_basis=T08MarketCollectionBasis(
                str(payload["collection_basis"])
            ),
            marks=marks,
        )
    except (KeyError, ValueError, TypeError) as error:
        raise DurableT08FactorEvidenceError(
            "T08 factor snapshot payload invalid"
        ) from error


def _sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _valid_sha(value: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DurableT08FactorEvidenceError(
            f"{name} must be timezone-aware"
        )
