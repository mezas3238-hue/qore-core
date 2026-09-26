"""Build the first evidence-bound CIBO Phase-19 integrated chronology replay.

This replay deliberately performs no USD capital arithmetic and never sums R
across Traders. It combines only causal trade identity plus observed position
lifetime, restricted to the strict common evidence window shared by all seven
CMA Trader lineages.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    ReplayEconomicsStatus,
    reconstructed_signal_fingerprint,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
    Phase19TraderEvidence,
    assess_phase19_readiness,
    build_phase19_integrated_timeline,
)

EXPECTED_SOURCE_ROWS = {
    TraderLineage.R38_GBPJPY: 897,
    TraderLineage.R43_GBPUSD: 907,
    TraderLineage.R42_AUDJPY: 1039,
    TraderLineage.R38_EURUSD: 863,
    TraderLineage.R34_XAUUSD: 921,
    TraderLineage.VT08_FOREX: 124,
    TraderLineage.VT31_NAS100: 806,
}
EXPECTED_COMMON_ROWS = {
    TraderLineage.R38_GBPJPY: 152,
    TraderLineage.R43_GBPUSD: 147,
    TraderLineage.R42_AUDJPY: 133,
    TraderLineage.R38_EURUSD: 130,
    TraderLineage.R34_XAUUSD: 132,
    TraderLineage.VT08_FOREX: 45,
    TraderLineage.VT31_NAS100: 116,
}
EXPECTED_COMMON_START = "2021-09-23T05:00:00+00:00"
EXPECTED_COMMON_END = "2022-06-29T09:00:00+00:00"
EXPECTED_TOTAL_COMMON_ROWS = 855
EXPECTED_MAX_CONCURRENCY = 5
EXPECTED_OVERLAP_PAIRS = 254
EXPECTED_CROSS_TRADER_OVERLAP_PAIRS = 250
EXPECTED_SAME_TRADER_OVERLAP_PAIRS = 4
EXPECTED_MULTI_TRADER_ENTRY_DAYS = 183


@dataclass(frozen=True, slots=True)
class SourceSpec:
    trader_id: TraderLineage
    qore_symbol: str | None
    artifact_id: int
    artifact_digest: str


SOURCE_SPECS = {
    "gbpjpy": SourceSpec(
        TraderLineage.R38_GBPJPY,
        "GBPJPY",
        10909937201,
        "sha256:b59d8c045a0e86f0e22fb0044dc04eb6dff0f17de4c9f7c7389b903adc443956",
    ),
    "gbpusd": SourceSpec(
        TraderLineage.R43_GBPUSD,
        "GBPUSD",
        10910093452,
        "sha256:93c9c4872543938571eb6ab12e242bde4ec9e7682f056593efde59f88b4579c9",
    ),
    "audjpy": SourceSpec(
        TraderLineage.R42_AUDJPY,
        "AUDJPY",
        10910875686,
        "sha256:7b40e1be53ce0508106b036c68ce4ebb3155bc5c14875144634e365cfb988de5",
    ),
    "eurusd": SourceSpec(
        TraderLineage.R38_EURUSD,
        "EURUSD",
        10910397898,
        "sha256:71bb5ce12b7cfc8f2d17b89dcf907b8b74f4a2257f2055adbe9e9d619c324774",
    ),
    "xauusd": SourceSpec(
        TraderLineage.R34_XAUUSD,
        "XAUUSD",
        10910328640,
        "sha256:aade958d597032bad08c56043a6c48c145b8ab263f032f2b65c147fd3db7aadd",
    ),
    "vt08": SourceSpec(
        TraderLineage.VT08_FOREX,
        None,
        10913050112,
        "sha256:8543a33962d24d3f5346981328df78d145286fc8af9387d73eca85519922f568",
    ),
    "vt31": SourceSpec(
        TraderLineage.VT31_NAS100,
        "NAS100",
        10912945588,
        "sha256:2200392deeb081525720430a816e8f82b18d7333c61a05eb197632ed24849e15",
    ),
}


@dataclass(frozen=True, slots=True)
class ParsedRow:
    opportunity: Phase19ChronologicalOpportunity


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _source_evidence_id(spec: SourceSpec) -> str:
    return (
        f"github-actions:phase18:{spec.artifact_id}:"
        f"{spec.artifact_digest}"
    )


def _parse_row(row: dict[str, Any], *, spec: SourceSpec) -> ParsedRow:
    if str(row.get("economics_status")) != "R_DENOMINATED_ONLY":
        raise ValueError(
            f"{spec.trader_id.value} row unexpectedly claims provider economics"
        )

    qore_symbol = spec.qore_symbol
    if qore_symbol is None:
        qore_symbol = str(row["symbol"])
    if not qore_symbol:
        raise ValueError(f"{spec.trader_id.value} qore symbol is empty")

    signal_at = datetime.fromisoformat(str(row["signal_at"]))
    entry_at = datetime.fromisoformat(str(row["entry_at"]))
    exit_at = datetime.fromisoformat(str(row["exit_at"]))
    side = str(row["side"]).lower()
    entry = Decimal(str(row["entry_price"]))
    stop = Decimal(str(row["structural_stop"]))
    target = Decimal(str(row["technical_target"]))
    evidence_ids = (_source_evidence_id(spec),)

    fingerprint = reconstructed_signal_fingerprint(
        trader_id=spec.trader_id,
        qore_symbol=qore_symbol,
        side=side,
        signal_at=signal_at,
        entry_at=entry_at,
        entry_price=entry,
        structural_stop=stop,
        technical_target=target,
        source_evidence_ids=evidence_ids,
    )
    return ParsedRow(
        opportunity=Phase19ChronologicalOpportunity(
            trader_id=spec.trader_id,
            signal_fingerprint=fingerprint,
            qore_symbol=qore_symbol,
            entry_at=entry_at,
            exit_at=exit_at,
        )
    )


def replay(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19 source set drift")

    parsed_by_trader: dict[
        TraderLineage,
        list[Phase19ChronologicalOpportunity],
    ] = {}
    source_rows: dict[TraderLineage, int] = {}

    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        source_rows[spec.trader_id] = len(rows)
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-18 source row-count drift"
            )
        parsed_by_trader[spec.trader_id] = [
            _parse_row(row, spec=spec).opportunity for row in rows
        ]

    if tuple(parsed_by_trader) != PHASE19_REQUIRED_TRADERS:
        raise ValueError("Phase 19 Trader source ordering drift")

    common_start = max(
        min(item.entry_at for item in items)
        for items in parsed_by_trader.values()
    )
    common_end = min(
        max(item.exit_at for item in items)
        for items in parsed_by_trader.values()
    )
    if common_start.isoformat() != EXPECTED_COMMON_START:
        raise ValueError("Phase 19 common-window start drift")
    if common_end.isoformat() != EXPECTED_COMMON_END:
        raise ValueError("Phase 19 common-window end drift")
    if common_end <= common_start:
        raise ValueError("Phase 19 common evidence window is empty")

    selected_by_trader = {
        trader: [
            item
            for item in items
            if item.entry_at >= common_start and item.exit_at <= common_end
        ]
        for trader, items in parsed_by_trader.items()
    }
    for trader, items in selected_by_trader.items():
        if len(items) != EXPECTED_COMMON_ROWS[trader]:
            raise ValueError(
                f"{trader.value} Phase-19 common-window row-count drift"
            )

    evidence = tuple(
        Phase19TraderEvidence(
            trader_id=trader,
            evidence_id=_source_evidence_id(
                next(
                    spec
                    for spec in SOURCE_SPECS.values()
                    if spec.trader_id is trader
                )
            ),
            row_count=source_rows[trader],
            economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
        )
        for trader in PHASE19_REQUIRED_TRADERS
    )
    readiness = assess_phase19_readiness(evidence)
    if not readiness.chronology_replay_authorized:
        raise ValueError("Phase 19 chronology unexpectedly not authorized")
    if readiness.usd_portfolio_replay_authorized:
        raise ValueError("Phase 19 USD replay must remain fail-closed")

    opportunities = tuple(
        item
        for trader in PHASE19_REQUIRED_TRADERS
        for item in selected_by_trader[trader]
    )
    if len(opportunities) != EXPECTED_TOTAL_COMMON_ROWS:
        raise ValueError("Phase 19 combined common-window row-count drift")

    timeline = build_phase19_integrated_timeline(
        opportunities,
        readiness=readiness,
    )
    if timeline.max_concurrent_positions != EXPECTED_MAX_CONCURRENCY:
        raise ValueError("Phase 19 max-concurrency drift")
    if timeline.overlapping_position_pairs != EXPECTED_OVERLAP_PAIRS:
        raise ValueError("Phase 19 overlap-pair drift")

    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    same_trader_overlap_pairs = 0
    cross_trader_overlap_pairs = 0
    ordered = timeline.opportunities
    for left_index, left in enumerate(ordered):
        for right in ordered[left_index + 1 :]:
            if right.entry_at >= left.exit_at:
                break
            if left.entry_at < right.exit_at and right.entry_at < left.exit_at:
                if left.trader_id is right.trader_id:
                    same_trader_overlap_pairs += 1
                    continue
                cross_trader_overlap_pairs += 1
                key = tuple(
                    sorted((left.trader_id.value, right.trader_id.value))
                )
                pair_counts[key] += 1

    if cross_trader_overlap_pairs != EXPECTED_CROSS_TRADER_OVERLAP_PAIRS:
        raise ValueError("Phase 19 cross-Trader overlap drift")
    if same_trader_overlap_pairs != EXPECTED_SAME_TRADER_OVERLAP_PAIRS:
        raise ValueError("Phase 19 same-Trader overlap drift")

    traders_by_entry_day: dict[str, set[TraderLineage]] = defaultdict(set)
    for item in ordered:
        traders_by_entry_day[item.entry_at.date().isoformat()].add(item.trader_id)
    multi_trader_entry_days = sum(
        len(traders) >= 2 for traders in traders_by_entry_day.values()
    )
    if multi_trader_entry_days != EXPECTED_MULTI_TRADER_ENTRY_DAYS:
        raise ValueError("Phase 19 multi-Trader entry-day drift")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.integrated_chronology_replay.v1",
        "identity": "CIBO_PHASE19_INTEGRATED_CHRONOLOGY_REPLAY_V1",
        "status": "CHRONOLOGY_GREEN_USD_PROVIDER_ECONOMICS_BLOCKED",
        "common_window": {
            "start": common_start.isoformat(),
            "end": common_end.isoformat(),
            "fully_observed_intervals_only": True,
        },
        "source_rows": {
            trader.value: source_rows[trader]
            for trader in PHASE19_REQUIRED_TRADERS
        },
        "common_window_rows": {
            trader.value: len(selected_by_trader[trader])
            for trader in PHASE19_REQUIRED_TRADERS
        },
        "total_common_window_rows": len(ordered),
        "max_concurrent_positions": timeline.max_concurrent_positions,
        "overlapping_position_pairs": timeline.overlapping_position_pairs,
        "cross_trader_overlapping_pairs": cross_trader_overlap_pairs,
        "same_trader_overlapping_pairs": same_trader_overlap_pairs,
        "multi_trader_entry_days": multi_trader_entry_days,
        "cross_trader_pair_overlap_counts": {
            f"{left}|{right}": count
            for (left, right), count in sorted(pair_counts.items())
        },
        "readiness": {
            "phase18_population_complete": readiness.phase18_population_complete,
            "chronology_replay_authorized": readiness.chronology_replay_authorized,
            "usd_portfolio_replay_authorized": readiness.usd_portfolio_replay_authorized,
            "cross_trader_r_aggregation_authorized": (
                readiness.cross_trader_r_aggregation_authorized
            ),
            "provider_economics_incomplete": [
                trader.value for trader in readiness.provider_economics_incomplete
            ],
        },
        "source_evidence": {
            key: {
                "trader_id": spec.trader_id.value,
                "artifact_id": spec.artifact_id,
                "artifact_digest": spec.artifact_digest,
            }
            for key, spec in SOURCE_SPECS.items()
        },
        "governance": {
            "research_only": True,
            "outcome_used_for_trade_authorization": False,
            "usd_capital_arithmetic_performed": False,
            "cross_trader_r_aggregation_performed": False,
            "provider_economics_fabricated": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {
        key: getattr(args, key)
        for key in SOURCE_SPECS
    }
    print(json.dumps(replay(paths=paths, output_path=args.output), sort_keys=True))


if __name__ == "__main__":
    main()
