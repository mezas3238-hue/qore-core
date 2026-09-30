from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab.capitalizer_cognitive_failure_fingerprint_audit_2y_v1 import (
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


def _control(
    *,
    entry_at: str,
    exit_at: str,
    realized_r: str,
    exit_reason: str,
) -> dict[str, object]:
    return {
        "symbol": "EURUSD",
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
        "exit_at": exit_at,
        "realized_gross_r": realized_r,
        "exit_reason": exit_reason,
        "same_minute_stop_target_ambiguity": False,
        "provenance": "CAUSAL_ARBITRATION_BASE",
    }


def _binding_row(
    *,
    entry_at: str,
    prior_same_session_selected: int,
) -> dict[str, object]:
    return {
        "symbol": "EURUSD",
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
            "M1_OB_FVG_OVERLAP:TRUE",
            "M3_MSS_AT:2026-01-05T08:55:00+00:00",
        ],
        "baseline_portfolio_exposure_bound": True,
        "baseline_active_positions": 0,
        "baseline_shared_factors": [],
        "baseline_same_direction_factors": [],
        "baseline_opposing_direction_factors": [],
        "day_session_journey_bound": True,
        "prior_closed_trades_today": prior_same_session_selected,
        "prior_realized_r_today": "0",
        "completed_prior_sessions": ["ASIA"],
        "prior_same_session_selected": prior_same_session_selected,
        "session_slots_remaining_before": 3 - prior_same_session_selected,
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


def test_failure_fingerprint_uses_only_causal_categories(tmp_path: Path) -> None:
    binding_root = tmp_path / "binding"
    target_root = tmp_path / "target"

    controls = [
        _control(
            entry_at="2026-01-05T09:00:00+00:00",
            exit_at="2026-01-05T09:05:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
        _control(
            entry_at="2026-01-05T09:10:00+00:00",
            exit_at="2026-01-05T09:15:00+00:00",
            realized_r="1",
            exit_reason="TARGET",
        ),
        _control(
            entry_at="2026-01-05T09:20:00+00:00",
            exit_at="2026-01-05T09:25:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
    ]
    _write_jsonl(
        target_root / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        controls,
    )

    binding_rows = [
        _binding_row(
            entry_at="2026-01-05T09:00:00+00:00",
            prior_same_session_selected=0,
        ),
        _binding_row(
            entry_at="2026-01-05T09:10:00+00:00",
            prior_same_session_selected=1,
        ),
        _binding_row(
            entry_at="2026-01-05T09:20:00+00:00",
            prior_same_session_selected=2,
        ),
    ]
    _write_json(
        binding_root / "capitalizer-cognitive-evidence-binding-audit-2y-v2.json",
        {
            "identity": binding_v2.IDENTITY,
            "control_trades": 3,
            "future_evidence_violations": 0,
            "binding_coverage": {
                "source_microstructure": 3,
                "evidence_provenance_complete": 3,
            },
        },
    )
    _write_jsonl(
        binding_root / "capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl",
        binding_rows,
    )

    report, rows = build_report(binding_root, target_root)

    assert report["control_trades"] == 3
    assert report["fingerprint_candidate_coverage"] == 3
    assert report["unique_structural_fingerprints"] == 1
    assert report["unique_contextual_fingerprints"] == 3
    assert report["recurrence_after_prior_closed_loss"]["structural_same_day"] == 2
    assert report["recurrence_after_prior_closed_loss"]["contextual_same_day"] == 0
    assert report["current_outcome_used_to_build_fingerprint"] is False
    assert report["current_outcome_used_to_detect_repeat"] is False
    assert report["runtime_failure_fingerprint_selected"] is False
    assert report["loss_memory_resolution_bound"] is False

    assert rows[0].prior_closed_loss_same_structural_same_day == 0
    assert rows[1].prior_closed_loss_same_structural_same_day == 1
    assert rows[2].prior_closed_loss_same_structural_same_day == 1
    assert all("_AT:" not in token for token in rows[0].structural_tokens)
    assert "M3_MSS_AT:2026-01-05T08:55:00+00:00" not in rows[0].structural_tokens
