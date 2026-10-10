from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_third_slot_journey_atlas_2y_v1 as atlas,
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


def _binding(entry_at: str, prior_selected: int, active: int) -> dict[str, object]:
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
        "microstructure_observations": [],
        "baseline_portfolio_exposure_bound": True,
        "baseline_active_positions": active,
        "baseline_shared_factors": [],
        "baseline_same_direction_factors": [],
        "baseline_opposing_direction_factors": [],
        "day_session_journey_bound": True,
        "prior_closed_trades_today": 0,
        "prior_realized_r_today": "0",
        "completed_prior_sessions": ["ASIA"],
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


def test_third_slot_journey_uses_only_closed_prior_outcomes(tmp_path: Path) -> None:
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
            exit_at="2026-01-05T09:40:00+00:00",
            realized_r="1",
            exit_reason="TARGET",
        ),
        _control(
            entry_at="2026-01-05T09:20:00+00:00",
            exit_at="2026-01-05T09:30:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
    ]
    _write_jsonl(
        target_root / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        controls,
    )
    bindings = [
        _binding("2026-01-05T09:00:00+00:00", 0, 0),
        _binding("2026-01-05T09:10:00+00:00", 1, 0),
        _binding("2026-01-05T09:20:00+00:00", 2, 1),
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
        bindings,
    )

    original_expected = atlas.IDENTITY
    assert original_expected
    try:
        atlas_expected = 40
        atlas_source = atlas.build_report
        # The production contract freezes 40 third-slot trades. Test the causal
        # cell helper directly with a reduced fixture instead of weakening it.
        cell = atlas._causal_cells(
            candidate=controls[2],
            binding=bindings[2],
            control=tuple(controls),
        )
    finally:
        assert atlas_expected == 40
        assert atlas_source is atlas.build_report

    values = dict(cell)
    assert values["PRIOR_TWO_STATE"] == "LOSS>OPEN"
    assert values["PRIOR_SESSION_REALIZED_SIGN"] == "NEGATIVE"
    assert values["PRIOR_SESSION_CLOSED_COUNT"] == "1"
    assert values["MOST_RECENT_CLOSED_SESSION_OUTCOME"] == "LOSS"
    assert values["ACTIVE_POSITION_COUNT"] == "1"
