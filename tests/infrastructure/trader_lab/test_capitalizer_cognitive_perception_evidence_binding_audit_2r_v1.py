from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_perception_evidence_binding_audit_2r_v1 as perception,
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
    entry_at: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": session,
        "operating_date": "2026-01-05",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "source_timestamps_causal": True,
        "evidence_provenance_complete": True,
        "source_microstructure_bound": True,
    }


def test_perception_binding_preserves_unknown_instead_of_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rebase, "EXPECTED_TRADES", 2)
    root = tmp_path / "rebase"

    _write_json(
        root / "capitalizer-cognitive-economic-rebase-2r-v1.json",
        {
            "identity": rebase.IDENTITY,
            "target_r": "2.00",
            "control_trades": 2,
        },
    )
    _write_jsonl(
        root / "capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl",
        [
            _row(
                symbol="AUDJPY",
                session="ASIA",
                entry_at="2026-01-05T02:00:00+00:00",
            ),
            _row(
                symbol="NAS100",
                session="NEW_YORK",
                entry_at="2026-01-05T08:00:00+00:00",
            ),
        ],
    )

    report, rows = perception.build_report(root)

    assert report["control_trades"] == 2
    assert report["fact_state_counts"]["quote_fresh"] == {
        "SUPPORTED_TRUE": 0,
        "SUPPORTED_FALSE": 0,
        "UNBOUND": 2,
    }
    assert report["fact_state_counts"]["bars_complete"] == {
        "SUPPORTED_TRUE": 0,
        "SUPPORTED_FALSE": 0,
        "UNBOUND": 2,
    }
    assert report["fact_state_counts"]["session_clock_valid"] == {
        "SUPPORTED_TRUE": 1,
        "SUPPORTED_FALSE": 1,
        "UNBOUND": 0,
    }
    assert report["known_hard_integrity_failure_trades"] == 1
    assert report["known_causal_integrity_true_trades"] == 1
    assert report["runtime_perception_assessor_called"] is False
    assert report["full_perception_status_supported_trades"] == 0
    assert report["unknown_evidence_coerced_to_false"] is False
    assert report["current_trade_outcome_visible_to_binding"] is False
    assert report["missing_evidence_fabricated"] is False

    first, second = rows
    assert first.session_clock_valid is perception.PerceptionEvidenceState.SUPPORTED_TRUE
    assert first.known_hard_integrity_failure is False
    assert second.session_clock_valid is perception.PerceptionEvidenceState.SUPPORTED_FALSE
    assert second.known_hard_integrity_failure is True
