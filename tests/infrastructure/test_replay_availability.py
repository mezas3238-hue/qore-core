from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    QuoteSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayAvailabilityValidationError,
    ReplayMarketDataObservation,
    ReplayObservationId,
)

_BASE = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("62000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("62000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.replay-test"),
)
_INSTRUMENT = Instrument("EURUSD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"62000000-0000-0000-0000-{suffix:012d}")


def _quote(*, observed_at: datetime = _BASE) -> QuoteSnapshot:
    return QuoteSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(10)),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        observed_at=observed_at,
        bid=1.16,
        ask=1.1602,
    )


def _bar(*, opened_at: datetime = _BASE) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(11)),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        timeframe=Timeframe(900),
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=15),
        open=1.155,
        high=1.165,
        low=1.15,
        close=1.16,
    )


def _evidence_ref(suffix: int = 20) -> ReplayAvailabilityEvidenceReference:
    return ReplayAvailabilityEvidenceReference(_uuid(suffix))


def test_structural_quote_availability_binds_exact_observed_boundary() -> None:
    quote = _quote()
    observation = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(30)),
        payload=quote,
        availability_evidence_at=quote.observed_at,
        available_at=quote.observed_at + timedelta(milliseconds=250),
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=_evidence_ref(),
    )

    assert observation.canonical_boundary == quote.observed_at
    assert observation.snapshot_id == quote.snapshot_id
    assert observation.instrument == quote.instrument
    assert observation.source == quote.source
    assert observation.available_at > observation.availability_evidence_at


def test_structural_bar_availability_binds_exact_close_boundary() -> None:
    bar = _bar()
    observation = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(31)),
        payload=bar,
        availability_evidence_at=bar.closed_at,
        available_at=bar.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=_evidence_ref(21),
    )

    assert observation.canonical_boundary == bar.closed_at
    assert observation.availability_evidence_at == bar.closed_at
    assert observation.available_at == bar.closed_at


def test_observed_receipt_may_delay_availability_but_never_backdate_it() -> None:
    bar = _bar()
    receipt = bar.closed_at + timedelta(seconds=2)
    observation = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(32)),
        payload=bar,
        availability_evidence_at=receipt,
        available_at=receipt + timedelta(seconds=3),
        availability_basis=ReplayAvailabilityBasis.OBSERVED_RECEIPT,
        availability_evidence_ref=_evidence_ref(22),
    )

    assert observation.available_at == bar.closed_at + timedelta(seconds=5)

    with pytest.raises(
        ReplayAvailabilityValidationError,
        match="available_at cannot predate availability evidence",
    ):
        ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_uuid(33)),
            payload=bar,
            availability_evidence_at=receipt,
            available_at=receipt - timedelta(microseconds=1),
            availability_basis=ReplayAvailabilityBasis.OBSERVED_RECEIPT,
            availability_evidence_ref=_evidence_ref(23),
        )


def test_availability_evidence_cannot_predate_payload_boundary() -> None:
    quote = _quote()
    with pytest.raises(
        ReplayAvailabilityValidationError,
        match="cannot predate the canonical payload boundary",
    ):
        ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_uuid(34)),
            payload=quote,
            availability_evidence_at=quote.observed_at - timedelta(microseconds=1),
            available_at=quote.observed_at,
            availability_basis=ReplayAvailabilityBasis.PROVIDER_EVIDENCE,
            availability_evidence_ref=_evidence_ref(24),
        )


def test_structural_basis_cannot_claim_later_evidence_timestamp() -> None:
    bar = _bar()
    with pytest.raises(
        ReplayAvailabilityValidationError,
        match="must equal the canonical payload boundary",
    ):
        ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_uuid(35)),
            payload=bar,
            availability_evidence_at=bar.closed_at + timedelta(seconds=1),
            available_at=bar.closed_at + timedelta(seconds=1),
            availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
            availability_evidence_ref=_evidence_ref(25),
        )


def test_replay_availability_rejects_naive_timestamps() -> None:
    bar = _bar()
    naive = datetime(2026, 8, 9, 12, 15)

    with pytest.raises(ReplayAvailabilityValidationError, match="timezone-aware"):
        ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_uuid(36)),
            payload=bar,
            availability_evidence_at=cast(datetime, naive),
            available_at=bar.closed_at,
            availability_basis=ReplayAvailabilityBasis.OBSERVED_RECEIPT,
            availability_evidence_ref=_evidence_ref(26),
        )

    with pytest.raises(ReplayAvailabilityValidationError, match="timezone-aware"):
        ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_uuid(37)),
            payload=bar,
            availability_evidence_at=bar.closed_at,
            available_at=cast(datetime, naive),
            availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
            availability_evidence_ref=_evidence_ref(27),
        )


def test_non_utc_timezone_aware_availability_is_valid_and_preserved() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    opened_at = datetime(2026, 8, 9, 17, 30, tzinfo=offset)
    bar = _bar(opened_at=opened_at)
    observation = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(38)),
        payload=bar,
        availability_evidence_at=bar.closed_at,
        available_at=bar.closed_at + timedelta(seconds=1),
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=_evidence_ref(28),
    )

    assert observation.available_at.isoformat().endswith("+05:30")
    assert observation.logical_values()[3] == observation.available_at.isoformat()


def test_replay_observation_rejects_runtime_type_bypasses() -> None:
    quote = _quote()

    with pytest.raises(ReplayAvailabilityValidationError, match="observation_id"):
        ReplayMarketDataObservation(
            observation_id=cast(ReplayObservationId, object()),
            payload=quote,
            availability_evidence_at=quote.observed_at,
            available_at=quote.observed_at,
            availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
            availability_evidence_ref=_evidence_ref(29),
        )

    with pytest.raises(ReplayAvailabilityValidationError, match="payload"):
        ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_uuid(39)),
            payload=cast(QuoteSnapshot, object()),
            availability_evidence_at=quote.observed_at,
            available_at=quote.observed_at,
            availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
            availability_evidence_ref=_evidence_ref(30),
        )

    with pytest.raises(ReplayAvailabilityValidationError, match="availability_basis"):
        ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_uuid(40)),
            payload=quote,
            availability_evidence_at=quote.observed_at,
            available_at=quote.observed_at,
            availability_basis=cast(ReplayAvailabilityBasis, "observed_receipt"),
            availability_evidence_ref=_evidence_ref(31),
        )


def test_replay_availability_contract_has_no_clock_visibility_or_trading_authority() -> None:
    prohibited = {
        "advance",
        "advance_to",
        "buy",
        "core_decision",
        "dispatch",
        "is_visible",
        "sell",
        "submit_order",
        "visible_at",
    }
    assert prohibited.isdisjoint(set(dir(ReplayMarketDataObservation)))
