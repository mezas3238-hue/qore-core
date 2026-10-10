from qore.infrastructure.trader_lab.capitalizer_session_window_differential_v48 import (
    FINDINGS,
    V48_SESSION_WINDOW_DIFFERENTIAL,
    V48SessionWindowStatus,
)


def test_new_york_current_hard_window_conflicts_with_ttrades_0930_1000_route() -> None:
    finding = next(item for item in FINDINGS if item.session == "NEW_YORK")
    assert finding.status is V48SessionWindowStatus.SOURCE_CONFLICT
    assert "07:00-09:00" in finding.current_qore_behavior
    assert "09:30" in finding.source_evidence
    assert "10:00" in finding.source_evidence


def test_london_killzone_cannot_be_global_cross_author_veto() -> None:
    finding = next(item for item in FINDINGS if item.session == "LONDON")
    assert finding.status is V48SessionWindowStatus.CROSS_SOURCE_OVERCONSTRAINT
    assert finding.route_specific_resolution_required is True


def test_asia_ict_window_remains_unresolved_for_ttrades_routes() -> None:
    finding = next(item for item in FINDINGS if item.session == "ASIA")
    assert finding.status is V48SessionWindowStatus.CROSS_SOURCE_UNRESOLVED


def test_v48_requires_route_specific_session_semantics() -> None:
    state = V48_SESSION_WINDOW_DIFFERENTIAL
    assert state.one_author_window_may_globally_veto_other_author_routes is False
    assert state.route_specific_time_context_required is True
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
