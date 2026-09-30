from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.shared_global_opportunity_board import (
    SharedGlobalOpportunityAttentionBoard,
    SharedOpportunityBoardEntry,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityMechanism,
)
from qore.infrastructure.core_stack_v2.shared_opportunity_surface import (
    SharedOpportunityRarityState,
    build_global_opportunity_surface,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
)

NOW = datetime(2026, 9, 30, 16, 45, tzinfo=UTC)


def _entry(candidate: str = "candidate-001") -> SharedOpportunityBoardEntry:
    return SharedOpportunityBoardEntry(
        candidate_id=candidate,
        market="NAS100",
        horizon="M1",
        maturity=SharedOpportunityMaturity.MATURE,
        trajectory=SharedOpportunityMechanism.EXPANSION,
        trajectory_score_bps=8_000,
        support_bps=7_500,
        contradiction_bps=1_500,
        uncertainty_bps=2_000,
        data_health_bps=9_900,
        relevant_traders=("VT31_NAS100",),
        observed_at=NOW,
        evidence_cutoff_at=NOW,
        provenance_refs=("sti3:surface-test",),
    )


def _board(index: int, *, include: bool = True) -> SharedGlobalOpportunityAttentionBoard:
    return SharedGlobalOpportunityAttentionBoard(
        board_id=f"board-{index}",
        as_of=NOW - timedelta(minutes=10 - index),
        evidence_cutoff_at=NOW - timedelta(minutes=10 - index),
        entries=(_entry(f"history-{index}"),) if include else (),
    )


def test_surface_is_descriptive_not_order_priority() -> None:
    current = SharedGlobalOpportunityAttentionBoard(
        board_id="current",
        as_of=NOW,
        evidence_cutoff_at=NOW,
        entries=(_entry(),),
    )
    surface = build_global_opportunity_surface(
        surface_id="surface-001",
        as_of=NOW,
        current_board=current,
        historical_boards=tuple(_board(i) for i in range(10)),
    )
    point = surface.points[0]
    assert point.evidence_asymmetry_bps == 5_750
    assert point.order_priority is False
    assert point.capital_priority is False
    assert surface.execution_authority is False
    assert len(surface.fingerprint()) == 64


def test_unseen_signature_is_very_rare() -> None:
    current = SharedGlobalOpportunityAttentionBoard(
        board_id="current",
        as_of=NOW,
        evidence_cutoff_at=NOW,
        entries=(_entry(),),
    )
    empty_history = tuple(_board(i, include=False) for i in range(10))
    surface = build_global_opportunity_surface(
        surface_id="surface-rare",
        as_of=NOW,
        current_board=current,
        historical_boards=empty_history,
    )
    assert surface.points[0].rarity_bps == 10_000
    assert surface.points[0].rarity_state is SharedOpportunityRarityState.VERY_RARE


def test_no_history_marks_rarity_insufficient() -> None:
    current = SharedGlobalOpportunityAttentionBoard(
        board_id="current",
        as_of=NOW,
        evidence_cutoff_at=NOW,
        entries=(_entry(),),
    )
    surface = build_global_opportunity_surface(
        surface_id="surface-no-history",
        as_of=NOW,
        current_board=current,
        historical_boards=(),
    )
    assert surface.points[0].rarity_state is SharedOpportunityRarityState.INSUFFICIENT


def test_empty_current_board_is_valid_surface() -> None:
    current = SharedGlobalOpportunityAttentionBoard(
        board_id="empty",
        as_of=NOW,
        evidence_cutoff_at=NOW,
        entries=(),
    )
    surface = build_global_opportunity_surface(
        surface_id="surface-empty",
        as_of=NOW,
        current_board=current,
        historical_boards=(),
    )
    assert surface.is_empty is True
