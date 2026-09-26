from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_destination_departure_binding_audit_2r_v1 as binding,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_destination_departure_information_atlas_2r_v1 as atlas,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
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
    symbol: str,
    entry_at: str,
    realized_r: str,
    exit_reason: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "entry_at": entry_at,
        "post_audit_exit_at": "2026-01-05T01:00:00+00:00",
        "post_audit_realized_gross_r": realized_r,
        "post_audit_exit_reason": exit_reason,
    }


def _binding_row(
    *,
    symbol: str,
    entry_at: str,
    bound: bool,
    count: int = 0,
    families: tuple[str, ...] = (),
    timeframes: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "m5_closeback_at": "2026-01-05T00:05:00+00:00" if bound else None,
        "target_context_match_found": bound,
        "target_context_causal": bound,
        "destination_departure_evidence_bound": bound,
        "active_candidate_count": count,
        "nearest_distance_ticks": "25" if bound else None,
        "candidate_families": list(families),
        "candidate_timeframes": list(timeframes),
        "departure_to_entry_seconds": "300" if bound else None,
        "departure_context_known_by_entry": bound,
        "destination_current_at_entry_supported": False,
        "destination_available_at_entry_supported": False,
        "target_result_fields_read": False,
        "current_trade_outcome_visible_to_binding": False,
    }


def test_destination_information_uses_only_bound_categorical_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rebase, "EXPECTED_TRADES", 4)
    monkeypatch.setattr(atlas, "MIN_DESCRIPTIVE_SUPPORT", 1)

    rebase_root = tmp_path / "rebase"
    destination_root = tmp_path / "destination"

    rebase_rows = [
        _rebase_row(
            symbol="AUDJPY",
            entry_at="2026-01-05T00:10:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
        _rebase_row(
            symbol="GBPJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            realized_r="2",
            exit_reason="TARGET",
        ),
        _rebase_row(
            symbol="USDJPY",
            entry_at="2026-01-05T00:30:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
        _rebase_row(
            symbol="AUDUSD",
            entry_at="2026-01-05T00:40:00+00:00",
            realized_r="2",
            exit_reason="TARGET",
        ),
    ]
    _write_json(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1.json",
        {
            "identity": rebase.IDENTITY,
            "target_r": "2.00",
            "control_trades": 4,
        },
    )
    _write_jsonl(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl",
        rebase_rows,
    )

    destination_rows = [
        _binding_row(
            symbol="AUDJPY",
            entry_at="2026-01-05T00:10:00+00:00",
            bound=True,
            count=3,
            families=(
                "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
                "SOURCE_OPPOSITE_BOUNDARY",
            ),
            timeframes=("H1", "H4"),
        ),
        _binding_row(
            symbol="GBPJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            bound=True,
            count=2,
            families=("PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",),
            timeframes=("H1",),
        ),
        _binding_row(
            symbol="USDJPY",
            entry_at="2026-01-05T00:30:00+00:00",
            bound=False,
        ),
        _binding_row(
            symbol="AUDUSD",
            entry_at="2026-01-05T00:40:00+00:00",
            bound=False,
        ),
    ]
    _write_json(
        destination_root
        / "capitalizer-cognitive-destination-departure-binding-audit-2r-v1.json",
        {
            "identity": binding.IDENTITY,
            "control_trades": 4,
            "destination_departure_evidence_bound_trades": 2,
            "future_evidence_violations": 0,
            "target_result_fields_read": False,
            "target_touch_fields_used": False,
            "destination_current_at_entry_supported": False,
            "destination_available_at_entry_supported": False,
        },
    )
    _write_jsonl(
        destination_root
        / "capitalizer-cognitive-destination-departure-binding-audit-2r-v1-rows.jsonl",
        destination_rows,
    )

    report = atlas.build_report(rebase_root, destination_root)

    assert report["control_trades"] == 4
    assert report["destination_bound_trades"] == 2
    assert report["destination_unbound_trades"] == 2
    assert report["feature_count"] == 5
    assert report["minimum_descriptive_support"] == 1
    assert report["supported_cell_count"] > 0
    assert report["unbound_is_not_destination_absent"] is True
    assert report["nearest_distance_not_used_for_cell_selection"] is True
    assert report["numeric_destination_thresholds_added"] is False
    assert report["target_result_fields_read"] is False
    assert report["target_touch_fields_used"] is False
    assert report["destination_current_at_entry_supported"] is False
    assert report["destination_available_at_entry_supported"] is False
    assert report["destination_intelligence_supported"] is False
    assert report["current_outcome_used_to_define_cells"] is False
    assert report["automatic_cell_selection"] is False
    assert report["runtime_rule_selected"] is False
