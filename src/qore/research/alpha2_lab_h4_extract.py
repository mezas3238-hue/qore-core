"""Trader Lab read-only native-M5 -> compact complete H4 for QORE Alpha2.

All source files verified BEFORE economic M5 prices; summary contains ONLY
historically consumed observations. No trading, no source alteration, no future
OHLC access, no claims about broker H4 session candles.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as new_source
from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as original
from qore.infrastructure.trader_lab import qore_native_final33_three_m5_g0_v1 as final
from qore.research.alpha2_intermarket import (
    MARKETS,
    RESEARCH_CUTOFF,
    Bar,
    aggregate_complete_h4,
    sha256_file,
)

SOURCE33_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
SOURCE33_HEAD = "dba0e0c3b61e430d3ed51abab562ebd92060a0ff"


def source33_manifest(folder: Path) -> dict:
    """Validate independently frozen upstream manifest + exact producer code."""
    name = "qore-native-complete33-source-m5.json"
    ledger = original.digest_ledger(folder / "OUTPUT_SHA256SUMS.txt")
    if set(ledger) != {name, "exact-code-head-sha.txt"}:
        raise ValueError("upstream 33 manifest checksum scope wrong")
    file = original.verified_file(folder, ledger, name)
    head = original.verified_file(folder, ledger, "exact-code-head-sha.txt")
    side = original.digest_ledger(folder / (name + ".sha256"))
    if (side != {name: SOURCE33_SHA} or ledger[name] != SOURCE33_SHA
            or head.read_text(encoding="utf-8").strip() != SOURCE33_HEAD):
        raise ValueError("original 33 manifest SHA or producer HEAD drift")
    data = json.loads(file.read_text(encoding="utf-8"))
    roster = data.get("market_roster")
    if (data.get("identity") != final.IDENTITY
            or data.get("status") != "G0_33_OF_33_PROVIDER_M5_SHA_VERIFIED_NO_ECONOMICS"
            or data.get("market_count") != 33
            or not isinstance(roster, list) or len(roster) != 33
            or {r["symbol"] for r in roster} != set(MARKETS)
            or data.get("all_33_original_m5_bars") != 24377420
            or data.get("market_outcomes_unexamined") is not True
            or data.get("net_execution_economics_authorized") is not False):
        raise ValueError("frozen provider 33 count/permissions not original")
    return data


def verify_source(
    symbol: str, folder: Path, frozen: dict, aggregate12: Path | None,
) -> dict:
    rows = frozen["market_roster"]
    row = next(x for x in rows if x["symbol"] == symbol)
    if symbol in original.SYMBOLS:
        if aggregate12 is None:
            raise ValueError("original 12 require authentic Atlas aggregate")
        originals = original.aggregate_index(aggregate12)
        evidence = original.audit_symbol(symbol, folder, originals[symbol])
        bars = evidence["native_m5_bars"]
        checked = evidence["all_11_years_raw_and_quality_sha256_verified"]
        audit_shas = {str(x["year"]): x["original_sha256"] for x in evidence["yearly"]}
        origin = "ORIGINAL12_CIBO_ATLAS"
    else:
        evidence = new_source.audit_new_symbol(
            symbol, folder, allowed_symbols=(symbol,),
        )
        bars = evidence["m5_bars"]
        checked = evidence["source_integrity_checked"]
        audit_shas = {str(x["year"]): x["raw_sha256"] for x in evidence["years"]}
        expected_sha = row.get("raw_sha256_by_year")
        if expected_sha is None:
            expected_sha = row.get("original_raw_sha256_by_year")
        if audit_shas != expected_sha:
            raise ValueError("33 source roster yearly original RAW hash drift")
        expected_manifest = row.get("manifest_sha256", row.get("source_manifest_sha256"))
        if evidence["manifest_sha256"] != expected_manifest:
            raise ValueError("new21 source manifest does not match 33 frozen source")
        origin = "NEW21_ICMARKETS_DEMO"
    if not checked or bars != row["m5_bars"] or len(audit_shas) != 11:
        raise ValueError("original 11-year source SHA/count admission failed")
    return {"symbol": symbol, "source_cohort": origin,
            "m5_bars_verified": bars, "raw_sha256_by_year": audit_shas,
            "native_original_source_sha_verified": True}


def source_rows_before_embargo(folder: Path, symbol: str) -> Iterator[Bar]:
    """Read pre-embargo OHLC only from independently SHA-verified raw ledger."""
    expected_schema = (original.RAW_SCHEMA if symbol in original.SYMBOLS
                       else new_source.NEW_RAW_SCHEMA)
    expected_identity = (original.PRODUCER if symbol in original.SYMBOLS
                         else new_source.NEW_CAPTURE_IDENTITY)
    expected_provider = original.SOURCE_SYMBOL_MAP.get(symbol, symbol)
    prior: datetime | None = None
    for year in range(2016, 2025):
        with (folder / "RAW_M5_LEDGER" / f"{year}.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                at = datetime.fromisoformat(row["opened_at"])
                if at.tzinfo is None or at.utcoffset() is None:
                    raise ValueError("original M5 naïve timestamp")
                at = at.astimezone(UTC)
                if at >= RESEARCH_CUTOFF:
                    continue  # explicit OHLC embargo: never access price fields
                if (prior is not None and at <= prior):
                    raise ValueError("native M5 source order invalid")
                prior = at
                if (row.get("schema") != expected_schema
                        or row.get("identity") != expected_identity
                        or row.get("canonical_symbol") != symbol
                        or row.get("provider_symbol") != expected_provider):
                    raise ValueError("provider RAW M5 identity/schema drift")
                for key in ("open_relative", "high_relative",
                            "low_relative", "close_relative"):
                    if type(row.get(key)) is not int:
                        raise ValueError("native provider OHLC must be exact integers")
                yield Bar(at=at, open=row["open_relative"], high=row["high_relative"],
                          low=row["low_relative"], close=row["close_relative"])


def extract(
    symbol: str, source: Path, signed33: Path, destination: Path,
    aggregate12: Path | None = None,
) -> dict:
    if symbol not in MARKETS:
        raise ValueError("unknown QORE Alpha2 market")
    frozen = source33_manifest(signed33)
    proof = verify_source(symbol, source, frozen, aggregate12)
    h4 = aggregate_complete_h4(source_rows_before_embargo(source, symbol))
    destination.mkdir(parents=True, exist_ok=True)
    outfile = destination / f"alpha2-complete-h4-{symbol}.csv"
    with outfile.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("timestamp_utc", "open", "high", "low", "close"))
        for t, bar in sorted(h4.items()):
            writer.writerow((t.isoformat(), int(bar.open), int(bar.high),
                             int(bar.low), int(bar.close)))
    summary = {
        "identity": "QORE_ALPHA2_SHA_GATED_CONSUMED_H4_FROM_NATIVE_M5_V1",
        "symbol": symbol, "source33_sha256": SOURCE33_SHA,
        "source33_producer_head": SOURCE33_HEAD,
        "source": proof, "complete_native_m5_H4_blocks": len(h4),
        "first_h4_utc": min(h4).isoformat() if h4 else None,
        "last_h4_utc": max(h4).isoformat() if h4 else None,
        "h4_csv_sha256": sha256_file(outfile), "csv_basename": outfile.name,
        "source_input_full_11_year_raw_sha_verified_before_OHLC": True,
        "post_2024_09_17_price_not_read": True,
        "broker_H4_session_semantics_claimed": False,
        "news_asof_verified": False,
        "broker_bidask_costs_verified": False,
        "paper_or_live_authorized": False,
        "pnl_or_outcomes_calculated": False,
    }
    manifest = destination / f"alpha2-h4-source-{symbol}.json"
    manifest.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    return summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbol", choices=MARKETS)
    p.add_argument("raw_original_provider", type=Path)
    p.add_argument("signed33", type=Path)
    p.add_argument("destination", type=Path)
    p.add_argument("--aggregate12", type=Path)
    opts = p.parse_args()
    summary = extract(opts.symbol, opts.raw_original_provider, opts.signed33,
                      opts.destination, opts.aggregate12)
    print(json.dumps({k: summary[k] for k in
                      ("identity", "symbol", "complete_native_m5_H4_blocks",
                       "h4_csv_sha256", "pnl_or_outcomes_calculated")}, sort_keys=True))


if __name__ == "__main__":
    main()
