from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.core_stack_v2.mc14_b04_cross_asset_causal import (
    extract_window_features,
    freeze_source_thresholds,
)


def _write_shard(
    root: Path,
    *,
    side: str,
    prices: list[tuple[str, int]],
) -> None:
    path = (
        root
        / "data"
        / side
        / f"w000000-p000000-{side}.jsonl.gz"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    header = {
        "header": {
            "quote_side": side,
            "window_index": 0,
            "request_from_at": "2026-01-01T10:00:00+00:00",
            "request_to_at": "2026-01-01T11:15:00+00:00",
        }
    }
    lines = [json.dumps(header)]
    lines.extend(
        json.dumps(
            {
                "tick": {
                    "provider_event_at": observed_at,
                    "relative_price": price,
                }
            }
        )
        for observed_at, price in prices
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def test_extract_window_features_excludes_post_source_ticks(
    tmp_path: Path,
) -> None:
    _write_shard(
        tmp_path,
        side="bid",
        prices=[
            ("2026-01-01T10:00:00+00:00", 100_000),
            ("2026-01-01T11:00:00+00:00", 110_000),
            ("2026-01-01T11:05:00+00:00", 900_000),
        ],
    )
    _write_shard(
        tmp_path,
        side="ask",
        prices=[
            ("2026-01-01T10:00:00+00:00", 102_000),
            ("2026-01-01T11:00:00+00:00", 112_000),
            ("2026-01-01T11:05:00+00:00", 902_000),
        ],
    )
    rows = extract_window_features(
        root=tmp_path,
        expected_window_count=1,
    )
    row = rows[0]
    assert row.complete is True
    assert row.source_at == datetime(
        2026,
        1,
        1,
        11,
        0,
        tzinfo=UTC,
    )
    assert row.bid_tick_count == 2
    assert row.ask_tick_count == 2
    assert row.feature("MID_RETURN_BPS") == 990
    assert row.feature("ABS_MID_RETURN_BPS") == 990
    assert row.feature(
        "QUOTE_SIDE_ACTIVITY_IMBALANCE_BPS"
    ) == 0


def test_extract_window_features_fails_closed_on_missing_quote_side(
    tmp_path: Path,
) -> None:
    _write_shard(
        tmp_path,
        side="bid",
        prices=[
            ("2026-01-01T10:00:00+00:00", 100_000),
            ("2026-01-01T11:00:00+00:00", 110_000),
        ],
    )
    rows = extract_window_features(
        root=tmp_path,
        expected_window_count=1,
    )
    assert rows[0].complete is False
    assert rows[0].values == ()


def test_freeze_source_thresholds_are_strict_and_target_blind() -> None:
    low, high = freeze_source_thresholds(list(range(1000)))
    assert low < high
    assert 400 <= low <= 500
    assert 500 <= high <= 600
