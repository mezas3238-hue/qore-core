"""Semantic, counterfactual source-CognitiveDecision review; NOT a PnL score."""
from __future__ import annotations

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import Side
from scripts.vt31_method_cog_scenario_court_20261014 import (
    _fixture,
    _record_proposal,
    scenario_dossier,
)


def test_exact_qualitative_actions_without_any_quantitative_trader_metrics():
    result = scenario_dossier()
    assert [c["case"] for c in result["cases"]] == [
        "LONG_RAID_MSS_DOL", "SHORT_MIRROR_DST", "NO_SWEEP_WAIT",
        "TWO_SIDES_SAME_M1_UNKNOWN", "WEAK_OR_UNCONFIRMED_MSS_WAIT",
        "INCOMPLETE_9AM_WAIT", "FUTURE_M1_REJECT",
        "WRONG_PROFILE_LONDON_REJECT", "STALE_RETURN_WAIT", "WRONG_DOL_DTO",
    ]
    assert [c["actual_action"] for c in result["cases"]] == [
        "LONG", "SHORT", "WAIT", "WAIT", "WAIT",
        "WAIT", "REJECT", "REJECT", "WAIT", "REJECT",
    ]
    for row in result["cases"]:
        assert row["case_procedurally_consistent"] is True
        assert row["decision_time_not_in_future"] is True
        assert row["execution_authorized"] is False
        assert row["author_source_fidelity_certified"] is False
        assert row["cognitive_autonomy_of_frozen_g3_verified"] is False
        assert row["human_independent_review_completed"] is False
    assert result["original_g3_cog_directly_examined"] is False
    assert result["methodology_author_certified"] is False
    assert result["cognitive_method_certified"] is False
    assert result["human_cog_ops_signatures"] is False
    assert result["certification_decision"].startswith("PENDING_")
    assert result["trader_lab_economic_gate_decision"] == "OUT_OF_SCOPE"
    assert result["financial_results"] is None
    assert result["fresh_oos_consumed"] is False
    assert result["orders_or_sizing"] == 0
    assert result["live_authorized"] is False


def test_oracle_is_not_permitted_to_change_actual_decision_to_pass():
    nine, ten = _fixture(month=7, side=Side.LONG)
    with pytest.raises(ValueError, match="COGNITIVE_SCENARIO_DISAGREEMENT"):
        _record_proposal(
            "FALSE_LABELLED_EXPECTATION", nine=nine, ten=ten[:3],
            expected_action="SHORT",
            expected_state="CONTEXT_ATTESTED_NOT_CERTIFIED",
        )


def test_correct_abstention_is_evidence_of_cognitive_judgment_not_failure():
    cases = scenario_dossier()["cases"]
    for name in (
        "NO_SWEEP_WAIT", "TWO_SIDES_SAME_M1_UNKNOWN",
        "WEAK_OR_UNCONFIRMED_MSS_WAIT",
        "INCOMPLETE_9AM_WAIT", "STALE_RETURN_WAIT",
    ):
        case = next(c for c in cases if c["case"] == name)
        assert case["actual_action"] == "WAIT"
        assert case["opposite_h1_dol"] is None
        assert case["case_procedurally_consistent"] is True


def test_incorrect_dol_cannot_receive_source_confirmation():
    item = scenario_dossier()["cases"][-1]
    assert item["case"] == "WRONG_DOL_DTO"
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in item["reason_codes"]
    assert item["actual_action"] == "REJECT"
    assert item["source"] == "SYNTHETIC_MUTATED_DTO_UNTRUSTED"


def test_dst_source_cases_are_distinct_ny_utc_observations():
    items = scenario_dossier()["cases"]
    summer = items[0]
    winter = items[1]
    assert summer["visible_as_of_ny"].endswith("-04:00")
    assert winter["visible_as_of_ny"].endswith("-05:00")
    assert summer["opposite_h1_dol"] == "110"
    assert winter["opposite_h1_dol"] == "90"
