"""Fail-closed as-of pairing for separate, genuine cTrader BID and ASK streams.

A paired state is NOT a synchronous tick nor a broker-execution acknowledgment.
Only actual pre-existing source prices are carried forward with explicit max age.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.research_accelerator.core import (
    Quote,
    ResearchDataError,
    canonical,
    checked_time,
    digest,
    number,
)


@dataclass(frozen=True, slots=True)
class SideInput:
    side: str
    sha256: str
    broker: str
    provider: str
    instrument: str
    symbol_id: str
    feed_version: str
    license: str
    provenance: str

    @classmethod
    def read(cls, path: Path) -> SideInput:
        obj = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "side", "sha256", "broker", "provider", "instrument",
            "symbol_id", "feed_version", "license", "provenance",
        }
        if not isinstance(obj, dict) or set(obj) != expected:
            raise ResearchDataError("side input manifest fields missing/unexpected")
        if obj["side"] not in ("bid", "ask"):
            raise ResearchDataError("side must be explicit BID or ASK")
        if any(not isinstance(x, str) or not x for x in obj.values()):
            raise ResearchDataError("all side provenance fields must be present")
        h = obj["sha256"]
        if len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
            raise ResearchDataError("invalid side SHA256")
        return cls(**obj)


def load_side(path: Path, descriptor: SideInput) -> tuple[tuple[datetime, object], ...]:
    """Normalised BID/ASK export with one price per observation and UTC time."""
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != descriptor.sha256:
        raise ResearchDataError("raw independent quote stream checksum mismatch")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames is None or set(reader.fieldnames) != {"at", "price"}:
        raise ResearchDataError("raw side stream columns must be at,price")
    out: list[tuple[datetime, object]] = []
    previous: datetime | None = None
    for row in reader:
        t = checked_time(row["at"])
        if previous is not None and t <= previous:
            raise ResearchDataError("side ticks not strictly ordered")
        out.append((t, number(row["price"])))
        previous = t
    if not out:
        raise ResearchDataError("empty BID/ASK side stream")
    return tuple(out)


def asof_pair(
    bid: tuple[tuple[datetime, object], ...],
    ask: tuple[tuple[datetime, object], ...],
    *,
    max_staleness_ms: int,
) -> tuple[tuple[Quote, ...], dict[str, int]]:
    """O(n log n) union scan; never invent a price or allow future-side timestamps."""
    from decimal import Decimal

    if type(max_staleness_ms) is not int or not 1 <= max_staleness_ms <= 10000:
        raise ResearchDataError("max-staleness-ms must be frozen in [1,10000]")
    max_age = timedelta(milliseconds=max_staleness_ms)
    times = sorted({t for t, _ in bid} | {t for t, _ in ask})
    bi = ai = 0
    last_bid: tuple[datetime, object] | None = None
    last_ask: tuple[datetime, object] | None = None
    pairs: list[Quote] = []
    counts = {"no_pair": 0, "stale": 0, "crossed": 0}
    for t in times:
        while bi < len(bid) and bid[bi][0] <= t:
            last_bid = bid[bi]
            bi += 1
        while ai < len(ask) and ask[ai][0] <= t:
            last_ask = ask[ai]
            ai += 1
        if last_bid is None or last_ask is None:
            counts["no_pair"] += 1
            continue
        if t - last_bid[0] > max_age or t - last_ask[0] > max_age:
            counts["stale"] += 1
            continue
        b, a = last_bid[1], last_ask[1]
        if not isinstance(b, Decimal) or not isinstance(a, Decimal):
            raise ResearchDataError("raw paired prices must be Decimal")
        if b > a:
            counts["crossed"] += 1
            continue
        pairs.append(Quote(t, b, a))
    if not pairs:
        raise ResearchDataError("no valid as-of state pairs; not an executable tick feed")
    return tuple(pairs), counts


def pair_files(
    bid_file: Path,
    bid_manifest_file: Path,
    ask_file: Path,
    ask_manifest_file: Path,
    *,
    max_staleness_ms: int,
    output_csv: Path,
    output_manifest: Path,
    receipt_file: Path,
) -> dict[str, object]:
    b = SideInput.read(bid_manifest_file)
    a = SideInput.read(ask_manifest_file)
    if (b.side, a.side) != ("bid", "ask"):
        raise ResearchDataError("BID input must be BID; ASK must be ASK")
    fields = ("broker", "provider", "instrument", "symbol_id", "feed_version", "license")
    if any(getattr(a, k) != getattr(b, k) for k in fields):
        raise ResearchDataError("separate quote streams are not the identical feed/contract")
    paired, counts = asof_pair(
        load_side(bid_file, b), load_side(ask_file, a),
        max_staleness_ms=max_staleness_ms,
    )
    table = io.StringIO(newline="")
    writer = csv.writer(table, lineterminator="\n")
    writer.writerow(("at", "bid", "ask"))
    for q in paired:
        writer.writerow((q.at.isoformat(), str(q.bid), str(q.ask)))
    output_bytes = table.getvalue().encode()
    quote_sha = sha256(output_bytes).hexdigest()
    receipt: dict[str, object] = {
        "schema": "qore.asof-side-pairing.v1",
        "input_bid_sha256": b.sha256, "input_ask_sha256": a.sha256,
        "method": "asof-last-observed-no-future",
        "max_staleness_ms": max_staleness_ms,
        "observed_state_count": len(paired),
        "quarantined": counts,
        "output_sha256": quote_sha,
        "claims": "RESEARCH_QUOTE_STATE_NOT_SIMULTANEOUS_TICK_OR_BROKER_ACK",
    }
    manifest: dict[str, str] = {
        "kind": "tick_bidask", "sha256": quote_sha,
        "broker": b.broker, "provider": b.provider, "instrument": b.instrument,
        "symbol_id": b.symbol_id, "feed_version": b.feed_version,
        "timezone": "UTC", "timeframe": "TICK",
        "provenance": "ASOF_PAIR_RECEIPT_SHA256:" + digest(receipt),
        "license": b.license,
    }
    for path, raw in (
        (output_csv, output_bytes),
        (output_manifest, canonical(manifest) + b"\n"),
        (receipt_file, canonical(receipt) + b"\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as out:
            out.write(raw)
    return receipt


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for item in ("bid", "bid-manifest", "ask", "ask-manifest", "output",
                 "output-manifest", "receipt"):
        p.add_argument("--" + item, type=Path, required=True)
    p.add_argument("--max-staleness-ms", type=int, required=True)
    args = p.parse_args()
    receipt = pair_files(
        args.bid, args.bid_manifest, args.ask, args.ask_manifest,
        max_staleness_ms=args.max_staleness_ms, output_csv=args.output,
        output_manifest=args.output_manifest, receipt_file=args.receipt,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
