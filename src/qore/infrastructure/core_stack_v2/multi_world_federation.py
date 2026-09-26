"""WP-02 Federation of Worlds for Shared Brain.

This layer turns the Market Digital Twin into a competition among multiple
internal explanations of market dynamics. Worlds are not hard-selected. Each
keeps posterior probability and is scored from prediction error, causal
coherence, calibration, trajectory accuracy and current evidence.

The federation is sequential: the previous posterior becomes the next prior.
High epistemic uncertainty/OOD evidence increases the unresolved world instead
of forcing false certainty.

No world has methodology, sizing, Risk, stop, target, order or execution
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp, log

from qore.infrastructure.core_stack_v2.market_digital_twin import (
    MarketDigitalTwinSnapshot,
)
from qore.infrastructure.core_stack_v2.multi_world_engine import (
    WorldModelFamily,
)


@dataclass(frozen=True, slots=True)
class WorldDiagnostic:
    family: WorldModelFamily
    as_of: datetime
    causal_consistency_bps: int
    calibration_bps: int
    trajectory_accuracy_bps: int
    current_evidence_bps: int
    integrity_bps: int = 10_000

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("world diagnostic as_of must be timezone-aware")
        for name in (
            "causal_consistency_bps",
            "calibration_bps",
            "trajectory_accuracy_bps",
            "current_evidence_bps",
            "integrity_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class WorldEvidence:
    family: WorldModelFamily
    as_of: datetime
    prediction_error_bps: int
    prediction_observation_count: int
    causal_consistency_bps: int
    calibration_bps: int
    trajectory_accuracy_bps: int
    current_evidence_bps: int
    integrity_bps: int

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("world evidence as_of must be timezone-aware")
        if self.prediction_observation_count < 0:
            raise ValueError("prediction observation count cannot be negative")
        for name in (
            "prediction_error_bps",
            "causal_consistency_bps",
            "calibration_bps",
            "trajectory_accuracy_bps",
            "current_evidence_bps",
            "integrity_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class FederatedWorldPosterior:
    family: WorldModelFamily
    probability_bps: int
    quality_bps: int
    prediction_error_bps: int
    evidence_reliability_bps: int

    def __post_init__(self) -> None:
        for name in (
            "probability_bps",
            "quality_bps",
            "prediction_error_bps",
            "evidence_reliability_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class WorldFederationState:
    as_of: datetime
    posteriors: tuple[FederatedWorldPosterior, ...]
    dominant_world: WorldModelFamily
    dominance_margin_bps: int
    disagreement_bps: int
    world_diversity_bps: int
    revision_pressure_bps: int
    previous_dominant_world: WorldModelFamily | None
    dominant_world_changed: bool
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("federation as_of must be timezone-aware")
        expected = set(WorldModelFamily)
        actual = {item.family for item in self.posteriors}
        if actual != expected:
            raise ValueError("federation must retain every world family")
        for name in (
            "dominance_margin_bps",
            "disagreement_bps",
            "world_diversity_bps",
            "revision_pressure_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if sum(item.probability_bps for item in self.posteriors) != 10_000:
            raise ValueError("world posterior mass must sum to 10000 bps")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("world federation cannot carry trading authority")


_MODEL_ALIASES = {
    "LIQUIDITY_WORLD": WorldModelFamily.LIQUIDITY_DRIVEN,
    "MOMENTUM_WORLD": WorldModelFamily.MOMENTUM_DRIVEN,
    "MEAN_REVERSION_WORLD": WorldModelFamily.MEAN_REVERSION,
    "AGENCY_WORLD": WorldModelFamily.AGENCY_INVENTORY,
    "INVENTORY_WORLD": WorldModelFamily.AGENCY_INVENTORY,
    "MACRO_WORLD": WorldModelFamily.MACRO_DRIVEN,
    "EVENT_WORLD": WorldModelFamily.EVENT_DISLOCATION,
    "DISLOCATION_WORLD": WorldModelFamily.EVENT_DISLOCATION,
    "UNKNOWN_WORLD": WorldModelFamily.UNRESOLVED,
}


def _resolve_family(raw: str) -> WorldModelFamily:
    try:
        return WorldModelFamily(raw)
    except ValueError:
        family = _MODEL_ALIASES.get(raw)
        if family is None:
            raise ValueError(f"unknown world-model family: {raw}") from None
        return family


def build_world_evidence_from_twin(
    *,
    twin: MarketDigitalTwinSnapshot,
    diagnostics: tuple[WorldDiagnostic, ...],
) -> tuple[WorldEvidence, ...]:
    """Bind digital-twin prediction error to independent world diagnostics."""

    if any(item.as_of > twin.as_of for item in diagnostics):
        raise ValueError("future world diagnostic is forbidden")
    by_family = {item.family: item for item in diagnostics}
    if len(by_family) != len(diagnostics):
        raise ValueError("world diagnostics must be unique by family")
    if set(by_family) != set(WorldModelFamily):
        raise ValueError("diagnostics must cover every world family")

    errors: dict[WorldModelFamily, list[int]] = {
        family: [] for family in WorldModelFamily
    }
    for record in twin.prediction_error_ledger:
        family = _resolve_family(record.model_family)
        errors[family].append(record.surprise_bps)

    evidence: list[WorldEvidence] = []
    for family in WorldModelFamily:
        diagnostic = by_family[family]
        family_errors = errors[family]
        prediction_error = (
            sum(family_errors) // len(family_errors)
            if family_errors
            else 5_000
        )
        evidence.append(
            WorldEvidence(
                family=family,
                as_of=diagnostic.as_of,
                prediction_error_bps=prediction_error,
                prediction_observation_count=len(family_errors),
                causal_consistency_bps=diagnostic.causal_consistency_bps,
                calibration_bps=diagnostic.calibration_bps,
                trajectory_accuracy_bps=diagnostic.trajectory_accuracy_bps,
                current_evidence_bps=diagnostic.current_evidence_bps,
                integrity_bps=diagnostic.integrity_bps,
            )
        )
    return tuple(evidence)


def _quality(item: WorldEvidence) -> int:
    raw = (
        (10_000 - item.prediction_error_bps) * 30
        + item.causal_consistency_bps * 25
        + item.calibration_bps * 20
        + item.trajectory_accuracy_bps * 15
        + item.current_evidence_bps * 10
    ) // 100
    return raw * item.integrity_bps // 10_000


def _normalized_entropy_bps(probabilities: list[float]) -> int:
    if len(probabilities) <= 1:
        return 0
    entropy = -sum(p * log(p) for p in probabilities if p > 0)
    maximum = log(len(probabilities))
    return max(0, min(10_000, int(round(entropy / maximum * 10_000))))


def _normalize_bps(probabilities: list[float]) -> list[int]:
    values = [int(value * 10_000) for value in probabilities]
    remainder = 10_000 - sum(values)
    order = sorted(
        range(len(probabilities)),
        key=lambda index: probabilities[index],
        reverse=True,
    )
    step = 1 if remainder >= 0 else -1
    for index in range(abs(remainder)):
        values[order[index % len(order)]] += step
    return values


def update_world_federation(
    *,
    as_of: datetime,
    evidence: tuple[WorldEvidence, ...],
    epistemic_uncertainty_bps: int,
    ood_risk_bps: int,
    previous: WorldFederationState | None = None,
) -> WorldFederationState:
    """Update posterior weights for all competing internal worlds."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    for name, value in (
        ("epistemic_uncertainty_bps", epistemic_uncertainty_bps),
        ("ood_risk_bps", ood_risk_bps),
    ):
        if not 0 <= value <= 10_000:
            raise ValueError(f"{name} must be within 0..10000")
    if any(item.as_of > as_of for item in evidence):
        raise ValueError("future world evidence is forbidden")

    by_family = {item.family: item for item in evidence}
    if len(by_family) != len(evidence):
        raise ValueError("world evidence must be unique by family")
    if set(by_family) != set(WorldModelFamily):
        raise ValueError("world evidence must cover every family")

    if previous is None:
        prior = {family: 1.0 / len(WorldModelFamily) for family in WorldModelFamily}
        previous_dominant = None
    else:
        if previous.as_of >= as_of:
            raise ValueError("world federation must advance in time")
        prior = {
            item.family: max(1, item.probability_bps) / 10_000.0
            for item in previous.posteriors
        }
        previous_dominant = previous.dominant_world

    qualities = {family: _quality(by_family[family]) for family in WorldModelFamily}
    log_scores: list[float] = []
    families = list(WorldModelFamily)
    unknown_boost = (
        epistemic_uncertainty_bps + ood_risk_bps
    ) / 10_000.0

    for family in families:
        score = log(prior[family])
        score += (qualities[family] - 5_000) / 2_000.0
        if family is WorldModelFamily.UNRESOLVED:
            score += unknown_boost
        log_scores.append(score)

    maximum = max(log_scores)
    shifted = [exp(value - maximum) for value in log_scores]
    total = sum(shifted)
    probabilities = [value / total for value in shifted]
    probabilities_bps = _normalize_bps(probabilities)

    posteriors = tuple(
        FederatedWorldPosterior(
            family=family,
            probability_bps=probabilities_bps[index],
            quality_bps=qualities[family],
            prediction_error_bps=by_family[family].prediction_error_bps,
            evidence_reliability_bps=by_family[family].integrity_bps,
        )
        for index, family in enumerate(families)
    )
    ranked = sorted(
        posteriors,
        key=lambda item: (-item.probability_bps, item.family.value),
    )
    dominant = ranked[0].family
    margin = ranked[0].probability_bps - ranked[1].probability_bps
    diversity = _normalized_entropy_bps(probabilities)
    disagreement = diversity

    mean_prediction_error = (
        sum(item.prediction_error_bps for item in evidence) // len(evidence)
    )
    change_pressure = 1_500 if (
        previous_dominant is not None and previous_dominant is not dominant
    ) else 0
    revision_pressure = min(
        10_000,
        mean_prediction_error // 2
        + disagreement // 4
        + epistemic_uncertainty_bps // 5
        + ood_risk_bps // 5
        + change_pressure,
    )

    return WorldFederationState(
        as_of=as_of,
        posteriors=posteriors,
        dominant_world=dominant,
        dominance_margin_bps=margin,
        disagreement_bps=disagreement,
        world_diversity_bps=diversity,
        revision_pressure_bps=revision_pressure,
        previous_dominant_world=previous_dominant,
        dominant_world_changed=(
            previous_dominant is not None and previous_dominant is not dominant
        ),
    )
