from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure import market_data
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.kernel.errors import InfrastructureError


class ReplayAvailabilityError(InfrastructureError):
    """Base error for point-in-time replay availability contracts."""

    __slots__ = ()


class ReplayAvailabilityValidationError(ReplayAvailabilityError):
    """Violation of a point-in-time replay availability invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ReplayAvailabilityValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ReplayAvailabilityValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ReplayObservationId:
    """Explicit identity of one immutable replay observation wrapper."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ReplayAvailabilityValidationError(
                "replay observation id must be a UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ReplayAvailabilityEvidenceReference:
    """Opaque reference to evidence or policy supporting replay availability."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ReplayAvailabilityValidationError(
                "replay availability evidence reference must be a UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class ReplayAvailabilityBasis(StrEnum):
    """Closed provenance class for one replay availability lower bound."""

    STRUCTURAL_BOUNDARY = "structural_boundary"
    PROVIDER_EVIDENCE = "provider_evidence"
    OBSERVED_RECEIPT = "observed_receipt"


type ReplayMarketDataPayload = market_data.QuoteSnapshot | market_data.OhlcSnapshot


def _payload_boundary(payload: ReplayMarketDataPayload) -> datetime:
    if isinstance(payload, market_data.QuoteSnapshot):
        return payload.observed_at
    if isinstance(payload, market_data.OhlcSnapshot):
        return payload.closed_at
    raise ReplayAvailabilityValidationError(
        "replay payload must be QuoteSnapshot or OhlcSnapshot"
    )


@dataclass(frozen=True, slots=True)
class ReplayMarketDataObservation:
    """Immutable market-data evidence with an explicit replay availability gate.

    ``availability_evidence_at`` is the temporal lower bound supported by the
    declared evidence basis. ``available_at`` is the replay visibility time and
    may delay that evidence, but it may never move knowledge earlier.

    ``STRUCTURAL_BOUNDARY`` is intentionally weaker than observed receipt or
    provider evidence. It represents only the earliest structurally valid time
    implied by the canonical payload and must not be described as observed
    historical receipt evidence.
    """

    observation_id: ReplayObservationId
    payload: ReplayMarketDataPayload
    availability_evidence_at: datetime
    available_at: datetime
    availability_basis: ReplayAvailabilityBasis
    availability_evidence_ref: ReplayAvailabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ReplayObservationId):
            raise ReplayAvailabilityValidationError(
                "observation_id must be ReplayObservationId"
            )
        if not isinstance(
            self.payload,
            (market_data.QuoteSnapshot, market_data.OhlcSnapshot),
        ):
            raise ReplayAvailabilityValidationError(
                "payload must be QuoteSnapshot or OhlcSnapshot"
            )
        _validate_timestamp(
            self.availability_evidence_at,
            field_name="availability_evidence_at",
        )
        _validate_timestamp(self.available_at, field_name="available_at")
        if not isinstance(self.availability_basis, ReplayAvailabilityBasis):
            raise ReplayAvailabilityValidationError(
                "availability_basis must be ReplayAvailabilityBasis"
            )
        if not isinstance(
            self.availability_evidence_ref,
            ReplayAvailabilityEvidenceReference,
        ):
            raise ReplayAvailabilityValidationError(
                "availability_evidence_ref must be ReplayAvailabilityEvidenceReference"
            )

        boundary = _payload_boundary(self.payload)
        if self.availability_evidence_at < boundary:
            raise ReplayAvailabilityValidationError(
                "availability evidence cannot predate the canonical payload boundary"
            )
        if (
            self.availability_basis is ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY
            and self.availability_evidence_at != boundary
        ):
            raise ReplayAvailabilityValidationError(
                "structural-boundary evidence must equal the canonical payload boundary"
            )
        if self.available_at < self.availability_evidence_at:
            raise ReplayAvailabilityValidationError(
                "available_at cannot predate availability evidence"
            )

    @property
    def instrument(self) -> market_data.Instrument:
        return self.payload.instrument

    @property
    def source(self) -> ExternalSourceDescriptor:
        return self.payload.source

    @property
    def snapshot_id(self) -> market_data.MarketDataSnapshotId:
        return self.payload.snapshot_id

    @property
    def canonical_boundary(self) -> datetime:
        """Earliest structural timestamp implied by the canonical payload."""

        return _payload_boundary(self.payload)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.payload.logical_values(),
            self.availability_evidence_at.isoformat(),
            self.available_at.isoformat(),
            self.availability_basis.value,
            self.availability_evidence_ref.logical_values(),
        )
