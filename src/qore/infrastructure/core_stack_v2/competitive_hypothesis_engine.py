"""Competitive causal-hypothesis engine for Shared Core.

Shared must keep multiple explanations alive simultaneously and update them as
new latent-state evidence arrives. This module performs that update without
collapsing cognition into a single hard label.

A hypothesis prototype describes the latent-state profile expected under that
scenario. Posterior probability is updated in log space from:
- prior hypothesis probability,
- current latent-factor posteriors,
- factor confidence,
- regime familiarity,
- overall epistemic uncertainty.

The engine is generic and authority-free. It contains no trader, setup, sizing,
Risk, stop, target, order or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import exp, log

from qore.infrastructure.core_stack_v2.latent_market_state_engine import (
    LatentMarketFactor,
    LatentMarketState,
)


class CompetitiveHypothesis(StrEnum):
    CONTINUATION = "CONTINUATION"
    SWEEP_REVERSAL = "SWEEP_REVERSAL"
    COMPRESSION_EXPANSION = "COMPRESSION_EXPANSION"
    LIQUIDITY_FALSE_MOVE = "LIQUIDITY_FALSE_MOVE"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class HypothesisPrototype:
    hypothesis: CompetitiveHypothesis
    expected_factor_bps: tuple[tuple[LatentMarketFactor, int], ...]
    prior_bps: int = 2_000

    def __post_init__(self) -> None:
        if not 1 <= self.prior_bps <= 9_999:
            raise ValueError("prior_bps must be within 1..9999")
        factors = [factor for factor, _ in self.expected_factor_bps]
        if len(factors) != len(set(factors)):
            raise ValueError("prototype latent factors must be unique")
        for _, probability_bps in self.expected_factor_bps:
            if not 1 <= probability_bps <= 9_999:
                raise ValueError("expected factor probability must be within 1..9999")


@dataclass(frozen=True, slots=True)
class HypothesisPosterior:
    hypothesis: CompetitiveHypothesis
    probability_bps: int
    support_bps: int
    contradiction_bps: int

    def __post_init__(self) -> None:
        for name in ("probability_bps", "support_bps", "contradiction_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class CompetitiveHypothesisState:
    as_of_iso: str
    posteriors: tuple[HypothesisPosterior, ...]
    entropy_bps: int
    confidence_bps: int
    epistemic_uncertainty_bps: int
    regime_familiarity_bps: int
    dominant_hypothesis: CompetitiveHypothesis
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "entropy_bps",
            "confidence_bps",
            "epistemic_uncertainty_bps",
            "regime_familiarity_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if len({item.hypothesis for item in self.posteriors}) != len(
            self.posteriors
        ):
            raise ValueError("hypothesis posteriors must be unique")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.stop_authority
            or self.target_authority
            or self.execution_authority
        ):
            raise ValueError("hypothesis state cannot carry trading authority")


def default_hypothesis_library() -> tuple[HypothesisPrototype, ...]:
    """Return generic market hypotheses, not trader-methodology hypotheses."""

    return (
        HypothesisPrototype(
            CompetitiveHypothesis.CONTINUATION,
            (
                (LatentMarketFactor.MOMENTUM_PERSISTENCE, 7_500),
                (LatentMarketFactor.POST_SWEEP_CONTINUATION, 7_000),
                (LatentMarketFactor.INFORMATIVE_MOVE, 6_500),
                (LatentMarketFactor.MULTISCALE_COHERENCE, 6_500),
                (LatentMarketFactor.STRUCTURAL_FRAGILITY, 3_000),
            ),
        ),
        HypothesisPrototype(
            CompetitiveHypothesis.SWEEP_REVERSAL,
            (
                (LatentMarketFactor.ABSORPTION, 7_500),
                (LatentMarketFactor.STRUCTURAL_FRAGILITY, 7_000),
                (LatentMarketFactor.REGIME_TRANSITION, 6_500),
                (LatentMarketFactor.POST_SWEEP_CONTINUATION, 2_500),
                (LatentMarketFactor.INFORMATIVE_MOVE, 6_000),
            ),
        ),
        HypothesisPrototype(
            CompetitiveHypothesis.COMPRESSION_EXPANSION,
            (
                (LatentMarketFactor.LIQUIDITY_VACUUM, 6_500),
                (LatentMarketFactor.REGIME_TRANSITION, 6_500),
                (LatentMarketFactor.MOMENTUM_PERSISTENCE, 5_500),
                (LatentMarketFactor.INFORMATIVE_MOVE, 5_500),
                (LatentMarketFactor.MULTISCALE_COHERENCE, 5_000),
            ),
        ),
        HypothesisPrototype(
            CompetitiveHypothesis.LIQUIDITY_FALSE_MOVE,
            (
                (LatentMarketFactor.ABSORPTION, 6_500),
                (LatentMarketFactor.INFORMATIVE_MOVE, 2_500),
                (LatentMarketFactor.MULTISCALE_COHERENCE, 3_000),
                (LatentMarketFactor.STRUCTURAL_FRAGILITY, 5_500),
                (LatentMarketFactor.POST_SWEEP_CONTINUATION, 2_500),
            ),
        ),
        HypothesisPrototype(
            CompetitiveHypothesis.UNRESOLVED,
            tuple((factor, 5_000) for factor in LatentMarketFactor),
        ),
    )


def _bernoulli_log_likelihood(
    observed_probability: float,
    expected_probability: float,
) -> float:
    observed = min(0.9999, max(0.0001, observed_probability))
    expected = min(0.9999, max(0.0001, expected_probability))
    return (
        observed * log(expected)
        + (1.0 - observed) * log(1.0 - expected)
    )


def _softmax(values: list[float]) -> list[float]:
    maximum = max(values)
    shifted = [exp(value - maximum) for value in values]
    total = sum(shifted)
    return [value / total for value in shifted]


def _entropy_bps(probabilities: list[float]) -> int:
    if len(probabilities) <= 1:
        return 0
    entropy = -sum(
        probability * log(probability)
        for probability in probabilities
        if probability > 0
    )
    maximum = log(len(probabilities))
    return max(0, min(10_000, int(round(entropy / maximum * 10_000))))


def update_competing_hypotheses(
    *,
    latent_state: LatentMarketState,
    prototypes: tuple[HypothesisPrototype, ...] | None = None,
    prior_state: CompetitiveHypothesisState | None = None,
) -> CompetitiveHypothesisState:
    """Update a full competing-hypothesis distribution from latent state."""

    models = prototypes or default_hypothesis_library()
    if not models:
        raise ValueError("at least one hypothesis prototype is required")
    if len({model.hypothesis for model in models}) != len(models):
        raise ValueError("hypothesis prototypes must be unique")

    latent = {item.factor: item for item in latent_state.posteriors}
    prior_lookup = (
        {item.hypothesis: item.probability_bps for item in prior_state.posteriors}
        if prior_state is not None
        else {}
    )

    log_scores: list[float] = []
    supports: list[int] = []
    contradictions: list[int] = []

    reliability = (
        (10_000 - latent_state.overall_epistemic_uncertainty_bps)
        * latent_state.regime_familiarity_bps
        / 100_000_000.0
    )

    for model in models:
        prior_bps = prior_lookup.get(model.hypothesis, model.prior_bps)
        score = log(max(1, prior_bps) / 10_000.0)
        support_weight = 0.0
        contradiction_weight = 0.0
        total_weight = 0.0

        for factor, expected_bps in model.expected_factor_bps:
            posterior = latent.get(factor)
            if posterior is None:
                continue
            confidence = posterior.confidence_bps / 10_000.0
            weight = confidence * reliability
            observed = posterior.probability_bps / 10_000.0
            expected = expected_bps / 10_000.0
            score += _bernoulli_log_likelihood(observed, expected) * weight
            agreement = 1.0 - abs(observed - expected)
            support_weight += agreement * weight
            contradiction_weight += (1.0 - agreement) * weight
            total_weight += weight

        if model.hypothesis is CompetitiveHypothesis.UNRESOLVED:
            score += (
                latent_state.overall_epistemic_uncertainty_bps / 10_000.0
                + (10_000 - latent_state.regime_familiarity_bps) / 10_000.0
            )

        log_scores.append(score)
        if total_weight <= 0:
            supports.append(0)
            contradictions.append(0)
        else:
            supports.append(
                int(round(10_000 * support_weight / total_weight))
            )
            contradictions.append(
                int(round(10_000 * contradiction_weight / total_weight))
            )

    probabilities = _softmax(log_scores)
    probability_bps = [int(probability * 10_000) for probability in probabilities]
    remainder = 10_000 - sum(probability_bps)
    if remainder:
        best = max(range(len(probabilities)), key=probabilities.__getitem__)
        probability_bps[best] += remainder

    posteriors = tuple(
        HypothesisPosterior(
            hypothesis=model.hypothesis,
            probability_bps=probability_bps[index],
            support_bps=supports[index],
            contradiction_bps=contradictions[index],
        )
        for index, model in enumerate(models)
    )
    dominant = max(
        posteriors,
        key=lambda item: (item.probability_bps, item.hypothesis.value),
    ).hypothesis
    entropy = _entropy_bps(probabilities)
    confidence = min(
        10_000 - entropy,
        10_000 - latent_state.overall_epistemic_uncertainty_bps,
        latent_state.regime_familiarity_bps,
    )

    return CompetitiveHypothesisState(
        as_of_iso=latent_state.as_of.isoformat(),
        posteriors=posteriors,
        entropy_bps=entropy,
        confidence_bps=confidence,
        epistemic_uncertainty_bps=(
            latent_state.overall_epistemic_uncertainty_bps
        ),
        regime_familiarity_bps=latent_state.regime_familiarity_bps,
        dominant_hypothesis=dominant,
    )
