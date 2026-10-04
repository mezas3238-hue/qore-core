"""Authority-free data/provider/identity/market-hours reality checks for Shared Lab."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Iterable


class DataFailure(StrEnum):
    PROVIDER_MISSING = "PROVIDER_MISSING"
    PROVIDER_STALE = "PROVIDER_STALE"
    PROVIDER_CONFLICT = "PROVIDER_CONFLICT"
    CORRUPTED_PAYLOAD = "CORRUPTED_PAYLOAD"
    INCOMPLETE_METADATA = "INCOMPLETE_METADATA"
    WRONG_SYMBOL_METADATA = "WRONG_SYMBOL_METADATA"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    WRONG_ASSET_CLASS = "WRONG_ASSET_CLASS"
    MARKET_CLOSED = "MARKET_CLOSED"
    UNEXPECTED_MARKET_OPEN = "UNEXPECTED_MARKET_OPEN"
    MISSING_OBSERVATION = "MISSING_OBSERVATION"
    DUPLICATE_OBSERVATION = "DUPLICATE_OBSERVATION"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    INVALID_VALUE = "INVALID_VALUE"
    STALE_OBSERVATION = "STALE_OBSERVATION"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    FUTURE_LEAKAGE = "FUTURE_LEAKAGE"


class DegradationClass(StrEnum):
    SAFE_DEGRADATION = "SAFE_DEGRADATION"
    DEGRADED_BUT_USABLE = "DEGRADED_BUT_USABLE"
    CRITICAL_SENSOR_FAILURE = "CRITICAL_SENSOR_FAILURE"
    ABSTENTION_REQUIRED = "ABSTENTION_REQUIRED"


@dataclass(frozen=True, slots=True)
class ProviderProvenance:
    provider: str
    source_id: str
    raw_sha256: str
    decoder_id: str
    mapping_revision: str

    def __post_init__(self) -> None:
        if not all((self.provider, self.source_id, self.decoder_id, self.mapping_revision)):
            raise ValueError("provider lineage fields are required")
        if len(self.raw_sha256) != 64:
            raise ValueError("raw_sha256 must be sha256 hex")


@dataclass(frozen=True, slots=True)
class CanonicalIdentity:
    economic_id: str
    asset_class: str
    base_or_underlying: str
    quote_currency: str | None = None
    venue: str | None = None
    maturity: str | None = None
    contract_month: str | None = None
    multiplier: float | None = None

    def __post_init__(self) -> None:
        if not self.economic_id or not self.asset_class or not self.base_or_underlying:
            raise ValueError("canonical identity is incomplete")
        if self.multiplier is not None and self.multiplier <= 0:
            raise ValueError("multiplier must be positive")


@dataclass(frozen=True, slots=True)
class ProviderDatum:
    datum_id: str
    provider_symbol: str
    provider: str
    sequence: int
    observed_at_ns: int
    available_at_ns: int
    bid: float | None
    ask: float | None
    metadata_asset_class: str
    provenance: ProviderProvenance
    canonical_identity: CanonicalIdentity
    market_open: bool
    session_id: str

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("sequence cannot be negative")
        if self.provider != self.provenance.provider:
            raise ValueError("provider/provenance mismatch")


@dataclass(frozen=True, slots=True)
class DataQualityThresholds:
    min_coverage: float = 0.99
    min_usable_ratio: float = 0.99
    max_duplicate_ratio: float = 0.001
    max_out_of_order_ratio: float = 0.001
    max_stale_ratio: float = 0.001
    max_invalid_ratio: float = 0.001
    max_provider_disagreement_ratio: float = 0.01

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            if not 0 <= value <= 1:
                raise ValueError("quality thresholds must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class DataQualityMetrics:
    expected_observations: int
    received_observations: int
    missing_count: int
    duplicate_count: int
    out_of_order_count: int
    stale_count: int
    invalid_count: int
    provider_disagreement_count: int
    gap_distribution_ns: tuple[int, ...]
    latency_distribution_ns: tuple[int, ...]
    usable_observations: int

    @property
    def coverage(self) -> float:
        return 1.0 if self.expected_observations == 0 else min(1.0, self.received_observations / self.expected_observations)

    @property
    def usable_observation_ratio(self) -> float:
        return 0.0 if self.received_observations == 0 else self.usable_observations / self.received_observations

    def _ratio(self, count: int) -> float:
        return 0.0 if self.received_observations == 0 else count / self.received_observations

    @property
    def duplicate_ratio(self) -> float:
        return self._ratio(self.duplicate_count)

    @property
    def out_of_order_ratio(self) -> float:
        return self._ratio(self.out_of_order_count)

    @property
    def stale_ratio(self) -> float:
        return self._ratio(self.stale_count)

    @property
    def invalid_ratio(self) -> float:
        return self._ratio(self.invalid_count)

    @property
    def provider_disagreement_ratio(self) -> float:
        return self._ratio(self.provider_disagreement_count)

    def passes(self, thresholds: DataQualityThresholds) -> bool:
        return (
            self.coverage >= thresholds.min_coverage
            and self.usable_observation_ratio >= thresholds.min_usable_ratio
            and self.duplicate_ratio <= thresholds.max_duplicate_ratio
            and self.out_of_order_ratio <= thresholds.max_out_of_order_ratio
            and self.stale_ratio <= thresholds.max_stale_ratio
            and self.invalid_ratio <= thresholds.max_invalid_ratio
            and self.provider_disagreement_ratio <= thresholds.max_provider_disagreement_ratio
        )


@dataclass(frozen=True, slots=True)
class DataRealityReceipt:
    datum_id: str
    provider_lineage_valid: bool
    identity_valid: bool
    market_hours_valid: bool
    chronology_valid: bool
    freshness_valid: bool
    quality_valid: bool
    completeness_valid: bool
    failures: tuple[DataFailure, ...]
    parent_fingerprint: str
    output_fingerprint: str

    @property
    def passed(self) -> bool:
        return (
            self.provider_lineage_valid and self.identity_valid and self.market_hours_valid
            and self.chronology_valid and self.freshness_valid and self.quality_valid
            and self.completeness_valid and not self.failures
        )


def normalize_alias(symbol: str) -> str:
    return "".join(ch for ch in symbol.upper() if ch.isalnum())


def resolve_identity(provider_symbol: str, alias_map: dict[str, tuple[CanonicalIdentity, ...]], metadata_asset_class: str) -> tuple[CanonicalIdentity | None, tuple[DataFailure, ...]]:
    key = normalize_alias(provider_symbol)
    matches = alias_map.get(key, ())
    if len(matches) != 1:
        return None, (DataFailure.IDENTITY_AMBIGUOUS,)
    identity = matches[0]
    if identity.asset_class != metadata_asset_class:
        return identity, (DataFailure.WRONG_ASSET_CLASS,)
    return identity, ()


def validate_market_hours(datum: ProviderDatum, expected_open: bool) -> tuple[bool, tuple[DataFailure, ...]]:
    if expected_open and not datum.market_open:
        return False, (DataFailure.MARKET_CLOSED,)
    if not expected_open and datum.market_open:
        return False, (DataFailure.UNEXPECTED_MARKET_OPEN,)
    return True, ()


def validate_values(datum: ProviderDatum) -> tuple[bool, tuple[DataFailure, ...]]:
    values = tuple(v for v in (datum.bid, datum.ask) if v is not None)
    if not values or any((not math.isfinite(v) or v <= 0) for v in values):
        return False, (DataFailure.INVALID_VALUE,)
    if datum.bid is not None and datum.ask is not None and datum.ask < datum.bid:
        return False, (DataFailure.INVALID_VALUE,)
    return True, ()


def fingerprint_datum(datum: ProviderDatum) -> str:
    raw = json.dumps(asdict(datum), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def classify_resilience(required_sensor_count: int, available_required_sensor_count: int, alternative_sensor_count: int, observability_ratio: float) -> DegradationClass:
    if required_sensor_count <= 0:
        raise ValueError("required_sensor_count must be positive")
    if available_required_sensor_count == required_sensor_count:
        return DegradationClass.SAFE_DEGRADATION
    if available_required_sensor_count > 0 and alternative_sensor_count > 0 and observability_ratio >= 0.8:
        return DegradationClass.DEGRADED_BUT_USABLE
    if available_required_sensor_count == 0 and alternative_sensor_count == 0:
        return DegradationClass.ABSTENTION_REQUIRED
    return DegradationClass.CRITICAL_SENSOR_FAILURE


def compute_quality_metrics(observations: Iterable[ProviderDatum], *, expected_observations: int, freshness_limit_ns: int, now_ns: int) -> DataQualityMetrics:
    items = tuple(observations)
    fingerprints: set[str] = set()
    duplicate = out_of_order = stale = invalid = usable = 0
    previous_sequence: int | None = None
    previous_observed: int | None = None
    gaps: list[int] = []
    latencies: list[int] = []
    for datum in items:
        fp = fingerprint_datum(datum)
        if fp in fingerprints:
            duplicate += 1
        fingerprints.add(fp)
        if previous_sequence is not None and datum.sequence <= previous_sequence:
            out_of_order += 1
        if previous_observed is not None:
            gaps.append(datum.observed_at_ns - previous_observed)
        previous_sequence = datum.sequence
        previous_observed = datum.observed_at_ns
        latency = datum.available_at_ns - datum.observed_at_ns
        latencies.append(latency)
        if now_ns - datum.available_at_ns > freshness_limit_ns:
            stale += 1
        valid, _ = validate_values(datum)
        if not valid:
            invalid += 1
        if valid and latency >= 0 and now_ns - datum.available_at_ns <= freshness_limit_ns:
            usable += 1
    return DataQualityMetrics(
        expected_observations=expected_observations,
        received_observations=len(items),
        missing_count=max(0, expected_observations - len(items)),
        duplicate_count=duplicate,
        out_of_order_count=out_of_order,
        stale_count=stale,
        invalid_count=invalid,
        provider_disagreement_count=0,
        gap_distribution_ns=tuple(gaps),
        latency_distribution_ns=tuple(latencies),
        usable_observations=usable,
    )


def provider_disagreement(left: ProviderDatum, right: ProviderDatum, tolerance: float) -> bool:
    if left.canonical_identity.economic_id != right.canonical_identity.economic_id:
        return True
    if left.bid is None or right.bid is None:
        return True
    return abs(left.bid - right.bid) > tolerance
