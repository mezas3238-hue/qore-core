"""R8 original provider-archive quality chain tests, never terminal authority."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_crt_original_atlas_quality_gap_custody import (
    FROZEN_GAPS,
    audit_original_producer_quality_gaps,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bar(stamp: datetime) -> ReplayBar:
    return ReplayBar(
        opened_at=stamp, open_price=100, high_price=101,
        low_price=99, close_price=100,
    )


def _write_files(root: Path, market: CrtPureMarket, gap_rows: list[dict]) -> None:
    year = 2025
    file = root / "DATA_QUALITY_LEDGER" / f"{year}.jsonl"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("".join(json.dumps(x) + "\n" for x in gap_rows))
    annual = root / "PARTITION_MANIFEST" / f"{year}.sha256"
    annual.parent.mkdir(parents=True, exist_ok=True)
    name = f"DATA_QUALITY_LEDGER/{year}.jsonl"
    annual.write_text(f"{_sha(file.read_bytes())}  {name}\n")
    manifest = root / "MANIFEST_SHA256SUMS.txt"
    manifest.write_text(
        f"{_sha(annual.read_bytes())}  PARTITION_MANIFEST/{year}.sha256\n"
    )


def _record(market: CrtPureMarket, before: datetime, after: datetime) -> dict:
    return {
        "schema": "qore.cibo_market_atlas.data_quality.v1",
        "identity": "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1",
        "canonical_symbol": market.value,
        "kind": "UNRESOLVED_CLOSURE_OR_MISSING_DATA",
        "previous_bar_at": before.isoformat(),
        "next_bar_at": after.isoformat(),
        "gap_start": (before + timedelta(minutes=5)).isoformat(),
        "gap_end_exclusive": after.isoformat(),
        "calendar_slots_without_bars": int(
            (after - before) / timedelta(minutes=5)
        ) - 1,
        "spans_weekend": (after - before).days >= 1,
        "market_open_expected": None,
        "outcome_only": False,
    }


def _claims(market: CrtPureMarket) -> tuple[dict, ...]:
    return tuple({
        "source_event_id": eid, "original_m5_missing_at_utc": when,
    } for when, eid in FROZEN_GAPS[market].items())


def _midweek(tmp_path: Path) -> tuple[tuple[ReplayBar, ...], dict]:
    market = CrtPureMarket.USDJPY
    missing = datetime.fromisoformat("2025-02-12T22:30:00+00:00")
    before, after = missing - timedelta(minutes=5), missing + timedelta(minutes=5)
    witness = _record(market, before, after)
    _write_files(tmp_path, market, [witness])
    return (_bar(before), _bar(after)), witness


def test_audusd_friday_producer_gap_witness_not_a_market_calendar(
    tmp_path: Path,
) -> None:
    market = CrtPureMarket.AUDUSD
    absent = datetime.fromisoformat("2025-04-25T21:00:00+00:00")
    before = absent - timedelta(minutes=5)
    after = datetime.fromisoformat("2025-04-27T21:00:00+00:00")
    witness = _record(market, before, after)
    _write_files(tmp_path, market, [witness])
    summary, results = audit_original_producer_quality_gaps(
        market, tmp_path, (_bar(before), _bar(after)), _claims(market)
    )
    assert summary["counts"]["PRODUCER_GAP_SPANS_WEEKEND"] == 1
    assert results[0]["producer_gap_previous_m5_utc"] == before.isoformat()
    assert results[0]["producer_gap_next_m5_utc"] == after.isoformat()
    assert results[0]["quality_ledger_sha_verified"]
    assert results[0]["broker_historical_calendar_authenticated"] is False
    assert results[0]["source_GM4_terminal_still_UNKNOWN"]
    assert results[0]["G_M4_PASS"] is False
    assert results[0]["not_a_trade"] and results[0]["no_sizing"]


def test_usdjpy_wednesday_one_missing_source_slot_no_fill(
    tmp_path: Path,
) -> None:
    market = CrtPureMarket.USDJPY
    rows, _ = _midweek(tmp_path)
    # Isolate the 2025 case; production USDJPY R8 must also reconcile 2026.
    from qore.infrastructure.trader_lab import vt08_crt_original_atlas_quality_gap_custody as module

    original = module.FROZEN_GAPS[market]
    module.FROZEN_GAPS[market] = {
        "2025-02-12T22:30:00+00:00": "11a7c3cdb30a9eabdbbe"
    }
    try:
        summary, evidence = audit_original_producer_quality_gaps(
            market, tmp_path, rows, ({"source_event_id": "11a7c3cdb30a9eabdbbe",
                                     "original_m5_missing_at_utc": "2025-02-12T22:30:00+00:00"},)
        )
    finally:
        module.FROZEN_GAPS[market] = original
    assert summary["counts"]["PRODUCER_ONE_M5_INTERIOR_GAP"] == 1
    assert evidence[0]["producer_calendar_slots_without_bars"] == 1
    assert not evidence[0]["producer_spans_weekend"]
    assert not evidence[0]["underlying_missing_m5_recovered"]


@pytest.mark.parametrize("attack", [
    "tampered_quality_without_sha", "forged_market", "fabricated_market_open",
    "bad_boundary", "overlap_duplicate",
])
def test_original_quality_forgery_fails_closed(tmp_path: Path, attack: str) -> None:
    market = CrtPureMarket.AUDUSD
    target = datetime.fromisoformat("2025-04-25T21:00:00+00:00")
    before = target - timedelta(minutes=5)
    after = datetime.fromisoformat("2025-04-27T21:00:00+00:00")
    item = _record(market, before, after)
    records = [item]
    if attack == "forged_market":
        item["canonical_symbol"] = "USDJPY"
    elif attack == "fabricated_market_open":
        item["market_open_expected"] = True
    elif attack == "bad_boundary":
        item["previous_bar_at"] = (before - timedelta(minutes=5)).isoformat()
    elif attack == "overlap_duplicate":
        records.append(item.copy())
    _write_files(tmp_path, market, records)
    if attack == "tampered_quality_without_sha":
        file = tmp_path / "DATA_QUALITY_LEDGER" / "2025.jsonl"
        file.write_text(file.read_text() + "\n")
    with pytest.raises(ValueError):
        audit_original_producer_quality_gaps(
            market, tmp_path, (_bar(before), _bar(after)), _claims(market)
        )


def test_mismatch_with_frozen_identity_rejected(tmp_path: Path) -> None:
    market = CrtPureMarket.AUDUSD
    when = datetime.fromisoformat("2025-04-25T21:00:00+00:00")
    before, after = when - timedelta(minutes=5), when + timedelta(days=2)
    _write_files(tmp_path, market, [_record(market, before, after)])
    with pytest.raises(ValueError, match="identity"):
        audit_original_producer_quality_gaps(
            market, tmp_path, (_bar(before), _bar(after)),
            ({"source_event_id": "fake", "original_m5_missing_at_utc": when.isoformat()},)
        )
