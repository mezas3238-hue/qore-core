"""Six-source uncertainty decomposition for Shared scientific cognition.

This V2 keeps uncertainty dimensions separate rather than compressing every
unknown into one confidence score. It is explicitly UNCALIBRATED: component
scores are bounded research indices, not probabilities.

Mandatory dimensions:
- ALEATORIC
- EPISTEMIC
- DATA
- REGIME
- CAUSAL
- SIMULATION
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SharedUncertaintySource(StrEnum):
    ALEATORIC = "ALEATORIC"
    EPISTEMIC = "EPISTEMIC"
    DATA = "DATA"
    REGIME = "REGIME"
    CAUSAL = "CAUSAL"
    SIMULATION = "SIMULATION"


@dataclass(frozen=True, slots=True)
class SharedUncertaintyEvidenceV2:
    observation_noise_bps: int
    realized_path_variability_bps: int
    scenario_overlap_bps: int

    model_disagreement_bps: int
    novelty_bps: int
    calibration_error_bps: int
    historical_distance_bps: int

    data_missingness_bps: int
    timestamp_ambiguity_bps: int
    provider_anomaly_bps: int

    regime_unfamiliarity_bps: int
    regime_transition_bps: int
    relationship_instability_bps: int

    causal_identification_ambiguity_bps: int
    confounding_risk_bps: int
    transportability_uncertainty_bps: int

    simulation_model_gap_bps: int
    scenario_coverage_gap_bps: int
    simulation_instability_bps: int

    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name in {
                "outcome_used",
                "pnl_used",
                "future_market_used",
            }:
                continue
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if self.outcome_used or self.pnl_used or self.future_market_used:
            raise ValueError(
                "uncertainty evidence must be causal and source-time only"
            )


@dataclass(frozen=True, slots=True)
class SharedUncertaintyDecompositionV2:
    aleatoric_bps: int
    epistemic_bps: int
    data_bps: int
    regime_bps: int
    causal_bps: int
    simulation_bps: int
    total_uncertainty_bps: int
    assertiveness_ceiling_bps: int
    dominant_sources: tuple[SharedUncertaintySource, ...]
    calibration_state: str = "UNCALIBRATED"
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "aleatoric_bps",
            "epistemic_bps",
            "data_bps",
            "regime_bps",
            "causal_bps",
            "simulation_bps",
            "total_uncertainty_bps",
            "assertiveness_ceiling_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if self.calibration_state != "UNCALIBRATED":
            raise ValueError(
                "V2 uncertainty must remain UNCALIBRATED until calibration proof"
            )
        if not self.dominant_sources:
            raise ValueError("uncertainty decomposition requires a dominant source")
        if tuple(sorted(set(self.dominant_sources), key=lambda x: x.value)) != (
            self.dominant_sources
        ):
            raise ValueError("dominant_sources must be unique and canonical")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError(
                "uncertainty decomposition cannot carry downstream authority"
            )


def _mean(*values: int) -> int:
    return sum(values) // len(values)


def decompose_uncertainty_v2(
    evidence: SharedUncertaintyEvidenceV2,
) -> SharedUncertaintyDecompositionV2:
    """Decompose six uncertainty sources without probabilistic theater."""

    aleatoric = _mean(
        evidence.observation_noise_bps,
        evidence.realized_path_variability_bps,
        evidence.scenario_overlap_bps,
    )
    epistemic = _mean(
        evidence.model_disagreement_bps,
        evidence.novelty_bps,
        evidence.calibration_error_bps,
        evidence.historical_distance_bps,
    )
    data = _mean(
        evidence.data_missingness_bps,
        evidence.timestamp_ambiguity_bps,
        evidence.provider_anomaly_bps,
    )
    regime = _mean(
        evidence.regime_unfamiliarity_bps,
        evidence.regime_transition_bps,
        evidence.relationship_instability_bps,
    )
    causal = _mean(
        evidence.causal_identification_ambiguity_bps,
        evidence.confounding_risk_bps,
        evidence.transportability_uncertainty_bps,
    )
    simulation = _mean(
        evidence.simulation_model_gap_bps,
        evidence.scenario_coverage_gap_bps,
        evidence.simulation_instability_bps,
    )
    components = {
        SharedUncertaintySource.ALEATORIC: aleatoric,
        SharedUncertaintySource.EPISTEMIC: epistemic,
        SharedUncertaintySource.DATA: data,
        SharedUncertaintySource.REGIME: regime,
        SharedUncertaintySource.CAUSAL: causal,
        SharedUncertaintySource.SIMULATION: simulation,
    }
    maximum = max(components.values())
    dominant = tuple(
        sorted(
            (
                source
                for source, value in components.items()
                if maximum - value <= 500
            ),
            key=lambda item: item.value,
        )
    )

    # Conservative research index: any severe uncertainty source can dominate.
    total = maximum

    # Aleatoric ambiguity limits predictability, but the ceiling below is
    # specifically about how assertive Shared may be about its *knowledge*.
    knowledge_uncertainty = max(
        epistemic,
        data,
        regime,
        causal,
        simulation,
    )
    assertiveness_ceiling = max(0, 10_000 - knowledge_uncertainty)

    return SharedUncertaintyDecompositionV2(
        aleatoric_bps=aleatoric,
        epistemic_bps=epistemic,
        data_bps=data,
        regime_bps=regime,
        causal_bps=causal,
        simulation_bps=simulation,
        total_uncertainty_bps=total,
        assertiveness_ceiling_bps=assertiveness_ceiling,
        dominant_sources=dominant,
    )
