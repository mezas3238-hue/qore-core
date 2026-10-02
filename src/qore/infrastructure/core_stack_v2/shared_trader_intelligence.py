"""Typed cognition-only contracts for proactive Shared↔Trader intelligence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

SHARED_TRADER_INTELLIGENCE_VERSION: Final = (
    "QORE_SHARED_TRADER_INTELLIGENCE_001"
)


class SharedEpistemicState(StrEnum):
    KNOWN = "KNOWN"
    PARTIALLY_KNOWN = "PARTIALLY_KNOWN"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTORY = "CONTRADICTORY"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"


class SharedDirectionalHypothesis(StrEnum):
    BULLISH_HYPOTHESIS = "BULLISH_HYPOTHESIS"
    BEARISH_HYPOTHESIS = "BEARISH_HYPOTHESIS"
    CONTINUATION_HYPOTHESIS = "CONTINUATION_HYPOTHESIS"
    REVERSAL_HYPOTHESIS = "REVERSAL_HYPOTHESIS"
    RANGE_HYPOTHESIS = "RANGE_HYPOTHESIS"
    REGIME_TRANSITION_HYPOTHESIS = "REGIME_TRANSITION_HYPOTHESIS"
    INSUFFICIENT = "INSUFFICIENT"


class SharedSupportState(StrEnum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    STRONG = "STRONG"
    INSUFFICIENT = "INSUFFICIENT"


class SharedOpportunityMaturity(StrEnum):
    NO_OPPORTUNITY = "NO_OPPORTUNITY"
    EARLY = "EARLY"
    DEVELOPING = "DEVELOPING"
    MATURE = "MATURE"
    DETERIORATING = "DETERIORATING"
    EXPIRED = "EXPIRED"
    INSUFFICIENT = "INSUFFICIENT"


class SharedAlertLifecycle(StrEnum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    STRENGTHENING = "STRENGTHENING"
    WEAKENING = "WEAKENING"
    RESOLVED = "RESOLVED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


class SharedRegimeTransitionState(StrEnum):
    STABLE = "STABLE"
    CONTINUATION = "CONTINUATION"
    EXHAUSTION_RISK = "EXHAUSTION_RISK"
    TRANSITION_DEVELOPING = "TRANSITION_DEVELOPING"
    REVERSAL_RISK = "REVERSAL_RISK"
    REGIME_BREAK = "REGIME_BREAK"
    STRUCTURAL_DECOUPLING = "STRUCTURAL_DECOUPLING"
    INSUFFICIENT = "INSUFFICIENT"


class SharedPositionThreatLevel(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    INSUFFICIENT = "INSUFFICIENT"


class SharedConfidenceCalibrationState(StrEnum):
    UNCALIBRATED = "UNCALIBRATED"
    CALIBRATED = "CALIBRATED"


class SharedIntelligenceClass(StrEnum):
    OPPORTUNITY = "OPPORTUNITY"
    REGIME_TRANSITION = "REGIME_TRANSITION"
    CONTINUATION = "CONTINUATION"
    WORLD_EXPLANATION = "WORLD_EXPLANATION"
    POSITION_THREAT = "POSITION_THREAT"


class TraderSharedOpportunityDisposition(StrEnum):
    VALID_TRADE = "VALID_TRADE"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"


class SharedPositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class SharedTraderIntelligenceValidationError(ValueError):
    """Shared↔Trader intelligence contract rejected invalid cognition."""


def _validate_text(value: str, *, field_name: str) -> None:
    if not value.strip():
        raise SharedTraderIntelligenceValidationError(
            f"{field_name} must be non-empty"
        )


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SharedTraderIntelligenceValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_refs(
    refs: tuple[str, ...],
    *,
    field_name: str,
    allow_empty: bool = False,
) -> None:
    if not allow_empty and not refs:
        raise SharedTraderIntelligenceValidationError(
            f"{field_name} must be non-empty"
        )
    if refs != tuple(sorted(set(refs))):
        raise SharedTraderIntelligenceValidationError(
            f"{field_name} must be unique and canonical"
        )
    if any(not item.strip() for item in refs):
        raise SharedTraderIntelligenceValidationError(
            f"{field_name} cannot contain empty references"
        )


def _validate_bps(value: int, *, field_name: str) -> None:
    if type(value) is not int or not 0 <= value <= 10_000:
        raise SharedTraderIntelligenceValidationError(
            f"{field_name} must be int within 0..10000"
        )


def _fingerprint(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedTraderIntelligenceSnapshot:
    """Evidence-bound Shared world cognition projected toward one instrument."""

    snapshot_id: str
    observed_at: datetime
    evidence_cutoff_at: datetime
    asset: str
    canonical_instrument_id: str
    market_family: str
    trader_horizon: str
    world_state: str
    market_regime: str
    macro_regime: str
    rates_state: str
    usd_state: str
    liquidity_state: str
    volatility_state: str
    commodity_state: str
    agricultural_state: str
    cross_asset_state: str
    relationship_coherence: SharedSupportState
    relationship_stability: SharedSupportState
    relationship_age_ms: int | None
    directional_hypothesis: SharedDirectionalHypothesis
    continuation_support: SharedSupportState
    reversal_support: SharedSupportState
    failure_hazard: SharedSupportState
    positive_tail_support: SharedSupportState
    systemic_stress: SharedSupportState
    regime_transition_state: SharedRegimeTransitionState
    epistemic_state: SharedEpistemicState
    uncertainty_bps: int
    confidence_bps: int
    confidence_calibration: SharedConfidenceCalibrationState
    calibration_evidence_refs: tuple[str, ...]
    data_quality_bps: int
    data_freshness_ms: int | None
    causal_maturity: str
    supporting_evidence_refs: tuple[str, ...]
    contradicting_evidence_refs: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    observation_horizon: str
    expected_validity_horizon: str
    decay_horizon: str
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    strategy_mutation_authority: bool = False
    broker_mutation_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "snapshot_id",
            "asset",
            "canonical_instrument_id",
            "market_family",
            "trader_horizon",
            "world_state",
            "market_regime",
            "macro_regime",
            "rates_state",
            "usd_state",
            "liquidity_state",
            "volatility_state",
            "commodity_state",
            "agricultural_state",
            "cross_asset_state",
            "causal_maturity",
            "observation_horizon",
            "expected_validity_horizon",
            "decay_horizon",
        ):
            _validate_text(str(getattr(self, name)), field_name=name)
        _validate_timestamp(self.observed_at, field_name="observed_at")
        _validate_timestamp(
            self.evidence_cutoff_at,
            field_name="evidence_cutoff_at",
        )
        if self.evidence_cutoff_at > self.observed_at:
            raise SharedTraderIntelligenceValidationError(
                "future Shared evidence is forbidden"
            )
        if self.relationship_age_ms is not None:
            if self.relationship_age_ms < 0:
                raise SharedTraderIntelligenceValidationError(
                    "relationship_age_ms cannot be negative"
                )
        if self.data_freshness_ms is not None:
            if self.data_freshness_ms < 0:
                raise SharedTraderIntelligenceValidationError(
                    "data_freshness_ms cannot be negative"
                )
        for name in (
            "uncertainty_bps",
            "confidence_bps",
            "data_quality_bps",
        ):
            _validate_bps(int(getattr(self, name)), field_name=name)
        _validate_refs(
            self.supporting_evidence_refs,
            field_name="supporting_evidence_refs",
        )
        _validate_refs(
            self.contradicting_evidence_refs,
            field_name="contradicting_evidence_refs",
            allow_empty=True,
        )
        _validate_refs(
            self.missing_evidence,
            field_name="missing_evidence",
            allow_empty=True,
        )
        _validate_refs(
            self.provenance_refs,
            field_name="provenance_refs",
        )
        _validate_refs(
            self.calibration_evidence_refs,
            field_name="calibration_evidence_refs",
            allow_empty=True,
        )
        if (
            self.confidence_calibration
            is SharedConfidenceCalibrationState.CALIBRATED
            and not self.calibration_evidence_refs
        ):
            raise SharedTraderIntelligenceValidationError(
                "calibrated confidence requires calibration evidence"
            )
        if (
            self.confidence_calibration
            is SharedConfidenceCalibrationState.UNCALIBRATED
            and self.calibration_evidence_refs
        ):
            raise SharedTraderIntelligenceValidationError(
                "uncalibrated confidence cannot carry calibration evidence"
            )
        if (
            self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
            or self.strategy_mutation_authority
            or self.broker_mutation_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Shared snapshot cannot carry sovereign authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["observed_at"] = self.observed_at.astimezone(UTC).isoformat()
        payload["evidence_cutoff_at"] = (
            self.evidence_cutoff_at.astimezone(UTC).isoformat()
        )
        for name in (
            "relationship_coherence",
            "relationship_stability",
            "directional_hypothesis",
            "continuation_support",
            "reversal_support",
            "failure_hazard",
            "positive_tail_support",
            "systemic_stress",
            "regime_transition_state",
            "epistemic_state",
            "confidence_calibration",
        ):
            payload[name] = getattr(self, name).value
        return _fingerprint(payload)


@dataclass(frozen=True, slots=True)
class SharedOpportunityAlert:
    alert_id: str
    hypothesis_id: str
    snapshot_id: str
    asset: str
    canonical_instrument_id: str
    created_at: datetime
    updated_at: datetime
    evidence_cutoff_at: datetime
    lifecycle: SharedAlertLifecycle
    maturity: SharedOpportunityMaturity
    directional_hypothesis: SharedDirectionalHypothesis
    expected_horizon: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    attention_only: bool = True
    creates_trader_setup: bool = False
    execution_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False
    broker_mutation_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "alert_id",
            "hypothesis_id",
            "snapshot_id",
            "asset",
            "canonical_instrument_id",
            "expected_horizon",
        ):
            _validate_text(str(getattr(self, name)), field_name=name)
        for name in ("created_at", "updated_at", "evidence_cutoff_at"):
            _validate_timestamp(getattr(self, name), field_name=name)
        if self.created_at > self.updated_at:
            raise SharedTraderIntelligenceValidationError(
                "opportunity alert updated_at cannot predate created_at"
            )
        if self.evidence_cutoff_at > self.updated_at:
            raise SharedTraderIntelligenceValidationError(
                "opportunity alert cannot use future evidence"
            )
        _validate_refs(self.reason_codes, field_name="reason_codes")
        _validate_refs(self.evidence_refs, field_name="evidence_refs")
        if not self.attention_only or self.creates_trader_setup:
            raise SharedTraderIntelligenceValidationError(
                "Shared opportunity is attention, never a Trader setup"
            )
        if (
            self.execution_authority
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
            or self.broker_mutation_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Shared opportunity cannot carry sovereign authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for name in ("created_at", "updated_at", "evidence_cutoff_at"):
            payload[name] = getattr(self, name).astimezone(UTC).isoformat()
        for name in ("lifecycle", "maturity", "directional_hypothesis"):
            payload[name] = getattr(self, name).value
        return _fingerprint(payload)


@dataclass(frozen=True, slots=True)
class TraderSharedOpportunityAssessment:
    """Trader-owned response to Shared attention; still not an order."""

    alert_id: str
    trader_id: str
    assessed_at: datetime
    disposition: TraderSharedOpportunityDisposition
    methodology_validated: bool
    evidence_refs: tuple[str, ...]
    execution_instruction: bool = False

    def __post_init__(self) -> None:
        _validate_text(self.alert_id, field_name="alert_id")
        _validate_text(self.trader_id, field_name="trader_id")
        _validate_timestamp(self.assessed_at, field_name="assessed_at")
        _validate_refs(self.evidence_refs, field_name="evidence_refs")
        if (
            self.disposition
            is TraderSharedOpportunityDisposition.VALID_TRADE
            and not self.methodology_validated
        ):
            raise SharedTraderIntelligenceValidationError(
                "VALID_TRADE requires Trader methodology validation"
            )
        if (
            self.disposition
            is not TraderSharedOpportunityDisposition.VALID_TRADE
            and self.methodology_validated
        ):
            raise SharedTraderIntelligenceValidationError(
                "WAIT/ABSTAIN cannot claim validated trade"
            )
        if self.execution_instruction:
            raise SharedTraderIntelligenceValidationError(
                "Trader Shared assessment is not an execution instruction"
            )


@dataclass(frozen=True, slots=True)
class SharedPositionObservationSubscription:
    """Read-only Shared observation binding to a Trader-owned position thesis."""

    subscription_id: str
    position_id: str
    trader_id: str
    asset: str
    canonical_instrument_id: str
    side: SharedPositionSide
    opened_at: datetime
    original_shared_snapshot_id: str
    original_world_state: str
    original_regime: str
    original_relationship_state: str
    expected_horizon: str
    relevant_sensors: tuple[str, ...]
    relevant_relationships: tuple[str, ...]
    relevant_factors: tuple[str, ...]
    read_only: bool = True
    position_management_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "subscription_id",
            "position_id",
            "trader_id",
            "asset",
            "canonical_instrument_id",
            "original_shared_snapshot_id",
            "original_world_state",
            "original_regime",
            "original_relationship_state",
            "expected_horizon",
        ):
            _validate_text(str(getattr(self, name)), field_name=name)
        _validate_timestamp(self.opened_at, field_name="opened_at")
        for name in (
            "relevant_sensors",
            "relevant_relationships",
            "relevant_factors",
        ):
            _validate_refs(
                getattr(self, name),
                field_name=name,
                allow_empty=True,
            )
        if not self.read_only:
            raise SharedTraderIntelligenceValidationError(
                "Shared position subscription must be read-only"
            )
        if (
            self.position_management_authority
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Shared position subscription cannot manage the position"
            )


@dataclass(frozen=True, slots=True)
class SharedPositionThesisDelta:
    delta_id: str
    subscription_id: str
    entry_snapshot_id: str
    current_snapshot_id: str
    observed_at: datetime
    evidence_cutoff_at: datetime
    world_state_delta_bps: int
    regime_delta_bps: int
    relationship_delta_bps: int
    continuation_delta_bps: int
    failure_hazard_delta_bps: int
    uncertainty_delta_bps: int
    systemic_stress_delta_bps: int
    threat_level: SharedPositionThreatLevel
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    mandatory_exit: bool = False
    mandatory_stop_change: bool = False
    mandatory_target_change: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "delta_id",
            "subscription_id",
            "entry_snapshot_id",
            "current_snapshot_id",
        ):
            _validate_text(str(getattr(self, name)), field_name=name)
        _validate_timestamp(self.observed_at, field_name="observed_at")
        _validate_timestamp(
            self.evidence_cutoff_at,
            field_name="evidence_cutoff_at",
        )
        if self.evidence_cutoff_at > self.observed_at:
            raise SharedTraderIntelligenceValidationError(
                "position thesis delta cannot use future evidence"
            )
        for name in (
            "world_state_delta_bps",
            "regime_delta_bps",
            "relationship_delta_bps",
            "continuation_delta_bps",
            "failure_hazard_delta_bps",
            "uncertainty_delta_bps",
            "systemic_stress_delta_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not -10_000 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within -10000..10000"
                )
        _validate_refs(self.reason_codes, field_name="reason_codes")
        _validate_refs(self.evidence_refs, field_name="evidence_refs")
        if (
            self.mandatory_exit
            or self.mandatory_stop_change
            or self.mandatory_target_change
            or self.execution_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Shared thesis delta cannot command position management"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["observed_at"] = self.observed_at.astimezone(UTC).isoformat()
        payload["evidence_cutoff_at"] = (
            self.evidence_cutoff_at.astimezone(UTC).isoformat()
        )
        payload["threat_level"] = self.threat_level.value
        return _fingerprint(payload)


@dataclass(frozen=True, slots=True)
class SharedPositionThreatAlert:
    alert_id: str
    hypothesis_id: str
    delta_id: str
    position_id: str
    trader_id: str
    created_at: datetime
    updated_at: datetime
    evidence_cutoff_at: datetime
    lifecycle: SharedAlertLifecycle
    threat_level: SharedPositionThreatLevel
    continuation_support: SharedSupportState
    failure_hazard: SharedSupportState
    uncertainty_bps: int
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    trader_action_required: bool = False
    forced_exit: bool = False
    forced_protection: bool = False
    execution_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "alert_id",
            "hypothesis_id",
            "delta_id",
            "position_id",
            "trader_id",
        ):
            _validate_text(str(getattr(self, name)), field_name=name)
        for name in ("created_at", "updated_at", "evidence_cutoff_at"):
            _validate_timestamp(getattr(self, name), field_name=name)
        if self.created_at > self.updated_at:
            raise SharedTraderIntelligenceValidationError(
                "position alert updated_at cannot predate created_at"
            )
        if self.evidence_cutoff_at > self.updated_at:
            raise SharedTraderIntelligenceValidationError(
                "position alert cannot use future evidence"
            )
        _validate_bps(self.uncertainty_bps, field_name="uncertainty_bps")
        _validate_refs(self.reason_codes, field_name="reason_codes")
        _validate_refs(self.evidence_refs, field_name="evidence_refs")
        if (
            self.trader_action_required
            or self.forced_exit
            or self.forced_protection
            or self.execution_authority
            or self.risk_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Shared position threat is evidence, never an action command"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for name in ("created_at", "updated_at", "evidence_cutoff_at"):
            payload[name] = getattr(self, name).astimezone(UTC).isoformat()
        for name in (
            "lifecycle",
            "threat_level",
            "continuation_support",
            "failure_hazard",
        ):
            payload[name] = getattr(self, name).value
        return _fingerprint(payload)


@dataclass(frozen=True, slots=True)
class SharedTraderCapability:
    trader_id: str
    markets: tuple[str, ...]
    horizons: tuple[str, ...]
    supported_intelligence_classes: tuple[SharedIntelligenceClass, ...]
    open_position_monitoring_capability: bool
    methodology_visible_to_shared: bool = False
    shared_methodology_mutation_authority: bool = False

    def __post_init__(self) -> None:
        _validate_text(self.trader_id, field_name="trader_id")
        for name in ("markets", "horizons"):
            _validate_refs(getattr(self, name), field_name=name)
        if self.supported_intelligence_classes != tuple(
            sorted(
                set(self.supported_intelligence_classes),
                key=lambda item: item.value,
            )
        ):
            raise SharedTraderIntelligenceValidationError(
                "supported intelligence classes must be unique and canonical"
            )
        if (
            self.methodology_visible_to_shared
            or self.shared_methodology_mutation_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Shared routing registry cannot own Trader methodology"
            )


@dataclass(frozen=True, slots=True)
class SharedTraderRelevantProjection:
    projection_id: str
    snapshot_id: str
    trader_id: str
    projected_at: datetime
    evidence_cutoff_at: datetime
    intelligence_classes: tuple[SharedIntelligenceClass, ...]
    relevant_fact_refs: tuple[str, ...]
    omitted_fact_refs: tuple[str, ...]
    global_state_fingerprint: str
    projection_changes_global_truth: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("projection_id", "snapshot_id", "trader_id"):
            _validate_text(str(getattr(self, name)), field_name=name)
        _validate_timestamp(self.projected_at, field_name="projected_at")
        _validate_timestamp(
            self.evidence_cutoff_at,
            field_name="evidence_cutoff_at",
        )
        if self.evidence_cutoff_at > self.projected_at:
            raise SharedTraderIntelligenceValidationError(
                "Trader projection cannot use future evidence"
            )
        if self.intelligence_classes != tuple(
            sorted(
                set(self.intelligence_classes),
                key=lambda item: item.value,
            )
        ):
            raise SharedTraderIntelligenceValidationError(
                "projection intelligence classes must be canonical"
            )
        _validate_refs(
            self.relevant_fact_refs,
            field_name="relevant_fact_refs",
            allow_empty=True,
        )
        _validate_refs(
            self.omitted_fact_refs,
            field_name="omitted_fact_refs",
            allow_empty=True,
        )
        if len(self.global_state_fingerprint) != 64:
            raise SharedTraderIntelligenceValidationError(
                "global_state_fingerprint must be sha256 hex"
            )
        try:
            int(self.global_state_fingerprint, 16)
        except ValueError as exc:
            raise SharedTraderIntelligenceValidationError(
                "global_state_fingerprint must be sha256 hex"
            ) from exc
        if self.projection_changes_global_truth or self.execution_authority:
            raise SharedTraderIntelligenceValidationError(
                "Trader projection cannot mutate global truth or execute"
            )
