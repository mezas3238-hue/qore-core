"""Immutable streaming shards for historical quote-side evidence.

One cTrader historical page becomes one immutable gzip JSONL shard. Content
identity excludes retrieval time so the same provider events reproduce the same
market-evidence digest. Provenance identity includes retrieval time and source
identity so acquisition history remains auditable separately.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from qore.infrastructure.historical_quote_side_evidence import (
    HistoricalQuoteSideObservation,
)
from qore.infrastructure.market_observation import MarketPriceSide

_SCHEMA: Final = "qore.shared.wp05.v12.historical_quote_side_shard.v1"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("historical shard timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class HistoricalQuoteSideShardRecord:
    quote_side: MarketPriceSide
    window_index: int
    page_index: int
    request_from_at: datetime
    request_to_at: datetime
    retrieved_at: datetime
    tick_count: int
    first_provider_event_at: datetime | None
    last_provider_event_at: datetime | None
    content_sha256: str
    provenance_sha256: str
    relative_path: str

    def __post_init__(self) -> None:
        if self.quote_side not in (MarketPriceSide.BID, MarketPriceSide.ASK):
            raise ValueError("historical shard side must be BID or ASK")
        if self.window_index < 0 or self.page_index < 0:
            raise ValueError("historical shard indexes cannot be negative")
        if _utc(self.request_to_at) <= _utc(self.request_from_at):
            raise ValueError("historical shard request window must be positive")
        _utc(self.retrieved_at)
        if self.tick_count < 0:
            raise ValueError("historical shard tick_count cannot be negative")
        for digest in (self.content_sha256, self.provenance_sha256):
            if len(digest) != 64:
                raise ValueError("historical shard digest must be SHA-256")
            int(digest, 16)
        if not self.relative_path or Path(self.relative_path).is_absolute():
            raise ValueError("historical shard path must be non-empty and relative")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.quote_side.value,
            self.window_index,
            self.page_index,
            _utc(self.request_from_at).isoformat(timespec="microseconds"),
            _utc(self.request_to_at).isoformat(timespec="microseconds"),
            _utc(self.retrieved_at).isoformat(timespec="microseconds"),
            self.tick_count,
            None
            if self.first_provider_event_at is None
            else _utc(self.first_provider_event_at).isoformat(
                timespec="microseconds"
            ),
            None
            if self.last_provider_event_at is None
            else _utc(self.last_provider_event_at).isoformat(
                timespec="microseconds"
            ),
            self.content_sha256,
            self.provenance_sha256,
            self.relative_path,
        )


class HistoricalQuoteSideShardSink:
    """Filesystem sink that fails closed instead of overwriting a shard."""

    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            raise TypeError("historical shard root must be pathlib.Path")
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def write_page(
        self,
        *,
        quote_side: MarketPriceSide,
        window_index: int,
        page_index: int,
        request_from_at: datetime,
        request_to_at: datetime,
        retrieved_at: datetime,
        observations: tuple[HistoricalQuoteSideObservation, ...],
    ) -> HistoricalQuoteSideShardRecord:
        if quote_side not in (MarketPriceSide.BID, MarketPriceSide.ASK):
            raise ValueError("historical shard side must be BID or ASK")
        if any(item.quote_side is not quote_side for item in observations):
            raise ValueError("historical shard page contains mixed quote sides")

        ordered = tuple(
            sorted(
                observations,
                key=lambda item: (
                    item.provider_event_at,
                    item.relative_price,
                ),
            )
        )
        content_rows = [
            {
                "provider_event_at": _utc(item.provider_event_at).isoformat(
                    timespec="microseconds"
                ),
                "relative_price": item.relative_price,
                "price": item.price.canonical,
            }
            for item in ordered
        ]
        provenance = {
            "schema": _SCHEMA,
            "quote_side": quote_side.value,
            "window_index": window_index,
            "page_index": page_index,
            "request_from_at": _utc(request_from_at).isoformat(
                timespec="microseconds"
            ),
            "request_to_at": _utc(request_to_at).isoformat(
                timespec="microseconds"
            ),
            "retrieved_at": _utc(retrieved_at).isoformat(
                timespec="microseconds"
            ),
            "source": (
                None
                if not ordered
                else ordered[0].source.logical_values()
            ),
            "provider_account_id": (
                None if not ordered else ordered[0].provider_account_id
            ),
            "provider_symbol_id": (
                None if not ordered else ordered[0].provider_symbol_id
            ),
            "provider_symbol": (
                None if not ordered else ordered[0].provider_symbol
            ),
            "content_sha256": _sha256_bytes(
                json.dumps(
                    content_rows,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ).encode("utf-8")
            ),
        }
        provenance_sha256 = _sha256_bytes(
            json.dumps(
                provenance,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        )
        side_dir = self._root / quote_side.value
        side_dir.mkdir(parents=True, exist_ok=True)
        relative = (
            Path(quote_side.value)
            / f"w{window_index:06d}-p{page_index:06d}-{provenance_sha256}.jsonl.gz"
        )
        destination = self._root / relative
        if destination.exists():
            raise FileExistsError(f"historical shard already exists: {relative}")

        header = {
            **provenance,
            "provenance_sha256": provenance_sha256,
            "tick_count": len(content_rows),
        }
        lines = [json.dumps({"header": header}, sort_keys=True)]
        lines.extend(
            json.dumps({"tick": row}, sort_keys=True)
            for row in content_rows
        )
        raw = ("\n".join(lines) + "\n").encode("utf-8")
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        destination.write_bytes(compressed)

        return HistoricalQuoteSideShardRecord(
            quote_side=quote_side,
            window_index=window_index,
            page_index=page_index,
            request_from_at=request_from_at,
            request_to_at=request_to_at,
            retrieved_at=retrieved_at,
            tick_count=len(ordered),
            first_provider_event_at=(
                ordered[0].provider_event_at if ordered else None
            ),
            last_provider_event_at=(
                ordered[-1].provider_event_at if ordered else None
            ),
            content_sha256=str(provenance["content_sha256"]),
            provenance_sha256=provenance_sha256,
            relative_path=relative.as_posix(),
        )


def historical_shard_dataset_digest(
    records: tuple[HistoricalQuoteSideShardRecord, ...],
) -> str:
    """Digest exact ordered provider content without retrieval-time contamination."""

    ordered = sorted(
        records,
        key=lambda item: (
            item.quote_side.value,
            _utc(item.request_from_at),
            item.window_index,
            item.page_index,
        ),
    )
    payload = [
        (
            item.quote_side.value,
            item.window_index,
            item.page_index,
            item.tick_count,
            item.content_sha256,
        )
        for item in ordered
    ]
    return _sha256_bytes(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    )
