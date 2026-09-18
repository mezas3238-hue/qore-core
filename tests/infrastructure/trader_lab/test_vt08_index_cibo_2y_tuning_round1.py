from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as mod


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _raw_row(
    symbol: str,
    opened: datetime,
    *,
    low: int,
    delta_open: int,
    delta_high: int,
    delta_close: int,
) -> dict[str, Any]:
    return {
        "schema": mod.RAW_SCHEMA,
        "identity": mod.SOURCE_IDENTITY,
        "canonical_symbol": symbol,
        "opened_at": opened.astimezone(UTC).isoformat(),
        "low_relative": low,
        "delta_open": delta_open,
        "delta_high": delta_high,
        "delta_close": delta_close,
        "open_relative": low + delta_open,
        "high_relative": low + delta_high,
        "close_relative": low + delta_close,
    }


def _raw_root(tmp_path: Path, symbol: str) -> Path:
    root = tmp_path / symbol
    (root / "RAW_M5_LEDGER").mkdir(parents=True)
    manifest = {
        "identity": mod.SOURCE_IDENTITY,
        "canonical_symbol": symbol,
        "read_only": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "target_start": "2016-09-17T00:00:00+00:00",
        "target_end_exclusive": "2026-09-17T00:00:00+00:00",
    }
    (root / "symbol-consumption-manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    start = datetime(2016, 9, 19, 13, 0, tzinfo=UTC)
    complete = [
        _raw_row(
            symbol,
            start + timedelta(minutes=offset),
            low=100_000_000 + offset * 1000,
            delta_open=10_000,
            delta_high=50_000,
            delta_close=30_000,
        )
        for offset in (0, 5, 10)
    ]
    incomplete = [
        _raw_row(
            symbol,
            start + timedelta(minutes=15),
            low=101_000_000,
            delta_open=10_000,
            delta_high=40_000,
            delta_close=20_000,
        )
    ]
    _write_jsonl(root / "RAW_M5_LEDGER" / "2016.jsonl", complete + incomplete)
    _write_jsonl(root / "RAW_M5_LEDGER" / "2017.jsonl", [])
    _write_jsonl(root / "RAW_M5_LEDGER" / "2018.jsonl", [])
    return root


def test_raw_cibo_loader_reconstructs_only_complete_m15(tmp_path: Path) -> None:
    root = _raw_root(tmp_path, "NAS100")
    bars, provenance = mod._load_cibo_m15(root, symbol="NAS100")
    assert len(bars) == 1
    bar = bars[0]
    assert bar.opened_at == datetime(2016, 9, 19, 13, 0, tzinfo=UTC)
    assert bar.closed_at == datetime(2016, 9, 19, 13, 15, tzinfo=UTC)
    assert bar.open == Decimal("1000.1")
    assert bar.high == Decimal("1000.6")
    assert bar.low == Decimal("1000")
    assert bar.close == Decimal("1000.4")
    assert provenance["raw_m5_rows_in_window"] == 4
    assert provenance["m15_complete_buckets"] == 1
    assert provenance["m15_incomplete_buckets_dropped"] == 1
    assert provenance["m15_complete_rate"] == "0.5"


def test_metrics_reports_pf_drawdown_and_losing_streak() -> None:
    result = mod._metrics(
        [
            Decimal("1.0"),
            Decimal("-1.0"),
            Decimal("-1.0"),
            Decimal("2.0"),
            Decimal("-0.5"),
        ]
    )
    assert result["sample"] == 5
    assert result["wins"] == 2
    assert result["losses"] == 3
    assert result["total_r"] == "0.5"
    assert result["profit_factor"] == "1.2"
    assert result["max_drawdown_r"] == "2.0"
    assert result["max_losing_streak"] == 2


def test_candidate_report_uses_only_selected_pre_entry_dimensions() -> None:
    base = datetime(2017, 1, 3, 15, 0, tzinfo=UTC)
    rows = [
        mod.TradeSurfaceRow(
            symbol="NAS100",
            signal_at=base,
            side="long",
            anchor=6,
            model_kind="same-c2-intracandle",
            poi_kind="fvg",
            outcomes={"1.0": Decimal("1"), "2.0": Decimal("-1")},
        ),
        mod.TradeSurfaceRow(
            symbol="SP500",
            signal_at=base + timedelta(days=1),
            side="short",
            anchor=10,
            model_kind="same-c2-intracandle",
            poi_kind="fvg",
            outcomes={"1.0": Decimal("-1"), "2.0": Decimal("2")},
        ),
        mod.TradeSurfaceRow(
            symbol="US30",
            signal_at=base + timedelta(days=2),
            side="long",
            anchor=6,
            model_kind="same-c2-intracandle",
            poi_kind="fvg",
            outcomes={"1.0": Decimal("1"), "2.0": Decimal("2")},
        ),
    ]
    report = mod._candidate_report(
        rows,
        targets={"NAS100": "1.0", "SP500": None, "US30": "2.0"},
        anchors=(6,),
        sides=("long",),
    )
    primary = report["primary_stress"]
    assert isinstance(primary, dict)
    assert primary["sample"] == 2
    assert primary["total_r"] == "2.90"
    assert report["config"]["targets"]["SP500"] is None


def test_tuning_window_is_explicitly_consumed_not_fresh() -> None:
    assert mod.START_DATE.isoformat() == "2016-09-18"
    assert mod.END_DATE_EXCLUSIVE.isoformat() == "2018-09-15"
    assert mod.END_DATE_EXCLUSIVE <= date.fromisoformat("2018-09-15")
    assert mod.IDENTITY == "VT08_INDEX_CIBO_2Y_TUNING_ROUND1"


def test_target_maps_include_market_specialization_without_all_off() -> None:
    maps = list(mod._target_maps())
    assert maps
    assert not any(all(value is None for value in row.values()) for row in maps)
    assert any(
        row["NAS100"] is None
        and row["SP500"] == "1.5"
        and row["US30"] == "2.0"
        for row in maps
    )


def test_sort_key_prioritizes_stability_and_activity() -> None:
    stable = {
        "positive_halves": 2,
        "positive_quarters": 7,
        "primary_stress": {
            "sample": 450,
            "profit_factor": "1.20",
            "max_drawdown_r": "10",
            "mean_r": "0.02",
        },
    }
    unstable = {
        "positive_halves": 1,
        "positive_quarters": 4,
        "primary_stress": {
            "sample": 800,
            "profit_factor": "1.50",
            "max_drawdown_r": "5",
            "mean_r": "0.08",
        },
    }
    assert mod._sort_key(stable) > mod._sort_key(unstable)
