"""Native Trader Lab QUALIFICATION smoke against SYNTHETIC M1-like carriers.

The candidate fixture remains generic EURUSD; NAS100 quotes below are synthetic
typed carriers only for qualification logic, not VT31's true canonical event
identity, not actual broker bid/ask, not a Trader Lab L3 certification.
"""
from __future__ import annotations

from datetime import UTC, timedelta
from decimal import Decimal
from uuid import UUID

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
from qore.infrastructure.trader_lab.fast_forward import (
    TraderLabFastForwardQualificationId,
    TraderLabFastForwardSchedule,
    TraderLabFastForwardStep,
    qualify_trader_lab_fast_forward,
    reference_trader_lab_fast_forward,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import SessionId
from qore.kernel.result import Failure, Success
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)


def _uid(n: int) -> UUID:
    return UUID(int=n)


def synthetic_carriers():
    bars, _ = short_fixture(session=SessionId.NY_AM, month=1)
    # Only three terminal CLOSED M1 checkpoints; quote values are invented
    # strict TYPE fixtures and never treated as quotes from a broker.
    descriptor = ExternalSourceDescriptor(
        adapter_id=AdapterId(_uid(11)),
        source_id=SourceId(_uid(12)),
        port_name=PortName("market-data.synthetic-vt31-chronology-only"),
    )
    result = []
    for index, candle in enumerate(bars[-3:]):
        received = candle.opened_at + timedelta(seconds=2)
        ingress = received + timedelta(milliseconds=1)
        observation = QualifiedQuoteTickObservation(
            observation_id=MarketObservationId(_uid(600+index)),
            instrument=Instrument("NAS100"),
            source=descriptor,
            observed_at=candle.opened_at,
            bid=MarketPrice(Decimal("100")),
            ask=MarketPrice(Decimal("101")),
            evidence_ref=MarketObservationEvidenceReference(_uid(800+index)),
        )
        result.append(RetainedMarketEventObservation(
            event_id=MarketEventObservationId(_uid(700+index)),
            payload=observation,
            capture_lineage_id=MarketCaptureLineageId(_uid(980)),
            capture_session_id=MarketCaptureSessionId(_uid(981)),
            capture_session_ordinal=MarketCaptureSessionOrdinal(0),
            ingress_sequence=MarketIngressSequence(index),
            boundary_received_at=received,
            core_ingress_at=ingress,
            availability_evidence_at=ingress,
            available_at=candle.closed_at,
            availability_basis=MarketEventAvailabilityBasis.CORE_INGRESS,
            availability_evidence_ref=MarketEventAvailabilityEvidenceReference(
                _uid(900+index)
            ),
        ))
    return tuple(result)


def test_real_trader_lab_fast_forward_contract_accepts_32x_visible_instants(
    candidate_factory,
):
    candidate = candidate_factory()
    events = synthetic_carriers()
    clocks = derive_market_event_availability_instants(events)
    assert len(clocks) == 3
    steps = tuple(
        TraderLabFastForwardStep(
            simulated_now=moment,
            wall_clock_advance=(
                (clocks[i+1]-moment)/32 if i < 2 else timedelta(0)
            ),
        )
        for i, moment in enumerate(clocks)
    )
    native = TraderLabFastForwardSchedule(
        steps=steps, acceleration_factor=32,
    )
    out = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uid(998)),
        candidate=candidate, schedule=native, observations=events,
        certified_at=clocks[-1] + timedelta(minutes=2),
    )
    assert isinstance(out, Success), out
    assert out.value.availability_instants == clocks
    proof = reference_trader_lab_fast_forward(
        candidate, out.value, observations=events,
    )
    assert proof is not None
    # Important: the candidate_factory is EURUSD generic; these 3 NAS100
    # typed quote carriers are synthetic. It is not VT31 L3 nor a real
    # NAS100 BID/ASK event replay.
    assert candidate.version.value == "v1"
    swapped = TraderLabFastForwardSchedule(
        steps=steps[:1]+(TraderLabFastForwardStep(
            simulated_now=clocks[1] + timedelta(seconds=15),
            wall_clock_advance=steps[1].wall_clock_advance,
        ),)+steps[2:],
        acceleration_factor=32,
    )
    failed = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uid(999)),
        candidate=candidate, schedule=swapped, observations=events,
        certified_at=clocks[-1] + timedelta(minutes=2),
    )
    assert isinstance(failed, Failure)
    assert "exact chronological order" in str(failed.error)


def test_synthetic_quote_carriers_not_real_market_or_vt31_candidate():
    events = synthetic_carriers()
    assert len(events) == 3
    assert {e.payload.instrument.value for e in events} == {"NAS100"}
    assert all(e.payload.bid.value == Decimal("100") for e in events)
    assert all(e.payload.ask.value == Decimal("101") for e in events)
    assert all(e.available_at > e.core_ingress_at for e in events)
    assert all(e.payload.source.port_name.value.endswith(
        "synthetic-vt31-chronology-only"
    ) for e in events)
