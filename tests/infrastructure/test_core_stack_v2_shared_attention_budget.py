from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_attention_budget import (
    SharedAttentionCandidate,
    SharedAttentionCategory,
    allocate_shared_attention,
)

NOW = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)


def _candidate(
    candidate_id: str,
    category: SharedAttentionCategory,
    *,
    information_value: int = 7_000,
    uncertainty: int = 5_000,
    urgency: int = 5_000,
    units: int = 1,
    health: bool = True,
    cutoff: datetime = NOW,
) -> SharedAttentionCandidate:
    return SharedAttentionCandidate(
        candidate_id=candidate_id,
        category=category,
        as_of=NOW,
        evidence_cutoff_at=cutoff,
        information_value_bps=information_value,
        uncertainty_bps=uncertainty,
        urgency_bps=urgency,
        compute_units=units,
        data_health_passed=health,
        provenance_refs=(f"ref:{candidate_id}",),
    )


def test_owner_priority_selects_open_position_before_background() -> None:
    candidates = tuple(
        sorted(
            (
                _candidate(
                    "background",
                    SharedAttentionCategory.BACKGROUND_WORLD,
                    information_value=10_000,
                ),
                _candidate(
                    "position",
                    SharedAttentionCategory.OPEN_POSITION,
                    information_value=3_000,
                ),
            ),
            key=lambda item: item.candidate_id,
        )
    )
    plan = allocate_shared_attention(
        candidates,
        as_of=NOW,
        budget_units=1,
    )

    selected = [item for item in plan.decisions if item.selected]
    assert [item.candidate_id for item in selected] == ["position"]
    assert plan.used_units == 1


def test_information_value_orders_within_same_category() -> None:
    candidates = tuple(
        sorted(
            (
                _candidate(
                    "low",
                    SharedAttentionCategory.ACTIVE_OPPORTUNITY,
                    information_value=4_000,
                ),
                _candidate(
                    "high",
                    SharedAttentionCategory.ACTIVE_OPPORTUNITY,
                    information_value=8_000,
                ),
            ),
            key=lambda item: item.candidate_id,
        )
    )
    plan = allocate_shared_attention(
        candidates,
        as_of=NOW,
        budget_units=1,
    )
    selected = [item for item in plan.decisions if item.selected]
    assert [item.candidate_id for item in selected] == ["high"]


def test_bad_data_health_is_never_selected() -> None:
    candidate = _candidate(
        "broken",
        SharedAttentionCategory.OPEN_POSITION,
        health=False,
    )
    plan = allocate_shared_attention(
        (candidate,),
        as_of=NOW,
        budget_units=5,
    )
    assert plan.decisions[0].selected is False
    assert plan.decisions[0].reason_code == "DATA_HEALTH_BLOCK"
    assert plan.unresolved_candidate_ids == ("broken",)


def test_zero_information_value_does_not_consume_budget() -> None:
    candidate = _candidate(
        "zero",
        SharedAttentionCategory.RELATIONSHIP_BREAK,
        information_value=0,
    )
    plan = allocate_shared_attention(
        (candidate,),
        as_of=NOW,
        budget_units=5,
    )
    assert plan.used_units == 0
    assert plan.decisions[0].reason_code == "ZERO_INFORMATION_VALUE"


def test_future_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="future evidence"):
        _candidate(
            "future",
            SharedAttentionCategory.GLOBAL_ANOMALY,
            cutoff=NOW + timedelta(seconds=1),
        )


def test_plan_has_no_downstream_authority() -> None:
    plan = allocate_shared_attention(
        (_candidate("watch", SharedAttentionCategory.TRADER_WATCHLIST),),
        as_of=NOW,
        budget_units=3,
    )
    assert plan.methodology_authority is False
    assert plan.capital_authority is False
    assert plan.risk_authority is False
    assert plan.execution_authority is False
