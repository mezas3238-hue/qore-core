from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from qore.infrastructure.trader_lab.capitalizer_candidate_window_filter_v1 import (
    filter_candidate_window,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_window_clone_v1 import (
    IDENTITY,
    clone_window,
)


def _write_candidate(path: Path, signal_at: str) -> None:
    payload = {
        "signal_at": signal_at,
        "outcome_used_for_selection": False,
        "symbol": "EURUSD",
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def test_candidate_filter_splits_without_outcome_selection(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    ledger = source / "capitalizer-eurusd-three-session-replay-cell-v1-trades.jsonl"
    _write_candidate(ledger, "2020-01-01T00:00:00+00:00")
    _write_candidate(ledger, "2023-01-01T00:00:00+00:00")

    source_count, retained = filter_candidate_window(
        source,
        output,
        start=datetime(2016, 9, 17, tzinfo=UTC),
        end_exclusive=datetime(2021, 9, 17, tzinfo=UTC),
    )

    assert source_count == 2
    assert retained == 1
    rows = [
        json.loads(line)
        for line in next(output.glob("*.jsonl")).read_text().splitlines()
    ]
    assert rows[0]["signal_at"].startswith("2020-01-01")
    assert rows[0]["outcome_used_for_selection"] is False


def test_m1_window_clone_restores_global_ten_year_contract(tmp_path: Path) -> None:
    from qore.infrastructure.trader_lab import capitalizer_cibo_10y_m1_clone_v1 as base

    original_start = base.TARGET_START
    original_end = base.TARGET_END_EXCLUSIVE
    start = datetime(2016, 9, 17, tzinfo=UTC)
    end = datetime(2021, 9, 17, tzinfo=UTC)

    fake_manifest = {
        "identity": base.IDENTITY,
        "retained_m1": 123,
        "provider_native_m1": True,
        "synthetic_m1": False,
        "interpolated_m1": False,
    }

    def fake_clone(symbol: str, output: Path) -> dict[str, object]:
        assert symbol == "EURUSD"
        assert base.TARGET_START == start
        assert base.TARGET_END_EXCLUSIVE == end
        output.mkdir(parents=True, exist_ok=True)
        return fake_manifest

    with patch.object(base, "clone_symbol", side_effect=fake_clone):
        result = clone_window(
            "EURUSD",
            tmp_path / "m1",
            start=start,
            end_exclusive=end,
            role="DEVELOPMENT",
        )

    assert result["identity"] == IDENTITY
    assert result["role"] == "DEVELOPMENT"
    assert result["target_start"] == start.isoformat()
    assert result["target_end_exclusive"] == end.isoformat()
    assert result["retained_m1"] == 123
    assert result["methodology_changed"] is False
    assert result["m1_mss_required"] is True
    assert result["m1_fvg_required"] is True
    assert result["m1_order_block_required"] is True
    assert base.TARGET_START == original_start
    assert base.TARGET_END_EXCLUSIVE == original_end
