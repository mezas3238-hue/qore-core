"""CIBO Market Journey V1.1 exact-equal-liquidity structure coverage.

Research-only extension of Journey V1. It preserves the frozen Behavior Lab
raid/reclaim/CISD semantics and adds one structure family that is already
measured causally by that lab: exact equal liquidity. No tolerance is invented;
only exact provider-price equality already present in ``exact_equal_count`` is
materialized. Unsupported structure families remain fail-closed.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_market_atlas_journey_extractor_v1 as base
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as behavior
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab_fast_runner as fast

IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1_1_EQUAL_LIQUIDITY"
PARENT_IDENTITY = base.IDENTITY
SOURCE_IDENTITY = base.SOURCE_IDENTITY
SOURCE_RUN_ID = base.SOURCE_RUN_ID
SOURCE_GIT_SHA = base.SOURCE_GIT_SHA
STRUCTURE_COVERAGE = "DETERMINISTIC_SUPPORTED_SUBSET_V1_1_FAIL_CLOSED"
EQUAL_LIQUIDITY_DETECTOR = "ICT_TS_BEHAVIOR_LAB_EXACT_EQUAL_V1"


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def event_ledgers_v1_1(event: behavior.Event) -> dict[str, list[dict[str, Any]]]:
    """Extend one frozen Behavior event without changing its base journey."""
    ledgers = base.event_ledgers(event)
    for rows in ledgers.values():
        for row in rows:
            row["identity"] = IDENTITY

    market = ledgers["MARKET_JOURNEY_LEDGER"][0]
    market["source_exact_equal_count"] = event.exact_equal_count
    market["source_exact_equal_liquidity"] = event.exact_equal_count >= 2
    market["structure_coverage_version"] = "V1.1"

    pre_departure = ledgers["PRE_DEPARTURE_SEQUENCE_LEDGER"][0]
    pre_departure["source_exact_equal_count"] = event.exact_equal_count
    pre_departure["equal_liquidity_detector"] = EQUAL_LIQUIDITY_DETECTOR

    if event.exact_equal_count < 2:
        return ledgers

    source_touch = dict(ledgers["STRUCTURE_TOUCH_LEDGER"][0])
    equal_touch = {
        **source_touch,
        "identity": IDENTITY,
        "structure_type": "EQUAL_LIQUIDITY",
        "detector_version": EQUAL_LIQUIDITY_DETECTOR,
        "structure_created_at": event.reference_opened_at.isoformat(),
        "first_touch_at": event.raid_at.isoformat(),
        "last_touch_at": event.raid_at.isoformat(),
        "price_low": str(event.reference_level),
        "price_high": str(event.reference_level),
        "exact_equal_count": event.exact_equal_count,
        "nearest_non_equal_peer_ticks": _decimal_text(event.nearest_peer_ticks),
        "classification_basis": "EXACT_PROVIDER_PRICE_EQUALITY_ONLY",
        "tolerance_ticks": "0",
        "last_structure_before_departure": False,
        "causal_feature": True,
        "outcome_only": False,
    }
    ledgers["STRUCTURE_TOUCH_LEDGER"].append(equal_touch)
    return ledgers


def build_symbol_journey(source: Path, output: Path) -> dict[str, Any]:
    evidence, provenance = base.load_raw_m5(source)
    fast.install()
    events = behavior.extract_events(
        evidence,
        asset_class=base.ASSET_CLASS[evidence.symbol],
        provider=str(provenance["provider_symbol"]),
        evidence_id=f"atlas10y:{SOURCE_RUN_ID}:{SOURCE_GIT_SHA}:{evidence.symbol}",
    )
    ledgers: dict[str, list[dict[str, Any]]] = {name: [] for name in base.LEDGER_NAMES}
    exact_equal_rows = 0
    for event in events:
        extended = event_ledgers_v1_1(event)
        if event.exact_equal_count >= 2:
            exact_equal_rows += 1
        for name, rows in extended.items():
            ledgers[name].extend(rows)

    daily_rows = base.daily_path_rows(evidence)
    for row in daily_rows:
        row["identity"] = IDENTITY
    ledgers["DAILY_PATH_LEDGER"] = daily_rows
    ledgers["TRADER_MARKET_SYNC_LEDGER"] = []

    output.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    hashes: dict[str, str] = {}
    for name in base.LEDGER_NAMES:
        path = output / f"{name}.jsonl"
        counts[name] = base._write_jsonl(path, ledgers[name])
        hashes[name] = base._sha256(path)

    manifest = {
        "schema": "qore.cibo_market_atlas.journey_manifest.v1_1",
        "identity": IDENTITY,
        "parent_identity": PARENT_IDENTITY,
        "source_identity": SOURCE_IDENTITY,
        "source_run_id": SOURCE_RUN_ID,
        "source_git_sha": SOURCE_GIT_SHA,
        "symbol": evidence.symbol,
        "provider_symbol": provenance["provider_symbol"],
        "digits": provenance["digits"],
        "pip_position": provenance["pip_position"],
        "retained_m5_bars": provenance["retained_bars"],
        "earliest_observed_m5": provenance["earliest_observed_m5"],
        "latest_observed_m5": provenance["latest_observed_m5"],
        "behavior_event_count": len(events),
        "equal_liquidity_structure_rows": exact_equal_rows,
        "equal_liquidity_detector": EQUAL_LIQUIDITY_DETECTOR,
        "ledger_counts": counts,
        "ledger_sha256": hashes,
        "structure_coverage": STRUCTURE_COVERAGE,
        "unsupported_structure_policy": "UNRESOLVED_STRUCTURE",
        "trader_sync_status": "UNLINKED_NO_TRADER_DECISION_STREAM",
        "research_evidence_consumed": True,
        "rule_promotion_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "journey-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="CIBO Journey V1.1 equal liquidity")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_symbol_journey(args.source, args.output)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
