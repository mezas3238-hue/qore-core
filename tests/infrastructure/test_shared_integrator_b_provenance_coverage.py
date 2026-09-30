from qore.infrastructure.core_stack_v2.shared_integrator_b_provenance_coverage import (
    EXPECTED_B_IDS,
    assess_b_provenance_coverage,
)


def test_combined_scopes_expand_to_individual_workstreams() -> None:
    result = assess_b_provenance_coverage(
        ("B-10/B-11/B-12", "B-16/B-17", "B-18/B-19/B-20")
    )
    assert {"B-10", "B-11", "B-12", "B-16", "B-17", "B-18", "B-19", "B-20"} <= set(
        result.covered_ids
    )


def test_current_shape_keeps_missing_provenance_explicit() -> None:
    scopes = (
        "B-02", "B-03", "B-05", "B-06", "B-09",
        "B-10/B-11/B-12", "B-13", "B-15",
        "B-16/B-17", "B-18/B-19/B-20",
    )
    result = assess_b_provenance_coverage(scopes)
    assert result.covered_ids == (
        "B-02", "B-03", "B-05", "B-06", "B-09", "B-10", "B-11", "B-12",
        "B-13", "B-15", "B-16", "B-17", "B-18", "B-19", "B-20",
    )
    assert result.missing_ids == (
        "B-01", "B-04", "B-07", "B-08", "B-14", "B-21", "B-22", "B-23", "B-24",
    )
    assert {"B-01", "B-23"} <= set(result.missing_terminal_ids)
    assert "B-14" in result.missing_external_blocked_ids
    assert result.coverage_complete is False


def test_full_coverage_is_exactly_b01_through_b24() -> None:
    result = assess_b_provenance_coverage(EXPECTED_B_IDS)
    assert result.coverage_complete is True
    assert result.missing_ids == ()
