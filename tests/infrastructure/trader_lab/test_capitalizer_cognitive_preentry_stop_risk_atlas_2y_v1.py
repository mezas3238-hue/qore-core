from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2y_v1 as atlas,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _control(
    *,
    symbol: str,
    entry_at: str,
    realized_r: str,
    exit_reason: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "h1_open": "2026-01-05T09:00:00+00:00",
        "h1_deadline": "2026-01-05T10:00:00+00:00",
        "entry_at": entry_at,
        "entry_price": "1.2500",
        "stop_price": "1.2490",
        "target_r": "1.00",
        "target_price": "1.2510",
        "exit_at": "2026-01-05T09:50:00+00:00",
        "realized_gross_r": realized_r,
        "exit_reason": exit_reason,
        "same_minute_stop_target_ambiguity": False,
        "provenance": "CAUSAL_ARBITRATION_BASE",
    }


def _binding(
    *,
    symbol: str,
    entry_at: str,
    mss_at: str,
    fvg_at: str,
    overlap: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "h1_open": "2026-01-05T09:00:00+00:00",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "source_microstructure_match_found": True,
        "source_microstructure_bound": True,
        "source_timestamps_causal": True,
        "evidence_provenance_complete": True,
        "source_microstructure_family": "CAUSAL_ARBITRATION_BASE",
        "microstructure_observations": [
            "LIQUIDITY_SOURCE:PDH",
            "LIQUIDITY_KIND:LOW",
            "ENTRY_MODE:FVG_CE50",
            f"M1_OB_FVG_OVERLAP:{overlap}",
            f"M3_MSS_AT:{mss_at}",
            f"M1_FVG_CONFIRMED_AT:{fvg_at}",
        ],
        "baseline_portfolio_exposure_bound": True,
        "baseline_active_positions": 0,
        "baseline_shared_factors": [],
        "baseline_same_direction_factors": [],
        "baseline_opposing_direction_factors": [],
        "day_session_journey_bound": True,
        "prior_closed_trades_today": 0,
        "prior_realized_r_today": "0",
        "completed_prior_sessions": ["ASIA"],
        "prior_same_session_selected": 0,
        "session_slots_remaining_before": 3,
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


def test_stop_risk_atlas_builds_cells_without_outcome_admission(
    tmp_path: Path,
) -> None:
    binding_root = tmp_path / "binding"
    target_root = tmp_path / "target"

    controls = [
        _control(
            symbol="EURUSD",
            entry_at="2026-01-05T09:10:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
        _control(
            symbol="GBPUSD",
            entry_at="2026-01-05T09:20:00+00:00",
            realized_r="1",
            exit_reason="TARGET",
        ),
    ]
    _write_jsonl(
        target_root / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        controls,
    )

    bindings = [
        _binding(
            symbol="EURUSD",
            entry_at="2026-01-05T09:10:00+00:00",
            mss_at="2026-01-05T09:08:00+00:00",
            fvg_at="2026-01-05T09:09:00+00:00",
            overlap="FALSE",
        ),
        _binding(
            symbol="GBPUSD",
            entry_at="2026-01-05T09:20:00+00:00",
            mss_at="2026-01-05T09:10:00+00:00",
            fvg_at="2026-01-05T09:15:00+00:00",
            overlap="TRUE",
        ),
    ]
    _write_json(
        binding_root / "capitalizer-cognitive-evidence-binding-audit-2y-v2.json",
        {
            "identity": binding_v2.IDENTITY,
            "control_trades": 2,
            "future_evidence_violations": 0,
            "binding_coverage": {
                "source_microstructure": 2,
                "evidence_provenance_complete": 2,
            },
        },
    )
    _write_jsonl(
        binding_root / "capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl",
        bindings,
    )

    report = atlas.build_report(binding_root, target_root)

    assert report["control_trades"] == 2
    assert report["control_stops"] == 1
    assert report["current_outcome_used_to_create_cells"] is False
    assert report["cell_selected_for_enforcement"] is False
    phases = {
        row["value"]: row
        for row in report["feature_cells"]["MSS_TO_ENTRY_PHASE"]
    }
    assert phases["EARLY_LT5M"]["trades"] == 1
    assert phases["EARLY_LT5M"]["stops"] == 1
    assert phases["MATURE_GE5M"]["trades"] == 1
    overlap = {
        row["value"]: row
        for row in report["feature_cells"]["OB_FVG_OVERLAP"]
    }
    assert overlap["FALSE"]["stops"] == 1
    assert overlap["TRUE"]["stops"] == 0
