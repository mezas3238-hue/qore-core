from datetime import UTC, datetime

from qore.infrastructure.trader_lab.cibo_market_atlas_10y_m5_consumer_v1 import (
    IDENTITY,
    PROVIDER_SYMBOL_MAP,
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
        schema="qore.cibo_market_atlas.raw_m5.v1",
        identity=IDENTITY,
        parent_identity="CIBO_MARKET_ATLAS_20Y_V1",
        canonical_symbol="EURUSD",
        provider_symbol="EURUSD",
        provider_symbol_id=1,
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


def test_ten_year_corpus_is_exact_calendar_window() -> None:
    assert TARGET_START == datetime(2016, 9, 17, tzinfo=UTC)
    assert TARGET_END_EXCLUSIVE == datetime(2026, 9, 17, tzinfo=UTC)
    assert TARGET_END_EXCLUSIVE.replace(year=2016) == TARGET_START


def test_provider_index_mapping_is_explicit_and_not_spxusd() -> None:
    assert PROVIDER_SYMBOL_MAP["NAS100"] == "USTEC"
    assert PROVIDER_SYMBOL_MAP["SP500"] == "US500"
    assert PROVIDER_SYMBOL_MAP["US30"] == "US30"
    assert "SPXUSD" not in PROVIDER_SYMBOL_MAP.values()


def test_partition_grid_preserves_partial_edge_years() -> None:
    partitions = partition_grid()
    assert len(partitions) == 11
    assert partitions[0] == Partition(
        "2016",
        datetime(2016, 9, 17, tzinfo=UTC),
        datetime(2017, 1, 1, tzinfo=UTC),
    )
    assert partitions[-1] == Partition(
        "2026",
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 9, 17, tzinfo=UTC),
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


def test_gap_is_unresolved_not_silently_called_missing_market_data() -> None:
    base = int(datetime(2026, 9, 14, 12, 0, tzinfo=UTC).timestamp() // 60)
    records = unresolved_gap_records((_bar(base), _bar(base + 15)))
    assert len(records) == 1
    record = records[0]
    assert record["kind"] == "UNRESOLVED_CLOSURE_OR_MISSING_DATA"
    assert record["calendar_slots_without_bars"] == 2
    assert record["market_open_expected"] is None
    assert record["outcome_only"] is False


def test_normal_adjacent_m5_bars_do_not_create_gap_record() -> None:
    base = int(datetime(2026, 9, 14, 12, 0, tzinfo=UTC).timestamp() // 60)
    assert unresolved_gap_records((_bar(base), _bar(base + 5))) == ()
