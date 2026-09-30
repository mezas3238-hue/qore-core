from qore.infrastructure.trader_lab.capitalizer_poi_target_differential_v48 import (
    FINDINGS,
    V48_POI_TARGET_DIFFERENTIAL,
    V48POITargetFinding,
    V48POITargetStatus,
)


def _finding(finding_id: str) -> V48POITargetFinding:
    return next(item for item in FINDINGS if item.finding_id == finding_id)


def test_v2_poi_inventory_misses_newer_cisd_fallback_semantics() -> None:
    finding = _finding("POI_CISD_FALLBACK_MISSING_FROM_V2")
    assert finding.status is V48POITargetStatus.SOURCE_GAP


def test_exactly_one_target_rule_is_qore_overconstraint() -> None:
    finding = _finding("TARGET_EXACTLY_ONE_PRICE_AND_KIND_REQUIRED")
    assert finding.status is V48POITargetStatus.QORE_OVERCONSTRAINT
    assert finding.consumed_run_id == 36615057309
    affected_count = finding.affected_count
    denominator = finding.denominator
    assert affected_count == 465
    assert denominator == 487
    assert affected_count / denominator > 0.95


def test_event_specific_recovery_is_diagnostic_not_new_policy() -> None:
    finding = _finding("EVENT_SPECIFIC_BOUNDARY_RECOVERED_POPULATION")
    assert finding.status is V48POITargetStatus.REQUIRES_ROUTE_POLICY
    assert finding.affected_count == 368
    assert finding.denominator == 487


def test_v48_does_not_invent_target_selector_during_differential_audit() -> None:
    state = V48_POI_TARGET_DIFFERENTIAL
    assert state.new_target_selector_chosen is False
    assert state.nearest_target_assumed is False
    assert state.rr_target_assumed is False
    assert state.outcome_ranked_target_allowed is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
