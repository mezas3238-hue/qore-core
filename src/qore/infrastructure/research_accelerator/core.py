"""Immutable, checksum-verified research data lake (M1 BID and observed BID/ASK ticks).

This accepts read-only exports from cTrader, MT5 or other providers. It does NOT
infer that distinct broker symbols/feeds are economically interchangeable.
"""
from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Literal

Kind = Literal["m1_bid", "tick_bidask"]


class ResearchDataError(ValueError):
    """Fail-closed source, checksum or chronological data violation."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: object) -> str:
    return sha256(canonical(value)).hexdigest()


def checked_time(raw: str) -> datetime:
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResearchDataError("invalid ISO timestamp") from exc
    offset = dt.utcoffset()
    if dt.tzinfo is None or offset is None or offset != timedelta(0):
        raise ResearchDataError("timestamps must be explicit UTC; no local/DST guessing")
    return dt.astimezone(UTC)


def number(raw: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ResearchDataError("invalid decimal price") from exc
    if not value.is_finite() or value <= 0:
        raise ResearchDataError("all prices must be finite and positive")
    return value


@dataclass(frozen=True)
class DatasetManifest:
    kind: Kind
    sha256: str
    broker: str
    provider: str
    instrument: str
    symbol_id: str
    feed_version: str
    timezone: str
    timeframe: str
    provenance: str
    license: str

    @classmethod
    def read(cls, path: Path) -> DatasetManifest:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ResearchDataError("manifest must be an object")
        expected = {
            "kind", "sha256", "broker", "provider", "instrument", "symbol_id",
            "feed_version", "timezone", "timeframe", "provenance", "license",
        }
        if set(payload) != expected:
            raise ResearchDataError("manifest fields missing/unexpected")
        if payload["kind"] not in ("m1_bid", "tick_bidask"):
            raise ResearchDataError("unsupported kind; never assume MID or ASK from BID")
        if payload["timezone"] != "UTC":
            raise ResearchDataError("manifest timezone must be UTC")
        if payload["timeframe"] != ("M1" if payload["kind"] == "m1_bid" else "TICK"):
            raise ResearchDataError("timeframe does not match evidence kind")
        if not all(isinstance(payload[k], str) and payload[k].strip() for k in expected):
            raise ResearchDataError("all manifest fields must be non-empty strings")
        h = payload["sha256"]
        if len(h) != 64 or any(ch not in "0123456789abcdef" for ch in h):
            raise ResearchDataError("invalid expected SHA256")
        return cls(**payload)

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind, "sha256": self.sha256, "broker": self.broker,
            "provider": self.provider, "instrument": self.instrument,
            "symbol_id": self.symbol_id, "feed_version": self.feed_version,
            "timezone": self.timezone, "timeframe": self.timeframe,
            "provenance": self.provenance, "license": self.license,
        }


@dataclass(frozen=True, slots=True)
class BidBar:
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class Quote:
    at: datetime
    bid: Decimal
    ask: Decimal


def _read_verified(path: Path, manifest: DatasetManifest) -> list[dict[str, str]]:
    data = path.read_bytes()
    if sha256(data).hexdigest() != manifest.sha256:
        raise ResearchDataError("SHA256 mismatch: dataset modified or wrong manifest")
    try:
        rows = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        result = list(rows)
    except (UnicodeError, csv.Error) as exc:
        raise ResearchDataError("invalid UTF-8 CSV") from exc
    if not result:
        raise ResearchDataError("empty dataset")
    return result


def load_bars(path: Path, manifest: DatasetManifest) -> tuple[BidBar, ...]:
    if manifest.kind != "m1_bid":
        raise ResearchDataError("BID OHLC bars required; no derived synthetic OHLC")
    rows = _read_verified(path, manifest)
    if set(rows[0]) != {"closed_at", "open", "high", "low", "close"}:
        raise ResearchDataError("M1 schema: closed_at,open,high,low,close")
    bars: list[BidBar] = []
    prev: datetime | None = None
    for row in rows:
        t = checked_time(row["closed_at"])
        if t.second or t.microsecond or (prev is not None and t <= prev):
            raise ResearchDataError("M1 closes must be minute-aligned and strictly increasing")
        o, h, low, c = (number(row[k]) for k in ("open", "high", "low", "close"))
        if low > min(o, c) or h < max(o, c) or h < low:
            raise ResearchDataError("invalid BID OHLC")
        bars.append(BidBar(t, o, h, low, c))
        prev = t
    return tuple(bars)


def load_quotes(path: Path, manifest: DatasetManifest) -> tuple[Quote, ...]:
    if manifest.kind != "tick_bidask":
        raise ResearchDataError("observed paired BID/ASK ticks required, not OHLC proxies")
    rows = _read_verified(path, manifest)
    if set(rows[0]) != {"at", "bid", "ask"}:
        raise ResearchDataError("tick schema: at,bid,ask (same-time observed pair)")
    quotes: list[Quote] = []
    prev: datetime | None = None
    for row in rows:
        t = checked_time(row["at"])
        if prev is not None and t <= prev:
            raise ResearchDataError("tick times must be strictly ascending; deduplicate upstream")
        b, a = number(row["bid"]), number(row["ask"])
        if b > a:
            raise ResearchDataError("crossed BID/ASK requires upstream quarantine")
        quotes.append(Quote(t, b, a))
        prev = t
    return tuple(quotes)


def assert_same_venue(bars: DatasetManifest, quotes: DatasetManifest) -> None:
    """No execution claim from unhomologated NAS100 versus USTEC or different brokers."""
    fields = ("broker", "provider", "instrument", "symbol_id", "feed_version")
    if any(getattr(bars, k) != getattr(quotes, k) for k in fields):
        raise ResearchDataError("unhomologated price streams; explicit venue mapping required")


def ingest(source: Path, manifest_file: Path, lake: Path) -> dict[str, str]:
    """Content-addressed write-once ingest. Refuse changed bytes and metadata collisions."""
    manifest = DatasetManifest.read(manifest_file)
    if manifest.kind == "m1_bid":
        count = len(load_bars(source, manifest))
    else:
        count = len(load_quotes(source, manifest))
    lake.mkdir(parents=True, exist_ok=True)
    object_file = lake / (manifest.sha256 + ".csv")
    metadata_id = digest(manifest.as_dict())
    metadata_file = lake / (metadata_id + ".manifest.json")
    data = source.read_bytes()
    encoded_meta = canonical(manifest.as_dict()) + b"\n"
    for target, payload in ((object_file, data), (metadata_file, encoded_meta)):
        try:
            with target.open("xb") as out:
                out.write(payload)
                out.flush()
                os.fsync(out.fileno())
        except FileExistsError:
            if target.read_bytes() != payload:
                raise ResearchDataError("immutable lake collision") from None
    return {
        "object": str(object_file), "manifest": str(metadata_file),
        "source_sha256": manifest.sha256, "manifest_sha256": metadata_id,
        "row_count": str(count),
    }


def verify_lake(lake: Path) -> int:
    """Verify every manifest and its bytes; suitable for CI and before every experiment."""
    manifest_files = sorted(lake.glob("*.manifest.json"))
    if not manifest_files:
        raise ResearchDataError("no verified manifests in lake")
    for path in manifest_files:
        manifest = DatasetManifest.read(path)
        if path.name != digest(manifest.as_dict()) + ".manifest.json":
            raise ResearchDataError("content-addressed manifest was modified")
        raw = lake / (manifest.sha256 + ".csv")
        if manifest.kind == "m1_bid":
            load_bars(raw, manifest)
        else:
            load_quotes(raw, manifest)
    return len(manifest_files)
