from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_event_replay import (
    MarketCaptureLineageId,
    MarketCaptureSessionId,
    MarketCaptureSessionOrdinal,
    MarketEventAvailabilityBasis,
    MarketEventAvailabilityEvidenceReference,
    MarketEventObservationId,
    MarketIngressSequence,
    RetainedMarketEventObservation,
    derive_market_event_availability_instants,
)
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketPrice,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabValidationError,
)
from qore.infrastructure.trader_lab.fast_forward import (
    TraderLabFastForwardQualification,
    TraderLabFastForwardQualificationId,
    TraderLabFastForwardSchedule,
    TraderLabFastForwardStep,
    compute_trader_lab_fast_forward_fingerprint,
    qualify_trader_lab_fast_forward,
    reference_trader_lab_fast_forward,
)
from qore.infrastructure.trader_lab.stage_evidence import TraderLabEvidenceDigest
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)

_CandidateFactory = Callable[..., TraderLabCandidateBinding]


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(1)),
        source_id=SourceId(_uuid(2)),
        port_name=PortName("market-data.trader-lab-ff"),
    )


def _price(value: str) -> MarketPrice:
    return MarketPrice(Decimal(value))


def _quote(*, observation_id: int, observed_at: datetime) -> QualifiedQuoteTickObservation:
    return QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(_uuid(observation_id)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        observed_at=observed_at,
        bid=_price("1.10000"),
        ask=_price("1.10010"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(observation_id + 1000)),
    )


def _event(
    *,
    event_id: int,
    sequence: int,
    observed_at: datetime,
    available_at: datetime,
) -> RetainedMarketEventObservation:
    received = observed_at + timedelta(seconds=1)
    ingress = received + timedelta(milliseconds=1)
    return RetainedMarketEventObservation(
        event_id=MarketEventObservationId(_uuid(event_id)),
        payload=_quote(observation_id=event_id + 50, observed_at=observed_at),
        capture_lineage_id=MarketCaptureLineageId(_uuid(400)),
        capture_session_id=MarketCaptureSessionId(_uuid(500)),
        capture_session_ordinal=MarketCaptureSessionOrdinal(0),
        ingress_sequence=MarketIngressSequence(sequence),
        boundary_received_at=received,
        core_ingress_at=ingress,
        availability_evidence_at=ingress,
        available_at=available_at,
        availability_basis=MarketEventAvailabilityBasis.CORE_INGRESS,
        availability_evidence_ref=MarketEventAvailabilityEvidenceReference(
            _uuid(event_id + 2000)
        ),
    )


def _observations() -> tuple[RetainedMarketEventObservation, ...]:
    return (
        _event(
            event_id=10,
            sequence=0,
            observed_at=_BASE,
            available_at=_BASE + timedelta(minutes=1),
        ),
        _event(
            event_id=11,
            sequence=1,
            observed_at=_BASE + timedelta(minutes=2),
            available_at=_BASE + timedelta(minutes=3),
        ),
        _event(
            event_id=12,
            sequence=2,
            observed_at=_BASE + timedelta(minutes=4),
            available_at=_BASE + timedelta(minutes=5),
        ),
    )


def _schedule(instants: tuple[datetime, ...], *, factor: int = 2) -> TraderLabFastForwardSchedule:
    base_wall = instants[-1] - instants[0]
    per_step = base_wall // (factor * (len(instants) - 1))
    steps = tuple(
        TraderLabFastForwardStep(
            simulated_now=instants[index],
            wall_clock_advance=(
                per_step if index < len(instants) - 1 else timedelta(0)
            ),
        )
        for index in range(len(instants))
    )
    return TraderLabFastForwardSchedule(steps=steps, acceleration_factor=factor)


def test_fast_forward_qualification_preserves_chronology(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    observations = _observations()
    instants = derive_market_event_availability_instants(observations)
    schedule = _schedule(instants)
    built = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(700)),
        candidate=candidate,
        schedule=schedule,
        observations=observations,
        certified_at=_BASE + timedelta(minutes=10),
    )
    assert isinstance(built, Success)
    assert built.value.availability_instants == instants


def test_identical_inputs_reproduce_identical_qualification(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    observations = _observations()
    instants = derive_market_event_availability_instants(observations)
    schedule = _schedule(instants)
    certified = _BASE + timedelta(minutes=10)
    first = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(701)),
        candidate=candidate,
        schedule=schedule,
        observations=observations,
        certified_at=certified,
    )
    second = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(702)),
        candidate=candidate,
        schedule=schedule,
        observations=observations,
        certified_at=certified,
    )
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.fingerprint == second.value.fingerprint


