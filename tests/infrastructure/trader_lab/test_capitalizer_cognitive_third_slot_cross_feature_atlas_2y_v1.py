from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_third_slot_cross_feature_atlas_2y_v1 as cross,
)
    cross.JOURNEY_FEATURES,
    cross.PREENTRY_FEATURES,
    build_report,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _trade(
    *,
    operating_day: str,
    index: int,
    realized_r: str,
    exit_reason: str,
) -> dict[str, object]:
    minute = index * 10
    entry = f"{operating_day}T09:{minute:02d}:00+00:00"
    exit_minute = minute + 5
    exit_at = f"{operating_day}T09:{exit_minute:02d}:00+00:00"
    return {
        "symbol": "EURUSD",
        "session": "LONDON",
        "operating_date": operating_day,
        "side": "LONG",
        "h1_open": f"{operating_day}T09:00:00+00:00",
        "h1_deadline": f"{operating_day}T10:00:00+00:00",
        "entry_at": entry,
        "entry_price": "1.2500",
        "stop_price": "1.2490",
        "target_r": "1.00",
        "target_price": "1.2510",
        "exit_at": exit_at,
        "realized_gross_r": realized_r,
        "exit_reason": exit_reason,
        "same_minute_stop_target_ambiguity": False,
        "provenance": "CAUSAL_ARBITRATION_BASE",
    }


def _binding(
    *,
    operating_day: str,
    index: int,
) -> dict[str, object]:
    minute = index * 10
    entry = f"{operating_day}T09:{minute:02d}:00+00:00"
    mss_minute = max(0, minute - 6)
    fvg_minute = max(0, minute - 2)
    return {
        "symbol": "EURUSD",
        "session": "LONDON",
        "operating_date": operating_day,
        "side": "LONG",
        "h1_open": f"{operating_day}T09:00:00+00:00",
        "entry_at": entry,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "source_microstructure_match_found": True,
        "source_microstructure_bound": True,
        "source_timestamps_causal": True,
        "evidence_provenance_complete": True,
        "source_microstructure_family": "CAUSAL_ARBITRATION_BASE",
        "microstructure_observations": [
            "LIQUIDITY_SOURCE:PDH",
            "LIQUIDITY_KIND:HIGH",
            "ENTRY_MODE:FVG_CE_50",
            "M1_OB_FVG_OVERLAP:TRUE",
            f"M3_MSS_AT:{operating_day}T09:{mss_minute:02d}:00+00:00",
            f"M1_FVG_CONFIRMED_AT:{operating_day}T09:{fvg_minute:02d}:00+00:00",
        ],
        "baseline_portfolio_exposure_bound": True,
        "baseline_active_positions": 0,
        "baseline_shared_factors": [],
        "baseline_same_direction_factors": [],
        "baseline_opposing_direction_factors": [],
        "day_session_journey_bound": True,
        "prior_closed_trades_today": index,
        "prior_realized_r_today": "0",
        "completed_prior_sessions": ["ASIA"],
        "prior_same_session_selected": index,
        "session_slots_remaining_before": 3 - index,
        "baseline_slot_state_bound": True,
        "failure_state_fingerprint_bound": False,
        "destination_intelligence_bound": False,
        "regime_intelligence_bound": False,
        "execution_quality_bound": False,
        "perception_integrity_bound": False,
        "full_opportunity_competition_bound": False,
        "current_outcome_visible_to_binding": False,
        "full_master_cognitive_frame_ready": False,
    }


def test_cross_feature_atlas_is_pairwise_and_causal(tmp_path: Path) -> None:
    binding_root = tmp_path / "binding"
    target_root = tmp_path / "target"

    controls: list[dict[str, object]] = []
    bindings: list[dict[str, object]] = []
    start = date(2026, 1, 1)
    for offset in range(40):
        operating_day = (start + timedelta(days=offset)).isoformat()
        controls.extend(
            [
                _trade(
                    operating_day=operating_day,
                    index=0,
                    realized_r="1",
                    exit_reason="TARGET",
                ),
                _trade(
                    operating_day=operating_day,
                    index=1,
                    realized_r="-1",
                    exit_reason="STOP",
                ),
                _trade(
                    operating_day=operating_day,
                    index=2,
                    realized_r="-1" if offset % 2 == 0 else "1",
                    exit_reason="STOP" if offset % 2 == 0 else "TARGET",
                ),
            ]
        )
        bindings.extend(
            [
                _binding(operating_day=operating_day, index=0),
                _binding(operating_day=operating_day, index=1),
                _binding(operating_day=operating_day, index=2),
            ]
        )

    _write_jsonl(
        target_root / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        controls,
    )
    _write_json(
        binding_root / "capitalizer-cognitive-evidence-binding-audit-2y-v2.json",
        {
            "identity": binding_v2.IDENTITY,
            "control_trades": len(controls),
            "future_evidence_violations": 0,
            "binding_coverage": {
                "source_microstructure": len(controls),
                "evidence_provenance_complete": len(controls),
            },
        },
    )
    _write_jsonl(
        binding_root / "capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl",
        bindings,
    )

    report = cross.build_report(binding_root, target_root)

    assert report["control_trades"] == 120
    assert report["third_slot_trades"] == 40
    assert report["journey_features"] == cross.JOURNEY_FEATURES
    assert report["preentry_features"] == cross.PREENTRY_FEATURES
    assert report["pairwise_cell_count"] > 0
    assert report["pairwise_only_no_three_way_search"] is True
    assert report["all_features_known_by_entry"] is True
    assert report["current_candidate_outcome_used_to_create_cell"] is False
    assert report["automatic_cell_selection"] is False
    assert report["runtime_rule_selected"] is False
    assert all(
        row["full_portfolio_if_abstained_trades"]
        + row["third_slot_trades"]
        == 120
        for row in report["cells"]
    )
