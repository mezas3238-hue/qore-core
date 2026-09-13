from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_index_r1_validation_rejection import (
    FORENSICS_SCHEMA,
    R1_SCHEMA,
    Vt08IndexR1ValidationRejectionError,
    build_rejection,
)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _inputs(tmp_path: Path) -> tuple[Path, Path]:
    economics: dict[str, object] = {
        "sample_size": 152,
        "winning_trades": 54,
        "losing_trades": 97,
        "flat_trades": 1,
        "total_r": "2.5547",
        "mean_r": "0.01681",
        "profit_factor": "1.0290",
        "max_drawdown_r": "14.8284",
        "max_losing_streak": 12,
    }
    r1 = tmp_path / "r1.json"
    forensics = tmp_path / "forensics.json"
    _write(
        r1,
        {
            "schema": R1_SCHEMA,
            "methodology_fingerprint": "a" * 64,
            "aggregate_equal_risk_trade_economics": economics,
        },
    )
    _write(
        forensics,
        {
            "schema": FORENSICS_SCHEMA,
            "methodology_fingerprint": "a" * 64,
            "aggregate": economics,
            "diagnostic": {"evidence_supports_robust_positive_edge": False},
            "governance": {"methodology_changed_after_result": False},
        },
    )
    return r1, forensics


def test_builds_fail_closed_rejection(tmp_path: Path) -> None:
    r1, forensics = _inputs(tmp_path)
    report = build_rejection(r1_path=r1, forensics_path=forensics)
    assert report["decision"] == "R1_REJECTED_FOR_PROMOTION"
    assert report["not_run_after_early_rejection"]
    assert report["governance"] == {
        "retrospective_subset_selection": False,
        "market_selection_from_outcomes": False,
        "anchor_selection_from_outcomes": False,
        "side_selection_from_outcomes": False,
        "cibo_selection_from_consumed_outcomes": False,
        "fresh_holdout_preserved_unopened": True,
        "demo_eligible": False,
        "live_authorized": False,
        "production_authorized": False,
    }


def test_rejects_methodology_drift(tmp_path: Path) -> None:
    r1, forensics = _inputs(tmp_path)
    payload = json.loads(forensics.read_text(encoding="utf-8"))
    payload["methodology_fingerprint"] = "b" * 64
    _write(forensics, payload)
    with pytest.raises(Vt08IndexR1ValidationRejectionError, match="identity drifted"):
        build_rejection(r1_path=r1, forensics_path=forensics)
