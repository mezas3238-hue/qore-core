"""Active-perception planner for Shared Core.

The planner asks: *what evidence would most reduce uncertainty between the
leading competing hypotheses right now?*

It does not fetch data and does not control execution. It emits ranked
information requests that perception/cross-market adapters may satisfy.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.competitive_hypothesis_engine import (
    CompetitiveHypothesis,
    CompetitiveHypothesisState,
    HypothesisPrototype,
    default_hypothesis_library,
)
from qore.infrastructure.core_stack_v2.latent_market_state_engine import (
    LatentMarketFactor,
    LatentMarketState,
)


@dataclass(frozen=True, slots=True)
class ActivePerceptionRequest:
    factor: LatentMarketFactor
    hypothesis_a: CompetitiveHypothesis
    hypothesis_b: CompetitiveHypothesis
    information_need_bps: int
    expected_separation_bps: int
    current_factor_uncertainty_bps: int
    suggested_source_families: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        for name in (
            "information_need_bps",
            "expected_separation_bps",
            "current_factor_uncertainty_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if not self.suggested_source_families:
            raise ValueError("active perception requires source families")


@dataclass(frozen=True, slots=True)
class ActivePerceptionPlan:
    requests: tuple[ActivePerceptionRequest, ...]
    top_hypotheses: tuple[CompetitiveHypothesis, ...]
    unresolved_information_need_bps: int
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.unresolved_information_need_bps <= 10_000:
            raise ValueError("unresolved information need must be within 0..10000")
        if self.execution_authority or self.risk_authority or self.sizing_authority:
            raise ValueError("active perception cannot carry trading authority")


_SOURCE_MAP: dict[LatentMarketFactor, tuple[str, ...]] = {
    LatentMarketFactor.BUY_PRESSURE: ("order_flow", "price_response", "cross_market"),
    LatentMarketFactor.SELL_PRESSURE: ("order_flow", "price_response", "cross_market"),
    LatentMarketFactor.ABSORPTION: ("liquidity_response", "microstructure", "price_response"),
    LatentMarketFactor.POST_SWEEP_CONTINUATION: (
        "post_sweep_path",
        "acceptance",
        "cross_market",
    ),
    LatentMarketFactor.STRUCTURAL_FRAGILITY: (
        "structure",
        "acceptance",
        "opposite_displacement",
    ),
    LatentMarketFactor.REGIME_TRANSITION: (
        "volatility",
        "structure",
        "cross_market",
    ),
    LatentMarketFactor.MOMENTUM_PERSISTENCE: (
        "path_velocity",
        "displacement",
        "cross_market",
    ),
    LatentMarketFactor.LIQUIDITY_VACUUM: (
        "liquidity",
        "volatility",
        "microstructure",
    ),
    LatentMarketFactor.INFORMATIVE_MOVE: (
        "acceptance",
        "cross_market",
        "follow_through",
    ),
    LatentMarketFactor.MULTISCALE_COHERENCE: (
        "multi_timeframe",
        "cross_market",
        "structure",
    ),
}


def _prototype_map(
    prototypes: tuple[HypothesisPrototype, ...],
) -> dict[CompetitiveHypothesis, dict[LatentMarketFactor, int]]:
    return {
        prototype.hypothesis: dict(prototype.expected_factor_bps)
        for prototype in prototypes
    }


def plan_active_perception(
    *,
    latent_state: LatentMarketState,
    hypothesis_state: CompetitiveHypothesisState,
    prototypes: tuple[HypothesisPrototype, ...] | None = None,
    maximum_requests: int = 5,
) -> ActivePerceptionPlan:
    """Rank evidence requests that best separate the leading hypotheses."""

    if maximum_requests < 1:
        raise ValueError("maximum_requests must be positive")
    models = prototypes or default_hypothesis_library()
    expectations = _prototype_map(models)
    ranked_hypotheses = sorted(
        hypothesis_state.posteriors,
        key=lambda item: (-item.probability_bps, item.hypothesis.value),
    )
    if len(ranked_hypotheses) < 2:
        raise ValueError("active perception requires at least two hypotheses")

    hypothesis_a = ranked_hypotheses[0].hypothesis
    hypothesis_b = ranked_hypotheses[1].hypothesis
    expected_a = expectations.get(hypothesis_a, {})
    expected_b = expectations.get(hypothesis_b, {})
    latent = {item.factor: item for item in latent_state.posteriors}

    requests: list[ActivePerceptionRequest] = []
    for factor in LatentMarketFactor:
        separation = abs(expected_a.get(factor, 5_000) - expected_b.get(factor, 5_000))
        posterior = latent.get(factor)
        uncertainty = (
            10_000
            if posterior is None
            else posterior.epistemic_uncertainty_bps
        )
        information_need = min(
            10_000,
            separation * uncertainty // 10_000,
        )
        if information_need <= 0:
            continue
        requests.append(
            ActivePerceptionRequest(
                factor=factor,
                hypothesis_a=hypothesis_a,
                hypothesis_b=hypothesis_b,
                information_need_bps=information_need,
                expected_separation_bps=separation,
                current_factor_uncertainty_bps=uncertainty,
                suggested_source_families=_SOURCE_MAP[factor],
                reason=(
                    f"{factor.value} most efficiently separates "
                    f"{hypothesis_a.value} from {hypothesis_b.value}"
                ),
            )
        )

    requests.sort(
        key=lambda item: (
            -item.information_need_bps,
            -item.expected_separation_bps,
            item.factor.value,
        )
    )
    selected = tuple(requests[:maximum_requests])
    unresolved = (
        hypothesis_state.entropy_bps
        + latent_state.overall_epistemic_uncertainty_bps
    ) // 2
    return ActivePerceptionPlan(
        requests=selected,
        top_hypotheses=tuple(
            item.hypothesis for item in ranked_hypotheses[:3]
        ),
        unresolved_information_need_bps=unresolved,
    )
