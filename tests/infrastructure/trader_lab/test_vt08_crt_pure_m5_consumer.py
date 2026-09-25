from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_m5_consumer import (
    IDENTITY,
    PARENT_IDENTITY,
    PROVIDER_SYMBOL_MAP,
    RAW_SCHEMA,
    TARGET_END_EXCLUSIVE,
    TARGET_START,
    Partition,
    RawM5Bar,
    chunk_grid,
    partition_grid,
    unresolved_gap_records,
)


def _bar(timestamp_minutes: int) -> RawM5Bar:
    opened_at = datetime.fromtimestamp(timestamp_minutes * 60, tz=UTC)
    return RawM5Bar(
        schema=RAW_SCHEMA,
        identity=IDENTITY,
        parent_identity=PARENT_IDENTITY,
        canonical_symbol="AUDUSD",
        provider_symbol="AUDUSD",
        provider_symbol_id=5,
        digits=5,
        pip_position=4,
        opened_at=opened_at.isoformat(),
        utc_timestamp_in_minutes=timestamp_minutes,
        low_relative=100000,
        delta_open=10,
        delta_high=30,
        delta_close=20,
        volume=100,
        open_relative=100010,
        high_relative=100030,
        close_relative=100020,
    )


def test_common_three_market_window_is_frozen() -> None:
    assert TARGET_START == datetime(2017, 1, 1, tzinfo=UTC)
    assert TARGET_END_EXCLUSIVE == datetime(2026, 9, 21, tzinfo=UTC)
    assert tuple(PROVIDER_SYMBOL_MAP) == ("AUDUSD", "USDJPY", "BTCUSD")
    assert PROVIDER_SYMBOL_MAP == {
        "AUDUSD": "AUDUSD",
        "USDJPY": "USDJPY",
        "BTCUSD": "BTCUSD",
    }


def test_partition_grid_is_contiguous_and_ends_at_frozen_boundary() -> None:
    partitions = partition_grid()
    assert partitions[0] == Partition(
        "2017",
        datetime(2017, 1, 1, tzinfo=UTC),
        datetime(2018, 1, 1, tzinfo=UTC),
    )
    assert partitions[-1] == Partition(
        "2026",
        datetime(2026, 1, 1, tzinfo=UTC),
        TARGET_END_EXCLUSIVE,
    )
    assert all(
        left.closed_at == right.opened_at
        for left, right in zip(partitions, partitions[1:], strict=False)
    )


def test_chunk_grid_never_exceeds_seven_days_and_has_no_holes() -> None:
    partition = Partition(
        "2026",
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 2, 1, tzinfo=UTC),
    )
    chunks = chunk_grid(partition)
    assert chunks[0][0] == partition.opened_at
    assert chunks[-1][1] == partition.closed_at
    assert all((closed - opened).days <= 7 for opened, closed in chunks)
    assert all(
        left[1] == right[0]
        for left, right in zip(chunks, chunks[1:], strict=False)
    )


def test_gap_is_retained_as_unresolved_evidence() -> None:
    base = int(datetime(2026, 9, 14, 12, 0, tzinfo=UTC).timestamp() // 60)
    records = unresolved_gap_records((_bar(base), _bar(base + 15)))
    assert len(records) == 1
    record = records[0]
    assert record["kind"] == "UNRESOLVED_CLOSURE_OR_MISSING_DATA"
    assert record["calendar_slots_without_bars"] == 2
    assert record["market_open_expected"] is None
    assert record["outcome_only"] is False


def test_adjacent_m5_bars_do_not_create_gap_record() -> None:
    base = int(datetime(2026, 9, 14, 12, 0, tzinfo=UTC).timestamp() // 60)
    assert unresolved_gap_records((_bar(base), _bar(base + 5))) == ()
