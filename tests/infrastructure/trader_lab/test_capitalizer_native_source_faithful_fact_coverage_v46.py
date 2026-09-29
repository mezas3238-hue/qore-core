from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_native_source_faithful_fact_coverage_v46 as v46,
)


def test_v46_inventory_is_exactly_frozen_26_facts() -> None:
    report = v46.build_report()
    assert report["mandatory_fact_count"] == 26
    assert len(report["facts"]) == 26
    assert [row["fact_index"] for row in report["facts"]] == list(range(1, 27))


def test_v46_phase_b_fails_closed_when_operationalization_is_incomplete() -> None:
    report = v46.build_report()
    assert report["phase_a_ready"] is False
    assert report["phase_b_authorized"] is False
    assert report["phase_b_executed"] is False
    assert report["next_phase"] == (
        "CANONICAL_FACT_OPERATIONALIZATION_GAPS_REQUIRE_IMPLEMENTATION"
    )


def test_v46_r1_closes_internal_fact_blockers_only() -> None:
    report = v46.build_report()
    assert report["r1_predeclaration_comment_id"] == 5883167207
    assert report["blocking_fact_count"] == 1
    assert report["blocking_facts"] == ["HISTORICAL_ASIAN_OPEN_REFERENCE"]


def test_v46_preserves_ready_source_primitives() -> None:
    report = v46.build_report()
    status = {row["fact"]: row["status"] for row in report["facts"]}
    assert status["SOURCE_SESSION_CONTEXT"] == "DETECTOR_READY"
    assert status["HTF_CANDLE2_CANDLE3_CLOSURE_AT_POI"] == "DETECTOR_READY"
    assert status["ICT_LIQUIDITY_REFERENCE"] == "DETECTOR_READY"
    assert status["ICT_LIQUIDITY_RAID"] == "DETECTOR_READY"
    assert status["ICT_MSS"] == "DETECTOR_READY"
    assert status["ICT_DISPLACEMENT_FVG"] == "DETECTOR_READY"
    assert status["ICT_VALID_PD_ARRAY_RETRACE"] == "DETECTOR_READY"
    assert status["TTRADES_LTF_CISD"] == "DETECTOR_READY"
    assert status["TTRADES_PROTECTED_SWING"] == "DETECTOR_READY"
    assert status["M1_FVG"] == "DETECTOR_READY"
    assert status["HTF_SOURCE_POI"] == "DETECTOR_READY"
    assert status["STRUCTURAL_HTF_TARGET_SELECTION"] == "DETECTOR_READY"
    assert status["ICT_EXPLICIT_NO_CHASE"] == "DETECTOR_READY"
    assert status["TTRADES_WICK_BEFORE_EXPANSION_BODY"] == (
        "COMPOSER_READY_REQUIRES_BOUND_INPUT"
    )
    assert status["M1_MSS"] == "DETECTOR_READY"
    assert status["M1_ORDER_BLOCK"] == "COMPOSER_READY_REQUIRES_BOUND_INPUT"
    assert status["DETERMINISTIC_SOURCE_ROUTE_RESOLUTION"] == "DETECTOR_READY"


def test_v46_never_opens_economics_or_fresh_holdout() -> None:
    report = v46.build_report()
    assert report["provider_native_m1_economics_opened"] is False
    assert report["strategy_economics_calculated"] is False
    assert report["fixed_2r_used_as_canonical_target"] is False
    assert report["synthetic_asian_open_used"] is False
    assert report["synthetic_structural_target_used"] is False
    assert report["outcomes_used"] is False
    assert report["admission_changed"] is False
    assert report["sizing_changed"] is False
    assert report["protection_changed"] is False
    assert report["fresh_holdout_opened"] is False
    assert report["candidate_count"] == 0
    assert report["trader_certified"] is False


def test_v46_historical_adapter_is_explicitly_missing() -> None:
    report = v46.build_report()
    assert report["canonical_historical_replay_adapter_status"] == (
        "REPLAY_ADAPTER_MISSING"
    )
