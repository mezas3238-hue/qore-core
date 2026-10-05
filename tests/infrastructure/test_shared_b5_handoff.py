from __future__ import annotations

from typing import cast

import pytest

from qore.infrastructure.core_stack_v2.shared_b5_handoff import build_b5_handoff


def test_b5_handoff_matches_current_b4_temporal_truth_without_overclaim() -> None:
    receipt = build_b5_handoff(
        b4_comparability_eligible_count=0,
        b4_relational_comparability_authorized=False,
    )
    assert receipt["owned_work_ids"] == ["B-11", "B-12", "B-13", "B-14", "B-15"]
    assert receipt["functional_engine_implemented_count"] == 5
    assert receipt["engineering_open_count"] == 0
    assert receipt["dependency_blocked_count"] == 3
    assert receipt["known_blindspot_count"] == 1
    assert receipt["governed_unknown_count"] == 1
    assert receipt["empirical_relational_population_complete"] is False
    assert receipt["b5_scientific_closure_complete"] is False
    assert receipt["handoff_to_integrator_3_ready"] is True
    assert receipt["fresh_holdout_opened"] is False
    assert receipt["target_or_outcome_read"] is False
    assert receipt["execution_authority"] is False
    assert len(str(receipt["handoff_fingerprint_sha256"])) == 64

    items = {
        item["work_id"]: item
        for item in cast(list[dict[str, object]], receipt["items"])
    }
    for work_id in ("B-11", "B-12", "B-13"):
        assert items[work_id]["disposition"] == "DEPENDENCY_BLOCKED"
        assert items[work_id]["empirical_population_complete"] is False
    assert items["B-14"]["disposition"] == "KNOWN_BLINDSPOT"
    assert items["B-14"]["proxy_used"] is False
    assert items["B-15"]["disposition"] == "GOVERNED_UNKNOWN"
    assert items["B-15"]["inference_used"] is False


def test_b5_handoff_is_deterministic() -> None:
    left = build_b5_handoff(
        b4_comparability_eligible_count=0,
        b4_relational_comparability_authorized=False,
    )
    right = build_b5_handoff(
        b4_comparability_eligible_count=0,
        b4_relational_comparability_authorized=False,
    )
    assert left == right


def test_b08_readiness_opens_empirical_work_but_does_not_prove_it() -> None:
    receipt = build_b5_handoff(
        b4_comparability_eligible_count=27,
        b4_relational_comparability_authorized=True,
    )
    items = {
        item["work_id"]: item
        for item in cast(list[dict[str, object]], receipt["items"])
    }

    assert receipt["complete_and_proven_count"] == 0
    assert receipt["dependency_blocked_count"] == 0
    assert receipt["empirical_relational_population_complete"] is False
    assert receipt["b5_scientific_closure_complete"] is False

    for work_id in ("B-11", "B-12", "B-13"):
        assert (
            items[work_id]["disposition"]
            == "READY_FOR_EMPIRICAL_POPULATION"
        )
        assert items[work_id]["empirical_population_complete"] is False
        assert len(cast(list[str], items[work_id]["blockers"])) == 1


def test_empirical_completion_requires_b08_authority_and_eligible_population() -> None:
    with pytest.raises(
        ValueError,
        match="empirical relational completion requires B4 comparability authority",
    ):
        build_b5_handoff(
            b4_comparability_eligible_count=0,
            b4_relational_comparability_authorized=False,
            b11_empirical_population_complete=True,
        )

    with pytest.raises(
        ValueError,
        match="empirical relational completion requires B4 comparability authority",
    ):
        build_b5_handoff(
            b4_comparability_eligible_count=0,
            b4_relational_comparability_authorized=True,
            b11_empirical_population_complete=True,
        )


def test_relational_items_close_only_after_explicit_empirical_completion() -> None:
    receipt = build_b5_handoff(
        b4_comparability_eligible_count=27,
        b4_relational_comparability_authorized=True,
        b11_empirical_population_complete=True,
        b12_empirical_population_complete=True,
        b13_empirical_population_complete=True,
    )
    items = {
        item["work_id"]: item
        for item in cast(list[dict[str, object]], receipt["items"])
    }

    assert receipt["complete_and_proven_count"] == 3
    assert receipt["dependency_blocked_count"] == 0
    assert receipt["empirical_relational_population_complete"] is True
    assert receipt["b5_scientific_closure_complete"] is False

    for work_id in ("B-11", "B-12", "B-13"):
        assert items[work_id]["disposition"] == "COMPLETE_AND_PROVEN"
        assert items[work_id]["empirical_population_complete"] is True
        assert items[work_id]["blockers"] == []
