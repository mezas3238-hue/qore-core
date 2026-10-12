"""QORE Native research cohort: original 12 M5 + first 11 new IC Markets DEMO M5.

Immutable, source-only union index. Each provider series retains its source run,
identity, account provenance and raw SHA witness. NEVER splice price series,
interpolate gaps, pretend broker equivalence, select a winner or access PnL.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0

IDENTITY = "QORE_NATIVE_COHORT_23_12_PLUS_11_M5_SOURCE_G0_V1"
NEW_CAPTURE_IDENTITY = "QORE_NATIVE_ICMARKETS_DEMO_UNIVERSE33_M5_10Y_NEW_CAPTURE_V1"
NEW_CAPTURE_SCHEMA = "qore.native.icmarkets_demo_universe33_m5_10y.v1"
NEW_RAW_SCHEMA = NEW_CAPTURE_SCHEMA + ".raw"
NEW_SOURCE_RUN = 38193802541
NEW_SOURCE_SHA = "e0ca5a13c866a19d8505c68cffc473598984b340"
ORIGINAL_G0B_RUN = 38201368296
ORIGINAL_G0B_CODE_SHA = "b62053df37cd7e1301c9e8452fb57f6412d1e213"
EXISTING = g0.SYMBOLS
# Snapshot frozen to exactly eleven completed NEW artifacts when owner requested 12+11.
NEW = (
    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "EURCHF", "EURCAD",
    "EURAUD", "EURNZD", "GBPCHF", "GBPCAD", "GBPAUD",
)
YEAR_LABELS = tuple(str(y) for y in g0.YEARS)
ALL = (*EXISTING, *NEW)
FINAL_STATUS = "G0_23_OF_23_M5_SOURCE_SHA_VERIFIED_ECONOMICS_NOT_AUTHORIZED"


def check_universe() -> None:
    if len(EXISTING) != 12 or len(NEW) != 11 or len(ALL) != 23:
        raise ValueError("frozen 12+11 population count mismatch")
    if len(set(ALL)) != 23:
        raise ValueError("original versus new symbol collision")
    if set(NEW) & set(EXISTING):
        raise ValueError("unintended overwrite of original source")


def _strict_flags(x: dict[str, Any]) -> None:
    if (x.get("read_only") is not True or x.get("research_evidence_consumed") is not True
            or any(x.get(key) is not False for key in (
                "demo_eligible", "live_authorized", "real_capital_authorized",
                "production_authorized",
            ))):
        raise ValueError("new source manifest authorizes production or is unverified")


def _hash_scope(path: Path, expected: set[str]) -> dict[str, str]:
    if not path.is_file():
        raise ValueError("required original hash witness missing")
    witness = g0.digest_ledger(path)
    if set(witness) != expected:
        raise ValueError("new original hash witness wrong scope")
    return witness


def audit_new_symbol(symbol: str, source: Path) -> dict[str, Any]:
    """Full raw + quality SHA verification and timestamps; zero OHLC or PnL."""
    check_universe()
    if symbol not in NEW or not source.is_dir():
        raise ValueError("symbol not in frozen new cohort or original archive absent")
    manifest_name = "symbol-consumption-manifest.json"
    expected_manifest_scope = {manifest_name} | {
        f"PARTITION_MANIFEST/{year}.{ext}"
        for year in YEAR_LABELS for ext in ("json", "sha256")
    }
    hashes = _hash_scope(source / "MANIFEST_SHA256SUMS.txt", expected_manifest_scope)
    p = g0.verified_file(source, hashes, manifest_name)
    capture_hashes = _hash_scope(source / "SOURCE_SHA256SUMS.txt", {manifest_name})
    if capture_hashes[manifest_name] != g0.sha256(p):
        raise ValueError("post-capture manifest SHA mismatch")
    m = json.loads(p.read_text(encoding="utf-8"))
    _strict_flags(m)
    if (
        m.get("schema") != NEW_CAPTURE_SCHEMA + ".symbol"
        or m.get("identity") != NEW_CAPTURE_IDENTITY
        or m.get("parent_identity") != g0.PRODUCER
        or m.get("canonical_symbol") != symbol
        or m.get("provider_symbol") != symbol
        or m.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD"
        or m.get("target_start") != g0.FIRST.isoformat()
        or m.get("target_end_exclusive") != g0.LAST_EXCLUSIVE.isoformat()
        or m.get("expected_open_calendar_status") != "UNVERIFIED_PROVIDER_SESSION_CALENDAR"
        or type(m.get("provider_symbol_id")) is not int
        or m["provider_symbol_id"] <= 0
        or type(m.get("digits")) is not int
        or m["digits"] <= 0
    ):
        raise ValueError("new source manifest identity/date/provider drift")
    parts = m.get("partitions")
    if not isinstance(parts, list) or [r.get("partition") for r in parts] != list(YEAR_LABELS):
        raise ValueError("new capture must include 11 ordered annual partitions")
    prev_minute: int | None = None
    count = 0
    first: str | None = None
    last: str | None = None
    annual = []
    for part in parts:
        year = part["partition"]
        if part.get("schema") != NEW_CAPTURE_SCHEMA + ".partition":
            raise ValueError("new annual partition schema drift")
        if (part.get("canonical_symbol") != symbol
                or part.get("provider_symbol_id") != m["provider_symbol_id"]
                or part.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD"
                or part.get("read_only") is not True
                or any(part.get(flag) is not False for flag in (
                    "demo_eligible", "live_authorized", "real_capital_authorized",
                    "production_authorized",
                ))
                or any(part.get(flag) != 0 for flag in (
                    "contradictory_bars", "timestamp_alignment_errors", "out_of_window_bars",
                ))):
            raise ValueError("new annual partition flags or identity invalid")
        part_name = f"PARTITION_MANIFEST/{year}.json"
        part_path = g0.verified_file(source, hashes, part_name)
        if json.loads(part_path.read_text(encoding="utf-8")) != part:
            raise ValueError("original partition differs from symbol manifest")
        sha_name = f"PARTITION_MANIFEST/{year}.sha256"
        sha_path = g0.verified_file(source, hashes, sha_name)
        raw_name = f"RAW_M5_LEDGER/{year}.jsonl"
        quality_name = f"DATA_QUALITY_LEDGER/{year}.jsonl"
        annual_hashes = _hash_scope(
            sha_path, {part_name, raw_name, quality_name}
        )
        g0.verified_file(source, annual_hashes, part_name)
        raw_path = g0.verified_file(source, annual_hashes, raw_name)
        g0.verified_file(source, annual_hashes, quality_name)
        local_count = 0
        local_first: str | None = None
        local_last: str | None = None
        with raw_path.open(encoding="utf-8") as reader:
            for line in reader:
                row = json.loads(line)
                if (row.get("schema") != NEW_RAW_SCHEMA
                        or row.get("identity") != NEW_CAPTURE_IDENTITY
                        or row.get("parent_identity") != g0.PRODUCER
                        or row.get("canonical_symbol") != symbol
                        or row.get("provider_symbol") != symbol
                        or row.get("provider_symbol_id") != m["provider_symbol_id"]
                        or row.get("digits") != m["digits"]):
                    raise ValueError("new original M5 row source identity drift")
                opened = datetime.fromisoformat(row["opened_at"])
                if opened.tzinfo is None or opened.utcoffset() is None:
                    raise ValueError("new M5 timestamp lacks timezone")
                utc = opened.astimezone(UTC)
                minute = int(utc.timestamp()) // 60
                if (not g0.FIRST <= utc < g0.LAST_EXCLUSIVE
                        or utc.year != int(year) or minute % 5
                        or utc.second or utc.microsecond
                        or row.get("utc_timestamp_in_minutes") != minute
                        or prev_minute is not None and minute <= prev_minute):
                    raise ValueError("new original M5 timing invalid")
                prev_minute = minute
                local_first = local_first or utc.isoformat()
                local_last = utc.isoformat()
                local_count += 1
        if (local_count != part.get("retained_bars")
                or local_first != part.get("first_observed_m5")
                or local_last != part.get("last_observed_m5")):
            raise ValueError("new annual bar count or boundaries invalid")
        count += local_count
        first = first or local_first
        last = local_last or last
        annual.append({
            "year": int(year),
            "bars": local_count,
            "raw_sha256": annual_hashes[raw_name],
            "quality_sha256": annual_hashes[quality_name],
            "partition_manifest_sha256": annual_hashes[part_name],
            "unclassified_gap_runs": part.get("unresolved_gap_runs"),
        })
    if (count != m.get("retained_bars") or count <= 0
            or first != m.get("earliest_observed_m5")
            or last != m.get("latest_observed_m5")):
        raise ValueError("new market total bars or time bounds mismatch")
    return {
        "status": "G0_NEW_PROVIDER_M5_SHA_PASS",
        "symbol": symbol,
        "provider_symbol": symbol,
        "provider_symbol_id": m["provider_symbol_id"],
        "capture_producer_identity": NEW_CAPTURE_IDENTITY,
        "capture_run": NEW_SOURCE_RUN,
        "capture_head_sha": NEW_SOURCE_SHA,
        "manifest_sha256": g0.sha256(p),
        "m5_bars": count,
        "first_utc": first, "last_utc": last,
        "years": annual,
        "source_integrity_checked": True,
        "capture_account_gated_icmarkets_demo_in_separate_job": True,
        "original_12_broker_account_equivalence_proven": False,
        "h4_d1_broker_session_candles_certified": False,
        "bid_ask_historical_available": False,
        "ohlc_prices_returns_or_pnl_analyzed": False,
        "g1_net_authorized": False,
    }


def verified_existing_g0b(artifact: Path) -> list[dict[str, Any]]:
    """Admit only immutable first cohort 12 with their previously verified hashes."""
    hashes = _hash_scope(
        artifact / "OUTPUT_SHA256SUMS.txt",
        {"qore-native-g0b-aggregate.json", "code-head-sha.txt"},
    )
    aggregate = g0.verified_file(artifact, hashes, "qore-native-g0b-aggregate.json")
    code = g0.verified_file(artifact, hashes, "code-head-sha.txt")
    if code.read_text(encoding="utf-8").strip() != ORIGINAL_G0B_CODE_SHA:
        raise ValueError("original twelve G0B executable SHA mismatch")
    data = json.loads(aggregate.read_text(encoding="utf-8"))
    rows = data.get("symbols")
    if (data.get("identity") != "QORE_NATIVE_EXISTING12_G0B_OBSERVED_CLOCK_AGGREGATE_V1"
            or data.get("source_run") != g0.SOURCE_RUN
            or data.get("native_m5_bars_verified") != 8726985
            or data.get("twelve_original_shas_revalidated") is not True
            or data.get("G1_net_authorized") is not False
            or data.get("no_market_outcomes_accessed") is not True
            or not isinstance(rows, list) or len(rows) != 12
            or {r["symbol"] for r in rows} != set(EXISTING)):
        raise ValueError("original G0B signed 12-market cohort invalid")
    return [
        {
            "symbol": row["symbol"],
            "source_cohort": "EXISTING12_CTRADER_DEMO_ORIGINAL",
            "provider_symbol": row["provider_symbol"],
            "m5_bars": row["timestamp_clock_census"]["bars"],
            "original_source_run": g0.SOURCE_RUN,
            "audit_run": ORIGINAL_G0B_RUN,
            "audit_exact_code_sha": ORIGINAL_G0B_CODE_SHA,
            "broker_icmarkets_same_account_as_new_verified": False,
            "raw_sha11_years_checked_in_original_g0b": True,
        }
        for row in rows
    ]


def combine(original: Path, witnesses: Path) -> dict[str, Any]:
    check_universe()
    a = verified_existing_g0b(original)
    expected = set(NEW)
    paths = list(witnesses.rglob("qore-native-cohort23-new-*.json"))
    if len(paths) != 11:
        raise ValueError("exactly 11 new independently rehashed source witnesses required")
    new = []
    for path in paths:
        sha_path = path.with_name(path.name + ".sha256")
        if not sha_path.is_file():
            raise ValueError("new witness digest missing")
        hashes = _hash_scope(sha_path, {path.name})
        g0.verified_file(path.parent, hashes, path.name)
        data = json.loads(path.read_text(encoding="utf-8"))
        if (data.get("status") != "G0_NEW_PROVIDER_M5_SHA_PASS"
                or data.get("source_integrity_checked") is not True
                or data.get("g1_net_authorized") is not False
                or data.get("ohlc_prices_returns_or_pnl_analyzed") is not False
                or data.get("capture_run") != NEW_SOURCE_RUN
                or data.get("capture_head_sha") != NEW_SOURCE_SHA
                or len(data.get("years", [])) != 11):
            raise ValueError("new source witness absent/unverified")
        new.append({
            "symbol": data["symbol"],
            "source_cohort": "NEW11_ICMARKETS_CTRADER_DEMO",
            "provider_symbol": data["provider_symbol"],
            "provider_symbol_id": data["provider_symbol_id"],
            "m5_bars": data["m5_bars"],
            "raw_sha256_by_year": {str(x["year"]): x["raw_sha256"] for x in data["years"]},
            "manifest_sha256": data["manifest_sha256"],
            "first_utc": data["first_utc"], "last_utc": data["last_utc"],
            "original_source_run": data["capture_run"],
            "producer_head_sha": data["capture_head_sha"],
            "broker_icmarkets_same_account_as_original_verified": False,
            "source_verified_as_m5_10y_target": True,
        })
    if {x["symbol"] for x in new} != expected:
        raise ValueError("new source witness symbols not exactly 11")
    combined = a + new
    if len(combined) != 23 or {x["symbol"] for x in combined} != set(ALL):
        raise ValueError("23 cohort union unexpected")
    return {
        "identity": IDENTITY, "status": FINAL_STATUS,
        "original_12_source_run": g0.SOURCE_RUN,
        "new_11_capture_run": NEW_SOURCE_RUN,
        "new_11_capture_head_sha": NEW_SOURCE_SHA,
        "original_12_m5_bars": sum(x["m5_bars"] for x in a),
        "new_11_m5_bars": sum(x["m5_bars"] for x in new),
        "combined_m5_bars": sum(x["m5_bars"] for x in combined),
        "cohort_count": 23, "original_count": 12, "new_sha_verified_count": 11,
        "markets": sorted(combined, key=lambda x: x["symbol"]),
        "source_boundaries_preserved": True,
        "cross_broker_raw_prices_not_concatenated": True,
        "no_bid_ask_historical_prices": True,
        "gross_exploration_allowed_only_after_separate_prereg": True,
        "net_execution_certified": False,
        "g1_net_authorized": False,
        "holdout_opened": False,
        "pnl_or_signals_used_to_pick_markets": False,
        "traders_certified": 0,
        "production_untouched": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="task", required=True)
    one = sub.add_parser("verify-new")
    one.add_argument("symbol", choices=NEW)
    one.add_argument("source", type=Path)
    one.add_argument("output", type=Path)
    two = sub.add_parser("combine")
    two.add_argument("original_g0b", type=Path)
    two.add_argument("new_witnesses", type=Path)
    two.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.task == "verify-new":
        result = audit_new_symbol(args.symbol, args.source)
        target = args.output / f"qore-native-cohort23-new-{args.symbol}.json"
    else:
        result = combine(args.original_g0b, args.new_witnesses)
        target = args.output / "qore-native-cohort23-unified-manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    target.with_name(target.name + ".sha256").write_text(
        g0.sha256(target) + f"  {target.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "identity": result.get("identity", "INDIVIDUAL_NEW_SOURCE"),
        "status": result["status"], "symbol": result.get("symbol"),
        "cohort_count": result.get("cohort_count"),
        "m5_bars": result.get("m5_bars", result.get("combined_m5_bars")),
        "no_pnl": True, "no_trade": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
