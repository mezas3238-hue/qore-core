"""Competitive multi-world engine for Shared Core.

Shared maintains several internal explanations of market dynamics instead of
assuming one universal mechanism. Each world earns or loses posterior weight
from prediction error, causal consistency, calibration and trajectory accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import exp, log


class WorldModelFamily(StrEnum):
    LIQUIDITY_DRIVEN = "LIQUIDITY_DRIVEN"
    MOMENTUM_DRIVEN = "MOMENTUM_DRIVEN"
    MEAN_REVERSION = "MEAN_REVERSION"
    EVENT_DISLOCATION = "EVENT_DISLOCATION"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class WorldModelEvidence:
    family: WorldModelFamily
    prediction_error_bps: int
    causal_consistency_bps: int
    calibration_bps: int
    trajectory_accuracy_bps: int
    prior_bps: int = 2_000

    def __post_init__(self) -> None:
        for name in (
            "prediction_error_bps",
            "causal_consistency_bps",
            "calibration_bps",
            "trajectory_accuracy_bps",
            "prior_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.prior_bps == 0:
            raise ValueError("world-model prior must be positive")


@dataclass(frozen=True, slots=True)
class WorldModelPosterior:
    family: WorldModelFamily
    probability_bps: int
    score_bps: int

    def __post_init__(self) -> None:
        for name in ("probability_bps", "score_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class MultiWorldState:
    posteriors: tuple[WorldModelPosterior, ...]
    dominant_world: WorldModelFamily
    disagreement_bps: int
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.disagreement_bps <= 10_000:
            raise ValueError("world disagreement must be within 0..10000")
        if len({item.family for item in self.posteriors}) != len(self.posteriors):
            raise ValueError("world families must be unique")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("multi-world state cannot carry trading authority")


def _softmax(values: list[float]) -> list[float]:
    maximum = max(values)
    shifted = [exp(value - maximum) for value in values]
    total = sum(shifted)
    return [value / total for value in shifted]


def update_multi_world_state(
    evidence: tuple[WorldModelEvidence, ...],
) -> MultiWorldState:
    """Score and normalize competing internal market worlds."""

    if not evidence:
        raise ValueError("multi-world engine requires evidence")
    if len({item.family for item in evidence}) != len(evidence):
        raise ValueError("world evidence families must be unique")

    scores: list[float] = []
    score_bps: list[int] = []
    for item in evidence:
        quality = (
            (10_000 - item.prediction_error_bps)
            + item.causal_consistency_bps
            + item.calibration_bps
            + item.trajectory_accuracy_bps
        ) // 4
        score_bps.append(quality)
        prior = max(1, item.prior_bps) / 10_000.0
        scores.append(log(prior) + (quality - 5_000) / 2_500.0)

    probabilities = _softmax(scores)
    probabilities_bps = [int(value * 10_000) for value in probabilities]
    remainder = 10_000 - sum(probabilities_bps)
    best = max(range(len(probabilities)), key=probabilities.__getitem__)
    probabilities_bps[best] += remainder

    posteriors = tuple(
        WorldModelPosterior(
            family=item.family,
            probability_bps=probabilities_bps[index],
            score_bps=score_bps[index],
        )
        for index, item in enumerate(evidence)
    )
    ranked = sorted(
        posteriors,
        key=lambda item: (-item.probability_bps, item.family.value),
    )
    top = ranked[0].probability_bps
    second = ranked[1].probability_bps if len(ranked) > 1 else 0
    disagreement = max(0, min(10_000, 10_000 - (top - second)))

    return MultiWorldState(
        posteriors=posteriors,
        dominant_world=ranked[0].family,
        disagreement_bps=disagreement,
    )
