"""Uncertainty decomposition for Shared Core.

Aleatoric uncertainty describes irreducible market ambiguity.
Epistemic uncertainty describes what Shared does not understand well enough.

Keeping them separate prevents two dangerous errors:
- treating chaotic market conditions as a model failure;
- treating model ignorance as if the market were merely noisy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UncertaintyEvidence:
    observation_noise_bps: int
    realized_path_variability_bps: int
    scenario_overlap_bps: int
    model_disagreement_bps: int
    novelty_bps: int
    calibration_error_bps: int
    historical_distance_bps: int
    regime_unfamiliarity_bps: int

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class UncertaintyDecomposition:
    aleatoric_bps: int
    epistemic_bps: int
    total_uncertainty_bps: int
    dominant_source: str
    confidence_ceiling_bps: int
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "aleatoric_bps",
            "epistemic_bps",
            "total_uncertainty_bps",
            "confidence_ceiling_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.dominant_source not in {"ALEATORIC", "EPISTEMIC", "BALANCED"}:
            raise ValueError("dominant_source is invalid")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("uncertainty state cannot carry trading authority")


def decompose_uncertainty(
    evidence: UncertaintyEvidence,
) -> UncertaintyDecomposition:
    """Separate market ambiguity from model ignorance."""

    aleatoric = (
        evidence.observation_noise_bps
        + evidence.realized_path_variability_bps
        + evidence.scenario_overlap_bps
    ) // 3
    epistemic = (
        evidence.model_disagreement_bps
        + evidence.novelty_bps
        + evidence.calibration_error_bps
        + evidence.historical_distance_bps
        + evidence.regime_unfamiliarity_bps
    ) // 5

    if abs(aleatoric - epistemic) <= 500:
        dominant = "BALANCED"
    elif aleatoric > epistemic:
        dominant = "ALEATORIC"
    else:
        dominant = "EPISTEMIC"

    total = min(
        10_000,
        (aleatoric * 45 + epistemic * 55) // 100,
    )
    confidence_ceiling = max(0, 10_000 - epistemic)

    return UncertaintyDecomposition(
        aleatoric_bps=aleatoric,
        epistemic_bps=epistemic,
        total_uncertainty_bps=total,
        dominant_source=dominant,
        confidence_ceiling_bps=confidence_ceiling,
    )
