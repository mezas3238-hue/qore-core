from __future__ import annotations

from qore.infrastructure.traders.vt08_b01_source_contract_r3_9 import (
    Authority,
    RULES,
    SOURCE_ENTRY_ANCHORS_NY,
    source_contract_fingerprint,
    source_contract_payload,
)


def _rules() -> dict[str, object]:
    return {item.rule_id: item for item in RULES}


def test_source_entry_anchors_are_exactly_01_05_09_and_exclude_13() -> None:
    assert SOURCE_ENTRY_ANCHORS_NY == (1, 5, 9)
    assert 13 not in SOURCE_ENTRY_ANCHORS_NY
    rules = _rules()
    anchors = rules["forex-entry-anchors"]
    assert anchors.authority is Authority.SOURCE_EXPLICIT
    assert anchors.source_behavior == "01/05/09 America/New_York"


def test_r38_behavior_is_aligned_without_silent_economic_mutation() -> None:
    payload = source_contract_payload()
    alignment = payload["r38_alignment"]
    assert isinstance(alignment, dict)
    assert alignment["aligned"] is True
    assert alignment["errors"] == []
    assert alignment["economic_behavior_changed_by_contract_freeze"] is False


def test_unresolved_rules_remain_containments_not_source_authority() -> None:
    rules = _rules()
    assert rules["source-day"].authority is Authority.FUNDAMENTALLY_UNRESOLVED
    assert rules["source-day"].qore_behavior == "17NY-to-17NY-research-containment"
    assert rules["stop-offset"].authority is Authority.FUNDAMENTALLY_UNRESOLVED
    assert rules["h4-filled-lifecycle"].authority is Authority.FUNDAMENTALLY_UNRESOLVED
    assert rules["order-type"].authority is Authority.FUNDAMENTALLY_UNRESOLVED
    assert rules["protected-swing-selection"].authority is Authority.FUNDAMENTALLY_UNRESOLVED
    assert rules["reentry-cardinality"].authority is Authority.FUNDAMENTALLY_UNRESOLVED


def test_target_family_does_not_invent_a_structural_liquidity_selector() -> None:
    target = _rules()["target-family"]
    assert target.authority is Authority.CONTEXT_DEPENDENT_SOURCE_FAMILY
    assert target.qore_behavior == "fixed-2r-research-replay-containment"
    assert "No deterministic next-liquidity selector" in target.note


def test_cisd_and_protected_swing_core_remain_source_bound() -> None:
    rules = _rules()
    assert rules["cisd-level"].authority is Authority.SOURCE_EXPLICIT
    assert rules["cisd-confirmation"].authority is Authority.SOURCE_EXPLICIT
    assert rules["cisd-series-minimum"].authority is Authority.SOURCE_SUPPORTED_FORMALIZATION
    assert rules["protected-swing"].authority is Authority.SOURCE_EXPLICIT
    assert rules["structural-stop"].authority is Authority.SOURCE_EXPLICIT


def test_c3_is_source_authorized_but_not_silently_added_to_r38_subset() -> None:
    c3 = _rules()["c3-path"]
    assert c3.authority is Authority.SOURCE_EXPLICIT
    assert c3.qore_behavior == "outside-current-r3.8-narrow-c2-subset"


def test_reconstruction_grid_is_not_exposed_as_entry_authority() -> None:
    grid = _rules()["h4-reconstruction-grid"]
    assert grid.authority is Authority.QORE_OPERATIONAL_CONTAINMENT
    assert "13" in grid.qore_behavior
    anchors = _rules()["forex-entry-anchors"]
    assert "13" not in anchors.source_behavior


def test_consumed_baseline_cannot_be_reused_as_independent_validation() -> None:
    payload = source_contract_payload()
    governance = payload["fresh_holdout_governance"]
    assert isinstance(governance, dict)
    assert governance["required"] is True
    assert governance["consumed_baseline_run_id"] == 34693803930
    assert governance["forbidden_reuse"] == "run-34693803930"
    assert governance["must_not_treat_overlapping_reacquisition_as_independent"] is True
    assert governance["independent_validation_authorized"] is False
    assert governance["status"] == "UNSEEN_INTERVAL_NOT_YET_RESERVED"


def test_contract_grants_no_execution_authority() -> None:
    payload = source_contract_payload()
    authority = payload["execution_authority"]
    assert isinstance(authority, dict)
    assert authority == {
        "research_only": True,
        "demo_eligible": False,
        "live": False,
        "real_capital": False,
    }


def test_source_contract_fingerprint_is_stable() -> None:
    assert source_contract_fingerprint() == source_contract_fingerprint()
    assert len(source_contract_fingerprint()) == 64
