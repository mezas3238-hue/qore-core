from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.shared_b_open_work_ledger import (
    B_WORK_ITEMS,
    SharedBWorkItem,
    SharedBWorkStatus,
    build_shared_b_open_work_ledger,
)


def test_b_ledger_tracks_exact_b01_to_b24() -> None:
    assert tuple(item.work_id for item in B_WORK_ITEMS) == tuple(
        f"B-{index:02d}" for index in range(1,25)
    )
    payload=build_shared_b_open_work_ledger()
    assert payload["mandatory_item_count"] == 24
    assert payload["required_open_count"] > 0
    assert payload["zero_open_required_work"] is False
    assert payload["b_lane_complete"] is False
    assert payload["shared_certification_authority"] is False
    assert payload["final_shared_holdout_authority"] is False
    assert len(payload["ledger_fingerprint_sha256"]) == 64


def test_b_ledger_does_not_hide_external_or_architecture_only_blockers() -> None:
    payload=build_shared_b_open_work_ledger()
    items={item["work_id"]:item for item in payload["items"]}
    assert items["B-07"]["status"] == "EXTERNALLY_BLOCKED"
    assert items["B-10"]["status"] == "ARCHITECTURE_VALIDATED_EVIDENCE_OPEN"
    assert items["B-14"]["status"] == "EXTERNALLY_BLOCKED"
    assert items["B-18"]["status"] == "ARCHITECTURE_VALIDATED_EVIDENCE_OPEN"
    for work_id in ("B-07","B-10","B-14","B-18"):
        assert items[work_id]["blockers"]


def test_complete_work_cannot_retain_blockers() -> None:
    with pytest.raises(ValueError,match="cannot retain blockers"):
        SharedBWorkItem(
            work_id="B-99",
            title="invalid",
            status=SharedBWorkStatus.COMPLETE_AND_PROVEN,
            evidence_refs=("run:1",),
            blockers=("still open",),
        )


def test_incomplete_mandatory_work_requires_explicit_blocker() -> None:
    with pytest.raises(ValueError,match="explicit blockers"):
        SharedBWorkItem(
            work_id="B-99",
            title="invalid",
            status=SharedBWorkStatus.OPEN,
            evidence_refs=(),
        )


def test_complete_evidence_items_have_no_blockers() -> None:
    complete=[
        item for item in B_WORK_ITEMS
        if item.status is SharedBWorkStatus.COMPLETE_AND_PROVEN
    ]
    assert complete
    assert all(not item.blockers for item in complete)
