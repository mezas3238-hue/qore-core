from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_simultaneous_factor_collision_atlas_2r_v1 as collision,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _row(
    *,
    symbol: str,
    session: str,
    side: str,
    operating_date: str,
    entry_at: str,
    exit_at: str,
    realized_r: str,
    exit_reason: str,
    prior_selected: int,
    entry_mode: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": session,
        "operating_date": operating_date,
        "side": side,
        "h1_open": entry_at,
        "h1_deadline": exit_at,
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "target_r": "2.00",
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
        "current_outcome_visible_to_cognitive_state": False,
        "current_outcome_attached_for_post_audit": True,
        "post_audit_exit_at": exit_at,
        "post_audit_realized_gross_r": realized_r,
        "post_audit_exit_reason": exit_reason,
        "post_audit_same_minute_stop_target_ambiguity": False,
    }


def test_true_2r_collision_atlas_is_outcome_blind(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(rebase, "EXPECTED_TRADES", 5)
    rebase_root = tmp_path / "rebase"
    cross_root = tmp_path / "cross"

    rows = [
        _row(
            symbol="AUDJPY",
            session="ASIA",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T00:10:00+00:00",
            exit_at="2026-01-05T00:20:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
            prior_selected=0,
            entry_mode="OB_FVG_RETEST",
        ),
        _row(
            symbol="GBPJPY",
            session="ASIA",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T00:10:00+00:00",
            exit_at="2026-01-05T00:20:00+00:00",
            realized_r="2",
            exit_reason="TARGET",
            prior_selected=0,
            entry_mode="OB_FVG_RETEST",
        ),
        _row(
            symbol="EURUSD",
            session="LONDON",
            side="LONG",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:00:00+00:00",
            exit_at="2026-01-05T07:05:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
            prior_selected=0,
            entry_mode="FVG_CE_50",
        ),
        _row(
            symbol="GBPUSD",
            session="LONDON",
            side="LONG",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:10:00+00:00",
            exit_at="2026-01-05T07:15:00+00:00",
            realized_r="0.2",
            exit_reason="TIME_EXIT",
            prior_selected=1,
            entry_mode="FVG_CE_50",
        ),
        _row(
            symbol="EURUSD",
            session="LONDON",
            side="SHORT",
            operating_date="2026-01-05",
            entry_at="2026-01-05T07:20:00+00:00",
            exit_at="2026-01-05T07:25:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
            prior_selected=2,
            entry_mode="OB_FVG_RETEST",
        ),
    ]

    _write_json(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1.json",
        {
            "identity": rebase.IDENTITY,
            "target_r": "2.00",
            "control_trades": 5,
        },
    )
    _write_jsonl(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl",
        rows,
    )
    _write_json(
        cross_root
        / "capitalizer-cognitive-third-slot-cross-feature-atlas-2r-v1.json",
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

    report = collision.build_report(rebase_root, cross_root)

    assert report["control_trades"] == 5
    assert report["third_slot_reference"]["trades"] == 1
    assert report["collision_cluster_count"] == 1
    assert report["collision_candidate_count"] == 2
    assert report["collision_factor_counts"] == {"JPY": 1}
    assert report["policy_count"] == 6
    assert report["all_policies_outcome_blind"] is True
    assert report["collision_policy_selected"] is False
    assert report["combined_rule_selected"] is False
    assert all(
        item["collision_dropped_trades"] == 1
        and item["combined_dropped_trades"] == 2
        and item["combined_metrics"]["trades"] == 3
        for item in report["policies"]
    )
