from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_destination_departure_binding_audit_2r_v1 as destination,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
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
    symbol: str,
    entry_at: str,
    closeback_at: str | None,
    provenance: str = "CAUSAL_ARBITRATION_BASE",
) -> dict[str, object]:
    observations: list[str] = []
    if closeback_at is not None:
        observations.append(f"M5_CLOSEBACK_AT:{closeback_at}")
    return {
        "symbol": symbol,
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "entry_at": entry_at,
        "provenance": provenance,
        "source_microstructure_family": provenance,
        "microstructure_observations": observations,
        "post_audit_exit_at": "2026-01-05T01:00:00+00:00",
        "post_audit_realized_gross_r": "-1",
        "post_audit_exit_reason": "STOP",
    }


def _target_row(
    *,
    departure_at: str,
    candidate_id: str,
    family: str,
    timeframe: str,
    distance: str,
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
        "candidate_distance_ticks": distance,
        "candidate_known_at": "2026-01-05T00:00:00+00:00",
        "candidate_structural_opened_at": "2026-01-04T23:00:00+00:00",
        "candidate_price": "100",
        "active_untouched_at_departure": True,
        "causal_feature": True,
        "outcome_only": False,
        "result_fields_outcome_only": True,
        "touch_m5_opened_at": "2026-01-05T03:00:00+00:00",
        "touch_within_24h": True,
    }


def test_destination_departure_binding_is_exact_and_outcome_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rebase, "EXPECTED_TRADES", 3)
    rebase_root = tmp_path / "rebase"
    target_root = tmp_path / "target"

    rows = [
        _rebase_row(
            symbol="AUDJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            closeback_at="2026-01-05T00:05:00+00:00",
        ),
        _rebase_row(
            symbol="AUDJPY",
            entry_at="2026-01-05T00:40:00+00:00",
            closeback_at="2026-01-05T00:35:00+00:00",
        ),
        _rebase_row(
            symbol="GBPJPY",
            entry_at="2026-01-05T00:50:00+00:00",
            closeback_at=None,
            provenance="PROTECTED_SWING_GEOMETRY_RESCUE",
        ),
    ]
    _write_json(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1.json",
        {
            "identity": rebase.IDENTITY,
            "target_r": "2.00",
            "control_trades": 3,
        },
    )
    _write_jsonl(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl",
        rows,
    )

    _write_jsonl(
        target_root / "AUDJPY" / "TARGET_DESTINATION_LEDGER_V2.jsonl",
        [
            _target_row(
                departure_at="2026-01-05T00:05:00+00:00",
                candidate_id="C1",
                family="SOURCE_OPPOSITE_BOUNDARY",
                timeframe="H1",
                distance="25",
            ),
            _target_row(
                departure_at="2026-01-05T00:05:00+00:00",
                candidate_id="C2",
                family="ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
                timeframe="H4",
                distance="80",
            ),
        ],
    )

    report, bound_rows = destination.build_report(rebase_root, target_root)

    assert report["control_trades"] == 3
    assert report["requested_exact_departure_keys"] == 2
    assert report["destination_departure_evidence_bound_trades"] == 1
    assert report["destination_departure_evidence_unbound_trades"] == 2
    assert report["future_evidence_violations"] == 0
    assert report["target_result_fields_read"] is False
    assert report["target_touch_fields_used"] is False
    assert report["departure_context_known_by_entry_supported"] is True
    assert report["destination_current_at_entry_supported"] is False
    assert report["destination_available_at_entry_supported"] is False
    assert report["destination_intelligence_supported"] is False
    assert report["current_trade_outcome_visible_to_binding"] is False
    assert report["missing_evidence_fabricated"] is False

    first, second, third = bound_rows
    assert first.destination_departure_evidence_bound is True
    assert first.active_candidate_count == 2
    assert first.nearest_distance_ticks == "25"
    assert first.candidate_families == (
        "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
        "SOURCE_OPPOSITE_BOUNDARY",
    )
    assert first.candidate_timeframes == ("H1", "H4")
    assert first.departure_to_entry_seconds == "900.0"

    assert second.m5_closeback_at == "2026-01-05T00:35:00+00:00"
    assert second.target_context_match_found is False
    assert second.destination_departure_evidence_bound is False

    assert third.m5_closeback_at is None
    assert third.destination_departure_evidence_bound is False
