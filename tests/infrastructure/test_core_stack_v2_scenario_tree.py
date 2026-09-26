from __future__ import annotations

from qore.infrastructure.core_stack_v2.competitive_hypothesis_engine import (
    CompetitiveHypothesis,
    CompetitiveHypothesisState,
    HypothesisPosterior,
)
from qore.infrastructure.core_stack_v2.scenario_tree import (
    ScenarioTransition,
    ScenarioTreePolicy,
    build_scenario_tree,
)


def _state() -> CompetitiveHypothesisState:
    return CompetitiveHypothesisState(
        as_of_iso="2026-09-26T02:50:00+00:00",
        posteriors=(
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.CONTINUATION,
                probability_bps=4_000,
                support_bps=7_000,
                contradiction_bps=3_000,
            ),
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.SWEEP_REVERSAL,
                probability_bps=3_000,
                support_bps=6_000,
                contradiction_bps=4_000,
            ),
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.COMPRESSION_EXPANSION,
                probability_bps=1_500,
                support_bps=5_500,
                contradiction_bps=4_500,
            ),
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.LIQUIDITY_FALSE_MOVE,
                probability_bps=1_000,
                support_bps=5_000,
                contradiction_bps=5_000,
            ),
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.UNRESOLVED,
                probability_bps=500,
                support_bps=3_000,
                contradiction_bps=7_000,
            ),
        ),
        entropy_bps=7_000,
        confidence_bps=2_000,
        epistemic_uncertainty_bps=2_000,
        regime_familiarity_bps=8_000,
        dominant_hypothesis=CompetitiveHypothesis.CONTINUATION,
    )


def test_scenario_tree_preserves_multiple_competing_paths() -> None:
    tree = build_scenario_tree(
        state=_state(),
        transitions=(
            ScenarioTransition(
                CompetitiveHypothesis.CONTINUATION,
                CompetitiveHypothesis.CONTINUATION,
                7_000,
            ),
            ScenarioTransition(
                CompetitiveHypothesis.CONTINUATION,
                CompetitiveHypothesis.SWEEP_REVERSAL,
                3_000,
            ),
            ScenarioTransition(
                CompetitiveHypothesis.SWEEP_REVERSAL,
                CompetitiveHypothesis.SWEEP_REVERSAL,
                6_000,
            ),
            ScenarioTransition(
                CompetitiveHypothesis.SWEEP_REVERSAL,
                CompetitiveHypothesis.CONTINUATION,
                4_000,
            ),
        ),
        policy=ScenarioTreePolicy(depth=2, beam_width=6),
    )

    assert len(tree.branches) >= 2
    assert any(
        branch.path[-1] is CompetitiveHypothesis.CONTINUATION
        for branch in tree.branches
    )
    assert any(
        branch.path[-1] is CompetitiveHypothesis.SWEEP_REVERSAL
        for branch in tree.branches
    )
    assert tree.execution_authority is False


def test_missing_transition_row_defaults_to_self_persistence() -> None:
    tree = build_scenario_tree(
        state=_state(),
        transitions=(),
        policy=ScenarioTreePolicy(depth=2, beam_width=8),
    )

    assert all(branch.path[0] is branch.path[-1] for branch in tree.branches)
