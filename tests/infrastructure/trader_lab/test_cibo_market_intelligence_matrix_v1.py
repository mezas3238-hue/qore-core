from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import cibo_market_intelligence_matrix_v1 as matrix


def test_symbol_contract_and_asset_classes() -> None:
    assert len(matrix.SYMBOLS) == 12
    assert matrix._asset_class("EURUSD") == "forex"
    assert matrix._asset_class("NAS100") == "index"
    assert matrix._asset_class("XAUUSD") == "metal"
    assert matrix.EVIDENCE_TIER == "E1_ASSOCIATION_ONLY"


def test_scalar_helpers() -> None:
    assert matrix._rate([]) is None
    assert matrix._rate([True, False, True]) == 2 / 3
    assert matrix._slug("ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY") == "active_swing_3_directional_boundary"


def test_target_summary_is_causal_and_not_complete_dol(tmp_path: Path) -> None:
    manifest = {
        "identity": matrix.TARGET_IDENTITY,
        "symbol": "XAUUSD",
        "resolved_departures": 2,
    }
    (tmp_path / "target-destination-v2-manifest.json").write_text(json.dumps(manifest))
    ledger = [
        {
            "candidate_type": "SOURCE_OPPOSITE_BOUNDARY",
            "candidate_distance_ticks": "10",
            "touch_within_24h": True,
            "time_to_touch_minutes": 20,
        },
        {
            "candidate_type": "SOURCE_OPPOSITE_BOUNDARY",
            "candidate_distance_ticks": "30",
            "touch_within_24h": False,
            "time_to_touch_minutes": None,
        },
    ]
    with (tmp_path / "TARGET_DESTINATION_LEDGER_V2.jsonl").open("w") as handle:
        for row in ledger:
            handle.write(json.dumps(row) + "\n")
    episodes = [
        {"active_candidate_count": 2, "first_touch_candidate_ids": ["a"]},
        {"active_candidate_count": 4, "first_touch_candidate_ids": []},
    ]
    with (tmp_path / "TARGET_DESTINATION_EPISODE_V2.jsonl").open("w") as handle:
        for row in episodes:
            handle.write(json.dumps(row) + "\n")

    result = matrix._target_summary(tmp_path, "XAUUSD")
    family = result["candidate_family"]["SOURCE_OPPOSITE_BOUNDARY"]
    assert family["touch_rate_24h"] == 0.5
    assert family["median_distance_ticks"] == "20"
    assert family["median_time_to_touch_minutes"] == 20.0
    assert result["episodes_with_any_supported_target_touch_24h_rate"] == 0.5
    assert result["complete_all_dol_claim"] is False
