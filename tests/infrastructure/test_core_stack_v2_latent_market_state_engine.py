# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.latent_market_state_engine import (
    LatentEvidenceAtom,
    LatentMarketFactor,
    infer_latent_market_state,
)


NOW = datetime(2026, 9, 26, 2, 30, tzinfo=UTC)


def _atom(
    factor: LatentMarketFactor,
    *,
    support: int,
    contradiction: int,
    group: str,
    seconds_ago: int = 0,
) -> LatentEvidenceAtom:
    return LatentEvidenceAtom(
        factor=factor,
        source_family=group,
        independence_group=group,
        as_of=NOW - timedelta(seconds=seconds_ago),
        support_bps=support,
        contradiction_bps=contradiction,
    )


def test_independent_support_raises_latent_probability_and_confidence() -> None:
    state = infer_latent_market_state(
        as_of=NOW,
        regime_familiarity_bps=8_000,
        evidence=(
            _atom(
                LatentMarketFactor.ABSORPTION,
                support=8_000,
                contradiction=2_000,
                group="price_reaction",
            ),
            _atom(
                LatentMarketFactor.ABSORPTION,
                support=7_500,
                contradiction=2_500,
                group="liquidity_response",
            ),
        ),
    )

    posterior = next(
        item
        for item in state.posteriors
        if item.factor is LatentMarketFactor.ABSORPTION
    )
    assert posterior.probability_bps > 5_000
    assert posterior.confidence_bps > 0
    assert posterior.independent_group_count == 2
    assert state.outcome_used is False
    assert state.execution_authority is False


def test_correlated_repeats_have_diminishing_weight() -> None:
    independent = infer_latent_market_state(
        as_of=NOW,
        regime_familiarity_bps=8_000,
        evidence=(
            _atom(
                LatentMarketFactor.STRUCTURAL_FRAGILITY,
                support=8_000,
                contradiction=2_000,
                group="structure",
            ),
            _atom(
                LatentMarketFactor.STRUCTURAL_FRAGILITY,
                support=8_000,
                contradiction=2_000,
                group="cross_market",
            ),
        ),
    )
    correlated = infer_latent_market_state(
        as_of=NOW,
        regime_familiarity_bps=8_000,
        evidence=(
            _atom(
                LatentMarketFactor.STRUCTURAL_FRAGILITY,
                support=8_000,
                contradiction=2_000,
                group="structure",
            ),
            _atom(
                LatentMarketFactor.STRUCTURAL_FRAGILITY,
                support=8_000,
                contradiction=2_000,
                group="structure",
            ),
        ),
    )

    assert independent.probability_bps(
        LatentMarketFactor.STRUCTURAL_FRAGILITY
    ) > correlated.probability_bps(
        LatentMarketFactor.STRUCTURAL_FRAGILITY
    )


def test_stale_evidence_contributes_less_than_fresh_evidence() -> None:
    fresh = infer_latent_market_state(
        as_of=NOW,
        regime_familiarity_bps=8_000,
        evidence=(
            _atom(
                LatentMarketFactor.MOMENTUM_PERSISTENCE,
                support=8_000,
                contradiction=2_000,
                group="momentum",
            ),
        ),
    )
    old = infer_latent_market_state(
        as_of=NOW,
        regime_familiarity_bps=8_000,
        evidence=(
            _atom(
                LatentMarketFactor.MOMENTUM_PERSISTENCE,
                support=8_000,
                contradiction=2_000,
                group="momentum",
                seconds_ago=1_800,
            ),
        ),
    )

    assert fresh.probability_bps(
        LatentMarketFactor.MOMENTUM_PERSISTENCE
    ) > old.probability_bps(
        LatentMarketFactor.MOMENTUM_PERSISTENCE
    )


def test_future_latent_evidence_fails_closed() -> None:
    with pytest.raises(ValueError):
        infer_latent_market_state(
            as_of=NOW,
            regime_familiarity_bps=8_000,
            evidence=(
                LatentEvidenceAtom(
                    factor=LatentMarketFactor.INFORMATIVE_MOVE,
                    source_family="future",
                    independence_group="future",
                    as_of=NOW + timedelta(seconds=1),
                    support_bps=7_000,
                    contradiction_bps=3_000,
                ),
            ),
        )
