"""Upgrade DEPARTURE_TIMING_LEDGER from trader-root rows to market episodes.

Consumes only the already-built eight-ledger result directory. Every completed
pre-departure sequence becomes one timing row; trader roots are overlays.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse(value: str | None) -> datetime | None:
    if not value:
        return None
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError(f"naive timestamp {value}")
    return result


def minutes(a: datetime | None, b: datetime | None) -> int | None:
    if a is None or b is None:
        return None
    return int((b - a).total_seconds() // 60)


def build(result_dir: Path) -> dict[str, Any]:
    sequences = read_jsonl(result_dir / "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl")
    sync = read_jsonl(result_dir / "TRADER_MARKET_SYNC_LEDGER.jsonl")
    by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for root in sync:
        by_episode[str(root["episode_id"])].append(root)

    timing: list[dict[str, Any]] = []
    for seq in sequences:
        departure = parse(seq.get("departure_pivot_at"))
        breach = parse(seq.get("first_breach_at"))
        objective = parse(seq.get("opposite_boundary_at"))
        structure_touch = parse(seq.get("last_structure_touch_at"))
        if departure is None or objective is None:
            raise ValueError(f"completed sequence missing departure/objective {seq['episode_id']}")
        local = departure.astimezone(NY)
        overlays: list[dict[str, Any]] = []
        for root in by_episode.get(str(seq["episode_id"]), []):
            signal = parse(root.get("signal_at"))
            overlays.append(
                {
                    "root_id": root["root_id"],
                    "terminal_family": root["terminal_family"],
                    "signal_at": root["signal_at"],
                    "minutes_signal_to_departure": minutes(signal, departure),
                    "trader_stopped_before_eventual_source_objective": root[
                        "trader_stopped_before_eventual_source_objective"
                    ],
                }
            )
        timing.append(
            {
                "episode_id": seq["episode_id"],
                "partition": seq["partition"],
                "market": seq["market"],
                "ny_date": seq["ny_date"],
                "weekday": seq["weekday"],
                "last_structure_before_departure": seq.get("last_structure_before_departure"),
                "last_structure_touch_at": seq.get("last_structure_touch_at"),
                "first_breach_at": seq.get("first_breach_at"),
                "departure_at": seq["departure_pivot_at"],
                "objective_at": seq["opposite_boundary_at"],
                "departure_hour_minute_ny": local.strftime("%H:%M"),
                "departure_bucket_5m": f"{local.hour:02d}:{(local.minute // 5) * 5:02d}",
                "departure_bucket_15m": f"{local.hour:02d}:{(local.minute // 15) * 15:02d}",
                "departure_bucket_30m": f"{local.hour:02d}:{(local.minute // 30) * 30:02d}",
                "minutes_breach_to_departure": minutes(breach, departure),
                "minutes_last_structure_touch_to_departure": minutes(structure_touch, departure),
                "minutes_last_structure_touch_to_objective": minutes(structure_touch, objective),
                "minutes_departure_to_objective": minutes(departure, objective),
                "trader_root_overlays": overlays,
                "timing_class": "POST_OUTCOME_RESEARCH",
            }
        )

    if len(timing) != len(sequences):
        raise AssertionError("departure timing must conserve all completed sequences")
    (result_dir / "DEPARTURE_TIMING_LEDGER.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in timing),
        encoding="utf-8",
    )
    summary_path = result_dir / "CIBO_ATLAS_VT31_EIGHT_LEDGER_SUMMARY.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["ledger_counts"]["DEPARTURE_TIMING_LEDGER"] = len(timing)
    summary["departure_timing_scope"] = "all-completed-market-reversal-episodes-with-trader-root-overlays"
    summary_path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"departure_timing_rows": len(timing), "trader_overlay_rows": len(sync)}


def self_test() -> None:
    a = datetime.fromisoformat("2020-01-01T10:00:00-05:00")
    b = datetime.fromisoformat("2020-01-01T10:05:00-05:00")
    assert minutes(a, b) == 5
    print("CIBO Atlas departure timing upgrade self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--result-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.result_dir is None:
        parser.error("result-dir is required")
    print(json.dumps(build(args.result_dir), sort_keys=True))


if __name__ == "__main__":
    main()
