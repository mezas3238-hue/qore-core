from __future__ import annotations

from dataclasses import replace

from qore.infrastructure.core_stack_v2.shared_b_open_work_ledger import (
    B_WORK_ITEMS,
    SharedBWorkStatus,
)
from qore.infrastructure.core_stack_v2.shared_b_world_perception_freeze import (
    PRE_FREEZE_REQUIRED_IDS,
    assess_final_b_handoff,
    assess_world_perception_freeze,
)
from qore.infrastructure.core_stack_v2.shared_integrator_b_provenance_coverage import (
    assess_b_provenance_coverage,
)


def _all_complete_except(*open_ids: str):
    return tuple(
        replace(
            item,
            status=(
                item.status
                if item.work_id in open_ids
                else SharedBWorkStatus.COMPLETE_AND_PROVEN
            ),
            blockers=(item.blockers if item.work_id in open_ids else ()),
        )
        for item in B_WORK_ITEMS
    )


def test_current_b22_state_fails_closed_with_exact_blockers() -> None:
    coverage = assess_b_provenance_coverage(PRE_FREEZE_REQUIRED_IDS)
    result = assess_world_perception_freeze(
        provenance_coverage=coverage,
        deterministic_replay_verified=False,
        explicit_unknowns_preserved=True,
        authority_free_outputs=True,
    )
    assert result.pre_freeze_provenance_complete is True
    assert result.provenance_missing_ids == ("B-22", "B-24")
    assert "B-06" in result.upstream_nonterminal_ids
    assert "B-16" in result.upstream_nonterminal_ids
    assert "B-21" in result.upstream_nonterminal_ids
    assert result.freeze_authorized is False
    assert len(result.fingerprint()) == 64


def test_b22_can_emit_after_upstream_terminal_without_future_pointer_cycle() -> None:
    items = _all_complete_except("B-22", "B-24")
    coverage = assess_b_provenance_coverage(PRE_FREEZE_REQUIRED_IDS)
    result = assess_world_perception_freeze(
        provenance_coverage=coverage,
        deterministic_replay_verified=True,
        explicit_unknowns_preserved=True,
        authority_free_outputs=True,
        items=items,
    )
    assert result.provenance_missing_ids == ("B-22", "B-24")
    assert result.pre_freeze_provenance_complete is True
    assert result.upstream_nonterminal_ids == ()
    assert result.freeze_authorized is True


def test_b22_still_refuses_if_unknowns_or_authority_integrity_fail() -> None:
    items = _all_complete_except("B-22", "B-24")
    coverage = assess_b_provenance_coverage(PRE_FREEZE_REQUIRED_IDS)
    for unknowns, authority in ((False, True), (True, False)):
        result = assess_world_perception_freeze(
            provenance_coverage=coverage,
            deterministic_replay_verified=True,
            explicit_unknowns_preserved=unknowns,
            authority_free_outputs=authority,
            items=items,
        )
        assert result.freeze_authorized is False


def test_b24_requires_b22_and_all_pre_handoff_work_terminal() -> None:
    covered_through_b22 = tuple(
        f"B-{index:02d}" for index in range(1, 24)
    )
    coverage = assess_b_provenance_coverage(covered_through_b22)

    before_freeze = _all_complete_except("B-22", "B-24")
    blocked = assess_final_b_handoff(
        provenance_coverage=coverage,
        world_perception_freeze_present=False,
        deterministic_replay_verified=True,
        explicit_unknowns_preserved=True,
        authority_free_outputs=True,
        items=before_freeze,
    )
    assert blocked.pre_handoff_provenance_complete is True
    assert blocked.provenance_missing_ids == ("B-24",)
    assert blocked.handoff_authorized is False
    assert "B-22" in blocked.pre_handoff_nonterminal_ids

    after_freeze = _all_complete_except("B-24")
    ready = assess_final_b_handoff(
        provenance_coverage=coverage,
        world_perception_freeze_present=True,
        deterministic_replay_verified=True,
        explicit_unknowns_preserved=True,
        authority_free_outputs=True,
        items=after_freeze,
    )
    assert ready.pre_handoff_nonterminal_ids == ()
    assert ready.pre_handoff_provenance_complete is True
    assert ready.handoff_authorized is True
    assert len(ready.fingerprint()) == 64


def test_b24_never_uses_its_own_future_pointer_as_prerequisite() -> None:
    items = _all_complete_except("B-24")
    coverage = assess_b_provenance_coverage(
        tuple(f"B-{index:02d}" for index in range(1, 24))
    )
    result = assess_final_b_handoff(
        provenance_coverage=coverage,
        world_perception_freeze_present=True,
        deterministic_replay_verified=True,
        explicit_unknowns_preserved=True,
        authority_free_outputs=True,
        items=items,
    )
    assert result.provenance_missing_ids == ("B-24",)
    assert result.handoff_authorized is True
