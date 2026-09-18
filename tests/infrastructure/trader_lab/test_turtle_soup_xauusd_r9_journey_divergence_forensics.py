from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_journey_divergence_forensics as r9j


def test_stage_selected_dol_reached_has_priority() -> None:
    assert r9j._journey_stage(True, [1, 2, 3], "TARGET") == "SELECTED_DOL_REACHED"


def test_stage_stop_before_any_dol() -> None:
    assert r9j._journey_stage(False, [], "STOP") == "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"
    assert r9j._journey_stage(False, [], "STOP_FIRST") == "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"


def test_stage_nearer_dol_then_stop() -> None:
    assert r9j._journey_stage(False, [1, 2], "STOP") == "NEARER_DOL_REACHED_THEN_INVALIDATED"


def test_stage_lifecycle_without_selected_target() -> None:
    assert r9j._journey_stage(False, [1], "TIME_24H") == "NEARER_DOL_REACHED_WITHOUT_SELECTED_DOL"
    assert r9j._journey_stage(False, [], "TIME_24H") == "NO_ACTIVE_DOL_REACHED_BEFORE_LIFECYCLE_EXIT"


def test_governance_constants_are_diagnostic_only() -> None:
    assert "POST_ENTRY" in r9j.EVIDENCE_STATUS
    assert r9j.STOP_REASONS == frozenset({"STOP", "STOP_FIRST", "GAP_STOP"})
