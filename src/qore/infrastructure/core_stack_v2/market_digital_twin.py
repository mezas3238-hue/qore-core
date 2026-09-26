"""Probabilistic Market Digital Twin for Shared Brain.

WP-01 of the maximum cognitive ceiling program.

The twin is a continuously updated, point-in-time representation of the real
market. It contains observable state, latent state, behavioral hypotheses,
liquidity/volatility topology, cross-market dependencies, regime structure,
uncertainty, expected state transitions and a prediction-error ledger.

The twin is deliberately authority-free. It does not own methodology, sizing,
capital, Risk, orders, stops, targets or execution.

Prediction error is computed only after a prediction target timestamp has
matured and an observation at or after that target is available. Future
observations are rejected.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _check_bps(name: str, value: int) -> None:
    if not 0 <= value <= 10_000:
        raise ValueError(f"{name} must be within 0..10000")


def _clamp_bps(value: int) -> int:
    return max(0, min(10_000, value))


class TwinDiagnosis(StrEnum):
    ALIGNED = "ALIGNED"
    WATCH = "WATCH"
    MODEL_DRIFT = "MODEL_DRIFT"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class TwinStateValue:
    concept: str
    probability_bps: int
    confidence_bps: int
    evidence_cutoff_at: datetime

    def __post_init__(self) -> None:
        if not self.concept:
            raise ValueError("concept must be non-empty")
        _check_bps("probability_bps", self.probability_bps)
        _check_bps("confidence_bps", self.confidence_bps)
        _require_aware("evidence_cutoff_at", self.evidence_cutoff_at)


@dataclass(frozen=True, slots=True)
class BehaviorHypothesis:
    behavior: str
    probability_bps: int
    confidence_bps: int
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.behavior:
            raise ValueError("behavior must be non-empty")
        _check_bps("probability_bps", self.probability_bps)
        _check_bps("confidence_bps", self.confidence_bps)


@dataclass(frozen=True, slots=True)
class LiquidityTopology:
    available_liquidity_bps: int
    absorption_bps: int
    vulnerability_bps: int
    vacuum_risk_bps: int
    imbalance_bps: int
    integrity_bps: int

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _check_bps(name, int(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class VolatilityTopology:
    realized_state_bps: int
    expansion_pressure_bps: int
    compression_pressure_bps: int
    shock_risk_bps: int
    persistence_bps: int
    integrity_bps: int

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _check_bps(name, int(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class CrossMarketDependency:
    source_node: str
    target_node: str
    dependence_bps: int
    lead_lag_bps: int
    stability_bps: int
    break_risk_bps: int

    def __post_init__(self) -> None:
        if not self.source_node or not self.target_node:
            raise ValueError("cross-market nodes must be non-empty")
        if self.source_node == self.target_node:
            raise ValueError("cross-market dependency cannot self-reference")
        for name in (
            "dependence_bps",
            "lead_lag_bps",
            "stability_bps",
            "break_risk_bps",
        ):
            _check_bps(name, int(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class RegimeStructure:
    regime: str
    transition_probability_bps: int
    familiarity_bps: int
    anomaly_bps: int
    stability_bps: int

    def __post_init__(self) -> None:
        if not self.regime:
            raise ValueError("regime must be non-empty")
        for name in (
            "transition_probability_bps",
            "familiarity_bps",
            "anomaly_bps",
            "stability_bps",
        ):
            _check_bps(name, int(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class TwinUncertainty:
    aleatoric_bps: int
    epistemic_bps: int
    model_disagreement_bps: int
    ood_risk_bps: int

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _check_bps(name, int(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class ExpectedStateTransition:
    horizon_bars: int
    target_state: str
    probability_bps: int
    confidence_bps: int

    def __post_init__(self) -> None:
        if self.horizon_bars < 1:
            raise ValueError("horizon_bars must be positive")
        if not self.target_state:
            raise ValueError("target_state must be non-empty")
        _check_bps("probability_bps", self.probability_bps)
        _check_bps("confidence_bps", self.confidence_bps)


@dataclass(frozen=True, slots=True)
class TwinPrediction:
    prediction_id: str
    channel: str
    made_at: datetime
    target_at: datetime
    expected_bps: int
    tolerance_bps: int
    model_family: str

    def __post_init__(self) -> None:
        if not self.prediction_id or not self.channel or not self.model_family:
            raise ValueError("prediction identity, channel and model family are required")
        _require_aware("made_at", self.made_at)
        _require_aware("target_at", self.target_at)
        if self.target_at <= self.made_at:
            raise ValueError("prediction target must be after made_at")
        _check_bps("expected_bps", self.expected_bps)
        _check_bps("tolerance_bps", self.tolerance_bps)


@dataclass(frozen=True, slots=True)
class TwinObservation:
    prediction_id: str
    channel: str
    observed_at: datetime
    observed_bps: int

    def __post_init__(self) -> None:
        if not self.prediction_id or not self.channel:
            raise ValueError("observation identity and channel are required")
        _require_aware("observed_at", self.observed_at)
        _check_bps("observed_bps", self.observed_bps)


@dataclass(frozen=True, slots=True)
class PredictionErrorRecord:
    prediction_id: str
    channel: str
    model_family: str
    made_at: datetime
    target_at: datetime
    observed_at: datetime
    expected_bps: int
    observed_bps: int
    signed_error_bps: int
    absolute_error_bps: int
    normalized_error_bps: int
    surprise_bps: int

    def __post_init__(self) -> None:
        for name in (
            "expected_bps",
            "observed_bps",
            "absolute_error_bps",
            "normalized_error_bps",
            "surprise_bps",
        ):
            _check_bps(name, int(getattr(self, name)))
        if not -10_000 <= self.signed_error_bps <= 10_000:
            raise ValueError("signed_error_bps must be within -10000..10000")


@dataclass(frozen=True, slots=True)
class MarketDigitalTwinSnapshot:
    as_of: datetime
    evidence_cutoff_at: datetime
    observable_state: tuple[TwinStateValue, ...]
    latent_state: tuple[TwinStateValue, ...]
    behavior_hypotheses: tuple[BehaviorHypothesis, ...]
    liquidity_topology: LiquidityTopology
    volatility_topology: VolatilityTopology
    cross_market_dependencies: tuple[CrossMarketDependency, ...]
    regime_structure: RegimeStructure
    uncertainty: TwinUncertainty
    expected_transitions: tuple[ExpectedStateTransition, ...]
    prediction_error_ledger: tuple[PredictionErrorRecord, ...]
    unresolved_prediction_ids: tuple[str, ...]
    aggregate_prediction_error_bps: int
    model_revision_pressure_bps: int
    diagnosis: TwinDiagnosis
    fingerprint: str
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
        _require_aware("as_of", self.as_of)
        _require_aware("evidence_cutoff_at", self.evidence_cutoff_at)
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future evidence cutoff is forbidden")
        for name in (
            "aggregate_prediction_error_bps",
            "model_revision_pressure_bps",
        ):
            _check_bps(name, int(getattr(self, name)))
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
            raise ValueError("Market Digital Twin cannot carry trading authority")


def _prediction_errors(
    *,
    as_of: datetime,
    predictions: tuple[TwinPrediction, ...],
    observations: tuple[TwinObservation, ...],
) -> tuple[tuple[PredictionErrorRecord, ...], tuple[str, ...]]:
    prediction_ids = [item.prediction_id for item in predictions]
    if len(prediction_ids) != len(set(prediction_ids)):
        raise ValueError("prediction ids must be unique")

    observation_by_id: dict[str, TwinObservation] = {}
    for observation in observations:
        if observation.observed_at > as_of:
            raise ValueError("future observation supplied to digital twin")
        if observation.prediction_id in observation_by_id:
            raise ValueError("duplicate observation for prediction id")
        observation_by_id[observation.prediction_id] = observation

    records: list[PredictionErrorRecord] = []
    unresolved: list[str] = []

    for prediction in predictions:
        if prediction.made_at > as_of:
            raise ValueError("future prediction supplied to digital twin")
        matched_observation = observation_by_id.get(prediction.prediction_id)

        if prediction.target_at > as_of:
            unresolved.append(prediction.prediction_id)
            if matched_observation is not None:
                raise ValueError("observation cannot mature before prediction target")
            continue

        if matched_observation is None:
            unresolved.append(prediction.prediction_id)
            continue
        if matched_observation.channel != prediction.channel:
            raise ValueError("prediction/observation channel mismatch")
        if matched_observation.observed_at < prediction.target_at:
            raise ValueError("observation predates matured prediction target")

        signed = matched_observation.observed_bps - prediction.expected_bps
        absolute = abs(signed)
        tolerance = max(1, prediction.tolerance_bps)
        normalized = _clamp_bps(absolute * 10_000 // tolerance)
        surprise = _clamp_bps(normalized)
        records.append(
            PredictionErrorRecord(
                prediction_id=prediction.prediction_id,
                channel=prediction.channel,
                model_family=prediction.model_family,
                made_at=prediction.made_at,
                target_at=prediction.target_at,
                observed_at=matched_observation.observed_at,
                expected_bps=prediction.expected_bps,
                observed_bps=matched_observation.observed_bps,
                signed_error_bps=signed,
                absolute_error_bps=absolute,
                normalized_error_bps=normalized,
                surprise_bps=surprise,
            )
        )

    unknown = set(observation_by_id) - set(prediction_ids)
    if unknown:
        raise ValueError(f"observation references unknown prediction ids: {sorted(unknown)}")

    return tuple(records), tuple(sorted(unresolved))


def _diagnose(
    *,
    errors: tuple[PredictionErrorRecord, ...],
    uncertainty: TwinUncertainty,
) -> tuple[int, int, TwinDiagnosis]:
    if not errors:
        return 0, uncertainty.epistemic_bps, TwinDiagnosis.INSUFFICIENT

    aggregate = sum(item.surprise_bps for item in errors) // len(errors)
    severe_count = sum(item.surprise_bps >= 7_500 for item in errors)
    revision = _clamp_bps(
        aggregate
        + uncertainty.epistemic_bps // 4
        + uncertainty.model_disagreement_bps // 5
        + uncertainty.ood_risk_bps // 5
        + severe_count * 500
    )

    if revision >= 7_000:
        diagnosis = TwinDiagnosis.MODEL_DRIFT
    elif revision >= 4_000:
        diagnosis = TwinDiagnosis.WATCH
    else:
        diagnosis = TwinDiagnosis.ALIGNED
    return aggregate, revision, diagnosis


def _fingerprint_payload(snapshot: dict[str, object]) -> str:
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def build_market_digital_twin(
    *,
    as_of: datetime,
    evidence_cutoff_at: datetime,
    observable_state: tuple[TwinStateValue, ...],
    latent_state: tuple[TwinStateValue, ...],
    behavior_hypotheses: tuple[BehaviorHypothesis, ...],
    liquidity_topology: LiquidityTopology,
    volatility_topology: VolatilityTopology,
    cross_market_dependencies: tuple[CrossMarketDependency, ...],
    regime_structure: RegimeStructure,
    uncertainty: TwinUncertainty,
    expected_transitions: tuple[ExpectedStateTransition, ...],
    predictions: tuple[TwinPrediction, ...] = (),
    observations: tuple[TwinObservation, ...] = (),
) -> MarketDigitalTwinSnapshot:
    """Build one deterministic point-in-time Market Digital Twin snapshot."""

    _require_aware("as_of", as_of)
    _require_aware("evidence_cutoff_at", evidence_cutoff_at)
    if evidence_cutoff_at > as_of:
        raise ValueError("future evidence cutoff is forbidden")

    for value in (*observable_state, *latent_state):
        if value.evidence_cutoff_at > as_of:
            raise ValueError("future state evidence supplied to digital twin")

    error_ledger, unresolved = _prediction_errors(
        as_of=as_of,
        predictions=predictions,
        observations=observations,
    )
    aggregate_error, revision_pressure, diagnosis = _diagnose(
        errors=error_ledger,
        uncertainty=uncertainty,
    )

    base = {
        "as_of": as_of.astimezone(UTC).isoformat(),
        "evidence_cutoff_at": evidence_cutoff_at.astimezone(UTC).isoformat(),
        "observable_state": [asdict(item) for item in observable_state],
        "latent_state": [asdict(item) for item in latent_state],
        "behavior_hypotheses": [asdict(item) for item in behavior_hypotheses],
        "liquidity_topology": asdict(liquidity_topology),
        "volatility_topology": asdict(volatility_topology),
        "cross_market_dependencies": [
            asdict(item) for item in cross_market_dependencies
        ],
        "regime_structure": asdict(regime_structure),
        "uncertainty": asdict(uncertainty),
        "expected_transitions": [asdict(item) for item in expected_transitions],
        "prediction_error_ledger": [asdict(item) for item in error_ledger],
        "unresolved_prediction_ids": unresolved,
        "aggregate_prediction_error_bps": aggregate_error,
        "model_revision_pressure_bps": revision_pressure,
        "diagnosis": diagnosis.value,
    }
    fingerprint = _fingerprint_payload(base)

    return MarketDigitalTwinSnapshot(
        as_of=as_of,
        evidence_cutoff_at=evidence_cutoff_at,
        observable_state=observable_state,
        latent_state=latent_state,
        behavior_hypotheses=behavior_hypotheses,
        liquidity_topology=liquidity_topology,
        volatility_topology=volatility_topology,
        cross_market_dependencies=cross_market_dependencies,
        regime_structure=regime_structure,
        uncertainty=uncertainty,
        expected_transitions=expected_transitions,
        prediction_error_ledger=error_ledger,
        unresolved_prediction_ids=unresolved,
        aggregate_prediction_error_bps=aggregate_error,
        model_revision_pressure_bps=revision_pressure,
        diagnosis=diagnosis,
        fingerprint=fingerprint,
    )
