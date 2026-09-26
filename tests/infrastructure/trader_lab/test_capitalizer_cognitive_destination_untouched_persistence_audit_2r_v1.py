from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_destination_departure_binding_audit_2r_v1 as departure,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_destination_untouched_persistence_audit_2r_v1 as persistence,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    EXPECTED_IDENTITY,
    EXPECTED_SCHEMA,
)
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    TARGET_IDENTITY,
    TARGET_SCHEMA,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _rebase_row(
    *,
    entry_at: str,
) -> dict[str, object]:
    return {
        "symbol": "AUDJPY",
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
    }


def _departure_row(
    *,
    entry_at: str,
    departure_at: str,
    candidate_count: int,
) -> dict[str, object]:
    return {
        "symbol": "AUDJPY",
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "m5_closeback_at": departure_at,
        "target_context_match_found": True,
        "target_context_causal": True,
        "destination_departure_evidence_bound": True,
        "active_candidate_count": candidate_count,
        "nearest_distance_ticks": "10",
        "candidate_families": ["SOURCE_OPPOSITE_BOUNDARY"],
        "candidate_timeframes": ["H1"],
        "departure_to_entry_seconds": "180",
        "departure_context_known_by_entry": True,
        "destination_current_at_entry_supported": False,
        "destination_available_at_entry_supported": False,
        "target_result_fields_read": False,
        "current_trade_outcome_visible_to_binding": False,
    }


def _target_row(
    *,
    departure_at: str,
    candidate_id: str,
    family: str,
    timeframe: str,
    price: str,
) -> dict[str, object]:
    return {
        "identity": TARGET_IDENTITY,
        "schema": TARGET_SCHEMA,
        "symbol": "AUDJPY",
        "side": "long",
        "departure_at": departure_at,
        "candidate_id": candidate_id,
        "candidate_type": family,
        "source_timeframe": timeframe,
        "candidate_price": price,
        "candidate_distance_ticks": "10",
        "candidate_known_at": "2026-01-04T23:55:00+00:00",
        "candidate_structural_opened_at": "2026-01-04T23:00:00+00:00",
        "active_untouched_at_departure": True,
        "causal_feature": True,
        "outcome_only": False,
        "result_fields_outcome_only": True,
        "touch_within_24h": True,
        "touch_m5_opened_at": "2026-01-05T03:00:00+00:00",
    }


def _m1_row(
    *,
    opened_at: str,
    high_relative: int,
    low_relative: int,
) -> dict[str, object]:
    return {
        "schema": EXPECTED_SCHEMA,
        "identity": EXPECTED_IDENTITY,
        "canonical_symbol": "AUDJPY",
        "opened_at": opened_at,
        "digits": 5,
        "open_relative": 100000,
        "high_relative": high_relative,
        "low_relative": low_relative,
        "close_relative": 100000,
        "volume": 100,
    }


def test_destination_untouched_persistence_is_m1_causal_and_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rebase, "EXPECTED_TRADES", 2)

    rebase_root = tmp_path / "rebase"
    departure_root = tmp_path / "departure"
    target_root = tmp_path / "target"
    m1_root = tmp_path / "m1"

    first_entry = "2026-01-05T00:08:00+00:00"
    second_entry = "2026-01-05T00:12:00+00:00"

    rebase_rows = [
        _rebase_row(entry_at=first_entry),
        _rebase_row(entry_at=second_entry),
    ]
    _write_json(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1.json",
        {
            "identity": rebase.IDENTITY,
            "target_r": "2.00",
            "control_trades": 2,
        },
    )
    _write_jsonl(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl",
        rebase_rows,
    )

    departure_rows = [
        _departure_row(
            entry_at=first_entry,
            departure_at="2026-01-05T00:05:00+00:00",
            candidate_count=2,
        ),
        _departure_row(
            entry_at=second_entry,
            departure_at="2026-01-05T00:10:00+00:00",
            candidate_count=1,
        ),
    ]
    _write_json(
        departure_root
        / "capitalizer-cognitive-destination-departure-binding-audit-2r-v1.json",
        {
            "identity": departure.IDENTITY,
            "control_trades": 2,
            "future_evidence_violations": 0,
            "target_result_fields_read": False,
            "target_touch_fields_used": False,
            "destination_current_at_entry_supported": False,
        },
    )
    _write_jsonl(
        departure_root
        / "capitalizer-cognitive-destination-departure-binding-audit-2r-v1-rows.jsonl",
        departure_rows,
    )

    _write_jsonl(
        target_root / "TARGET_DESTINATION_LEDGER_V2.jsonl",
        [
            _target_row(
                departure_at="2026-01-05T00:05:00+00:00",
                candidate_id="A",
                family="SOURCE_OPPOSITE_BOUNDARY",
                timeframe="H1",
                price="1.00100",
            ),
            _target_row(
                departure_at="2026-01-05T00:05:00+00:00",
                candidate_id="B",
                family="ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
                timeframe="H4",
                price="1.00500",
            ),
            _target_row(
                departure_at="2026-01-05T00:10:00+00:00",
                candidate_id="C",
                family="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
                timeframe="H1",
                price="1.00400",
            ),
        ],
    )

    _write_jsonl(
        m1_root / "RAW_M1_LEDGER" / "2026.jsonl",
        [
            _m1_row(
                opened_at="2026-01-05T00:05:00+00:00",
                high_relative=100050,
                low_relative=99950,
            ),
            _m1_row(
                opened_at="2026-01-05T00:06:00+00:00",
                high_relative=100150,
                low_relative=99950,
            ),
            _m1_row(
                opened_at="2026-01-05T00:07:00+00:00",
                high_relative=100050,
                low_relative=99950,
            ),
            _m1_row(
                opened_at="2026-01-05T00:10:00+00:00",
                high_relative=100050,
                low_relative=99950,
            ),
        ],
    )

    report, rows = persistence.build_market_report(
        rebase_root,
        departure_root,
        target_root,
        m1_root,
        symbol="AUDJPY",
    )

    assert report["departure_bound_trades"] == 2
    assert report["m1_window_complete_trades"] == 1
    assert report["m1_window_incomplete_trades"] == 1
    assert report["at_least_one_candidate_untouched_through_entry_trades"] == 1
    assert report["all_candidates_touched_before_entry_trades"] == 0
    assert report["target_result_fields_read"] is False
    assert report["target_touch_fields_read"] is False
    assert report["current_trade_outcome_visible_to_audit"] is False
    assert report["destination_structural_current_at_entry_supported"] is False
    assert report["destination_available_at_entry_supported"] is False
    assert report["destination_intelligence_supported"] is False

    first, second = rows
    assert first.m1_window_complete is True
    assert first.expected_m1_bars == 3
    assert first.observed_m1_bars == 3
    assert first.touched_before_entry_count == 1
    assert first.untouched_through_entry_count == 1
    assert first.untouched_candidate_families == (
        "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
    )
    assert first.untouched_candidate_timeframes == ("H4",)
    assert first.at_least_one_candidate_untouched_through_entry is True

    assert second.m1_window_complete is False
    assert second.expected_m1_bars == 2
    assert second.observed_m1_bars == 1
    assert second.touched_before_entry_count == 0
    assert second.untouched_through_entry_count == 0
    assert second.untouched_persistence_supported is False
