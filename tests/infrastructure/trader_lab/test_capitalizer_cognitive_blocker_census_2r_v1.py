from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_blocker_census_2r_v1 as census,
)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_blocker_census_separates_historical_and_live_only_layers(
    tmp_path: Path,
) -> None:
    rebase_root = tmp_path / "rebase"
    perception_root = tmp_path / "perception"
    regime_root = tmp_path / "regime"
    destination_root = tmp_path / "destination"
    fingerprint_root = tmp_path / "fingerprint"
    evidence_root = tmp_path / "evidence"
    collision_root = tmp_path / "collision"

    _write(
        rebase_root / "capitalizer-cognitive-economic-rebase-2r-v1.json",
        {
            "identity": "QORE_CAPITALIZER_COGNITIVE_ECONOMIC_REBASE_2R_V1",
            "control_trades": 948,
            "control_metrics": {
                "trades": 948,
                "profit_factor": "1.466020472120789368123727041",
                "max_drawdown_r": "12.93584837435268644582248142",
                "total_r": "153.9928",
                "stops": 275,
            },
        },
    )
    _write(
        perception_root
        / "capitalizer-cognitive-perception-bars-complete-binding-2r-v2.json",
        {
            "identity": (
                "QORE_CAPITALIZER_COGNITIVE_PERCEPTION_BARS_COMPLETE_BINDING_2R_V2"
            ),
            "control_trades": 948,
            "bars_complete_state_counts": {
                "SUPPORTED_TRUE": 948,
                "SUPPORTED_FALSE": 0,
                "UNBOUND": 0,
            },
            "quote_fresh_evidence_bound": False,
        },
    )
    _write(
        regime_root
        / "capitalizer-cognitive-regime-evidence-binding-audit-2r-v1.json",
        {
            "identity": "QORE_CAPITALIZER_COGNITIVE_REGIME_EVIDENCE_BINDING_AUDIT_2R_V1",
            "control_trades": 948,
            "regime_evidence_bound_trades": 789,
            "regime_intelligence_supported": False,
        },
    )
    _write(
        destination_root
        / "capitalizer-nine-market-destination-untouched-persistence-matrix-2r-v1.json",
        {
            "identity": (
                "QORE_CAPITALIZER_COGNITIVE_DESTINATION_UNTOUCHED_"
                "PERSISTENCE_MATRIX_2R_V1"
            ),
            "departure_bound_trades": 82,
            "at_least_one_candidate_untouched_through_entry_trades": 82,
            "destination_intelligence_supported": False,
        },
    )
    _write(
        fingerprint_root
        / "capitalizer-cognitive-failure-fingerprint-audit-2y-v1.json",
        {
            "identity": "QORE_CAPITALIZER_COGNITIVE_FAILURE_FINGERPRINT_AUDIT_2Y_V1",
            "control_trades": 948,
            "fingerprint_candidate_coverage": 948,
            "runtime_failure_fingerprint_selected": False,
            "loss_memory_resolution_bound": False,
        },
    )
    _write(
        evidence_root
        / "capitalizer-cognitive-evidence-binding-audit-2y-v2.json",
        {
            "identity": "QORE_CAPITALIZER_COGNITIVE_EVIDENCE_BINDING_AUDIT_2Y_V2",
            "control_trades": 948,
            "binding_coverage": {
                "source_microstructure": 948,
                "day_session_journey": 948,
                "baseline_portfolio_exposure": 948,
                "baseline_slot_state": 948,
            },
        },
    )
    _write(
        collision_root
        / "capitalizer-cognitive-simultaneous-factor-collision-atlas-2r-v1.json",
        {
            "identity": (
                "QORE_CAPITALIZER_COGNITIVE_SIMULTANEOUS_FACTOR_"
                "COLLISION_ATLAS_2R_V1"
            ),
            "control_trades": 948,
            "collision_candidate_count": 22,
            "collision_policy_selected": False,
            "combined_rule_selected": False,
        },
    )

    report = census.build_report(
        rebase_root,
        perception_root,
        regime_root,
        destination_root,
        fingerprint_root,
        evidence_root,
        collision_root,
    )
    by_layer = {row["layer"]: row for row in report["layers"]}

    assert report["control_trades"] == 948
    assert report["historical_master_replay_ready"] is False
    assert report["final_cognitive_engine_ready"] is False
    assert report["runtime_engine_called"] is False
    assert report["numeric_confidence_fabricated"] is False
    assert report["missing_evidence_fabricated"] is False

    assert by_layer["SOURCE_MICROSTRUCTURE"]["status"] == "BOUND"
    assert by_layer["SOURCE_MICROSTRUCTURE"]["bound_trades"] == 948
    assert by_layer["PERCEPTION_BARS_COMPLETE"]["status"] == "BOUND"
    assert by_layer["PERCEPTION_BARS_COMPLETE"]["coverage"] == "1"

    assert by_layer["PERCEPTION_QUOTE_FRESH"]["status"] == "LIVE_ONLY"
    assert by_layer["PERCEPTION_QUOTE_FRESH"][
        "blocks_historical_master_replay"
    ] is False
    assert by_layer["PERCEPTION_QUOTE_FRESH"][
        "blocks_final_execution_decision"
    ] is True

    assert by_layer["REGIME_DESCRIPTIVE_EVIDENCE"]["status"] == "PARTIAL"
    assert by_layer["REGIME_DESCRIPTIVE_EVIDENCE"]["bound_trades"] == 789
    assert by_layer["DESTINATION_DEPARTURE_CONTEXT"]["status"] == "PARTIAL"
    assert by_layer["DESTINATION_DEPARTURE_CONTEXT"]["bound_trades"] == 82
    assert by_layer["FAILURE_FINGERPRINT_CANDIDATE"]["status"] == "BOUND"
    assert by_layer["LOSS_MEMORY_RESOLUTION"]["status"] == "RESEARCH_OPEN"
    assert by_layer["SIMULTANEOUS_OPPORTUNITY_COMPETITION"]["status"] == "PARTIAL"
    assert by_layer["SIMULTANEOUS_OPPORTUNITY_COMPETITION"]["bound_trades"] == 22
    assert by_layer["EXECUTION_QUALITY"]["status"] == "LIVE_ONLY"

    assert len(report["bound_layers"]) == 6
    assert len(report["partial_layers"]) == 4
    assert len(report["live_only_layers"]) == 2
    assert "PERCEPTION_QUOTE_FRESH" not in report["historical_research_blockers"]
    assert "EXECUTION_QUALITY" not in report["historical_research_blockers"]
    assert "PERCEPTION_QUOTE_FRESH" in report["final_execution_blockers"]
    assert "EXECUTION_QUALITY" in report["final_execution_blockers"]
