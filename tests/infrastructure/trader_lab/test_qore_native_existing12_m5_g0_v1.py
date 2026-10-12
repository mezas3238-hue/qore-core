"""Independent G0 source and timestamp tests; never evaluate market outcomes."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as v


def test_exactly_twelve_locked_symbols_and_producer_id() -> None:
    assert v.SYMBOLS == (
        "AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD",
        "NAS100", "SP500", "US30", "USDCAD", "USDJPY", "XAGUSD", "XAUUSD"
    )
    assert v.SOURCE_SYMBOL_MAP["NAS100"] == "USTEC"
    assert v.SOURCE_SYMBOL_MAP["SP500"] == "US500"
    assert v.PRODUCER_SHA == "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
    assert v.SOURCE_RUN == 35166210458
    assert v.AGGREGATE_ARTIFACT == 10476615509
    assert v.AGGREGATE_INDEX_SHA256 == "47f5763d7ea2c10dd32fa40a84d7480c8124f1a512b623c1299ef2ba7b8c51c2"
    assert len(v.YEARS) == 11


def test_h4_utc_presence_is_48_slots_and_day_288() -> None:
    hour4: dict[int, int] = {}
    day: dict[int, int] = {}
    for idx in range(288):
        v.audit_timestamp_bucket(idx * 5, None if idx == 0 else (idx - 1) * 5, hour4, day)
    assert len(hour4) == 6
    assert all(mask.bit_count() == 48 for mask in hour4.values())
    assert len(day) == 1
    assert next(iter(day.values())).bit_count() == 288


def test_missing_one_m5_stays_partial_without_synthetic_fill() -> None:
    hour4: dict[int, int] = {}
    day: dict[int, int] = {}
    previous: int | None = None
    for idx in range(288):
        if idx == 12:
            continue
        minute = idx * 5
        v.audit_timestamp_bucket(minute, previous, hour4, day)
        previous = minute
    assert len(hour4) == 6
    assert sorted(mask.bit_count() for mask in hour4.values()) == [47, 48, 48, 48, 48, 48]
    assert len(day) == 1
    assert next(iter(day.values())).bit_count() == 287


def test_bad_alignment_duplicate_and_backdated_m5_rejected() -> None:
    hour4: dict[int, int] = {}
    day: dict[int, int] = {}
    v.audit_timestamp_bucket(0, None, hour4, day)
    for ts in (0, 4, -5):
        with pytest.raises(ValueError, match="M5 timestamp"):
            v.audit_timestamp_bucket(ts, 0, hour4, day)


def test_source_sha_witness_enforced_not_just_manifest_flags(tmp_path: Path) -> None:
    source = tmp_path / "original.json"
    source.write_text('{"x": 1}\n')
    signed = hashlib.sha256(source.read_bytes()).hexdigest()
    ledger_path = tmp_path / "SHA256SUMS.txt"
    ledger_path.write_text(f"{signed}  original.json\n")
    witness = v.digest_ledger(ledger_path)
    assert v.verified_file(tmp_path, witness, source.name) == source
    source.write_text('{"x": 2}\n')
    with pytest.raises(ValueError, match="SHA256"):
        v.verified_file(tmp_path, witness, source.name)


def test_sha_manifest_path_attack_rejected(tmp_path: Path) -> None:
    d = tmp_path / "list.sha256"
    d.write_text("f" * 64 + "  ../somewhere\n")
    with pytest.raises(ValueError, match="unsafe"):
        v.digest_ledger(d)


def test_unknown_symbol_fail_closed_before_market_data() -> None:
    with pytest.raises(ValueError, match="frozen 12"):
        v.audit_symbol("NZDUSD", Path("/tmp"), {})


def test_code_avoids_ohlc_and_future_outcome_access() -> None:
    code = Path(v.__file__).read_text(encoding="utf-8")
    forbidden = (
        'row["close_relative"]', 'row["open_relative"]',
        'row["high_relative"]', 'row["low_relative"]',
        'row.get("close_relative")', 'row["volume"]',
        'return_bps', 'profit_factor', 'win_rate',
        'sharpe_ratio', 'math.log(', 'backtest(',
        'ctrader_open_api_client', 'order_request',
    )
    for string in forbidden:
        assert string not in code
