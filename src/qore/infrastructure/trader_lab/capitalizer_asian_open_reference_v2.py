"""Historical Asian Open reference contract for QORE Capitalizer V2.

ICT's reviewed lesson explicitly treats the Asian Open as a relative reference that can shift
with daylight-saving alignment. QORE therefore does not derive one universal clock. Replay must
provide a causal historical reference for each Asian operating date; this resolver validates and
retrieves that metadata without inventing precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class CapitalizerAsianOpenReferenceSource(StrEnum):
    CIBO_HISTORICAL_SESSION_METADATA = "CIBO_HISTORICAL_SESSION_METADATA"
    BROKER_HISTORICAL_SESSION_METADATA = "BROKER_HISTORICAL_SESSION_METADATA"


@dataclass(frozen=True, slots=True)
class CapitalizerAsianOpenReference:
    operating_date: date
    opened_at: datetime
    source: CapitalizerAsianOpenReferenceSource
    source_record_id: str
    inferred_from_fixed_clock: bool = False

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise ValueError("Asian Open historical reference must be timezone-aware")
        if not self.source_record_id:
            raise ValueError("Asian Open historical reference requires source record id")
        if self.inferred_from_fixed_clock:
            raise ValueError("Asian Open reference cannot be invented from a universal clock")


@dataclass(frozen=True, slots=True)
class CapitalizerAsianOpenReferenceBook:
    references: tuple[CapitalizerAsianOpenReference, ...]

    def __post_init__(self) -> None:
        dates = tuple(item.operating_date for item in self.references)
        if len(dates) != len(set(dates)):
            raise ValueError("Asian Open reference book requires one reference per operating date")

    def resolve(self, operating_date: date) -> datetime | None:
        matches = tuple(
            item.opened_at
            for item in self.references
            if item.operating_date == operating_date
        )
        if len(matches) > 1:
            raise AssertionError("validated Asian Open reference book became non-unique")
        return None if not matches else matches[0]


def require_asian_open_reference(
    *,
    book: CapitalizerAsianOpenReferenceBook,
    operating_date: date,
) -> datetime:
    resolved = book.resolve(operating_date)
    if resolved is None:
        raise ValueError(
            f"historical Asian Open reference missing for operating date {operating_date.isoformat()}"
        )
    return resolved
