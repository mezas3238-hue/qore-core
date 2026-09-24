from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_failure_fingerprint_audit_2y_v1 as fp,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_loss_memory_resolution_atlas_2y_v1 as atlas,
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


def _fp_row(
    *,
    entry_at: str,
    exit_at: str,
    realized_r: str,
    structural: str,
    contextual: str,
) -> dict[str, object]:
    return {
        "symbol": "EURUSD",
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "entry_at": entry_at,
        "exit_at": exit_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "structural_fingerprint": structural,
        "contextual_fingerprint": contextual,
        "structural_tokens": ["SYMBOL:EURUSD"],
        "contextual_tokens": ["SYMBOL:EURUSD"],
        "prior_closed_loss_same_structural_all_history": 0,
        "prior_closed_loss_same_structural_same_day": 0,
        "prior_closed_loss_same_structural_same_session_day": 0,
        "prior_closed_loss_same_contextual_all_history": 0,
        "prior_closed_loss_same_contextual_same_day": 0,
        "prior_closed_loss_same_contextual_same_session_day": 0,
        "current_exit_reason": "STOP" if realized_r == "-1" else "TARGET",
        "current_realized_gross_r": realized_r,
        "current_outcome_used_to_build_fingerprint": False,
        "current_outcome_used_to_detect_repeat": False,
    }


def test_resolution_semantics_are_causal_and_distinct(tmp_path: Path) -> None:
    fingerprint_root = tmp_path / "fingerprints"
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
        _control(
            entry_at="2026-01-05T09:30:00+00:00",
            exit_at="2026-01-05T09:35:00+00:00",
            realized_r="1",
            exit_reason="TARGET",
        ),
    ]
    _write_jsonl(
        target_root / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl",
        controls,
    )

    fp_rows = [
        _fp_row(
            entry_at="2026-01-05T09:00:00+00:00",
            exit_at="2026-01-05T09:05:00+00:00",
            realized_r="-1",
            structural="A",
            contextual="A0",
        ),
        _fp_row(
            entry_at="2026-01-05T09:10:00+00:00",
            exit_at="2026-01-05T09:15:00+00:00",
            realized_r="1",
            structural="A",
            contextual="A1",
        ),
        _fp_row(
            entry_at="2026-01-05T09:20:00+00:00",
            exit_at="2026-01-05T09:25:00+00:00",
            realized_r="-1",
            structural="A",
            contextual="A2",
        ),
        _fp_row(
            entry_at="2026-01-05T09:30:00+00:00",
            exit_at="2026-01-05T09:35:00+00:00",
            realized_r="1",
            structural="B",
            contextual="B0",
        ),
    ]
    _write_json(
        fingerprint_root
        / "capitalizer-cognitive-failure-fingerprint-audit-2y-v1.json",
        {
            "identity": fp.IDENTITY,
            "control_trades": 4,
            "current_outcome_used_to_build_fingerprint": False,
        },
    )
    _write_jsonl(
        fingerprint_root
        / "capitalizer-cognitive-failure-fingerprint-audit-2y-v1-rows.jsonl",
        fp_rows,
    )

    report = atlas.build_report(fingerprint_root, target_root)
    structural = {
        row["semantics"]: row
        for row in report["variants"]["STRUCTURAL"]
    }

    assert report["control_trades"] == 4
    assert structural["PERSISTENT_ANY_PRIOR_LOSS"]["blocked_trades"] == 2
    assert structural["LAST_SAME_FINGERPRINT_LOSS"]["blocked_trades"] == 1
    assert structural["LATEST_SAME_SYMBOL_STATE_LOSS"]["blocked_trades"] == 1
    assert structural["SAME_DAY_ANY_PRIOR_LOSS"]["blocked_trades"] == 2
    assert report["current_trade_outcome_visible_to_memory_decision"] is False
    assert report["semantic_variant_selected"] is False
    assert report["runtime_enforcement_allowed"] is False
