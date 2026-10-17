"""Read-only adapter for the *existing* QORE Native / CIBO original 10Y M5.

Original source: GitHub Actions run 35166210458 (AUDUSD and USDJPY).
No external download, broker authentication, orders, sizing, or other data feed.
Verify producer identity and SHA per annual raw partition before reading OHLC.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    START,
    ReplayBar,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

PRODUCER_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
PRODUCER_IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
RAW_SCHEMA = "qore.cibo_market_atlas.raw_m5.v1"
SOURCE_RUN_ID = 35166210458
SOURCE_ARTIFACT_IDS = {
    CrtPureMarket.AUDUSD: 10475697610,
    CrtPureMarket.USDJPY: 10475389415,
}
SOURCE_ARCHIVE_SHA256 = {
    CrtPureMarket.AUDUSD: "ac72aaf438c164cd79691a7cf1f3f0a68f4c65aa6a91a921a721c7a04ebdc2f0",
    CrtPureMarket.USDJPY: "e3ac9a45f3000c3e3bd93e50c730c952ddd08f77f1c857b5c4b3a67679fcaa51",
}
SOURCE_END_EXCLUSIVE = datetime(2026, 9, 17, tzinfo=UTC)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ledger(path: Path) -> dict[str, str]:
    """Parse exact relative SHA witness names; never trust traversal paths."""
    records: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) != 2:
            raise ValueError("invalid original Atlas SHA witness")
        sha, name = parts
        if (
            len(sha) != 64
            or any(c not in "0123456789abcdef" for c in sha)
            or name.startswith("/")
            or name.startswith("../")
            or "/../" in name
            or "\\" in name
            or name in records
        ):
            raise ValueError("unsafe original Atlas SHA witness")
        records[name] = sha
    return records


def _verified(root: Path, ledger: dict[str, str], name: str) -> Path:
    if name not in ledger:
        raise ValueError(f"missing original annual SHA witness: {name}")
    file = root / name
    if not file.is_file() or _sha256(file) != ledger[name]:
        raise ValueError(f"source original Atlas SHA mismatch: {name}")
    return file


def load_atlas_vt08_m5(
    market: CrtPureMarket, root: Path
) -> tuple[tuple[ReplayBar, ...], dict[str, Any]]:
    """Use only consumed VT08 2Y window, never call cTrader or other providers."""
    if market not in SOURCE_ARTIFACT_IDS:
        raise ValueError("VT08 replay only admits AUDUSD and USDJPY; BTCUSD frozen")
    if (root / "git-sha.txt").read_text(encoding="utf-8").strip() != PRODUCER_SHA:
        raise ValueError("original 10Y Atlas producer code SHA changed")

    symbol_ledger = _ledger(root / "SYMBOL_SHA256SUMS.txt")
    manifest_path = _verified(root, symbol_ledger, "symbol-consumption-manifest.json")
    _verified(root, symbol_ledger, "MANIFEST_SHA256SUMS.txt")
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        m.get("identity") != PRODUCER_IDENTITY
        or m.get("canonical_symbol") != market.value
        or m.get("provider_symbol") != market.value
        or m.get("target_end_exclusive") != SOURCE_END_EXCLUSIVE.isoformat()
        or m.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD"
        or m.get("live_authorized") is not False
    ):
        raise ValueError("original Atlas manifest identity or source window differs")
    partition_ledger = _ledger(root / "MANIFEST_SHA256SUMS.txt")
    if partition_ledger.get(manifest_path.name) != _sha256(manifest_path):
        raise ValueError("original Atlas manifest cross-SHA mismatch")
    by_year = {str(p["partition"]): p for p in m["partitions"]}
    expected_years = ("2024", "2025", "2026")
    if not set(expected_years).issubset(by_year):
        raise ValueError("missing expected source annual M5 partitions")

    rows: list[ReplayBar] = []
    prior: datetime | None = None
    yearly_sha: dict[str, str] = {}
    for year in expected_years:
        witness_name = f"PARTITION_MANIFEST/{year}.sha256"
        _verified(root, partition_ledger, witness_name)
        yearly = _ledger(root / witness_name)
        partition_name = f"PARTITION_MANIFEST/{year}.json"
        _verified(root, partition_ledger, partition_name)
        partition = json.loads((root / partition_name).read_text(encoding="utf-8"))
        if partition != by_year[year]:
            raise ValueError("source annual manifest not equal to publisher partition")
        _verified(root, yearly, partition_name)
        raw_name = f"RAW_M5_LEDGER/{year}.jsonl"
        raw = _verified(root, yearly, raw_name)
        _verified(root, yearly, f"DATA_QUALITY_LEDGER/{year}.jsonl")
        yearly_sha[year] = yearly[raw_name]
        scanned = 0
        with raw.open(encoding="utf-8") as stream:
            for line in stream:
                source = json.loads(line)
                opened_at = datetime.fromisoformat(source["opened_at"]).astimezone(UTC)
                if (
                    source.get("schema") != RAW_SCHEMA
                    or source.get("identity") != PRODUCER_IDENTITY
                    or source.get("canonical_symbol") != market.value
                    or opened_at.year != int(year)
                    or opened_at.minute % 5 != 0
                    or opened_at.second != 0
                    or opened_at.microsecond != 0
                ):
                    raise ValueError("noncanonical original Atlas M5 row")
                if prior is not None and opened_at <= prior:
                    raise ValueError("original Atlas native chronology moved backward")
                prior = opened_at
                scanned += 1
                if not START - timedelta(days=1) <= opened_at < END_EXCLUSIVE:
                    continue
                vals = [source.get(x) for x in (
                    "open_relative", "high_relative", "low_relative", "close_relative"
                )]
                if any(type(x) is not int or x <= 0 for x in vals):
                    raise ValueError("original Atlas prices not provider-relative integer")
                op, hi, lo, close = vals
                if lo > min(op, close) or hi < max(op, close):
                    raise ValueError("original Atlas M5 OHLC invalid")
                rows.append(ReplayBar(
                    opened_at=opened_at,
                    open_price=op,
                    high_price=hi,
                    low_price=lo,
                    close_price=close,
                ))
        if scanned != by_year[year]["retained_bars"]:
            raise ValueError("original Atlas annual M5 count changed")

    if not rows:
        raise ValueError("no retained original Atlas M5 inside VT08 replay window")
    return tuple(rows), {
        "source": "QORE_NATIVE_EXISTING_12_CIBO_ORIGINAL_M5",
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_IDS[market],
        "source_zip_sha256": SOURCE_ARCHIVE_SHA256[market],
        "source_producer_sha": PRODUCER_SHA,
        "yearly_raw_sha256_verified": yearly_sha,
        "source_broker_identity": "CIBO_ATLAS_CTRADER_DEMO_NOT_ICMARKETS_NEW21",
        "used_start_utc": rows[0].opened_at.isoformat(),
        "used_end_utc": rows[-1].opened_at.isoformat(),
        "used_m5_bars": len(rows),
        "dataset_original_end_exclusive": SOURCE_END_EXCLUSIVE.isoformat(),
        "requested_replay_end_exclusive": END_EXCLUSIVE.isoformat(),
        "history_complete_for_requested_2y": False,
        "this_period_previously_consumed_holdout": True,
        "bid_ask_available_in_this_artifact": False,
        "costs_or_broker_fills_validated": False,
        "trading_permission_needed": False,
    }
