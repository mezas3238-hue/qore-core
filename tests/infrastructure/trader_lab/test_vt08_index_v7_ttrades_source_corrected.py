from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_v7_ttrades_source_corrected import (
    CANDIDATE_ID,
    EXECUTABLE_H4_ANCHORS_NY,
    RULE_FINGERPRINT,
    _expected_source_day_slots,
    _source_day,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

_NY = ZoneInfo("America/New_York")


def _bar(opened_at: datetime, value: str = "100") -> Vt08IndexC2R1Bar:
    price = Decimal(value)
    return Vt08IndexC2R1Bar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=15),
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
    )


def test_v7_identity_and_execution_anchors_are_frozen() -> None:
    assert CANDIDATE_ID == "VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001"
    assert EXECUTABLE_H4_ANCHORS_NY == (22, 2, 6, 10)
    assert len(RULE_FINGERPRINT) == 64


def test_source_day_accepts_only_documented_1615_maintenance_gap() -> None:
    end_date = date(2020, 10, 5)
    slots = _expected_source_day_slots(end_date)
    indexed = {slot: _bar(slot) for slot in slots}
    maintenance_slot = next(
        slot
        for slot in slots
        if slot.astimezone(_NY).date() == end_date
        and slot.astimezone(_NY).hour == 16
        and slot.astimezone(_NY).minute == 15
    )
    del indexed[maintenance_slot]
    result = _source_day(indexed, end_date=end_date)
    assert result is not None
    aggregate, missing = result
    assert missing == (maintenance_slot,)
    assert aggregate.opened_at.astimezone(_NY).hour == 18
    assert aggregate.closed_at.astimezone(_NY).hour == 17


def test_source_day_rejects_unexplained_gap() -> None:
    end_date = date(2020, 10, 5)
    slots = _expected_source_day_slots(end_date)
    indexed = {slot: _bar(slot) for slot in slots}
    unexplained = next(
        slot
        for slot in slots
        if slot.astimezone(_NY).date() == end_date
        and slot.astimezone(_NY).hour == 12
        and slot.astimezone(_NY).minute == 0
    )
    del indexed[unexplained]
    assert _source_day(indexed, end_date=end_date) is None


def test_source_day_never_synthesizes_missing_ohlc() -> None:
    end_date = date(2020, 10, 5)
    slots = _expected_source_day_slots(end_date)
    indexed = {slot: _bar(slot, str(100 + index)) for index, slot in enumerate(slots)}
    maintenance_slot = next(
        slot
        for slot in slots
        if slot.astimezone(_NY).date() == end_date
        and slot.astimezone(_NY).hour == 16
        and slot.astimezone(_NY).minute == 15
    )
    removed = indexed.pop(maintenance_slot)
    result = _source_day(indexed, end_date=end_date)
    assert result is not None
    aggregate, _ = result
    assert aggregate.high == max(bar.high for bar in indexed.values())
    assert aggregate.low == min(bar.low for bar in indexed.values())
    assert removed.opened_at.astimezone(UTC) not in indexed
