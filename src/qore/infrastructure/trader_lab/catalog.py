"""Mandatory Trader Lab intake for the complete VT-01..VT-31 catalog.

Catalog intake is deliberately weaker than candidate qualification.  Enrolling a
Trader records that it has entered the governed Lab intake and guarantees that
no catalog member can be silently omitted from governance.  It does not invent a
versioned implementation, research evidence, Lab lifecycle, DEMO eligibility, or
execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.trader_lab.candidate import TraderLabValidationError
from qore.infrastructure.traders.contracts import DemoTradingTraderCode

TRADER_LAB_CATALOG_CODES: tuple[str, ...] = tuple(
    f"vt-{index:02d}" for index in range(1, 32)
)
FIRST_DEMO_COHORT_CODES: tuple[str, ...] = (
    "vt-01",
    "vt-08",
    "vt-09",
    "vt-17",
    "vt-31",
)


class TraderLabCatalogIntakeState(StrEnum):
    """Catalog-level intake state; never a promotion state."""

    ENROLLED = "enrolled"


@dataclass(frozen=True, slots=True)
class TraderLabCatalogEnrollment:
    """One exact catalog Trader admitted to Trader Lab intake."""

    trader_code: DemoTradingTraderCode
    state: TraderLabCatalogIntakeState
    enrolled_at: datetime

    def __post_init__(self) -> None:
        if type(self.trader_code) is not DemoTradingTraderCode:
            raise TraderLabValidationError(
                "catalog enrollment trader_code must be DemoTradingTraderCode"
            )
        if self.trader_code.value not in TRADER_LAB_CATALOG_CODES:
            raise TraderLabValidationError(
                "catalog enrollment trader_code must belong to VT-01..VT-31"
            )
        if type(self.state) is not TraderLabCatalogIntakeState:
            raise TraderLabValidationError(
                "catalog enrollment state must be TraderLabCatalogIntakeState"
            )
        if self.state is not TraderLabCatalogIntakeState.ENROLLED:
            raise TraderLabValidationError(
                "catalog intake may only record explicit ENROLLED state"
            )
        if (
            type(self.enrolled_at) is not datetime
            or self.enrolled_at.tzinfo is None
            or self.enrolled_at.utcoffset() is None
        ):
            raise TraderLabValidationError(
                "catalog enrollment enrolled_at must be timezone-aware"
            )

    @property
    def first_demo_cohort_member(self) -> bool:
        return self.trader_code.value in FIRST_DEMO_COHORT_CODES

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_code.logical_values(),
            self.state.value,
            self.enrolled_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.first_demo_cohort_member,
        )


@dataclass(frozen=True, slots=True)
class TraderLabCatalogEnrollmentSet:
    """Closed proof that every one of the 31 catalog Traders entered Lab intake."""

    enrollments: tuple[TraderLabCatalogEnrollment, ...]

    def __post_init__(self) -> None:
        if type(self.enrollments) is not tuple or len(self.enrollments) != 31:
            raise TraderLabValidationError(
                "Trader Lab catalog intake must contain exactly 31 enrollments"
            )
        if any(
            type(item) is not TraderLabCatalogEnrollment
            for item in self.enrollments
        ):
            raise TraderLabValidationError(
                "catalog intake must contain TraderLabCatalogEnrollment values"
            )
        for item in self.enrollments:
            item.__post_init__()
        codes = tuple(item.trader_code.value for item in self.enrollments)
        if codes != TRADER_LAB_CATALOG_CODES:
            raise TraderLabValidationError(
                "Trader Lab catalog intake must contain VT-01..VT-31 exactly once "
                "in canonical order"
            )

    @property
    def all_traders_enrolled(self) -> bool:
        return True

    @property
    def first_demo_cohort(self) -> tuple[TraderLabCatalogEnrollment, ...]:
        return tuple(
            item for item in self.enrollments if item.first_demo_cohort_member
        )

    def logical_values(self) -> tuple[object, ...]:
        return tuple(item.logical_values() for item in self.enrollments)


def enroll_complete_trader_catalog(
    *,
    enrolled_at: datetime,
) -> TraderLabCatalogEnrollmentSet:
    """Enroll all 31 Traders into governed Lab intake at one explicit instant."""

    if (
        type(enrolled_at) is not datetime
        or enrolled_at.tzinfo is None
        or enrolled_at.utcoffset() is None
    ):
        raise TraderLabValidationError(
            "catalog enrollment enrolled_at must be timezone-aware"
        )
    return TraderLabCatalogEnrollmentSet(
        enrollments=tuple(
            TraderLabCatalogEnrollment(
                trader_code=DemoTradingTraderCode(code),
                state=TraderLabCatalogIntakeState.ENROLLED,
                enrolled_at=enrolled_at,
            )
            for code in TRADER_LAB_CATALOG_CODES
        )
    )
