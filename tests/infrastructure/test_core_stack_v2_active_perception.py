# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.active_perception import (
    plan_active_perception,
)
from qore.infrastructure.core_stack_v2.competitive_hypothesis_engine import (
    CompetitiveHypothesis,
    CompetitiveHypothesisState,
    HypothesisPosterior,
)
from qore.infrastructure.core_stack_v2.latent_market_state_engine import (
    LatentFactorPosterior,
    LatentMarketFactor,
    LatentMarketState,
)


NOW = datetime(2026, 9, 26, 3, 5, tzinfo=UTC)


def _latent() -> LatentMarketState:
    return LatentMarketState(
        as_of=NOW,
        posteriors=tuple(
            LatentFactorPosterior(
                factor=factor,
                probability_bps=5_000,
                confidence_bps=2_000,
                epistemic_uncertainty_bps=8_000,
                independent_group_count=1,
                evidence_count=1,
            )
            for factor in LatentMarketFactor
        ),
        overall_epistemic_uncertainty_bps=8_000,
        regime_familiarity_bps=7_000,
        evidence_cutoff_at=NOW,
    )


def _hypotheses() -> CompetitiveHypothesisState:
    return CompetitiveHypothesisState(
        as_of_iso=NOW.isoformat(),
        posteriors=(
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.CONTINUATION,
                probability_bps=4_200,
                support_bps=6_000,
                contradiction_bps=4_000,
            ),
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.SWEEP_REVERSAL,
                probability_bps=3_800,
                support_bps=5_500,
                contradiction_bps=4_500,
            ),
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.COMPRESSION_EXPANSION,
                probability_bps=1_000,
                support_bps=5_000,
                contradiction_bps=5_000,
            ),
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.LIQUIDITY_FALSE_MOVE,
                probability_bps=700,
                support_bps=5_000,
                contradiction_bps=5_000,
            ),
            HypothesisPosterior(
                hypothesis=CompetitiveHypothesis.UNRESOLVED,
                probability_bps=300,
                support_bps=3_000,
                contradiction_bps=7_000,
            ),
        ),
        entropy_bps=7_500,
        confidence_bps=2_000,
        epistemic_uncertainty_bps=8_000,
        regime_familiarity_bps=7_000,
        dominant_hypothesis=CompetitiveHypothesis.CONTINUATION,
    )


def test_active_perception_targets_discriminative_uncertain_factors() -> None:
    plan = plan_active_perception(
        latent_state=_latent(),
        hypothesis_state=_hypotheses(),
        maximum_requests=3,
    )

    assert len(plan.requests) == 3
    assert plan.top_hypotheses[:2] == (
        CompetitiveHypothesis.CONTINUATION,
        CompetitiveHypothesis.SWEEP_REVERSAL,
    )
    assert all(request.information_need_bps > 0 for request in plan.requests)
    assert plan.execution_authority is False


def test_active_perception_respects_request_limit() -> None:
    plan = plan_active_perception(
        latent_state=_latent(),
        hypothesis_state=_hypotheses(),
        maximum_requests=1,
    )

    assert len(plan.requests) == 1
