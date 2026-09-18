from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r11_positive_validity_candidate_contract import (
    IDENTITY,
    STATUS,
    candidate_manifest,
)


def test_candidate_is_frozen_and_evidence_bound() -> None:
    payload = candidate_manifest()
    assert payload["identity"] == IDENTITY
    assert payload["status"] == STATUS
    assert payload["hypothesis"]["scope"] == "EXACT_BREAK_A_ONLY"
    assert payload["consumed_evidence"]["source_run_id"] == 35282212625
    assert payload["consumed_evidence"]["source_artifact_id"] == 10522679602
    assert payload["consumed_evidence"]["pre_entry_recognized"] == 31
    assert payload["consumed_evidence"]["binary_auditable"] == 30
    assert payload["consumed_evidence"]["dol_capable"] == 21
    assert payload["consumed_evidence"]["binary_dol_capable_rate"] == "0.7"


def test_candidate_predicts_capacity_not_profit() -> None:
    hypothesis = candidate_manifest()["hypothesis"]
    assert (
        hypothesis["predicted_structural_property"]
        == "ELEVATED_PLAUSIBILITY_OF_TOUCHING_AT_LEAST_ONE_ACTIVE_DOL"
    )
    assert hypothesis["predicts_profit"] is False
    assert hypothesis["predicts_selected_target_hit"] is False
    assert hypothesis["guarantees_direction"] is False


def test_exact_break_a_and_two_channels_are_frozen() -> None:
    hypothesis = candidate_manifest()["hypothesis"]
    assert hypothesis["family_signature"] == {
        "raid_depth_range_bucket": "q4:<=0.50",
        "cisd_progress_bucket": "q3:<=0.75",
        "reclaim_latency_bucket": "<=5m",
        "protected_risk_range_bucket": "q3:<=1.0",
    }
    conditions = hypothesis["required_multichannel_conditions"]
    assert conditions["c1_directional_wick_fraction"]["operator"] == ">="
    assert (
        conditions["c1_directional_wick_fraction"]["threshold"]
        == "0.2041168495008011832860840626"
    )
    assert (
        conditions["post_reclaim_max_reviolation_source_fraction"]["operator"]
        == "<="
    )
    assert (
        conditions["post_reclaim_max_reviolation_source_fraction"]["threshold"]
        == "0.3897675775115538206129133576"
    )


def test_temporal_transfer_matches_exact_r11_audit() -> None:
    periods = candidate_manifest()["consumed_evidence"]["temporal_transfer"]
    assert periods["early_2016_2020"] == {
        "pre_entry_candidates": 16,
        "binary_auditable": 16,
        "dol_capable": 10,
        "rate": "0.625",
    }
    assert periods["transition_2021_2023"] == {
        "pre_entry_candidates": 9,
        "binary_auditable": 8,
        "dol_capable": 6,
        "rate": "0.75",
    }
    assert periods["recent_2024_2026"] == {
        "pre_entry_candidates": 6,
        "binary_auditable": 6,
        "dol_capable": 5,
        "rate": "0.8333333333333333333333333333",
    }


def test_contract_is_fail_closed_and_does_not_open_holdout() -> None:
    payload = candidate_manifest()
    validation = payload["validation_contract"]
    governance = payload["governance"]

    assert validation["family_signature_mutable_after_freeze"] is False
    assert validation["anchor_thresholds_mutable_after_freeze"] is False
    assert validation["calendar_year_allowed_as_rule"] is False
    assert validation["post_entry_information_allowed_as_recognition_input"] is False
    assert validation["pnl_allowed_as_recognition_input"] is False
    assert validation["automatic_threshold_search"] is False
    assert validation["automatic_candidate_expansion"] is False
    assert validation["independent_validation_required_before_positive_operating_contract"] is True
    assert validation["fresh_holdout_opened_by_this_contract"] is False

    assert governance["candidate_promoted_to_operating_rule"] is False
    assert governance["fresh_holdout_consumed"] is False
    assert governance["demo_eligible"] is False
    assert governance["live_authorized"] is False
    assert governance["real_capital_authorized"] is False
    assert governance["production_authorized"] is False
