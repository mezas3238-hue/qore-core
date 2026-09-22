"""Operational, evidence-only Trader Lab intake for the complete VT catalog.

This module records the governance event that every VT-01..VT-31 Trader has
entered Trader Lab intake.  Intake is deliberately not qualification: only the
five first-DEMO cohort members proceed to candidate evidence and none receives
DEMO, Risk, execution, Production, LIVE, or real-capital authority here.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from qore.infrastructure.trader_lab.candidate import TraderLabValidationError
from qore.infrastructure.trader_lab.catalog import (
    FIRST_DEMO_COHORT_CODES,
    TRADER_LAB_CATALOG_CODES,
    TraderLabCatalogEnrollmentSet,
    enroll_complete_trader_catalog,
)


@dataclass(frozen=True, slots=True)
class TraderLabOperationalIntakeReport:
    """Sanitized proof that the complete catalog entered governed Lab intake."""

    catalog: TraderLabCatalogEnrollmentSet
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.catalog, TraderLabCatalogEnrollmentSet):
            raise TraderLabValidationError(
                "operational intake catalog must be TraderLabCatalogEnrollmentSet"
            )
        self.catalog.__post_init__()
        if (
            type(self.recorded_at) is not datetime
            or self.recorded_at.tzinfo is None
            or self.recorded_at.utcoffset() is None
        ):
            raise TraderLabValidationError(
                "operational intake recorded_at must be timezone-aware"
            )
        if any(item.enrolled_at != self.recorded_at for item in self.catalog.enrollments):
            raise TraderLabValidationError(
                "all catalog enrollments must bind the exact intake instant"
            )

    @property
    def all_31_entered_lab(self) -> bool:
        return self.catalog.all_traders_enrolled

    @property
    def first_cohort_entered_lab(self) -> bool:
        return tuple(
            item.trader_code.value for item in self.catalog.first_demo_cohort
        ) == FIRST_DEMO_COHORT_CODES

    def sanitized_payload(self) -> dict[str, object]:
        """Return secret-free machine evidence suitable for an Actions artifact."""
        return {
            "schema": "qore.trader_lab.operational_intake.v1",
            "recorded_at": self.recorded_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "all_31_entered_lab": self.all_31_entered_lab,
            "trader_count": len(self.catalog.enrollments),
            "traders": list(TRADER_LAB_CATALOG_CODES),
            "first_demo_cohort": list(FIRST_DEMO_COHORT_CODES),
            "first_cohort_entered_lab": self.first_cohort_entered_lab,
            "qualification_claimed": False,
            "execution_authority_claimed": False,
        }

    def sanitized_json(self) -> str:
        return json.dumps(
            self.sanitized_payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )


def record_operational_trader_lab_intake(
    *,
    recorded_at: datetime,
) -> TraderLabOperationalIntakeReport:
    """Enroll VT-01..VT-31 at one exact instant and return auditable evidence."""
    catalog = enroll_complete_trader_catalog(enrolled_at=recorded_at)
    return TraderLabOperationalIntakeReport(catalog=catalog, recorded_at=recorded_at)


def main() -> None:
    """Write only sanitized intake evidence to stdout for an operational runner."""
    encoded = os.environ.get("QORE_TRADER_LAB_RECORDED_AT", "")
    if not encoded:
        raise TraderLabValidationError(
            "missing required environment input: QORE_TRADER_LAB_RECORDED_AT"
        )
    try:
        recorded_at = datetime.fromisoformat(encoded)
    except ValueError as error:
        raise TraderLabValidationError(
            "QORE_TRADER_LAB_RECORDED_AT must be an ISO-8601 timestamp"
        ) from error
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise TraderLabValidationError(
            "QORE_TRADER_LAB_RECORDED_AT must be timezone-aware"
        )
    report = record_operational_trader_lab_intake(
        recorded_at=recorded_at.astimezone(UTC)
    )
    print(report.sanitized_json())


if __name__ == "__main__":
    main()
