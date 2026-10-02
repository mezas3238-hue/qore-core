"""Run the frozen VT08 seven-market methodology over Phase22 V2 M5 sources."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
    V2_SOURCE_BINDINGS,
)
from qore.infrastructure.cibo_phase22_vt08_fresh_engine import (
    Phase22Vt08SymbolResult,
    evaluate_vt08_phase22_symbol,
    validate_full_vt08_surface,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import AUTHORIZED_FOREX_MARKETS


def _source_digest(symbol: str) -> str:
    matches = tuple(
        item
        for item in V2_SOURCE_BINDINGS
        if item.symbol == symbol and item.timeframe == "M5"
    )
    if len(matches) != 1:
        raise ValueError(f"VT08 Phase22 V2 source binding drift: {symbol}")
    return matches[0].artifact_digest


def build_vt08_phase22_fresh_payload(
    results: tuple[Phase22Vt08SymbolResult, ...],
) -> dict[str, object]:
    validate_full_vt08_surface(results)
    opportunities = [
        asdict(opportunity)
        for result in results
        for opportunity in result.opportunities
    ]
    return {
        "schema": "qore.cibo.phase22.vt08-fresh-lane.v1",
        "candidate_id": CANDIDATE_ID,
        "trader_id": "VT08_FOREX",
        "markets": list(AUTHORIZED_FOREX_MARKETS),
        "source_artifact_sha256s": [
            [symbol, _source_digest(symbol)]
            for symbol in AUTHORIZED_FOREX_MARKETS
        ],
        "symbol_results": [
            {
                "symbol": result.symbol,
                "resampling": result.resampling.payload(),
                "candidate_count": result.candidate_count,
                "multiple_candidate_days": result.multiple_candidate_days,
                "incomplete_exit_windows": result.incomplete_exit_windows,
                "abstain_reasons": [list(item) for item in result.abstain_reasons],
                "opportunity_count": len(result.opportunities),
            }
            for result in results
        ],
        "opportunities": opportunities,
        "fresh_outcomes_executed": True,
        "methodology_changed": False,
        "legacy_trader_sizing_used_for_cibo": False,
        "broker_mutation_performed": False,
        "productive_authority": False,
    }


def parse_sources(values: list[str]) -> tuple[tuple[str, Path], ...]:
    parsed: dict[str, Path] = {}
    for value in values:
        symbol, sep, raw_path = value.partition("=")
        if not sep or not symbol or not raw_path:
            raise ValueError("VT08 source must be SYMBOL=PATH")
        if symbol in parsed:
            raise ValueError(f"VT08 duplicate source: {symbol}")
        parsed[symbol] = Path(raw_path)
    if set(parsed) != set(AUTHORIZED_FOREX_MARKETS):
        raise ValueError("VT08 Phase22 requires exact seven-market source surface")
    return tuple((symbol, parsed[symbol]) for symbol in AUTHORIZED_FOREX_MARKETS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sources = parse_sources(args.source)
    results = tuple(
        evaluate_vt08_phase22_symbol(raw_root=path)
        for _symbol, path in sources
    )
    payload = build_vt08_phase22_fresh_payload(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": CANDIDATE_ID,
                "trader_id": "VT08_FOREX",
                "markets": len(AUTHORIZED_FOREX_MARKETS),
                "opportunities": len(payload["opportunities"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
