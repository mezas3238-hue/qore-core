"""CIBO Market Atlas Journey Layer V1 contracts.

Research-only schemas for reconstructing the complete price journey around a
market departure. These contracts do not classify a setup as tradable and do
not grant any execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
SCHEMA = "qore.cibo_market_atlas.journey.v1"

PROVIDER_INDEX_MAP = {
    "NAS100": "USTEC",
    "SP500": "US500",
    "US30": "US30",
}

REQUIRED_LEDGERS = (
    "MARKET_JOURNEY_LEDGER",
    "STRUCTURE_TOUCH_LEDGER",
    "PRE_DEPARTURE_SEQUENCE_LEDGER",
    "DEPARTURE_TIMING_LEDGER",
    "TARGET_DESTINATION_LEDGER",
    "CROSS_INDEX_JOURNEY_LEDGER",
    "DAILY_PATH_LEDGER",
    "TRADER_MARKET_SYNC_LEDGER",
)


class EvidenceRole(StrEnum):
    """Whether a field is legal for causal state or only post-outcome research."""

    CAUSAL_FEATURE = "CAUSAL_FEATURE"
    OUTCOME_ONLY = "OUTCOME_ONLY"


class StructureType(StrEnum):
    """Versioned structure families admitted by the journey contract."""

    LIQUIDITY_RAID = "LIQUIDITY_RAID"
    PRIOR_HIGH_LOW = "PRIOR_HIGH_LOW"
    SWING_HIGH_LOW = "SWING_HIGH_LOW"
    EQUAL_HIGH_LOW = "EQUAL_HIGH_LOW"
    STACKED_LIQUIDITY = "STACKED_LIQUIDITY"
    ORDER_BLOCK = "ORDER_BLOCK"
    BREAKER_BLOCK = "BREAKER_BLOCK"
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"
    DISPLACEMENT_ORIGIN = "DISPLACEMENT_ORIGIN"
    PROTECTED_SWING = "PROTECTED_SWING"
    CISD_STRUCTURE = "CISD_STRUCTURE"
    SESSION_HIGH_LOW = "SESSION_HIGH_LOW"
    DAILY_WEEKLY_BOUNDARY = "DAILY_WEEKLY_BOUNDARY"
    COMPRESSION_RANGE = "COMPRESSION_RANGE"
    EXPANSION_REJECTION_ZONE = "EXPANSION_REJECTION_ZONE"
    UNRESOLVED_STRUCTURE = "UNRESOLVED_STRUCTURE"


class JourneyState(StrEnum):
    """Descriptive states; never automatic trading rules."""

    ACCUMULATION = "ACCUMULATION"
    COMPRESSION = "COMPRESSION"
    OVERLAP = "OVERLAP"
    RAIDING_BOTH_SIDES = "RAIDING_BOTH_SIDES"
    REJECTION = "REJECTION"
    ACCEPTANCE = "ACCEPTANCE"
    EXPANSION = "EXPANSION"
    TRANSITION = "TRANSITION"
    UNRESOLVED = "UNRESOLVED"


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _require_non_negative(value: Decimal | int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True, slots=True)
class StructureTouch:
    """One exact structure visit before or at a frozen departure boundary."""

    episode_id: str
    event_id: str
    symbol: str
    structure_type: StructureType
    detector_version: str
    source_timeframe: str
    created_at: datetime
    first_touch_at: datetime
    last_touch_at: datetime
    price_low: Decimal
    price_high: Decimal
    distance_from_source_ticks: Decimal
    distance_from_opposite_ticks: Decimal
    penetration_ticks: Decimal
    dwell_minutes: int
    revisit_count: int
    last_before_departure: bool
    evidence_role: EvidenceRole = EvidenceRole.CAUSAL_FEATURE

    def __post_init__(self) -> None:
        if not self.episode_id or not self.event_id or not self.symbol:
            raise ValueError("episode_id, event_id and symbol must be non-empty")
        if not self.detector_version or not self.source_timeframe:
            raise ValueError("detector_version and source_timeframe must be non-empty")
        for timestamp, timestamp_name in (
            (self.created_at, "created_at"),
            (self.first_touch_at, "first_touch_at"),
            (self.last_touch_at, "last_touch_at"),
        ):
            _require_aware(timestamp, timestamp_name)
        if not self.created_at <= self.first_touch_at <= self.last_touch_at:
            raise ValueError("structure chronology must be created <= first_touch <= last_touch")
        if self.price_low > self.price_high:
            raise ValueError("price_low must be <= price_high")
        for metric, metric_name in (
            (self.distance_from_source_ticks, "distance_from_source_ticks"),
            (self.distance_from_opposite_ticks, "distance_from_opposite_ticks"),
            (self.penetration_ticks, "penetration_ticks"),
            (self.dwell_minutes, "dwell_minutes"),
            (self.revisit_count, "revisit_count"),
        ):
            _require_non_negative(metric, metric_name)
        if self.evidence_role is not EvidenceRole.CAUSAL_FEATURE:
            raise ValueError("pre-departure structure touches must be causal features")


@dataclass(frozen=True, slots=True)
class DepartureTiming:
    """Clock relationship between the last structure touch and true departure."""

    episode_id: str
    symbol: str
    source_event_at: datetime
    final_structure_at: datetime
    departure_at: datetime
    structure_to_departure_minutes: int
    source_to_departure_minutes: int
    ny_minute_of_day: int
    weekday: int
    evidence_role: EvidenceRole = EvidenceRole.CAUSAL_FEATURE

    def __post_init__(self) -> None:
        for value, name in (
            (self.source_event_at, "source_event_at"),
            (self.final_structure_at, "final_structure_at"),
            (self.departure_at, "departure_at"),
        ):
            _require_aware(value, name)
        if not self.source_event_at <= self.final_structure_at <= self.departure_at:
            raise ValueError("departure chronology is invalid")
        _require_non_negative(
            self.structure_to_departure_minutes,
            "structure_to_departure_minutes",
        )
        _require_non_negative(self.source_to_departure_minutes, "source_to_departure_minutes")
        if not 0 <= self.ny_minute_of_day < 24 * 60:
            raise ValueError("ny_minute_of_day must be within one day")
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be 0..6")
        if self.evidence_role is not EvidenceRole.CAUSAL_FEATURE:
            raise ValueError("departure timing must be causal")


@dataclass(frozen=True, slots=True)
class TargetCandidate:
    """Objective that was knowable at departure time."""

    episode_id: str
    candidate_id: str
    objective_type: str
    price: Decimal
    distance_ticks: Decimal
    detector_version: str
    evidence_role: EvidenceRole = EvidenceRole.CAUSAL_FEATURE

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.objective_type or not self.detector_version:
            raise ValueError("target candidate identity fields must be non-empty")
        _require_non_negative(self.distance_ticks, "distance_ticks")
        if self.evidence_role is not EvidenceRole.CAUSAL_FEATURE:
            raise ValueError("target candidates known at departure must be causal")


@dataclass(frozen=True, slots=True)
class TargetOutcome:
    """Post-departure destination evidence; illegal for causal classification."""

    episode_id: str
    candidate_id: str
    reached: bool
    reached_at: datetime | None
    minutes_to_reach: int | None
    extension_beyond_ticks: Decimal
    path_drawdown_ticks: Decimal
    evidence_role: EvidenceRole = EvidenceRole.OUTCOME_ONLY

    def __post_init__(self) -> None:
        if self.reached_at is not None:
            _require_aware(self.reached_at, "reached_at")
        if self.reached and self.reached_at is None:
            raise ValueError("reached targets require reached_at")
        if not self.reached and self.reached_at is not None:
            raise ValueError("unreached targets cannot have reached_at")
        if self.minutes_to_reach is not None:
            _require_non_negative(self.minutes_to_reach, "minutes_to_reach")
        _require_non_negative(self.extension_beyond_ticks, "extension_beyond_ticks")
        _require_non_negative(self.path_drawdown_ticks, "path_drawdown_ticks")
        if self.evidence_role is not EvidenceRole.OUTCOME_ONLY:
            raise ValueError("target outcomes must remain outcome-only")


@dataclass(frozen=True, slots=True)
class CrossIndexJourney:
    """Synchronized descriptive state across the three frozen US indices."""

    episode_id: str
    observed_at: datetime
    nas100_state: str
    sp500_state: str
    us30_state: str
    lead_symbol: str | None
    lag_symbol: str | None
    lead_lag_minutes: int | None
    agreement: bool
    divergence: bool
    evidence_role: EvidenceRole

    def __post_init__(self) -> None:
        _require_aware(self.observed_at, "observed_at")
        if self.lead_lag_minutes is not None:
            _require_non_negative(self.lead_lag_minutes, "lead_lag_minutes")
        admitted = set(PROVIDER_INDEX_MAP)
        if self.lead_symbol is not None and self.lead_symbol not in admitted:
            raise ValueError("lead_symbol must be a canonical frozen index")
        if self.lag_symbol is not None and self.lag_symbol not in admitted:
            raise ValueError("lag_symbol must be a canonical frozen index")
        if self.agreement and self.divergence:
            raise ValueError("agreement and divergence cannot both be true")


def assert_no_outcome_leakage(roles: tuple[EvidenceRole, ...]) -> None:
    """Fail closed if an outcome-only field is supplied to a causal feature set."""

    if EvidenceRole.OUTCOME_ONLY in roles:
        raise ValueError("OUTCOME_ONLY evidence cannot enter causal feature classification")
