from datetime import UTC, datetime

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
    BURNED_USD60_HOLDOUT_2017H1_V1,
    CURRENT_FRESH_USD60_HOLDOUT_CANDIDATE,
    NEXT_PREREGISTERED_USD60_HOLDOUT,
    PREREGISTERED_USD60_HOLDOUT,
    CiboHoldoutCandidate,
    CiboHoldoutCandidateStatus,
    candidate_is_burn_clean_for_all_lineages,
    candidate_overlaps_confirmed_burn,
)


def test_legacy_v1_is_explicitly_burned_and_not_rehabilitated() -> None:
    candidate = BURNED_USD60_HOLDOUT_2017H1_V1

    assert PREREGISTERED_USD60_HOLDOUT is candidate
    assert candidate.start_at == datetime(2017, 1, 1, tzinfo=UTC)
    assert candidate.end_exclusive_at == datetime(2017, 7, 1, tzinfo=UTC)
    assert candidate.status is CiboHoldoutCandidateStatus.BURNED
    assert candidate.outcome_data_inspected_at_selection is False
    assert candidate.source_validation_complete is True
    assert candidate_is_burn_clean_for_all_lineages(candidate) is False


def test_v2_legacy_alias_is_source_frozen_but_scientifically_consumed() -> None:
    candidate = NEXT_PREREGISTERED_USD60_HOLDOUT

    assert ACTIVE_USD60_HOLDOUT_CANDIDATE is candidate
    assert candidate.start_at == datetime(2015, 10, 19, tzinfo=UTC)
    assert candidate.end_exclusive_at == datetime(2016, 4, 19, tzinfo=UTC)
    assert candidate.status is CiboHoldoutCandidateStatus.ELIGIBLE_FROZEN
    assert candidate.outcome_data_inspected_at_selection is False
    assert candidate.source_validation_complete is True
    assert candidate_is_burn_clean_for_all_lineages(candidate) is False


def test_v6_is_current_fresh_candidate_pending_source_validation() -> None:
    candidate = CURRENT_FRESH_USD60_HOLDOUT_CANDIDATE

    assert candidate.start_at == datetime(2013, 10, 19, tzinfo=UTC)
    assert candidate.end_exclusive_at == datetime(2014, 4, 19, tzinfo=UTC)
    assert candidate.status is CiboHoldoutCandidateStatus.SOURCE_VALIDATION_PENDING
    assert candidate.outcome_data_inspected_at_selection is False
    assert candidate.source_validation_complete is False
    assert candidate_is_burn_clean_for_all_lineages(candidate) is True


def test_known_vt31_burn_overlap_is_detected() -> None:
    candidate = CiboHoldoutCandidate(
        candidate_id="overlap-vt31",
        start_at=datetime(2017, 7, 1, tzinfo=UTC),
        end_exclusive_at=datetime(2018, 1, 1, tzinfo=UTC),
        status=CiboHoldoutCandidateStatus.SOURCE_VALIDATION_PENDING,
        selection_rule="test-only",
        outcome_data_inspected_at_selection=False,
        source_validation_complete=False,
    )

    assert candidate_overlaps_confirmed_burn(
        candidate,
        lineage=TraderLineage.VT31_NAS100,
    ) is True


def test_end_exclusive_boundary_does_not_overlap_vt31_burn() -> None:
    candidate = CiboHoldoutCandidate(
        candidate_id="boundary-clean",
        start_at=datetime(2013, 10, 19, tzinfo=UTC),
        end_exclusive_at=datetime(2014, 4, 19, tzinfo=UTC),
        status=CiboHoldoutCandidateStatus.SOURCE_VALIDATION_PENDING,
        selection_rule="test-only",
        outcome_data_inspected_at_selection=False,
        source_validation_complete=False,
    )

    assert candidate_overlaps_confirmed_burn(
        candidate,
        lineage=TraderLineage.VT31_NAS100,
    ) is False
