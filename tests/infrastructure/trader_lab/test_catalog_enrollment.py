from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.trader_lab.candidate import TraderLabValidationError
from qore.infrastructure.trader_lab.catalog import (
    FIRST_DEMO_COHORT_CODES,
    TRADER_LAB_CATALOG_CODES,
    TraderLabCatalogEnrollmentSet,
    enroll_complete_trader_catalog,
)

_NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def test_all_31_traders_enter_trader_lab_intake_exactly_once() -> None:
    enrolled = enroll_complete_trader_catalog(enrolled_at=_NOW)

    assert isinstance(enrolled, TraderLabCatalogEnrollmentSet)
    assert enrolled.all_traders_enrolled is True
    assert tuple(item.trader_code.value for item in enrolled.enrollments) == (
        TRADER_LAB_CATALOG_CODES
    )
    assert tuple(item.trader_code.value for item in enrolled.first_demo_cohort) == (
        FIRST_DEMO_COHORT_CODES
    )


def test_catalog_intake_rejects_missing_trader() -> None:
    enrolled = enroll_complete_trader_catalog(enrolled_at=_NOW)

    with pytest.raises(TraderLabValidationError):
        TraderLabCatalogEnrollmentSet(enrollments=enrolled.enrollments[:-1])


def test_catalog_intake_rejects_naive_timestamp() -> None:
    with pytest.raises(TraderLabValidationError):
        enroll_complete_trader_catalog(
            enrolled_at=datetime(2026, 9, 7, 12, 0)
        )
