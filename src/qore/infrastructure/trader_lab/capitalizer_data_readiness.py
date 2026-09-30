"""Capitalizer development-data readiness audit over the consumed CIBO Atlas index.

This audit proves only that the frozen development corpus is present, covers the intended
markets, and retains clean provider payload integrity. It does not prove strategy edge,
session-calendar completeness, or fresh-holdout status.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_research_lineage import (
    CAPITALIZER_CONSUMED_LINEAGE,
    CONSUMED_END_EXCLUSIVE,
    CONSUMED_START,
    M5_GIT_SHA,
    M5_RUN_ID,
    validate_consumed_lineage_coverage,
)

EXPECTED_IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
EXPECTED_SCHEMA = "qore.cibo_market_atlas.m5_consumption.aggregate.v1"


@dataclass(frozen=True, slots=True)
class CapitalizerMarketDataReadiness:
    symbol: str
    retained_m5_bars: int
    expected_retained_m5_bars: int
    earliest_observed_m5: str
    latest_observed_m5: str
    raw_integrity_status: str
    contradictory_bars: int
    timestamp_alignment_errors: int
    out_of_window_bars: int
    research_evidence_consumed: bool
    ready_for_development: bool
    fresh_holdout_eligible: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerDataReadinessReport:
    identity: str
    source_run_id: int
    source_git_sha: str
    consumed_start: str
    consumed_end_exclusive: str
    market_count: int
    retained_m5_bars: int
    ready_markets: int
    all_markets_ready_for_development: bool
    fresh_holdout_eligible: bool
    markets: tuple[CapitalizerMarketDataReadiness, ...]


def _read_index(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Atlas aggregate index must be a JSON object")
    if payload.get("identity") != EXPECTED_IDENTITY:
        raise ValueError("unexpected Atlas identity")
    if payload.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("unexpected Atlas aggregate schema")
    if payload.get("research_evidence_consumed") is not True:
        raise ValueError("Atlas development evidence must remain marked consumed")
    return payload


def build_data_readiness_report(index_path: Path) -> CapitalizerDataReadinessReport:
    """Build exact readiness against the frozen Capitalizer lineage."""

    validate_consumed_lineage_coverage()
    payload = _read_index(index_path)
    raw_symbols = payload.get("symbols")
    if not isinstance(raw_symbols, list):
        raise ValueError("Atlas symbols must be a list")

    by_symbol: dict[str, dict[str, Any]] = {}
    for raw in raw_symbols:
        if not isinstance(raw, dict):
            raise ValueError("Atlas symbol row must be an object")
        symbol = raw.get("canonical_symbol")
        if not isinstance(symbol, str):
            raise ValueError("Atlas symbol row requires canonical_symbol")
        if symbol in by_symbol:
            raise ValueError(f"duplicate Atlas symbol row: {symbol}")
        by_symbol[symbol] = raw

    markets: list[CapitalizerMarketDataReadiness] = []
    expected_symbols = {item.symbol for item in CAPITALIZER_CONSUMED_LINEAGE}
    missing = expected_symbols - set(by_symbol)
    if missing:
        raise ValueError(f"Atlas index is missing Capitalizer symbols: {sorted(missing)}")

    for lineage in CAPITALIZER_CONSUMED_LINEAGE:
        row = by_symbol[lineage.symbol]
        partitions = row.get("partitions")
        if not isinstance(partitions, list) or not partitions:
            raise ValueError(f"{lineage.symbol} requires partition manifests")
        contradictory = sum(
            int(item.get("contradictory_bars", 0)) for item in partitions
        )
        alignment = sum(
            int(item.get("timestamp_alignment_errors", 0)) for item in partitions
        )
        out_of_window = sum(
            int(item.get("out_of_window_bars", 0)) for item in partitions
        )
        retained = int(row.get("retained_bars", 0))
        integrity = str(row.get("raw_integrity_status", "UNKNOWN"))
        consumed = row.get("research_evidence_consumed") is True
        ready = (
            retained == lineage.retained_m5_bars
            and retained > 0
            and integrity == "CLEAN_PROVIDER_PAYLOAD"
            and contradictory == 0
            and alignment == 0
            and out_of_window == 0
            and consumed
        )
        markets.append(
            CapitalizerMarketDataReadiness(
                symbol=lineage.symbol,
                retained_m5_bars=retained,
                expected_retained_m5_bars=lineage.retained_m5_bars,
                earliest_observed_m5=str(row.get("earliest_observed_m5")),
                latest_observed_m5=str(row.get("latest_observed_m5")),
                raw_integrity_status=integrity,
                contradictory_bars=contradictory,
                timestamp_alignment_errors=alignment,
                out_of_window_bars=out_of_window,
                research_evidence_consumed=consumed,
                ready_for_development=ready,
            )
        )

    ready_markets = sum(item.ready_for_development for item in markets)
    return CapitalizerDataReadinessReport(
        identity="QORE_CAPITALIZER_DATA_READINESS_V1",
        source_run_id=M5_RUN_ID,
        source_git_sha=M5_GIT_SHA,
        consumed_start=CONSUMED_START.isoformat(),
        consumed_end_exclusive=CONSUMED_END_EXCLUSIVE.isoformat(),
        market_count=len(markets),
        retained_m5_bars=sum(item.retained_m5_bars for item in markets),
        ready_markets=ready_markets,
        all_markets_ready_for_development=ready_markets == len(markets),
        fresh_holdout_eligible=False,
        markets=tuple(markets),
    )


def write_data_readiness_report(
    report: CapitalizerDataReadinessReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "capitalizer-data-readiness-v1.json"
    md_path = output / "capitalizer-data-readiness-v1.md"
    json_path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rows = [
        "# QORE Capitalizer — Data Readiness V1",
        "",
        f"- Source M5 run: {report.source_run_id}",
        f"- Source SHA: {report.source_git_sha}",
        f"- Consumed window: {report.consumed_start} .. {report.consumed_end_exclusive}",
        f"- Markets ready: {report.ready_markets}/{report.market_count}",
        f"- Retained M5 bars: {report.retained_m5_bars:,}",
        "- Fresh holdout eligible: NO",
        "",
        "| Market | M5 bars | Integrity | Development-ready |",
        "|---|---:|---|---|",
    ]
    rows.extend(
        (
            f"| {item.symbol} | {item.retained_m5_bars:,} | "
            f"{item.raw_integrity_status} | "
            f"{'YES' if item.ready_for_development else 'NO'} |"
        )
        for item in report.markets
    )
    md_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="QORE Capitalizer data-readiness audit")
    parser.add_argument("index", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_data_readiness_report(args.index)
    write_data_readiness_report(report, args.output)
    print(json.dumps(asdict(report), sort_keys=True))
    if not report.all_markets_ready_for_development:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
