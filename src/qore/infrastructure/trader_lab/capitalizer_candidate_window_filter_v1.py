"""Window a frozen Capitalizer higher-level candidate ledger without changing methodology.

This utility filters the immutable 10Y higher-level candidate ledger by signal timestamp.
It never inspects trade outcome fields for selection and preserves each retained row verbatim.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def filter_candidate_window(
    source_root: Path,
    output_root: Path,
    *,
    start: datetime,
    end_exclusive: datetime,
) -> tuple[int, int]:
    paths = sorted(
        source_root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl")
    )
    if len(paths) != 1:
        raise ValueError(f"expected one higher-level ledger, got {len(paths)}")

    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / paths[0].name
    source_count = 0
    retained = 0
    with paths[0].open(encoding="utf-8") as src, output.open(
        "w", encoding="utf-8"
    ) as dst:
        for line in src:
            if not line.strip():
                continue
            raw: Any = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("candidate row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("candidate windowing cannot consume outcome-selected rows")
            source_count += 1
            signal = datetime.fromisoformat(str(raw["signal_at"]))
            if signal.tzinfo is None or signal.utcoffset() is None:
                raise ValueError("signal_at must be timezone-aware")
            if start <= signal < end_exclusive:
                dst.write(json.dumps(raw, sort_keys=True) + "\n")
                retained += 1

    if retained <= 0:
        raise ValueError("candidate window is empty")
    return source_count, retained


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end-exclusive", required=True)
    args = parser.parse_args()

    start = datetime.fromisoformat(args.start)
    end_exclusive = datetime.fromisoformat(args.end_exclusive)
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("--start must be timezone-aware")
    if end_exclusive.tzinfo is None or end_exclusive.utcoffset() is None:
        raise ValueError("--end-exclusive must be timezone-aware")
    if end_exclusive <= start:
        raise ValueError("window end must be after start")

    source_count, retained = filter_candidate_window(
        args.source_root,
        args.output_root,
        start=start,
        end_exclusive=end_exclusive,
    )
    print(
        json.dumps(
            {
                "source_candidates": source_count,
                "retained_candidates": retained,
                "start": start.isoformat(),
                "end_exclusive": end_exclusive.isoformat(),
                "outcome_used_for_selection": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
