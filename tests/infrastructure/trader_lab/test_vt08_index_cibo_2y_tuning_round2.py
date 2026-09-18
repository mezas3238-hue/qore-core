from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round2 as mod


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _row(symbol: str, opened: datetime, offset: int) -> dict[str, Any]:
    low = 100_000_000 + offset * 10_000
    return {
        "schema": r1.RAW_SCHEMA,
        "identity": r1.SOURCE_IDENTITY,
        "canonical_symbol": symbol,
        "opened_at": opened.isoformat(),
        "low_relative": low,
        "open_relative": low + 10_000,
        "high_relative": low + 50_000,
        "close_relative": low + 30_000,
    }


def _root(tmp_path: Path, symbol: str) -> Path:
    root = tmp_path / symbol
    (root / "RAW_M5_LEDGER").mkdir(parents=True)
    (root / "symbol-consumption-manifest.json").write_text(
        json.dumps(
            {
                "identity": r1.SOURCE_IDENTITY,
                "canonical_symbol": symbol,
                "read_only": True,
                "live_authorized": False,
                "real_capital_authorized": False,
                "target_start": "2016-09-17T00:00:00+00:00",
                "target_end_exclusive": "2026-09-17T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    start = datetime(2016, 9, 19, 13, 0, tzinfo=UTC)
    rows = [
        _row(symbol, start + timedelta(minutes=0), 0),
        _row(symbol, start + timedelta(minutes=5), 1),
        _row(symbol, start + timedelta(minutes=10), 2),
        _row(symbol, start + timedelta(minutes=15), 3),
        _row(symbol, start + timedelta(minutes=25), 4),
    ]
    _write_jsonl(root / "RAW_M5_LEDGER" / "2016.jsonl", rows)
    _write_jsonl(root / "RAW_M5_LEDGER" / "2017.jsonl", [])
    _write_jsonl(root / "RAW_M5_LEDGER" / "2018.jsonl", [])
    return root


def test_provider_available_reconstruction_keeps_partial_m15(tmp_path: Path) -> None:
    root = _root(tmp_path, "SP500")
    bars, provenance = mod._load_cibo_m15_available(root, symbol="SP500")
    assert len(bars) == 2
    assert provenance["m15_bucket_size_counts"] == {"1": 0, "2": 1, "3": 1}
    assert provenance["partial_m15_buckets"] == 1
    assert provenance["synthetic_prices"] == 0
    assert provenance["interpolated_prices"] == 0


def test_round2_available_reconstruction_is_less_destructive_than_round1(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, "NAS100")
    strict, _ = r1._load_cibo_m15(root, symbol="NAS100")
    available, _ = mod._load_cibo_m15_available(root, symbol="NAS100")
    assert len(strict) == 1
    assert len(available) == 2


def test_round2_identity_and_governance_are_explicit() -> None:
    assert mod.IDENTITY == "VT08_INDEX_CIBO_2Y_TUNING_ROUND2_PROVIDER_AVAILABLE_M15"
    assert r1.START_DATE.isoformat() == "2016-09-18"
    assert r1.END_DATE_EXCLUSIVE.isoformat() == "2018-09-15"
