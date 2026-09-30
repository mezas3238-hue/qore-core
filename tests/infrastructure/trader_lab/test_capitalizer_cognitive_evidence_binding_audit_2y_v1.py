from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_cognitive_evidence_binding_audit_2y_v1 import (
    build_report,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _control(
    *,
    symbol: str,
    entry_at: str,
    exit_at: str,
    exit_reason: str,
    realized_r: str,
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
        "exit_at": exit_at,
        "realized_gross_r": realized_r,
        "exit_reason": exit_reason,
        "same_minute_stop_target_ambiguity": False,
        "provenance": provenance,
    }


def _arbitration(
    *,
    symbol: str,
    entry_at: str,
    fvg_confirmed_at: str = "2026-01-05T08:59:00+00:00",
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "h1_open": "2026-01-05T09:00:00+00:00",
        "h1_deadline": "2026-01-05T10:00:00+00:00",
        "liquidity_source": "PDH",
        "liquidity_kind": "LOW",
        "liquidity_price": "1.2400",
        "h1_sweep_at": "2026-01-05T08:40:00+00:00",
        "h1_sweep_extreme": "1.2390",
        "m5_closeback_at": "2026-01-05T08:50:00+00:00",
        "m3_mss_at": "2026-01-05T08:55:00+00:00",
        "m3_broken_swing_price": "1.2450",
        "m3_cisd_boundary": "1.2460",
        "m3_body_ratio": "0.70",
        "m3_atr14": "0.0010",
        "m3_displacement_range": "0.0015",
        "m1_ob_opened_at": "2026-01-05T08:56:00+00:00",
        "m1_ob_low": "1.2480",
        "m1_ob_high": "1.2490",
        "m1_fvg_confirmed_at": fvg_confirmed_at,
        "m1_fvg_low": "1.2490",
        "m1_fvg_high": "1.2500",
        "m1_ob_fvg_overlap": True,
        "entry_mode": "FVG_CE50",
        "entry_at": entry_at,
        "exit_at": "2026-01-05T09:30:00+00:00",
        "entry_price": "1.2500",
        "stop_price": "1.2490",
        "stop_buffer_price": "0.0001",
        "target_price": "1.2520",
        "realized_gross_r": "-1",
        "exit_reason": "STOP",
        "m1_bars_held": 30,
        "same_minute_stop_target_ambiguity": False,
    }


def test_binding_audit_reconstructs_only_causal_context(tmp_path: Path) -> None:
    target_root = tmp_path / "target"
    arbitration_root = tmp_path / "arbitration"

    _write_jsonl(
        target_root / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        [
            _control(
                symbol="EURUSD",
                entry_at="2026-01-05T09:00:00+00:00",
                exit_at="2026-01-05T09:30:00+00:00",
                exit_reason="STOP",
                realized_r="-1",
                provenance="CAUSAL_ARBITRATION_BASE",
            ),
            _control(
                symbol="GBPUSD",
                entry_at="2026-01-05T09:10:00+00:00",
                exit_at="2026-01-05T09:20:00+00:00",
                exit_reason="TARGET",
                realized_r="1",
                provenance="PROTECTED_SWING_GEOMETRY_RESCUE",
            ),
        ],
    )
    _write_jsonl(
        arbitration_root
        / "capitalizer-eurusd-v3-source-first-no-rearm-closeback-arbitration-2y-v1-trades.jsonl",
        [
            _arbitration(
                symbol="EURUSD",
                entry_at="2026-01-05T09:00:00+00:00",
            )
        ],
    )

    report, rows = build_report(target_root, arbitration_root)

    assert report["control_trades"] == 2
    assert report["control_stops"] == 1
    assert report["binding_coverage"]["source_microstructure"] == 1
    assert report["binding_coverage"]["baseline_portfolio_exposure"] == 2
    assert report["binding_coverage"]["day_session_journey"] == 2
    assert report["stop_label_coverage"]["source_microstructure_bound"] == 1
    assert report["future_evidence_violations"] == 0
    assert report["current_trade_outcome_used_for_binding"] is False
    assert report["binding_coverage"]["full_master_cognitive_frame_ready"] == 0

    first, second = rows
    assert first.source_microstructure_match_found is True
    assert first.source_microstructure_bound is True
    assert first.source_timestamps_causal is True
    assert "LIQUIDITY_SOURCE:PDH" in first.microstructure_observations

    assert second.source_microstructure_match_found is False
    assert second.source_microstructure_bound is False
    assert second.baseline_active_positions == 1
    assert second.baseline_shared_factors == ("USD",)
    assert second.baseline_same_direction_factors == ("USD",)
    assert second.prior_closed_trades_today == 0
    assert second.prior_same_session_selected == 1
    assert second.session_slots_remaining_before == 2


def test_binding_audit_rejects_future_microstructure_from_binding(
    tmp_path: Path,
) -> None:
    target_root = tmp_path / "target"
    arbitration_root = tmp_path / "arbitration"

    _write_jsonl(
        target_root / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        [
            _control(
                symbol="EURUSD",
                entry_at="2026-01-05T09:00:00+00:00",
                exit_at="2026-01-05T09:30:00+00:00",
                exit_reason="STOP",
                realized_r="-1",
                provenance="CAUSAL_ARBITRATION_BASE",
            )
        ],
    )
    _write_jsonl(
        arbitration_root
        / "capitalizer-eurusd-v3-source-first-no-rearm-closeback-arbitration-2y-v1-trades.jsonl",
        [
            _arbitration(
                symbol="EURUSD",
                entry_at="2026-01-05T09:00:00+00:00",
                fvg_confirmed_at="2026-01-05T09:01:00+00:00",
            )
        ],
    )

    report, rows = build_report(target_root, arbitration_root)

    assert report["future_evidence_violations"] == 1
    assert report["binding_coverage"]["source_microstructure"] == 0
    assert rows[0].source_microstructure_match_found is True
    assert rows[0].source_microstructure_bound is False
    assert rows[0].source_timestamps_causal is False
    assert rows[0].microstructure_observations == ()
