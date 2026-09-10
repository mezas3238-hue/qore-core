from __future__ import annotations

import json
from datetime import UTC, datetime

from qore.infrastructure.trader_lab.catalog import (
    FIRST_DEMO_COHORT_CODES,
    TRADER_LAB_CATALOG_CODES,
)
from qore.infrastructure.trader_lab.operational_intake import (
    record_operational_trader_lab_intake,
)

_NOW = datetime(2026, 9, 7, 12, 40, tzinfo=UTC)


def test_operational_intake_records_all_31_and_first_five_without_promotion() -> None:
    report = record_operational_trader_lab_intake(recorded_at=_NOW)

    assert report.all_31_entered_lab is True
    assert report.first_cohort_entered_lab is True
    assert tuple(item.trader_code.value for item in report.catalog.enrollments) == (
        TRADER_LAB_CATALOG_CODES
    )
    assert tuple(
        item.trader_code.value for item in report.catalog.first_demo_cohort
    ) == FIRST_DEMO_COHORT_CODES

    payload = json.loads(report.sanitized_json())
    assert payload["trader_count"] == 31
    assert payload["all_31_entered_lab"] is True
    assert payload["first_cohort_entered_lab"] is True
    assert payload["qualification_claimed"] is False
    assert payload["execution_authority_claimed"] is False
