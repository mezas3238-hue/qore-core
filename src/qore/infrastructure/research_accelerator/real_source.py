"""Validate real VT31 cTrader USTEC BID/ASK source artifacts (30 selected hours).

NO network, credentials, orders, strategy tuning, holdout or production.
Archives must match pre-registered byte SHA. Parsed quotes are quarantined
as research diagnostics; symbol equivalence and licence are NOT certified.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import tempfile
from bisect import bisect_right
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any
from zipfile import ZipFile

from qore.infrastructure.research_accelerator.asof import (
    SideInput,
    asof_pair,
    load_side,
    pair_files,
)
from qore.infrastructure.research_accelerator.core import (
    Quote,
    ResearchDataError,
    canonical,
    ingest,
    load_quotes,
    verify_lake,
)

SOURCES = (
    (
        "pilot6", 11801205225,
        "7c599294f3853c684f05ee17941b530f35b80bee832e115f51d3d5ff6c3c6f03",
        6,
    ),
    (
        "wave24", 11801263502,
        "a0cb3e62f2c889b414e7283d7d426576468e753b34f60351d0c9aa1965fc1edf",
        24,
    ),
)
MAX_STALENESS_MS = 250
ARCHIVE_MEMBER_BYTES_LIMIT = 40_000_000
ARCHIVE_TOTAL_UNCOMPRESSED_LIMIT = 120_000_000


def _get_verified_member(archive: ZipFile, name: str, expected_hash: str) -> bytes:
    contents = archive.read(name)
    if sha256(contents).hexdigest() != expected_hash:
        raise ResearchDataError("source member digest mismatch: " + name)
    return contents


def _read_and_check_zip(
    path: Path, expected_sha: str, planned_hours: int
) -> tuple[ZipFile, dict[str, Any]]:
    if sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise ResearchDataError("source ZIP SHA256 does not match the audited GitHub artifact")
    z = ZipFile(path)
    names = z.namelist()
    if len(names) != len(set(names)) or any(
        item.startswith("/") or ".." in Path(item).parts or "\\" in item for item in names
    ):
        raise ResearchDataError("unsafe ZIP path or duplicate member")
    if any(z.getinfo(n).file_size > ARCHIVE_MEMBER_BYTES_LIMIT for n in names):
        raise ResearchDataError("oversized ZIP member")
    if sum(z.getinfo(n).file_size for n in names) > ARCHIVE_TOTAL_UNCOMPRESSED_LIMIT:
        raise ResearchDataError("ZIP total uncompressed size exceeded")
    register_bytes = z.read("SHA256SUMS.txt")
    seen: set[str] = set()
    for entry in register_bytes.decode("ascii").splitlines():
        h, delimiter, name = entry.partition("  ")
        if not delimiter or len(h) != 64 or name in seen or name not in names:
            raise ResearchDataError("invalid manifest SHA register")
        seen.add(name)
        _get_verified_member(z, name, h)
    if seen != set(names) - {"SHA256SUMS.txt", "WORKFLOW-COMMIT.txt"}:
        raise ResearchDataError("source manifest incomplete or has unexpected members")
    meta = json.loads(z.read("VT31-G5-USTEC-SB-BIDASK-NOT-NET.json"))
    if not isinstance(meta, dict):
        raise ResearchDataError("invalid source manifest object")
    if (
        meta.get("provider") != "ICMARKETS_CTRADER_DEMO"
        or meta.get("provider_symbol") != "USTEC"
        or meta.get("provider_symbol_id") != 10014
        or meta.get("strategy_contract_equivalent") is not False
        or meta.get("net_pnl_certified") is not False
        or meta.get("fresh_holdout_accessed") is not False
        or meta.get("orders_submitted") != 0
        or meta.get("live_authorized") is not False
    ):
        raise ResearchDataError("source governance/venue contract rejected")
    windows = meta.get("windows_attempted")
    if not isinstance(windows, list) or len(windows) != planned_hours:
        raise ResearchDataError("source planned hour count mismatch")
    return z, meta


def _decode_jsonl_stream(raw: bytes, *, expected_count: int,
                         start: datetime, end: datetime) -> list[tuple[datetime, Decimal]]:
    rows: list[tuple[datetime, Decimal]] = []
    previous_epoch = -1
    for index, line in enumerate(raw.splitlines()):
        obj = json.loads(line)
        if obj.get("native_sequence") != index:
            raise ResearchDataError("noncontiguous native tick sequence")
        ms = obj.get("epoch_ms")
        if type(ms) is not int or ms <= previous_epoch:
            raise ResearchDataError("out-of-order or duplicate tick milliseconds")
        previous_epoch = ms
        t = datetime.fromtimestamp(ms / 1000, tz=UTC)
        if not start <= t < end:
            raise ResearchDataError("provider tick outside preregistered NY/DST hour")
        value = Decimal(obj["decimal_price"])
        if not value.is_finite() or value <= 0:
            raise ResearchDataError("nonpositive/nonfinite provider price")
        rows.append((t, value))
    if len(rows) != expected_count:
        raise ResearchDataError("reported provider tick count mismatches source")
    return rows


def _validate_native_integer(raw: bytes, decoded: list[tuple[datetime, Decimal]]) -> None:
    lines = raw.splitlines()
    if len(lines) != len(decoded):
        raise ResearchDataError("provider integer and decoded tick counts differ")
    for line, (t, price) in zip(lines, decoded, strict=True):
        obj = json.loads(line)
        if (
            obj.get("epoch_ms") != int(t.timestamp() * 1000)
            or obj.get("integer_price_1e5") != int(price * 100000)
            or price * 100000 != int(price * 100000)
        ):
            raise ResearchDataError("provider original integer price parity failed")


def _write_side_csv(path: Path, rows: list[tuple[datetime, Decimal]]) -> str:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("at", "price"))
    for t, v in rows:
        writer.writerow((t.isoformat(), str(v)))
    raw = out.getvalue().encode()
    path.write_bytes(raw)
    return sha256(raw).hexdigest()


def _slow_reference(
    bids: tuple[tuple[datetime, object], ...],
    asks: tuple[tuple[datetime, object], ...],
    *,
    max_staleness_ms: int,
) -> tuple[tuple[tuple[str, str, str], ...], dict[str, int]]:
    """Intentionally naive independent O(n^2) verifier, benchmarking <= 1500 ticks."""
    from datetime import timedelta

    times = sorted({t for t, _ in bids} | {t for t, _ in asks})
    bound = timedelta(milliseconds=max_staleness_ms)
    result: list[tuple[str, str, str]] = []
    counts = {"no_pair": 0, "stale": 0, "crossed": 0}
    for t in times:
        b = next((item for item in reversed(bids) if item[0] <= t), None)
        a = next((item for item in reversed(asks) if item[0] <= t), None)
        if b is None or a is None:
            counts["no_pair"] += 1
            continue
        if t - b[0] > bound or t - a[0] > bound:
            counts["stale"] += 1
            continue
        if not isinstance(b[1], Decimal) or not isinstance(a[1], Decimal):
            raise ResearchDataError("slow reference expected Decimal provider quotes")
        if b[1] > a[1]:
            counts["crossed"] += 1
            continue
        result.append((t.isoformat(), str(b[1]), str(a[1])))
    return tuple(result), counts


def _binary_reference(
    bids: tuple[tuple[datetime, object], ...],
    asks: tuple[tuple[datetime, object], ...],
    *,
    max_staleness_ms: int,
) -> tuple[tuple[Quote, ...], dict[str, int]]:
    """Independent full-source binary-search oracle; no use of asof_pair."""
    bid_times = tuple(t for t, _ in bids)
    ask_times = tuple(t for t, _ in asks)
    times = sorted(set(bid_times) | set(ask_times))
    bound = timedelta(milliseconds=max_staleness_ms)
    states: list[Quote] = []
    quarantined = {"no_pair": 0, "stale": 0, "crossed": 0}
    for at in times:
        bi = bisect_right(bid_times, at) - 1
        ai = bisect_right(ask_times, at) - 1
        if bi < 0 or ai < 0:
            quarantined["no_pair"] += 1
            continue
        tb, bid = bids[bi]
        ta, ask = asks[ai]
        if at - tb > bound or at - ta > bound:
            quarantined["stale"] += 1
            continue
        if not isinstance(bid, Decimal) or not isinstance(ask, Decimal):
            raise ResearchDataError("binary oracle requires Decimal source prices")
        if bid > ask:
            quarantined["crossed"] += 1
            continue
        states.append(Quote(at, bid, ask))
    return tuple(states), quarantined


def _parity_benchmark(
    bids: tuple[tuple[datetime, object], ...],
    asks: tuple[tuple[datetime, object], ...],
) -> dict[str, object]:
    # Independent slow runner on a frozen small subset; don't assert 10x without evidence.
    left = bids[:1500]
    right = asks[:1500]
    start = perf_counter()
    baseline, slow_counts = _slow_reference(
        left, right, max_staleness_ms=MAX_STALENESS_MS,
    )
    elapsed_slow = perf_counter() - start
    start = perf_counter()
    fast, fast_counts = asof_pair(
        left, right, max_staleness_ms=MAX_STALENESS_MS,
    )
    elapsed_fast = perf_counter() - start
    fast_data = tuple((x.at.isoformat(), str(x.bid), str(x.ask)) for x in fast)
    if fast_data != baseline or fast_counts != slow_counts:
        raise ResearchDataError("indexed as-of failed independent slow runner parity")
    return {
        "sample_per_side_max": 1500,
        "parity": "PASS_EXACT",
        "slow_seconds": round(elapsed_slow, 6),
        "fast_seconds": round(elapsed_fast, 6),
        "speedup_observed": round(elapsed_slow / max(elapsed_fast, 1e-12), 3),
        "scope": "ASOF_1500_TICKS_ONLY_NOT_COMPLETE_TRADER_REPLAY",
    }


def _stats(quote_csv: Path, manifest_file: Path) -> dict[str, object]:
    from qore.infrastructure.research_accelerator.core import DatasetManifest

    quotes = load_quotes(quote_csv, DatasetManifest.read(manifest_file))
    ordered = sorted(q.ask - q.bid for q in quotes)
    n = len(ordered)
    return {
        "n_observed_asof_states": n,
        "spread_p50_price_points": str(ordered[n // 2]),
        "spread_p95_price_points": str(ordered[min(n - 1, int(.95 * n))]),
        "spread_max_price_points": str(ordered[-1]),
    }


def process_sources(pilot: Path, wave: Path, *, report_file: Path) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    roots = (pilot, wave)
    with tempfile.TemporaryDirectory(prefix="qore-verified-dev-source-") as tmp:
        root = Path(tmp)
        lake = root / "lake"
        first_benchmark: dict[str, object] | None = None
        for path, spec in zip(roots, SOURCES, strict=True):
            name, artifact_id, expected_zip_sha, expected_count = spec
            z, meta = _read_and_check_zip(path, expected_zip_sha, expected_count)
            try:
                for index, item in enumerate(meta["windows_attempted"], 1):
                    if not isinstance(item, dict):
                        raise ResearchDataError("invalid source window")
                    start = datetime.fromisoformat(item["start_utc"])
                    end = datetime.fromisoformat(item["end_utc"])
                    if start.utcoffset() != end.utcoffset() or start.utcoffset() is None:
                        raise ResearchDataError("source UTC window must use explicit UTC")
                    if (end - start).total_seconds() != 3600:
                        raise ResearchDataError("only preregistered one-hour segments supported")
                    folder = root / (name + "-" + str(index).zfill(2))
                    folder.mkdir()
                    paths = {}
                    by_side = item["by_side"]
                    for side in ("BID", "ASK"):
                        origin = by_side[side]
                        raw = _get_verified_member(
                            z, origin["decoded_file"], origin["decoded_sha256"],
                        )
                        values = _decode_jsonl_stream(
                            raw, expected_count=origin["tick_count"],
                            start=start, end=end,
                        )
                        ints = _get_verified_member(
                            z, origin["integer_file"], origin["integer_sha256"],
                        )
                        _validate_native_integer(ints, values)
                        lower = side.lower()
                        csvpath = folder / (lower + ".csv")
                        h = _write_side_csv(csvpath, values)
                        descriptor = {
                            "side": lower, "sha256": h, "broker": "IC Markets DEMO",
                            "provider": "cTrader Open API", "instrument": "USTEC",
                            "symbol_id": "10014",
                            "feed_version": "ICMARKETS_CTRADER_DEMO_SOURCE_20261013",
                            "license": "RESEARCH_LICENSE_UNVERIFIED_NO_PUBLIC_DATA_REUPLOAD",
                            "provenance": (
                                f"github-actions:{artifact_id}:"
                                f"{origin['decoded_sha256']}"
                            ),
                        }
                        metapath = folder / (lower + ".json")
                        metapath.write_bytes(canonical(descriptor) + b"\n")
                        paths[side] = (csvpath, metapath)
                    resultpath = folder / "asof.csv"
                    resultmeta = folder / "asof.json"
                    receiptpath = folder / "asof-receipt.json"
                    receipt = pair_files(
                        *paths["BID"], *paths["ASK"],
                        max_staleness_ms=MAX_STALENESS_MS,
                        output_csv=resultpath, output_manifest=resultmeta,
                        receipt_file=receiptpath,
                    )
                    from qore.infrastructure.research_accelerator.core import (
                        DatasetManifest,
                    )
                    ingested = ingest(resultpath, resultmeta, lake)
                    b = load_side(paths["BID"][0], SideInput.read(paths["BID"][1]))
                    a = load_side(paths["ASK"][0], SideInput.read(paths["ASK"][1]))
                    if first_benchmark is None:
                        first_benchmark = _parity_benchmark(b, a)
                    oracle_states, oracle_counts = _binary_reference(
                        b, a, max_staleness_ms=MAX_STALENESS_MS,
                    )
                    observed_states = load_quotes(
                        resultpath, DatasetManifest.read(resultmeta),
                    )
                    if (
                        oracle_states != observed_states
                        or oracle_counts != receipt["quarantined"]
                    ):
                        raise ResearchDataError(
                            "FULL SOURCE PARITY FAILED: independent binary-search oracle"
                        )
                    reports.append({
                        "source": name, "source_artifact_id": artifact_id,
                        "window": index, "day_ny": item["day_ny"],
                        "session": item["session"], "start_utc": item["start_utc"],
                        "end_utc": item["end_utc"],
                        "bid_records": by_side["BID"]["tick_count"],
                        "ask_records": by_side["ASK"]["tick_count"],
                        "paired_asof": receipt["observed_state_count"],
                        "quarantine": receipt["quarantined"],
                        "output_sha256": ingested["source_sha256"],
                        "source_quote_state_only": True,
                        "full_binary_oracle_parity": "PASS_EXACT",
                        **_stats(resultpath, resultmeta),
                    })
                    if DatasetManifest.read(resultmeta).kind != "tick_bidask":
                        raise ResearchDataError("normalized quote manifest kind mismatch")
                    shutil.rmtree(folder)
            finally:
                z.close()
        if verify_lake(lake) != 30:
            raise ResearchDataError("not all source windows passed lake re-verification")
        total_bid = sum(row["bid_records"] for row in reports)
        total_ask = sum(row["ask_records"] for row in reports)
        if (total_bid, total_ask) != (241538, 241565):
            raise ResearchDataError("30h provider source tick totals drifted")
        result: dict[str, object] = {
            "schema": "qore.real-source-ustec-30h-validation.v1",
            "source": "ICMARKETS_CTRADER_DEMO_USTEC_10014",
            "data_status": "30_SELECTED_DEVELOPMENT_HOURS_NOT_3Y_CONTINUOUS",
            "strategy_homologation": "BLOCKED_NAS100_USTEC_NO_CONTRACT_EQUIVALENCE",
            "pnl_status": "NOT_COMPUTED_UNVERIFIED_NET",
            "license_status": "UNVERIFIED_DO_NOT_PUBLISH_SOURCE_BYTES",
            "source_archives_sha256": [x[2] for x in SOURCES],
            "source_records_bid": total_bid, "source_records_ask": total_ask,
            "validated_hours": len(reports),
            "asof_max_staleness_ms": MAX_STALENESS_MS,
            "total_observed_asof_states": sum(row["paired_asof"] for row in reports),
            "quarantined_stale": sum(row["quarantine"]["stale"] for row in reports),
            "quarantined_crossed": sum(row["quarantine"]["crossed"] for row in reports),
            "reference_benchmark": first_benchmark,
            "full_binary_oracle_parity": "PASS_30_OF_30_ALL_QUOTE_STATES",
            "windows": reports,
            "raw_ticks_embedded": False,
            "lake_verified_manifest_count": 30,
        }
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with report_file.open("xb") as output:
        output.write(canonical(result) + b"\n")
    report_file.with_name(report_file.name + ".sha256").write_text(
        sha256(report_file.read_bytes()).hexdigest() + "\n", encoding="ascii",
    )
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot6", required=True, type=Path)
    p.add_argument("--wave24", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args()
    result = process_sources(args.pilot6, args.wave24, report_file=args.report)
    print(json.dumps({
        "status": "REAL_SOURCE_QA_PASS_NOT_PNL",
        "source_records": result["source_records_bid"] + result["source_records_ask"],
        "paired_asof": result["total_observed_asof_states"],
        "quarantine_stale": result["quarantined_stale"],
        "reference": result["reference_benchmark"],
        "report_sha256": sha256(args.report.read_bytes()).hexdigest(),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
