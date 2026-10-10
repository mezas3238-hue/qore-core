from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_simultaneous_factor_collision_atlas_2y_v1 as collision,
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
    symbol: str,
    session: str,
    side: str,
    operating_date: str,
    entry_at: str,
    exit_at: str,
    realized_r: str,
    exit_reason: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": session,
        "operating_date": operating_date,
        "side": side,
        "h1_open": entry_at,
        "h1_deadline": exit_at,
        "entry_at": entry_at,
        "entry_price": "1",
        "stop_price": "0.9",
        "target_r": "1.00",
        "target_price": "1.1",
        "exit_at": exit_at,
        "realized_gross_r": realized_r,
        "exit_reason": exit_reason,
        "same_minute_stop_target_ambiguity": False,
        "provenance": "CAUSAL_ARBITRATION_BASE",
    }


def _binding(
    *,
    symbol: str,
    session: str,
    side: str,
    operating_date: str,
    entry_at: str,
    prior_selected: int,
    entry_mode: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": session,
        "operating_date": operating_date,
        "side": side,
        "h1_open": entry_at,
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "source_microstructure_match_found": True,
        "source_microstructure_bound": True,
        "source_timestamps_causal": True,
        "evidence_provenance_complete": True,
        "source_microstructure_family": "CAUSAL_ARBITRATION_BASE",
        "microstructure_observations": [
            f"ENTRY_MODE:{entry_mode}",
            "M3_MSS_AT:2026-01-05T00:00:00+00:00",
            "M1_FVG_CONFIRMED_AT:2026-01-05T00:00:00+00:00",
        ],
        "baseline_portfolio_exposure_bound": True,
        "baseline_active_positions": 0,
        "baseline_shared_factors": [],
        "baseline_same_direction_factors": [],
        "baseline_opposing_direction_factors": [],
        "day_session_journey_bound": True,
        "prior_closed_trades_today": prior_selected,
        "prior_realized_r_today": "0",
        "completed_prior_sessions": [],
        "prior_same_session_selected": prior_selected,
        "session_slots_remaining_before": 3 - prior_selected,
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


def test_collision_atlas_detects_same_timestamp_factor_competition(
    tmp_path: Path,
) -> None:
    binding_root = tmp_path / "binding"
    target_root = tmp_path / "target"
    cross_root = tmp_path / "cross"

    controls = [
        _trade(
            symbol="AUDJPY",
            session="ASIA",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T00:10:00+00:00",
            exit_at="2026-01-05T00:20:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
        _trade(
            symbol="GBPJPY",
            session="ASIA",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T00:10:00+00:00",
            exit_at="2026-01-05T00:20:00+00:00",
            realized_r="1",
            exit_reason="TARGET",
        ),
        _trade(
            symbol="EURUSD",
            session="LONDON",
            side="LONG",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:00:00+00:00",
            exit_at="2026-01-05T07:05:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
        _trade(
            symbol="GBPUSD",
            session="LONDON",
            side="LONG",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:10:00+00:00",
            exit_at="2026-01-05T07:15:00+00:00",
            realized_r="0.2",
            exit_reason="TIME_EXIT",
        ),
        _trade(
            symbol="EURUSD",
            session="LONDON",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:20:00+00:00",
            exit_at="2026-01-05T07:25:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
    ]
    _write_jsonl(
        target_root
        / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        controls,
    )

    bindings = [
        _binding(
            symbol="AUDJPY",
            session="ASIA",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T00:10:00+00:00",
            prior_selected=0,
            entry_mode="OB_FVG_RETEST",
        ),
        _binding(
            symbol="GBPJPY",
            session="ASIA",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T00:10:00+00:00",
            prior_selected=0,
            entry_mode="OB_FVG_RETEST",
        ),
        _binding(
            symbol="EURUSD",
            session="LONDON",
            side="LONG",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:00:00+00:00",
            prior_selected=0,
            entry_mode="FVG_CE_50",
        ),
        _binding(
            symbol="GBPUSD",
            session="LONDON",
            side="LONG",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:10:00+00:00",
            prior_selected=1,
            entry_mode="FVG_CE_50",
        ),
        _binding(
            symbol="EURUSD",
            session="LONDON",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:20:00+00:00",
            prior_selected=2,
            entry_mode="OB_FVG_RETEST",
        ),
    ]
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
        binding_root
        / "capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl",
        bindings,
    )

    _write_json(
        cross_root
        / "capitalizer-cognitive-third-slot-cross-feature-atlas-2y-v1.json",
        {
            "cells": [
                {
                    "journey_feature": "PRIOR_SESSION_REALIZED_SIGN",
                    "journey_value": "NEGATIVE",
                    "preentry_feature": "ENTRY_MODE",
                    "preentry_value": "OB_FVG_RETEST",
                    "third_slot_trades": 1,
                    "full_portfolio_if_abstained_metrics": {"trades": 4},
                }
            ]
        },
    )

    report = collision.build_report(binding_root, target_root, cross_root)

    assert report["control_trades"] == 5
    assert report["third_slot_reference"]["trades"] == 1
    assert report["collision_cluster_count"] == 1
    assert report["collision_candidate_count"] == 2
    assert report["collision_factor_counts"] == {"JPY": 1}
    assert report["policy_count"] == len(collision.POLICIES)
    assert report["all_policies_outcome_blind"] is True
    assert report["collision_policy_selected"] is False
    assert report["combined_rule_selected"] is False
    assert all(
        row["collision_dropped_trades"] == 1
        and row["combined_dropped_trades"] == 2
        and row["combined_metrics"]["trades"] == 3
        for row in report["policies"]
    )
