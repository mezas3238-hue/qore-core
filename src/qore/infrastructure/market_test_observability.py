from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_TEXT_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret=",
    "password=",
    "secret=",
    "token=",
)


class MarketTestObservabilityError(ExternalPortError):
    """Base error for MISSION-02 operational observability evidence."""

    __slots__ = ()


class MarketTestObservabilityValidationError(MarketTestObservabilityError):
    """Violation of market-test observability invariants."""

    __slots__ = ()


class MarketTestObservationCategory(StrEnum):
    MARKET_DATA = "market_data"
    DECISION = "decision"
    SUPERVISION = "supervision"
    SAFETY = "safety"
    EXECUTION = "execution"
    RECONCILIATION = "reconciliation"


class MarketTestObservationState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


_REQUIRED_CATEGORIES = tuple(
    sorted(MarketTestObservationCategory, key=lambda category: category.value)
)


def _validate_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise MarketTestObservabilityValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketTestObservabilityValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_public_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MarketTestObservabilityValidationError(
            f"{field_name} must be non-empty"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_TEXT_PARTS):
        raise MarketTestObservabilityValidationError(
            f"{field_name} must not contain sensitive material"
        )


@dataclass(frozen=True, slots=True)
class MarketTestObservation:
    category: MarketTestObservationCategory
    state: MarketTestObservationState
    observed_at: datetime
    message: str
    reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.category, MarketTestObservationCategory):
            raise MarketTestObservabilityValidationError(
                "observation category must be MarketTestObservationCategory"
            )
        if not isinstance(self.state, MarketTestObservationState):
            raise MarketTestObservabilityValidationError(
                "observation state must be MarketTestObservationState"
            )
        _validate_datetime(self.observed_at, field_name="observed_at")
        _validate_public_text(self.message, field_name="observation message")
        if not isinstance(self.reference, str) or fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:-]*", self.reference
        ) is None:
            raise MarketTestObservabilityValidationError(
                "observation reference must be a stable non-secret identifier"
            )
        _validate_public_text(self.reference, field_name="observation reference")

    def logical_values(self) -> tuple[str, str, str, str, str]:
        return (
            self.category.value,
            self.state.value,
            self.observed_at.isoformat(),
            self.message,
            self.reference,
        )


@dataclass(frozen=True, slots=True)
class MarketTestObservabilityEvidence:
    """Complete sanitized evidence bundle for one market-test cycle."""

    observations: tuple[MarketTestObservation, ...]
    evaluated_at: datetime
    state: MarketTestObservationState

    def __post_init__(self) -> None:
        _validate_datetime(self.evaluated_at, field_name="evaluated_at")
        if not isinstance(self.state, MarketTestObservationState):
            raise MarketTestObservabilityValidationError(
                "evidence state must be MarketTestObservationState"
            )
        if not isinstance(self.observations, tuple):
            raise MarketTestObservabilityValidationError(
                "observations must be a tuple"
            )
        categories = tuple(item.category for item in self.observations)
        if categories != _REQUIRED_CATEGORIES:
            raise MarketTestObservabilityValidationError(
                "observability evidence requires every category exactly once in stable order"
            )
        if any(item.observed_at > self.evaluated_at for item in self.observations):
            raise MarketTestObservabilityValidationError(
                "observations must not postdate evidence evaluation"
            )
        expected_state = _aggregate_state(self.observations)
        if self.state is not expected_state:
            raise MarketTestObservabilityValidationError(
                "evidence state must equal deterministic aggregate state"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(item.logical_values() for item in self.observations),
            self.evaluated_at.isoformat(),
            self.state.value,
        )


def _aggregate_state(
    observations: tuple[MarketTestObservation, ...],
) -> MarketTestObservationState:
    states = {item.state for item in observations}
    if MarketTestObservationState.BLOCKED in states:
        return MarketTestObservationState.BLOCKED
    if MarketTestObservationState.DEGRADED in states:
        return MarketTestObservationState.DEGRADED
    return MarketTestObservationState.HEALTHY


def build_market_test_observability_evidence(
    observations: tuple[MarketTestObservation, ...],
    *,
    evaluated_at: datetime,
) -> Result[MarketTestObservabilityEvidence, MarketTestObservabilityError]:
    if not isinstance(observations, tuple):
        return Failure(
            MarketTestObservabilityValidationError(
                "observability evidence requires a tuple of observations"
            )
        )
    if any(not isinstance(item, MarketTestObservation) for item in observations):
        return Failure(
            MarketTestObservabilityValidationError(
                "observability evidence entries must be MarketTestObservation"
            )
        )
    ordered = tuple(sorted(observations, key=lambda item: item.category.value))
    try:
        evidence = MarketTestObservabilityEvidence(
            observations=ordered,
            evaluated_at=evaluated_at,
            state=_aggregate_state(ordered),
        )
    except MarketTestObservabilityError as error:
        return Failure(error)
    return Success(evidence)
