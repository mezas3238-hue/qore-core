from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.competitive_hypothesis_engine import (
    CompetitiveHypothesis,
    update_competing_hypotheses,
)
from qore.infrastructure.core_stack_v2.latent_market_state_engine import (
    LatentFactorPosterior,
    LatentMarketFactor,
    LatentMarketState,
)


NOW = datetime(2026, 9, 26, 2, 45, tzinfo=UTC)


def _state(
    values: dict[LatentMarketFactor, int],
    *,
    uncertainty: int = 1_500,
    familiarity: int = 8_500,
) -> LatentMarketState:
    posteriors = tuple(
        LatentFactorPosterior(
            factor=factor,
            probability_bps=values.get(factor, 5_000),
            confidence_bps=8_000,
            epistemic_uncertainty_bps=2_000,
            independent_group_count=3,
            evidence_count=5,
        )
        for factor in LatentMarketFactor
    )
    return LatentMarketState(
        as_of=NOW,
        posteriors=posteriors,
        overall_epistemic_uncertainty_bps=uncertainty,
        regime_familiarity_bps=familiarity,
        evidence_cutoff_at=NOW,
    )


def test_continuation_profile_raises_continuation_hypothesis() -> None:
    state = _state(
        {
            LatentMarketFactor.MOMENTUM_PERSISTENCE: 8_000,
            LatentMarketFactor.POST_SWEEP_CONTINUATION: 7_500,
            LatentMarketFactor.INFORMATIVE_MOVE: 7_000,
            LatentMarketFactor.MULTISCALE_COHERENCE: 7_000,
            LatentMarketFactor.STRUCTURAL_FRAGILITY: 2_500,
        }
    )
    result = update_competing_hypotheses(latent_state=state)

    assert result.dominant_hypothesis is CompetitiveHypothesis.CONTINUATION
    assert sum(item.probability_bps for item in result.posteriors) == 10_000
    assert result.execution_authority is False


def test_false_move_profile_competes_with_other_hypotheses() -> None:
    state = _state(
        {
            LatentMarketFactor.ABSORPTION: 7_500,
            LatentMarketFactor.INFORMATIVE_MOVE: 2_000,
            LatentMarketFactor.MULTISCALE_COHERENCE: 2_500,
            LatentMarketFactor.STRUCTURAL_FRAGILITY: 6_000,
            LatentMarketFactor.POST_SWEEP_CONTINUATION: 2_000,
        }
    )
    result = update_competing_hypotheses(latent_state=state)

    assert result.dominant_hypothesis is CompetitiveHypothesis.LIQUIDITY_FALSE_MOVE
    assert len(result.posteriors) == 5


def test_high_epistemic_uncertainty_pushes_unresolved_probability() -> None:
    certain = update_competing_hypotheses(
        latent_state=_state(
            {
                LatentMarketFactor.MOMENTUM_PERSISTENCE: 8_000,
                LatentMarketFactor.POST_SWEEP_CONTINUATION: 8_000,
            },
            uncertainty=1_000,
            familiarity=9_000,
        )
    )
    uncertain = update_competing_hypotheses(
        latent_state=_state(
            {
                LatentMarketFactor.MOMENTUM_PERSISTENCE: 8_000,
                LatentMarketFactor.POST_SWEEP_CONTINUATION: 8_000,
            },
            uncertainty=9_000,
            familiarity=2_000,
        )
    )

    def unresolved(result: object) -> int:
        return next(
            item.probability_bps
            for item in result.posteriors
            if item.hypothesis is CompetitiveHypothesis.UNRESOLVED
        )

    assert unresolved(uncertain) > unresolved(certain)


def test_prior_state_supports_online_sequential_update() -> None:
    first = update_competing_hypotheses(
        latent_state=_state(
            {
                LatentMarketFactor.MOMENTUM_PERSISTENCE: 7_000,
                LatentMarketFactor.POST_SWEEP_CONTINUATION: 6_500,
                LatentMarketFactor.INFORMATIVE_MOVE: 6_000,
            }
        )
    )
    second = update_competing_hypotheses(
        latent_state=_state(
            {
                LatentMarketFactor.MOMENTUM_PERSISTENCE: 8_000,
                LatentMarketFactor.POST_SWEEP_CONTINUATION: 8_000,
                LatentMarketFactor.INFORMATIVE_MOVE: 7_000,
            }
        ),
        prior_state=first,
    )

    first_continuation = next(
        item.probability_bps
        for item in first.posteriors
        if item.hypothesis is CompetitiveHypothesis.CONTINUATION
    )
    second_continuation = next(
        item.probability_bps
        for item in second.posteriors
        if item.hypothesis is CompetitiveHypothesis.CONTINUATION
    )
    assert second_continuation >= first_continuation