def test_reordered_chronology_is_rejected(candidate_factory: _CandidateFactory) -> None:
    # A non-ascending schedule cannot even be constructed.
    instants = derive_market_event_availability_instants(_observations())
    reordered = (instants[0], instants[2], instants[1])
    with pytest.raises(TraderLabValidationError):
        _schedule(reordered)

    # A substituted (still-ascending) instant is rejected by the qualification.
    candidate = candidate_factory()
    observations = _observations()
    base_instants = derive_market_event_availability_instants(observations)
    substituted = (
        base_instants[0],
        base_instants[1] + timedelta(seconds=30),
        base_instants[2],
    )
    schedule = _schedule(substituted)
    built = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(703)),
        candidate=candidate,
        schedule=schedule,
        observations=observations,
        certified_at=_BASE + timedelta(minutes=10),
    )
    assert isinstance(built, Failure)
    assert "exact chronological order" in str(built.error)


def test_skipping_an_availability_instant_is_rejected(candidate_factory: _CandidateFactory) -> None:
    candidate = candidate_factory()
    observations = _observations()
    instants = derive_market_event_availability_instants(observations)
    schedule = _schedule((instants[0], instants[2]))
    built = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(704)),
        candidate=candidate,
        schedule=schedule,
        observations=observations,
        certified_at=_BASE + timedelta(minutes=10),
    )
    assert isinstance(built, Failure)
    assert "exact chronological order" in str(built.error)


def test_wrong_acceleration_factor_is_rejected(candidate_factory: _CandidateFactory) -> None:
    candidate = candidate_factory()
    observations = _observations()
    instants = derive_market_event_availability_instants(observations)
    schedule = _schedule(instants, factor=2)
    mismatched = TraderLabFastForwardSchedule(
        steps=schedule.steps,
        acceleration_factor=3,
    )
    built = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(705)),
        candidate=candidate,
        schedule=mismatched,
        observations=observations,
        certified_at=_BASE + timedelta(minutes=10),
    )
    assert isinstance(built, Failure)
    assert "exactly the acceleration factor" in str(built.error)


def test_schedule_rejects_non_acceleration_and_bool_factor() -> None:
    instants = derive_market_event_availability_instants(_observations())
    schedule = _schedule(instants)
    with pytest.raises(TraderLabValidationError):
        TraderLabFastForwardSchedule(
            steps=schedule.steps,
            acceleration_factor=1,
        )
    bad_factor: Any = True
    with pytest.raises(TraderLabValidationError):
        TraderLabFastForwardSchedule(
            steps=schedule.steps,
            acceleration_factor=bad_factor,
        )


def test_single_availability_instant_cannot_qualify(candidate_factory: _CandidateFactory) -> None:
    candidate = candidate_factory()
    single = (_observations()[0],)
    instants = derive_market_event_availability_instants(single)
    assert len(instants) == 1
    # The insufficient-instant guard fires before any schedule-content check.
    fake_schedule = _schedule((_BASE, _BASE + timedelta(minutes=2)))
    built = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(706)),
        candidate=candidate,
        schedule=fake_schedule,
        observations=single,
        certified_at=_BASE + timedelta(minutes=10),
    )
    assert isinstance(built, Failure)
    assert "insufficient availability instants" in str(built.error)

def test_external_r2_public_constructor_cannot_bypass_reference_revalidation(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    observations = _observations()
    real_instants = derive_market_event_availability_instants(observations)
    forged_instants = (
        real_instants[0],
        real_instants[1] + timedelta(seconds=30),
        real_instants[2],
    )
    forged_schedule = _schedule(forged_instants)
    forged_digest = TraderLabEvidenceDigest("a" * 64)
    certified_at = _BASE + timedelta(minutes=10)
    fingerprint = compute_trader_lab_fast_forward_fingerprint(
        candidate=candidate,
        schedule=forged_schedule,
        observations_digest=forged_digest,
        availability_instants=forged_instants,
        certified_at=certified_at,
    )
    forged = TraderLabFastForwardQualification(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(799)),
        candidate=candidate,
        schedule=forged_schedule,
        observations_digest=forged_digest,
        availability_instants=forged_instants,
        certified_at=certified_at,
        fingerprint=fingerprint,
    )
    with pytest.raises(
        TraderLabValidationError,
        match="does not match the exact replay chronology",
    ):
        reference_trader_lab_fast_forward(
            candidate, forged, observations=observations
        )


def test_fast_forward_reference_revalidates_legitimate_qualification(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    observations = _observations()
    instants = derive_market_event_availability_instants(observations)
    built = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(798)),
        candidate=candidate,
        schedule=_schedule(instants),
        observations=observations,
        certified_at=_BASE + timedelta(minutes=10),
    )
    assert isinstance(built, Success)
    reference = reference_trader_lab_fast_forward(
        candidate, built.value, observations=observations
    )
    assert reference.kind.value == "trader_lab.fast_forward"
