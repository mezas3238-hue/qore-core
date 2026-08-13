from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import (
    InstrumentMarketSpecification,
    QualifiedOhlcBarObservation,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.kernel.errors import InfrastructureError


class MarketEventReplayError(InfrastructureError):
    """Base error for deterministic mixed market-event replay evidence."""

    __slots__ = ()


class MarketEventReplayValidationError(MarketEventReplayError):
    """Violation of a mixed market-event chronology invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise MarketEventReplayValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketEventReplayValidationError(
            f"{field_name} must be timezone-aware"
        )


def _canonical_timestamp(value: datetime, *, field_name: str) -> str:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True, slots=True)
class MarketEventObservationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise MarketEventReplayValidationError(
                "market event observation id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketCaptureLineageId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise MarketEventReplayValidationError(
                "market capture lineage id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketCaptureSessionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise MarketEventReplayValidationError(
                "market capture session id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketCaptureSessionOrdinal:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 0:
            raise MarketEventReplayValidationError(
                "market capture session ordinal must be a non-negative int"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class MarketIngressSequence:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 0:
            raise MarketEventReplayValidationError(
                "market ingress sequence must be a non-negative int"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class MarketEventAvailabilityEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise MarketEventReplayValidationError(
                "market event availability evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class MarketEventAvailabilityBasis(StrEnum):
    """Closed evidence class supporting one replay visibility lower bound."""

    PROVIDER_EVIDENCE = "provider_evidence"
    OBSERVED_RECEIPT = "observed_receipt"
    CORE_INGRESS = "core_ingress"


type MarketEventPayload = (
    QualifiedOhlcBarObservation
    | QualifiedQuoteTickObservation
    | InstrumentMarketSpecification
)


def _payload_boundary(payload: MarketEventPayload) -> datetime:
    if isinstance(payload, QualifiedOhlcBarObservation):
        return payload.closed_at
    if isinstance(payload, QualifiedQuoteTickObservation):
        return payload.observed_at
    if isinstance(payload, InstrumentMarketSpecification):
        return payload.effective_at
    raise MarketEventReplayValidationError(
        "market event payload must be OHLC, quote, or instrument specification"
    )


def _payload_kind(payload: MarketEventPayload) -> str:
    if isinstance(payload, QualifiedOhlcBarObservation):
        return "ohlc"
    if isinstance(payload, QualifiedQuoteTickObservation):
        return "quote"
    if isinstance(payload, InstrumentMarketSpecification):
        return "instrument_specification"
    raise MarketEventReplayValidationError(
        "market event payload must be OHLC, quote, or instrument specification"
    )


@dataclass(frozen=True, slots=True)
class RetainedMarketEventObservation:
    """One captured market event with explicit arrival and replay provenance."""

    event_id: MarketEventObservationId
    payload: MarketEventPayload
    capture_lineage_id: MarketCaptureLineageId
    capture_session_id: MarketCaptureSessionId
    capture_session_ordinal: MarketCaptureSessionOrdinal
    ingress_sequence: MarketIngressSequence
    boundary_received_at: datetime
    core_ingress_at: datetime
    availability_evidence_at: datetime
    available_at: datetime
    availability_basis: MarketEventAvailabilityBasis
    availability_evidence_ref: MarketEventAvailabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, MarketEventObservationId):
            raise MarketEventReplayValidationError(
                "market event event_id must be MarketEventObservationId"
            )
        if not isinstance(
            self.payload,
            (
                QualifiedOhlcBarObservation,
                QualifiedQuoteTickObservation,
                InstrumentMarketSpecification,
            ),
        ):
            raise MarketEventReplayValidationError(
                "market event payload must be retained market evidence v2"
            )
        if not isinstance(self.capture_lineage_id, MarketCaptureLineageId):
            raise MarketEventReplayValidationError(
                "capture_lineage_id must be MarketCaptureLineageId"
            )
        if not isinstance(self.capture_session_id, MarketCaptureSessionId):
            raise MarketEventReplayValidationError(
                "capture_session_id must be MarketCaptureSessionId"
            )
        if not isinstance(
            self.capture_session_ordinal,
            MarketCaptureSessionOrdinal,
        ):
            raise MarketEventReplayValidationError(
                "capture_session_ordinal must be MarketCaptureSessionOrdinal"
            )
        if not isinstance(self.ingress_sequence, MarketIngressSequence):
            raise MarketEventReplayValidationError(
                "ingress_sequence must be MarketIngressSequence"
            )
        _validate_timestamp(
            self.boundary_received_at,
            field_name="market event boundary_received_at",
        )
        _validate_timestamp(
            self.core_ingress_at,
            field_name="market event core_ingress_at",
        )
        _validate_timestamp(
            self.availability_evidence_at,
            field_name="market event availability_evidence_at",
        )
        _validate_timestamp(
            self.available_at,
            field_name="market event available_at",
        )
        if not isinstance(self.availability_basis, MarketEventAvailabilityBasis):
            raise MarketEventReplayValidationError(
                "availability_basis must be MarketEventAvailabilityBasis"
            )
        if not isinstance(
            self.availability_evidence_ref,
            MarketEventAvailabilityEvidenceReference,
        ):
            raise MarketEventReplayValidationError(
                "availability_evidence_ref must be "
                "MarketEventAvailabilityEvidenceReference"
            )

        boundary = _payload_boundary(self.payload)
        if self.boundary_received_at < boundary:
            raise MarketEventReplayValidationError(
                "market event receipt cannot predate payload boundary"
            )
        if self.core_ingress_at < self.boundary_received_at:
            raise MarketEventReplayValidationError(
                "market event core ingress cannot predate boundary receipt"
            )
        if self.availability_evidence_at < boundary:
            raise MarketEventReplayValidationError(
                "availability evidence cannot predate payload boundary"
            )
        if (
            self.availability_basis
            is MarketEventAvailabilityBasis.OBSERVED_RECEIPT
            and self.availability_evidence_at != self.boundary_received_at
        ):
            raise MarketEventReplayValidationError(
                "observed-receipt basis must equal boundary_received_at"
            )
        if (
            self.availability_basis is MarketEventAvailabilityBasis.CORE_INGRESS
            and self.availability_evidence_at != self.core_ingress_at
        ):
            raise MarketEventReplayValidationError(
                "core-ingress basis must equal core_ingress_at"
            )
        if self.available_at < self.availability_evidence_at:
            raise MarketEventReplayValidationError(
                "available_at cannot predate availability evidence"
            )
        if self.available_at < self.core_ingress_at:
            raise MarketEventReplayValidationError(
                "available_at cannot predate core ingress"
            )

    @property
    def canonical_boundary(self) -> datetime:
        return _payload_boundary(self.payload)

    @property
    def instrument(self) -> Instrument:
        return self.payload.instrument

    @property
    def source(self) -> ExternalSourceDescriptor:
        return self.payload.source

    @property
    def payload_kind(self) -> str:
        return _payload_kind(self.payload)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.event_id.logical_values(),
            self.payload_kind,
            self.payload.logical_values(),
            self.capture_lineage_id.logical_values(),
            self.capture_session_id.logical_values(),
            self.capture_session_ordinal.logical_values(),
            self.ingress_sequence.logical_values(),
            _canonical_timestamp(
                self.boundary_received_at,
                field_name="market event boundary_received_at",
            ),
            _canonical_timestamp(
                self.core_ingress_at,
                field_name="market event core_ingress_at",
            ),
            _canonical_timestamp(
                self.availability_evidence_at,
                field_name="market event availability_evidence_at",
            ),
            _canonical_timestamp(
                self.available_at,
                field_name="market event available_at",
            ),
            self.availability_basis.value,
            self.availability_evidence_ref.logical_values(),
        )


type MarketEventArrivalOrderKey = tuple[int, int]


def market_event_arrival_order_key(
    observation: RetainedMarketEventObservation,
) -> MarketEventArrivalOrderKey:
    """Return true retained arrival provenance, never UUID-derived ordering."""

    if not isinstance(observation, RetainedMarketEventObservation):
        raise MarketEventReplayValidationError(
            "ordered market event must be RetainedMarketEventObservation"
        )
    return (
        observation.capture_session_ordinal.value,
        observation.ingress_sequence.value,
    )


def _validate_arrival_provenance(
    observations: tuple[RetainedMarketEventObservation, ...],
) -> tuple[RetainedMarketEventObservation, ...]:
    if not isinstance(observations, tuple) or any(
        not isinstance(item, RetainedMarketEventObservation)
        for item in observations
    ):
        raise MarketEventReplayValidationError(
            "market events must be an immutable retained-event tuple"
        )
    if not observations:
        return ()

    event_ids = tuple(item.event_id for item in observations)
    if len(set(event_ids)) != len(event_ids):
        raise MarketEventReplayValidationError(
            "market event wrapper identities must be unique"
        )

    lineage = observations[0].capture_lineage_id
    if any(item.capture_lineage_id != lineage for item in observations):
        raise MarketEventReplayValidationError(
            "market event ordering requires one capture lineage"
        )

    session_to_ordinal: dict[MarketCaptureSessionId, MarketCaptureSessionOrdinal] = {}
    ordinal_to_session: dict[MarketCaptureSessionOrdinal, MarketCaptureSessionId] = {}
    arrival_keys: set[MarketEventArrivalOrderKey] = set()
    for item in observations:
        existing_ordinal = session_to_ordinal.get(item.capture_session_id)
        if (
            existing_ordinal is not None
            and existing_ordinal != item.capture_session_ordinal
        ):
            raise MarketEventReplayValidationError(
                "capture session must retain one session ordinal"
            )
        existing_session = ordinal_to_session.get(item.capture_session_ordinal)
        if (
            existing_session is not None
            and existing_session != item.capture_session_id
        ):
            raise MarketEventReplayValidationError(
                "capture session ordinal must identify one capture session"
            )
        session_to_ordinal[item.capture_session_id] = item.capture_session_ordinal
        ordinal_to_session[item.capture_session_ordinal] = item.capture_session_id

        key = market_event_arrival_order_key(item)
        if key in arrival_keys:
            raise MarketEventReplayValidationError(
                "capture arrival provenance must be unique"
            )
        arrival_keys.add(key)

    ordered = tuple(sorted(observations, key=market_event_arrival_order_key))
    previous = ordered[0]
    for current in ordered[1:]:
        if current.boundary_received_at < previous.boundary_received_at:
            raise MarketEventReplayValidationError(
                "arrival provenance contradicts boundary receipt chronology"
            )
        if current.core_ingress_at < previous.core_ingress_at:
            raise MarketEventReplayValidationError(
                "arrival provenance contradicts core ingress chronology"
            )
        previous = current
    return ordered


def order_market_event_observations(
    observations: tuple[RetainedMarketEventObservation, ...],
) -> tuple[RetainedMarketEventObservation, ...]:
    """Canonicalize mixed observations by explicit arrival provenance."""

    return _validate_arrival_provenance(observations)


def visible_market_event_observations(
    observations: tuple[RetainedMarketEventObservation, ...],
    *,
    simulated_now: datetime,
) -> tuple[RetainedMarketEventObservation, ...]:
    """Return observations visible inclusively, retaining arrival ordering."""

    _validate_timestamp(simulated_now, field_name="market event simulated_now")
    ordered = order_market_event_observations(observations)
    return tuple(item for item in ordered if item.available_at <= simulated_now)


def derive_market_event_availability_instants(
    observations: tuple[RetainedMarketEventObservation, ...],
) -> tuple[datetime, ...]:
    """Return sorted distinct replay data-availability instants for Schedule B."""

    ordered = order_market_event_observations(observations)
    return tuple(sorted({item.available_at for item in ordered}))
