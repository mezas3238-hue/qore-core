"""Nine-market read-only instrumentation of the V49 entry sensor panel.

Uses frozen original source IDs, provider-native M1 and AS-OF route observers.
Does not call trade execution, change selection, or infer missing broker prices.
One independent pretrade sensor panel per original V49 opportunity. In a
later integration A1 will supply M15 attestation and full cognitive evidence.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    IDENTITY as SENSOR_ID,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    EntrySensorInput,
    observe_entry_timing_sensors,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_timing_session_diagnostic_v1 import (
    aware,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)

IDENTITY = "QORE_SCALPER_A2_ENTRY_SENSOR_SHADOW_9MARKET_CENSUS_V1"


def build_market(
    original_v49: Path, native_m1: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    paths = sorted(original_v49.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    if len(paths) != 1:
        raise ValueError("need precisely one pinned V49 opportunity ledger")
    sources = tuple(V49Opportunity(**r) for r in _jsonl(paths[0]))
    if not sources:
        raise ValueError("V49 original source ledger cannot be empty")
    symbol = sources[0].symbol
    if any(s.symbol != symbol or s.session != sources[0].session for s in sources):
        raise ValueError("source file mixes symbols or sessions")
    bars = tuple(
        bar for bar in iter_cibo_m1(native_m1)
        if DEV_WINDOW_START - timedelta(days=2) <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars or any(b.symbol != symbol for b in bars):
        raise ValueError("wrong provider-native M1 market")
    opened = tuple(b.opened_at for b in bars)
    frames: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    first_route_counts: Counter[str] = Counter()
    for source in sources:
        at = aware(source.m1_trigger_confirmed_at)
        m15 = aware(source.m15_setup_confirmed_at)
        # Include a bounded amount of BEFORE-thesis history for M1/H1 phase
        # and local noise; source route observer re-slices to post-M15 bars.
        left = bisect.bisect_left(
            opened,
            min(m15, at.replace(minute=0, second=0, microsecond=0))
            - timedelta(minutes=20),
        )
        right = bisect.bisect_left(opened, at)
        witness = bars[left:right]
        if not witness or witness[-1].closed_at != at:
            raise ValueError("native M1 lacks the original executed close")
        frame = observe_entry_timing_sensors(EntrySensorInput(
            symbol=source.symbol, session=source.session,
            decision_at=at, h1_direction=source.h1_state_direction,
            h1_basis=source.h1_state_basis,
            h1_confirmed_at=aware(source.h1_state_from),
            m15_confirmed_at=m15,
            m15_protected_stop=Decimal(source.m15_protected_swing_price),
            m1_bars=witness,
            # V49 only supplies the target PRICE, not independent timestamp
            # witness. It is intentionally not passed into this panel.
            witnessed_h1_target=None,
            h1_target_confirmed_at=None,
            bid=None, ask=None, commission_round_trip_per_lot=None,
        ))
        sensor_matches_source = (
            frame.source_event_observed
            and frame.first_source_cisd_family == source.m1_trigger_family
            and frame.first_source_cisd_confirmed_at == source.m1_trigger_confirmed_at
        )
        if not sensor_matches_source:
            # Do not suppress original V49 sources in an observational census.
            # Preserve the conflicting pair for forensic review, explicitly
            # disallow any downstream admission relying on this unmatched view.
            status_counts["ORIGINAL_SOURCE_SENSOR_MISMATCH"] += 1
        else:
            status_counts["ORIGINAL_SOURCE_SENSOR_MATCH"] += 1
        if frame.identity != SENSOR_ID:
            raise ValueError("different sensor panel contract")
        rows = [asdict(r) for r in frame.sensors]
        for x in rows:
            status_counts[f"{x['sensor']}:{x['status']}"] += 1
        first_route_counts[str(frame.first_source_cisd_family)] += 1
        frames.append({
            "source_opportunity_id": source_id(source),
            "symbol": symbol,
            "original_entry_at": source.m1_trigger_confirmed_at,
            "original_trigger_family": source.m1_trigger_family,
            "first_source_cisd_family": frame.first_source_cisd_family,
            "first_source_cisd_confirmed_at": frame.first_source_cisd_confirmed_at,
            "sensor_count": len(frame.sensors),
            "sensor_source_identity_match": sensor_matches_source,
            "original_source_signal_preserved": True,
            "paper_entry_authorized": False,
            "sensors": rows,
            "execution_authorized": frame.execution_authorized,
            "hard_entry_gate_added": frame.hard_entry_gate_added,
            "full_master_frame_attested": frame.cognitive_master_frame_attested,
            "trader_certified": frame.trader_certified,
            "live_authorized": frame.live_authorized,
        })
    if len({r["source_opportunity_id"] for r in frames}) != len(sources):
        raise ValueError("source identity duplication")
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "original_source_opportunities": len(sources),
        "source_cisd_identical": len(frames) - status_counts["ORIGINAL_SOURCE_SENSOR_MISMATCH"],
        "source_cisd_mismatch": status_counts["ORIGINAL_SOURCE_SENSOR_MISMATCH"],
        "sensor_status_counts": dict(sorted(status_counts.items())),
        "route_counts": dict(sorted(first_route_counts.items())),
        "modified_original_entries": 0,
        "full_master_frame_attested": False,
        "physical_broker_costs_attested": False,
        "new_entry_filter_applied": False,
        "trader_certified": False,
        "live_authorized": False,
    }, tuple(frames)


def write_market(
    report: dict[str, Any],
    rows: tuple[dict[str, Any], ...],
    target: Path,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "scalper-entry-sensors-market.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (target / "scalper-entry-sensors-rows.jsonl").open(
        "w", encoding="utf-8"
    ) as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def aggregate(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("scalper-entry-sensors-market.json"))
    if len(paths) != 9:
        raise ValueError("9 independent native M1 markets mandatory")
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    if len({r["symbol"] for r in reports}) != 9:
        raise ValueError("duplicated native market report")
    rows = [
        row for path in sorted(root.rglob("scalper-entry-sensors-rows.jsonl"))
        for row in _jsonl(path)
    ]
    if len(rows) != 2876 or len({r["source_opportunity_id"] for r in rows}) != 2876:
        raise ValueError("shadow sensor source census differs from original 2876")
    matched = sum(r["source_cisd_identical"] for r in reports)
    mismatched = sum(r["source_cisd_mismatch"] for r in reports)
    if matched + mismatched != 2876:
        raise ValueError("source identity evidence census is incomplete")
    if sum(bool(r["sensor_source_identity_match"]) for r in rows) != matched:
        raise ValueError("per-source identity flags not reconciled")
    if any(r["execution_authorized"] or r["hard_entry_gate_added"]
           or r["full_master_frame_attested"] or r["trader_certified"]
           or r["live_authorized"] for r in rows):
        raise ValueError("research panel authorized an operation")
    counts: Counter[str] = Counter()
    for r in reports:
        counts.update(r["sensor_status_counts"])
    return {
        "identity": IDENTITY,
        "markets": 9,
        "original_source_opportunities": 2876,
        "source_cisd_identical": matched,
        "source_cisd_mismatch": mismatched,
        "sensor_status_counts": dict(sorted(counts.items())),
        "source_event_observed": 2876,
        "entries_changed": 0,
        "new_hard_gates": 0,
        "full_cognitive_master_frame_wired": False,
        "physical_bid_ask_costs_wired": False,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("control", type=Path)
    m.add_argument("native_m1", type=Path)
    m.add_argument("output", type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("reports", type=Path)
    a.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.mode == "market":
        report, rows = build_market(args.control, args.native_m1)
        write_market(report, rows, args.output)
        print(json.dumps({
            "symbol": report["symbol"], "source": report["original_source_opportunities"],
            "identity_proof": report["source_cisd_identical"],
            "trader_certified": False,
        }, sort_keys=True))
    else:
        report = aggregate(args.reports)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "scalper-entry-sensors-nine-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
