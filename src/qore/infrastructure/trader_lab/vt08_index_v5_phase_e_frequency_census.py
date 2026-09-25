"""Consumed-evidence frequency-loss census for VT-08 Index V5 Phase E."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import (
    ClosurePolicy,
    SwingPolicy,
    _signal,
)
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _in_partition,
    _load_candidate_market,
)
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    _geometry,
    _geometry_accepts,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    AUTHORIZED_MARKETS,
    OWNER_ENTRY_ANCHORS_NY,
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_v5_phase_e_frequency_census.v1"
WINDOWS = (
    (
        "2022_23",
        date(2022, 9, 15),
        date(2023, 9, 15),
        "106a34282fe8eac2f8c466bcc8502d4ec8d73855",
        350,
    ),
    (
        "2023_24",
        date(2023, 9, 15),
        date(2024, 8, 13),
        "58dd289646de8814449f836ad617a51342eba0da",
        300,
    ),
    (
        "2024_26",
        date(2024, 8, 13),
        date(2026, 9, 12),
        "a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0",
        700,
    ),
)
_NY = ZoneInfo("America/New_York")


def _load(
    path: Path,
    *,
    symbol: str,
    sha: str,
    minimum_days: int,
) -> dict[datetime, Vt08IndexC2R1Bar]:
    _, _, _, bars = _load_candidate_market(
        path,
        expected_symbol=symbol,
        expected_software_sha=sha,
        minimum_evidence_days=minimum_days,
    )
    return {bar.opened_at.astimezone(UTC): bar for bar in bars}


def _window_census(
    *,
    paths: dict[str, Path],
    start: date,
    end_exclusive: date,
    sha: str,
    minimum_days: int,
) -> dict[str, Any]:
    raw_rows: list[dict[str, Any]] = []
    decisions = 0
    for symbol in AUTHORIZED_MARKETS:
        indexed = _load(
            paths[symbol],
            symbol=symbol,
            sha=sha,
            minimum_days=minimum_days,
        )
        symbol_decisions = tuple(
            opened
            for opened in indexed
            if opened.astimezone(_NY).minute == 0
            and opened.astimezone(_NY).hour in OWNER_ENTRY_ANCHORS_NY
            and _in_partition(
                opened,
                start_date=start,
                end_date_exclusive=end_exclusive,
            )
        )
        decisions += len(symbol_decisions)
        for decision in symbol_decisions:
            signal = _signal(
                symbol=symbol,
                bars_by_open=indexed,
                decision_at=decision,
                closure=ClosurePolicy.C2_OR_C3_BODY_CLOSE,
                swing=SwingPolicy.FARTHEST_STRUCTURAL,
            )
            if signal is None:
                continue
            geometry = _geometry(signal, bars_by_open=indexed)
            raw_rows.append(
                {
                    "symbol": symbol,
                    "signal_at": signal.decision_at.astimezone(UTC).isoformat(),
                    "ny_date": signal.decision_at.astimezone(_NY).date().isoformat(),
                    "anchor": signal.anchor,
                    "side": signal.side.value,
                    "geometry_available": geometry is not None,
                    "geometry_accepts": (
                        geometry is not None and _geometry_accepts(geometry)
                    ),
                }
            )

    by_symbol_day: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        by_symbol_day[(str(row["symbol"]), str(row["ny_date"]))].append(row)

    unique_daily_rows: list[dict[str, Any]] = []
    geometry_unique_rows: list[dict[str, Any]] = []
    multi_signal_days = 0
    for rows in by_symbol_day.values():
        if len(rows) != 1:
            multi_signal_days += 1
            continue
        unique_daily_rows.extend(rows)
        if bool(rows[0]["geometry_accepts"]):
            geometry_unique_rows.extend(rows)

    same_decision: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        same_decision[(str(row["signal_at"]), str(row["side"]))].append(row)
    peer_counts = Counter(min(3, len(rows)) for rows in same_decision.values())

    def breakdown(field: str) -> dict[str, int]:
        return dict(sorted(Counter(str(row[field]) for row in raw_rows).items()))

    geometry_admitted = sum(bool(row["geometry_accepts"]) for row in raw_rows)
    return {
        "decisions": decisions,
        "raw_structural_signals": len(raw_rows),
        "geometry_admitted_signals": geometry_admitted,
        "geometry_rejected_or_unavailable": len(raw_rows) - geometry_admitted,
        "unique_daily_signals": len(unique_daily_rows),
        "v3_geometry_plus_unique_daily_admitted": len(geometry_unique_rows),
        "multi_signal_symbol_days": multi_signal_days,
        "raw_signal_retention_after_v3_constraints": (
            len(geometry_unique_rows) / len(raw_rows) if raw_rows else 0.0
        ),
        "by_symbol": breakdown("symbol"),
        "by_anchor": breakdown("anchor"),
        "by_side": breakdown("side"),
        "simultaneous_same_side_group_size_counts": {
            str(key): value for key, value in sorted(peer_counts.items())
        },
    }


def run(
    *,
    v3_paths: dict[str, Path],
    v2_paths: dict[str, Path],
    development_paths: dict[str, Path],
    output: Path,
) -> dict[str, Any]:
    path_sets = {
        "2022_23": v3_paths,
        "2023_24": v2_paths,
        "2024_26": development_paths,
    }
    windows: dict[str, Any] = {}
    for window_id, start, end_exclusive, sha, minimum_days in WINDOWS:
        windows[window_id] = _window_census(
            paths=path_sets[window_id],
            start=start,
            end_exclusive=end_exclusive,
            sha=sha,
            minimum_days=minimum_days,
        )
    report = {
        "schema": SCHEMA,
        "contract": "consumed-evidence-only; diagnostic; holdout sealed",
        "windows": windows,
        "candidate_freeze_permitted": False,
        "holdout_open_permitted": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for prefix in ("v3", "v2", "development"):
        for symbol in ("nas100", "sp500", "us30"):
            parser.add_argument(f"--{prefix}-{symbol}", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(
        v3_paths={
            "NAS100": args.v3_nas100,
            "SP500": args.v3_sp500,
            "US30": args.v3_us30,
        },
        v2_paths={
            "NAS100": args.v2_nas100,
            "SP500": args.v2_sp500,
            "US30": args.v2_us30,
        },
        development_paths={
            "NAS100": args.development_nas100,
            "SP500": args.development_sp500,
            "US30": args.development_us30,
        },
        output=args.out,
    )


if __name__ == "__main__":
    main()
