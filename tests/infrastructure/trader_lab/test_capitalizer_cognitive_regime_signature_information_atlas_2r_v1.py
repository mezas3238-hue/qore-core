from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_evidence_binding_audit_2r_v1 as binding,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_signature_information_atlas_2r_v1 as atlas,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _rebase_row(
    *,
    symbol: str,
    entry_at: str,
    realized_r: str,
    exit_reason: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "entry_at": entry_at,
        "post_audit_exit_at": "2026-01-05T01:00:00+00:00",
        "post_audit_realized_gross_r": realized_r,
        "post_audit_exit_reason": exit_reason,
    }


def _binding_row(
    *,
    symbol: str,
    entry_at: str,
    bound: bool,
    signature: str | None,
    token: str | None,
    match: bool,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "source_family": "CAUSAL_ARBITRATION_BASE",
        "m5_closeback_at": token,
        "micro_context_match_found": match,
        "micro_context_causal": bound,
        "regime_evidence_bound": bound,
        "microstructure_signature": signature,
        "body_fraction": "0.60" if bound else None,
        "close_location": "0.40" if bound else None,
        "previous_range_ratio": "1.20" if bound else None,
        "regime_family_id": None,
        "regime_intelligence_supported": False,
        "outcome_visible_to_binding": False,
    }


def test_signature_atlas_uses_only_bound_causal_signature_membership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rebase, "EXPECTED_TRADES", 4)
    monkeypatch.setattr(atlas, "MIN_DESCRIPTIVE_SUPPORT", 1)

    rebase_root = tmp_path / "rebase"
    regime_root = tmp_path / "regime"

    rebase_rows = [
        _rebase_row(
            symbol="AUDJPY",
            entry_at="2026-01-05T00:10:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
        _rebase_row(
            symbol="GBPJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            realized_r="2",
            exit_reason="TARGET",
        ),
        _rebase_row(
            symbol="USDJPY",
            entry_at="2026-01-05T00:30:00+00:00",
            realized_r="-1",
            exit_reason="STOP",
        ),
        _rebase_row(
            symbol="AUDUSD",
            entry_at="2026-01-05T00:40:00+00:00",
            realized_r="2",
            exit_reason="TARGET",
        ),
    ]
    _write_json(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1.json",
        {
            "identity": rebase.IDENTITY,
            "target_r": "2.00",
            "control_trades": 4,
        },
    )
    _write_jsonl(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl",
        rebase_rows,
    )

    binding_rows = [
        _binding_row(
            symbol="AUDJPY",
            entry_at="2026-01-05T00:10:00+00:00",
            bound=True,
            signature="LOW_ACCEPTANCE+LOW_BREAK_ATTEMPT",
            token="2026-01-05T00:05:00+00:00",
            match=True,
        ),
        _binding_row(
            symbol="GBPJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            bound=True,
            signature="HIGH_ACCEPTANCE+HIGH_BREAK_ATTEMPT",
            token="2026-01-05T00:15:00+00:00",
            match=True,
        ),
        _binding_row(
            symbol="USDJPY",
            entry_at="2026-01-05T00:30:00+00:00",
            bound=False,
            signature=None,
            token="2026-01-05T00:25:00+00:00",
            match=False,
        ),
        _binding_row(
            symbol="AUDUSD",
            entry_at="2026-01-05T00:40:00+00:00",
            bound=False,
            signature=None,
            token=None,
            match=False,
        ),
    ]
    _write_json(
        regime_root
        / "capitalizer-cognitive-regime-evidence-binding-audit-2r-v1.json",
        {
            "identity": binding.IDENTITY,
            "control_trades": 4,
            "regime_evidence_bound_trades": 2,
            "regime_family_id_selected": False,
            "regime_intelligence_supported": False,
            "future_evidence_violations": 0,
        },
    )
    _write_jsonl(
        regime_root
        / "capitalizer-cognitive-regime-evidence-binding-audit-2r-v1-rows.jsonl",
        binding_rows,
    )

    report = atlas.build_report(rebase_root, regime_root)

    assert report["control_trades"] == 4
    assert report["regime_evidence_bound_trades"] == 2
    assert report["regime_evidence_unbound_trades"] == 2
    assert report["signature_cell_count"] == 2
    assert report["supported_signature_cell_count"] == 2
    assert report["unbound_reason_counts"] == {
        "NO_M5_CLOSEBACK_TOKEN": 1,
        "TOKEN_WITHOUT_EXACT_CONTEXT_MATCH": 1,
    }
    assert report["signature_membership_known_by_entry"] is True
    assert report["numeric_microstructure_thresholds_added"] is False
    assert report["regime_family_id_selected"] is False
    assert report["automatic_signature_selection"] is False
    assert report["runtime_rule_selected"] is False
    assert all(row["trades"] == 1 for row in report["cells"])
