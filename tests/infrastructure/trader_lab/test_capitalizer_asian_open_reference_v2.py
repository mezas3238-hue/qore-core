from datetime import UTC, date, datetime

import pytest

from qore.infrastructure.trader_lab.capitalizer_asian_open_reference_v2 import (
    CapitalizerAsianOpenReference,
    CapitalizerAsianOpenReferenceBook,
    CapitalizerAsianOpenReferenceSource,
    require_asian_open_reference,
)


def test_historical_asian_open_reference_is_explicit_not_fixed_clock_inference() -> None:
    reference = CapitalizerAsianOpenReference(
        operating_date=date(2026, 1, 6),
        opened_at=datetime(2026, 1, 5, 0, 15, tzinfo=UTC),
        source=CapitalizerAsianOpenReferenceSource.CIBO_HISTORICAL_SESSION_METADATA,
        source_record_id="CIBO:ASIA:2026-01-06",
    )
    book = CapitalizerAsianOpenReferenceBook((reference,))

    assert require_asian_open_reference(
        book=book,
        operating_date=date(2026, 1, 6),
    ) == datetime(2026, 1, 5, 0, 15, tzinfo=UTC)
    assert reference.inferred_from_fixed_clock is False


def test_missing_historical_asian_open_reference_fails_closed() -> None:
    with pytest.raises(ValueError, match="historical Asian Open reference missing"):
        require_asian_open_reference(
            book=CapitalizerAsianOpenReferenceBook(()),
            operating_date=date(2026, 1, 6),
        )


def test_duplicate_asian_open_operating_date_is_rejected() -> None:
    left = CapitalizerAsianOpenReference(
        operating_date=date(2026, 1, 6),
        opened_at=datetime(2026, 1, 5, 0, 0, tzinfo=UTC),
        source=CapitalizerAsianOpenReferenceSource.CIBO_HISTORICAL_SESSION_METADATA,
        source_record_id="A",
    )
    right = CapitalizerAsianOpenReference(
        operating_date=date(2026, 1, 6),
        opened_at=datetime(2026, 1, 5, 1, 0, tzinfo=UTC),
        source=CapitalizerAsianOpenReferenceSource.BROKER_HISTORICAL_SESSION_METADATA,
        source_record_id="B",
    )

    with pytest.raises(ValueError, match="one reference per operating date"):
        CapitalizerAsianOpenReferenceBook((left, right))
