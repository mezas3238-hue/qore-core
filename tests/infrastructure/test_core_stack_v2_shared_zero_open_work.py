from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.core_stack_v2.shared_zero_open_work import (
    SharedOpenWorkItem,
    SharedWorkState,
    assess_zero_open_work,
    build_shared_master_open_work_ledger,
)


def test_master_ledger_contains_all_required_program_families() -> None:
    ledger = build_shared_master_open_work_ledger()
    ids = {item.work_id for item in ledger}

    assert {f"WP-{i:02d}" for i in range(1, 13)} <= ids
    assert {f"MC-{i:02d}" for i in range(1, 29)} <= ids
    assert {f"STI-{i}" for i in range(17)} <= ids
    assert {f"GW-{i}" for i in range(24)} <= ids
    assert {"X-20", "X-21", "X-22"} <= ids


def test_zero_open_work_is_blocked_by_current_required_items() -> None:
    assessment = assess_zero_open_work()

    assert assessment.zero_open_required_work is False
    assert assessment.pre_certification_ready is False
    assert assessment.final_certification_exam_authorized is False
    assert assessment.protected_holdout_opening_authorized is False
    assert assessment.productive_authority is False
    assert "WP-05" in assessment.blocker_ids
    assert "MC-28" in assessment.blocker_ids
    assert "STI-2" in assessment.blocker_ids
    assert "STI-8" in assessment.blocker_ids
    assert "GW-2" in assessment.blocker_ids
    assert "X-20" in assessment.blocker_ids


def test_closed_wp_status_does_not_close_later_mandatory_capabilities() -> None:
    ledger = build_shared_master_open_work_ledger()
    by_id = {item.work_id: item for item in ledger}

    assert by_id["WP-01"].state is SharedWorkState.COMPLETED_AND_PROVEN
    assert by_id["WP-04"].state is SharedWorkState.COMPLETED_AND_PROVEN
    assert by_id["WP-05"].state is SharedWorkState.RESEARCH_INCOMPLETE
    assert by_id["MC-01"].state is SharedWorkState.UNRESOLVED_REQUIRED_AUDIT
    assert by_id["MC-04"].state is SharedWorkState.UNRESOLVED_REQUIRED_AUDIT
    assert by_id["MC-05"].state is SharedWorkState.UNRESOLVED_REQUIRED_AUDIT


def test_falsified_v1_cannot_close_mandatory_capability() -> None:
    item = SharedOpenWorkItem(
        work_id="STI-2",
        family="STI",
        title="Opportunity Discovery Engine",
        mandatory=True,
        state=SharedWorkState.RESEARCH_INCOMPLETE,
        evidence_refs=("sti2-v1-falsified",),
    )

    with pytest.raises(
        ValueError,
        match="mandatory capability cannot be closed",
    ):
        replace(item, state=SharedWorkState.FALSIFIED_AND_CLOSED)


def test_optional_hypothesis_may_be_falsified_and_closed() -> None:
    item = SharedOpenWorkItem(
        work_id="HYP-001",
        family="HYPOTHESIS",
        title="Non-mandatory hypothesis",
        mandatory=False,
        state=SharedWorkState.FALSIFIED_AND_CLOSED,
        evidence_refs=("experiment-001",),
        replacement_required_if_falsified=False,
    )
    assessment = assess_zero_open_work((item,))

    assert assessment.zero_open_required_work is True
    assert assessment.mandatory_items == 0
    assert assessment.optional_closed == 1
    assert assessment.pre_certification_ready is False


def test_all_mandatory_completed_still_does_not_open_final_exam() -> None:
    items = (
        SharedOpenWorkItem(
            work_id="TEST-01",
            family="TEST",
            title="Completed mandatory item",
            mandatory=True,
            state=SharedWorkState.COMPLETED_AND_PROVEN,
            evidence_refs=("verified-evidence",),
        ),
    )
    assessment = assess_zero_open_work(items)

    assert assessment.zero_open_required_work is True
    assert assessment.pre_certification_ready is False
    assert assessment.final_certification_exam_authorized is False
    assert assessment.protected_holdout_opening_authorized is False
