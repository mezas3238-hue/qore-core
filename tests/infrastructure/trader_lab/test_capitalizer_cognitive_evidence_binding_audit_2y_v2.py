from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as v1,
)
from qore.infrastructure.trader_lab.capitalizer_cognitive_evidence_binding_audit_2y_v2 import (
    ARBITRATION,
    PROTECTED,
    REARM,
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
    symbol: str,
    entry_at: str,
    provenance: str,
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
        "realized_gross_r": "-1",
        "exit_reason": "STOP",
        "same_minute_stop_target_ambiguity": False,
        "provenance": provenance,
    }


def _v1_row(
    *,
    symbol: str,
    entry_at: str,
    provenance: str,
    bound: bool,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "h1_open": "2026-01-05T09:00:00+00:00",
        "entry_at": entry_at,
        "provenance": provenance,
        "source_microstructure_match_found": bound,
        "source_microstructure_bound": bound,
        "source_timestamps_causal": bound,
        "evidence_provenance_complete": bound,
        "microstructure_observations": (
            ["LIQUIDITY_SOURCE:PDH"] if bound else []
        ),
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


def _protected(
    *,
    symbol: str,
    entry_at: str,
    protected_at: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "source_first_mss_at": "2026-01-05T09:02:00+00:00",
        "displacement_opened_at": "2026-01-05T09:01:00+00:00",
        "final_fill_at": entry_at,
        "final_entry_mode": "FVG_CE50",
        "ob_fvg_overlap": True,
        "wait5_armed": False,
        "entry_price": "1.2500",
        "broken_swing_price": "1.2495",
        "original_stop_price": "1.2501",
        "original_stop_valid": False,
        "original_stop_intersected_before_fill": False,
        "fill_bar_contains_original_stop": False,
        "fill_bar_entirely_beyond_original_stop": False,
        "protected_at_mss_present": True,
        "protected_at_mss_confirmed_at": protected_at,
        "protected_at_mss_price": "1.2480",
        "protected_at_mss_stop_price": "1.2479",
        "protected_at_mss_stop_valid": True,
        "protected_before_fill_present": True,
        "protected_before_fill_confirmed_at": protected_at,
        "protected_before_fill_price": "1.2480",
        "protected_before_fill_stop_price": "1.2479",
        "protected_before_fill_stop_valid": True,
        "protected_updated_after_mss": False,
        "outcome_used_for_classification": False,
    }


def _rearm(*, symbol: str, entry_at: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "original_terminal_reason": "WAIT_NO_REFILL",
        "side": "LONG",
        "original_mss_at": "2026-01-05T09:00:00+00:00",
        "rearm_eligible_at": "2026-01-05T09:05:00+00:00",
        "h1_deadline": "2026-01-05T10:00:00+00:00",
        "new_raid_at": "2026-01-05T09:10:00+00:00",
        "new_closeback_at": "2026-01-05T09:12:00+00:00",
        "new_mss_at": "2026-01-05T09:15:00+00:00",
        "new_fvg_at": "2026-01-05T09:18:00+00:00",
        "new_fill_at": entry_at,
        "stop_valid": True,
        "terminal_stage": "REARM_EXECUTABLE",
        "outcome_fields_read": False,
    }


def _roots(tmp_path: Path, *, future_protected: bool = False) -> tuple[Path, ...]:
    v1_root = tmp_path / "v1"
    target_root = tmp_path / "target"
    protected_root = tmp_path / "protected"
    rearm_root = tmp_path / "rearm"

    controls = [
        _control(
            symbol="EURUSD",
            entry_at="2026-01-05T09:05:00+00:00",
            provenance=ARBITRATION,
        ),
        _control(
            symbol="GBPUSD",
            entry_at="2026-01-05T09:20:00+00:00",
            provenance=PROTECTED,
        ),
        _control(
            symbol="USDJPY",
            entry_at="2026-01-05T09:30:00+00:00",
            provenance=REARM,
        ),
    ]
    _write_jsonl(
        target_root / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        controls,
    )

    v1_rows = [
        _v1_row(
            symbol="EURUSD",
            entry_at="2026-01-05T09:05:00+00:00",
            provenance=ARBITRATION,
            bound=True,
        ),
        _v1_row(
            symbol="GBPUSD",
            entry_at="2026-01-05T09:20:00+00:00",
            provenance=PROTECTED,
            bound=False,
        ),
        _v1_row(
            symbol="USDJPY",
            entry_at="2026-01-05T09:30:00+00:00",
            provenance=REARM,
            bound=False,
        ),
    ]
    _write_json(
        v1_root / "capitalizer-cognitive-evidence-binding-audit-2y-v1.json",
        {
            "identity": v1.IDENTITY,
            "control_trades": 3,
            "future_evidence_violations": 0,
            "missing_evidence_fabricated": False,
            "binding_coverage": {
                "source_microstructure": 1,
                "evidence_provenance_complete": 1,
            },
        },
    )
    _write_jsonl(
        v1_root / "capitalizer-cognitive-evidence-binding-audit-2y-v1-rows.jsonl",
        v1_rows,
    )

    _write_jsonl(
        protected_root
        / "capitalizer-gbpusd-v3-source-first-wait5-stop-invalid-geometry-atlas-2y-v1-rows.jsonl",
        [
            _protected(
                symbol="GBPUSD",
                entry_at="2026-01-05T09:20:00+00:00",
                protected_at=(
                    "2026-01-05T09:21:00+00:00"
                    if future_protected
                    else "2026-01-05T09:10:00+00:00"
                ),
            )
        ],
    )
    _write_jsonl(
        rearm_root
        / "capitalizer-usdjpy-v3-source-first-wait-rejected-parallel-rearm-atlas-2y-v1-rows.jsonl",
        [
            _rearm(
                symbol="USDJPY",
                entry_at="2026-01-05T09:30:00+00:00",
            )
        ],
    )
    return v1_root, target_root, protected_root, rearm_root


def test_v2_binds_all_three_source_families(tmp_path: Path) -> None:
    roots = _roots(tmp_path)
    report, rows = build_report(*roots)

    assert report["control_trades"] == 3
    assert report["binding_coverage"]["source_microstructure"] == 3
    assert report["binding_coverage"]["evidence_provenance_complete"] == 3
    assert report["delta_vs_v1"]["source_microstructure"] == 2
    assert report["source_microstructure_family_counts"] == {
        ARBITRATION: 1,
        PROTECTED: 1,
        REARM: 1,
    }
    assert report["stop_label_coverage"]["source_microstructure_bound"] == 3
    assert report["future_evidence_violations"] == 0
    assert report["binding_coverage"]["full_master_cognitive_frame_ready"] == 0

    by_symbol = {str(row["symbol"]): row for row in rows}
    assert by_symbol["GBPUSD"]["source_microstructure_family"] == PROTECTED
    assert (
        "RECOVERY_SOURCE:PROTECTED_SWING_GEOMETRY_RESCUE"
        in by_symbol["GBPUSD"]["microstructure_observations"]
    )
    assert by_symbol["USDJPY"]["source_microstructure_family"] == REARM
    assert (
        "RECOVERY_SOURCE:WAIT_REJECTED_PARALLEL_REARM"
        in by_symbol["USDJPY"]["microstructure_observations"]
    )


def test_v2_fail_closes_future_recovery_evidence(tmp_path: Path) -> None:
    roots = _roots(tmp_path, future_protected=True)
    report, rows = build_report(*roots)

    assert report["future_evidence_violations"] == 1
    assert report["binding_coverage"]["source_microstructure"] == 2
    gbp = next(row for row in rows if row["symbol"] == "GBPUSD")
    assert gbp["source_microstructure_match_found"] is True
    assert gbp["source_microstructure_bound"] is False
    assert gbp["source_timestamps_causal"] is False
