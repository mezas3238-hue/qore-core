"""End-to-end validated sensor observation pipeline for QORE Shared Lab.

This is scientific infrastructure only. It never grants trading, sizing, risk,
certification, holdout-opening, or productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import (
    CanonicalIdentity,
    DataFailure,
    DataQualityMetrics,
    DataQualityThresholds,
    ProviderDatum,
    fingerprint_datum,
    resolve_identity,
    validate_market_hours,
    validate_values,
)
from qore.infrastructure.core_stack_v2.shared_lab_temporal_harness import assess_temporal


class ContinuityEvent(StrEnum):
    NORMAL = "NORMAL"
    RECONNECT = "RECONNECT"
    DROPPED_EVENT = "DROPPED_EVENT"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    PROVIDER_SWITCH = "PROVIDER_SWITCH"


class ObservationDisposition(StrEnum):
    VALIDATED = "VALIDATED"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True, slots=True)
class SensorObservation:
    sensor_id: str
    datum_id: str
    canonical_economic_id: str
    observed_at_ns: int
    available_at_ns: int
    sensor_output: float
    uncertainty: float
    parent_fingerprint: str

    def __post_init__(self) -> None:
        if not self.sensor_id or not self.canonical_economic_id:
            raise ValueError("sensor identity is required")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("uncertainty must be in [0,1]")


@dataclass(frozen=True, slots=True)
class LabDataReceipt:
    sensor_id: str
    datum_id: str
    provider: str
    canonical_economic_id: str | None
    disposition: ObservationDisposition
    chronology_pass: bool
    provider_lineage_pass: bool
    identity_pass: bool
    market_hours_pass: bool
    freshness_pass: bool
    value_pass: bool
    quality_pass: bool
    completeness_pass: bool
    uncertainty: float
    continuity_event: ContinuityEvent
    failures: tuple[str, ...]
    raw_parent_fingerprint: str
    sensor_output_fingerprint: str | None
    next_consumer_parent_fingerprint: str | None = None
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.productive_authority:
            raise ValueError("Shared Lab data receipt cannot grant productive authority")

    @property
    def lineage_exact_to_next_consumer(self) -> bool:
        return (
            self.sensor_output_fingerprint is not None
            and self.next_consumer_parent_fingerprint == self.sensor_output_fingerprint
        )

    @property
    def passed(self) -> bool:
        return (
            self.disposition is ObservationDisposition.VALIDATED
            and self.chronology_pass
            and self.provider_lineage_pass
            and self.identity_pass
            and self.market_hours_pass
            and self.freshness_pass
            and self.value_pass
            and self.quality_pass
            and self.completeness_pass
            and not self.failures
        )


def fingerprint_sensor_observation(observation: SensorObservation) -> str:
    raw = json.dumps(asdict(observation), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def uncertainty_after_degradation(
    *,
    base_uncertainty: float,
    missing_required_fraction: float,
    provider_conflict: bool,
    stale: bool,
) -> float:
    if not 0 <= base_uncertainty <= 1:
        raise ValueError("base_uncertainty must be in [0,1]")
    if not 0 <= missing_required_fraction <= 1:
        raise ValueError("missing_required_fraction must be in [0,1]")
    penalty = 0.5 * missing_required_fraction
    if provider_conflict:
        penalty += 0.25
    if stale:
        penalty += 0.25
    return min(1.0, base_uncertainty + penalty)


def classify_continuity(sequences: tuple[int, ...], *, reconnected: bool = False, provider_switched: bool = False) -> ContinuityEvent:
    if provider_switched:
        return ContinuityEvent.PROVIDER_SWITCH
    if reconnected:
        return ContinuityEvent.RECONNECT
    if len(sequences) != len(set(sequences)):
        return ContinuityEvent.DUPLICATE_EVENT
    if any(b != a + 1 for a, b in zip(sequences, sequences[1:])):
        return ContinuityEvent.SEQUENCE_GAP
    return ContinuityEvent.NORMAL


def build_validated_sensor_receipt(
    *,
    datum: ProviderDatum,
    sensor_id: str,
    sensor_output: float,
    alias_map: dict[str, tuple[CanonicalIdentity, ...]],
    expected_market_open: bool,
    decision_at_ns: int,
    consumed_at_ns: int,
    now_ns: int,
    freshness_limit_ns: int,
    quality_metrics: DataQualityMetrics,
    quality_thresholds: DataQualityThresholds,
    continuity_event: ContinuityEvent = ContinuityEvent.NORMAL,
    base_uncertainty: float = 0.0,
    missing_required_fraction: float = 0.0,
    provider_conflict: bool = False,
) -> tuple[SensorObservation | None, LabDataReceipt]:
    failures: list[str] = []

    identity, identity_failures = resolve_identity(
        datum.provider_symbol, alias_map, datum.metadata_asset_class
    )
    identity_pass = identity is not None and not identity_failures
    failures.extend(item.value for item in identity_failures)

    market_hours_pass, market_failures = validate_market_hours(datum, expected_market_open)
    failures.extend(item.value for item in market_failures)

    value_pass, value_failures = validate_values(datum)
    failures.extend(item.value for item in value_failures)

    temporal = assess_temporal(
        datum_id=datum.datum_id,
        observed_at_ns=datum.observed_at_ns,
        available_at_ns=datum.available_at_ns,
        decision_at_ns=decision_at_ns,
        consumed_at_ns=consumed_at_ns,
    )
    chronology_pass = temporal.passed
    failures.extend(item.value for item in temporal.failures)

    provider_lineage_pass = (
        datum.provider == datum.provenance.provider
        and len(datum.provenance.raw_sha256) == 64
        and bool(datum.provenance.decoder_id)
        and bool(datum.provenance.mapping_revision)
    )
    if not provider_lineage_pass:
        failures.append("PROVIDER_LINEAGE_INVALID")

    freshness_pass = now_ns - datum.available_at_ns <= freshness_limit_ns
    if not freshness_pass:
        failures.append(DataFailure.STALE_OBSERVATION.value)

    quality_pass = quality_metrics.passes(quality_thresholds)
    completeness_pass = (
        quality_metrics.expected_observations == 0
        or quality_metrics.received_observations >= quality_metrics.expected_observations
    )
    if not quality_pass:
        failures.append("DATA_QUALITY_THRESHOLD_FAIL")
    if not completeness_pass:
        failures.append(DataFailure.MISSING_OBSERVATION.value)

    uncertainty = uncertainty_after_degradation(
        base_uncertainty=base_uncertainty,
        missing_required_fraction=missing_required_fraction,
        provider_conflict=provider_conflict,
        stale=not freshness_pass,
    )

    critical_failure = (
        not chronology_pass
        or not provider_lineage_pass
        or not identity_pass
        or not value_pass
    )
    if critical_failure:
        disposition = ObservationDisposition.BLOCKED
    elif uncertainty >= 1.0:
        disposition = ObservationDisposition.ABSTAIN
    elif not (market_hours_pass and freshness_pass and quality_pass and completeness_pass):
        disposition = ObservationDisposition.DEGRADED
    else:
        disposition = ObservationDisposition.VALIDATED

    observation: SensorObservation | None = None
    output_fingerprint: str | None = None
    if disposition is ObservationDisposition.VALIDATED and identity is not None:
        observation = SensorObservation(
            sensor_id=sensor_id,
            datum_id=datum.datum_id,
            canonical_economic_id=identity.economic_id,
            observed_at_ns=datum.observed_at_ns,
            available_at_ns=datum.available_at_ns,
            sensor_output=sensor_output,
            uncertainty=uncertainty,
            parent_fingerprint=fingerprint_datum(datum),
        )
        output_fingerprint = fingerprint_sensor_observation(observation)

    receipt = LabDataReceipt(
        sensor_id=sensor_id,
        datum_id=datum.datum_id,
        provider=datum.provider,
        canonical_economic_id=None if identity is None else identity.economic_id,
        disposition=disposition,
        chronology_pass=chronology_pass,
        provider_lineage_pass=provider_lineage_pass,
        identity_pass=identity_pass,
        market_hours_pass=market_hours_pass,
        freshness_pass=freshness_pass,
        value_pass=value_pass,
        quality_pass=quality_pass,
        completeness_pass=completeness_pass,
        uncertainty=uncertainty,
        continuity_event=continuity_event,
        failures=tuple(dict.fromkeys(failures)),
        raw_parent_fingerprint=fingerprint_datum(datum),
        sensor_output_fingerprint=output_fingerprint,
    )
    return observation, receipt


def bind_next_consumer(receipt: LabDataReceipt, consumer_parent_fingerprint: str) -> LabDataReceipt:
    """Bind the exact validated sensor output fingerprint to its next lab consumer."""
    if receipt.sensor_output_fingerprint is None:
        raise ValueError("blocked/degraded receipt has no validated sensor output to bind")
    return replace(receipt, next_consumer_parent_fingerprint=consumer_parent_fingerprint)


def deterministic_replay_equal(
    first_observation: SensorObservation | None,
    first_receipt: LabDataReceipt,
    second_observation: SensorObservation | None,
    second_receipt: LabDataReceipt,
) -> bool:
    """Strict replay identity: typed output and full receipt must be byte-stable in meaning."""
    return first_observation == second_observation and first_receipt == second_receipt
