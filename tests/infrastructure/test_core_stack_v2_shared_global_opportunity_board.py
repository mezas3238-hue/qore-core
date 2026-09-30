from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_global_opportunity_board import (
    SharedOpportunityBoardCandidate,
    build_global_opportunity_attention_board,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityHeadState,
    SharedOpportunityMechanism,
    SharedOpportunityTrajectoryAssessment,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
    SharedTraderIntelligenceValidationError,
)

NOW = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)


def _assessment(
    *,
    asset: str = "NAS100",
    maturity: SharedOpportunityMaturity = SharedOpportunityMaturity.DEVELOPING,
    contradiction: int = 1_500,
    uncertainty: int = 2_000,
) -> SharedOpportunityTrajectoryAssessment:
    return SharedOpportunityTrajectoryAssessment(
        asset=asset,
        maturity=maturity,
        dominant_mechanism=SharedOpportunityMechanism.EXPANSION,
        head_states=(
            SharedOpportunityHeadState(
                mechanism=SharedOpportunityMechanism.EXPANSION,
                current_level_bps=7_000,
                velocity_bps=1_000,
                persistence_bps=8_000,
                trajectory_score_bps=7_500,
                maturity=maturity,
            ),
        ),
        contradiction_bps=contradiction,
        uncertainty_bps=uncertainty,
        reason_codes=("DOMINANT_EXPANSION",),
    )


def _candidate(
    *,
    candidate_id: str = "opp-001",
    asset: str = "NAS100",
    maturity: SharedOpportunityMaturity = SharedOpportunityMaturity.DEVELOPING,
) -> SharedOpportunityBoardCandidate:
    return SharedOpportunityBoardCandidate(
        candidate_id=candidate_id,
        assessment=_assessment(asset=asset, maturity=maturity),
        observed_at=NOW,
        evidence_cutoff_at=NOW - timedelta(seconds=1),
        horizon="M15",
        data_health_bps=9_900,
        relevant_traders=("VT31_NAS100",),
        provenance_refs=("sti2-v2:trajectory",),
    )


def test_empty_board_is_valid() -> None:
    board = build_global_opportunity_attention_board(
        board_id="board-empty",
        as_of=NOW,
        evidence_cutoff_at=NOW - timedelta(seconds=1),
        candidates=(),
    )
    assert board.is_empty is True
    assert board.empty_board_valid is True
    assert board.execution_authority is False
    assert len(board.fingerprint()) == 64


def test_real_sti2_assessment_maps_to_attention_entry() -> None:
    board = build_global_opportunity_attention_board(
        board_id="board-001",
        as_of=NOW,
        evidence_cutoff_at=NOW - timedelta(seconds=1),
        candidates=(_candidate(),),
    )
    entry = board.entries[0]
    assert entry.market == "NAS100"
    assert entry.maturity is SharedOpportunityMaturity.DEVELOPING
    assert entry.trajectory is SharedOpportunityMechanism.EXPANSION
    assert entry.trajectory_score_bps == 7_500
    assert entry.support_bps == 5_750
    assert entry.contradiction_bps == 1_500
    assert entry.uncertainty_bps == 2_000
    assert entry.data_health_bps == 9_900
    assert entry.relevant_traders == ("VT31_NAS100",)
    assert entry.ranking_is_order_priority is False
    assert entry.creates_trader_setup is False


def test_no_opportunity_or_insufficient_do_not_create_board_priority() -> None:
    candidates = (
        _candidate(
            candidate_id="none",
            maturity=SharedOpportunityMaturity.NO_OPPORTUNITY,
        ),
        _candidate(
            candidate_id="insufficient",
            maturity=SharedOpportunityMaturity.INSUFFICIENT,
        ),
    )
    board = build_global_opportunity_attention_board(
        board_id="board-002",
        as_of=NOW,
        evidence_cutoff_at=NOW - timedelta(seconds=1),
        candidates=candidates,
    )
    assert board.is_empty is True


def test_board_order_is_identity_order_not_support_rank() -> None:
    low_asset = _candidate(candidate_id="z", asset="US30")
    high_asset = _candidate(candidate_id="a", asset="NAS100")
    board = build_global_opportunity_attention_board(
        board_id="board-003",
        as_of=NOW,
        evidence_cutoff_at=NOW - timedelta(seconds=1),
        candidates=(low_asset, high_asset),
    )
    assert tuple(entry.market for entry in board.entries) == ("NAS100", "US30")
    assert board.ranking_semantics == "CANONICAL_IDENTITY_NOT_EXECUTION_PRIORITY"


def test_candidate_rejects_future_evidence() -> None:
    candidate = _candidate()
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot use future evidence",
    ):
        replace(candidate, evidence_cutoff_at=NOW + timedelta(seconds=1))


def test_relevant_traders_are_not_an_execution_ranking() -> None:
    candidate = _candidate()
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="relevant_traders must be unique and canonical",
    ):
        replace(candidate, relevant_traders=("VT31_NAS100", "R34_XAUUSD"))
