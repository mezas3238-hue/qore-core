"""Precutoff, London DST and fail-closed data-quality gates for G0C."""
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab import qore_native_existing_demo_fx_g0c_v1 as g0c


def _make_source(tmp_path, entries, cutoff="2023-03-28T00:00:00+00:00"):
    root = tmp_path
    p = root / "raw-7y-base.json"
    cov = {
        name: {"bar_count": max(len(entries), 1)}
        for name in ("M1", "M5", "M15", "H4")
    }
    header = {
        "account_discovered": True,
        "account_is_live": False,
        "environment": "demo",
        "fresh_cutoff": cutoff,
        "intended_future_use": "VT08_COGNITIVE_EXPANSION_M3_UNSEEN_VALIDATION",
        "coverage": cov,
    }
    bars = []
    for open_utc, close_utc in entries:
        bars.append({
            "close": "999.999", "closed_at": close_utc.isoformat(),
            "high": "999.999", "low": "111.111", "open": "111.111",
            "opened_at": open_utc.isoformat(), "period": "M5"})
    p.write_text(json.dumps({**header, "periods": {"M5": bars}},
                            separators=(",", ":"), sort_keys=True))
    g0c.EXPECTED_SHA["EURJPY"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return root


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(UTC)


def test_london_dst_uses_local_clock() -> None:
    a = _utc("2023-03-24T08:00:00+00:00")
    b = _utc("2023-03-27T07:00:00+00:00")
    seen = g0c.observation_slots([a, b])
    for day in seen:
        assert seen[day]["LONDON_OPEN_0800_0900"] == 1
    assert len(seen) == 2


def test_archive_precutoff_census_does_not_parse_sealed_values(tmp_path) -> None:
    open_utc = _utc("2023-03-27T07:00:00+00:00")
    # Second (cutoff) record valid, followed by malformed data that MUST NOT be touched.
    cutoff = _utc("2023-03-28T00:00:00+00:00")
    root = _make_source(tmp_path, [
        (open_utc, open_utc + timedelta(minutes=5)),
        (cutoff, cutoff + timedelta(minutes=5))],
        cutoff=cutoff.isoformat())
    payload, rows = g0c.census("EURJPY", root)
    assert payload["m5_observed_dev"] == 1
    assert payload["m5_last_dev_utc"] == open_utc.isoformat()
    assert payload["prices_read"] is False
    assert payload["virgin_oos_claimed"] is False
    assert payload["ctrader_oauth_needed"] is False
    open_rows = [r for r in rows if r["window"] == "LONDON_OPEN_0800_0900"]
    assert len(open_rows) == 1
    assert open_rows[0]["present_m5"] == 1


def test_reject_out_of_order_m5(tmp_path) -> None:
    start = _utc("2023-03-27T07:00:00+00:00")
    root = _make_source(tmp_path, [
        (start, start + timedelta(minutes=5)),
        (start, start + timedelta(minutes=5))])
    with pytest.raises(ValueError, match="duplicates/out-of-order"):
        g0c.census("EURJPY", root)


def test_reject_invalid_period(tmp_path) -> None:
    start = _utc("2023-03-27T07:00:00+00:00")
    root = _make_source(tmp_path, [(start, start + timedelta(minutes=15))])
    with pytest.raises(ValueError, match="wrong period"):
        g0c.census("EURJPY", root)


def test_reject_source_sha_mismatch(tmp_path) -> None:
    start = _utc("2023-03-27T07:00:00+00:00")
    root = _make_source(tmp_path, [(start, start + timedelta(minutes=5))])
    g0c.EXPECTED_SHA["EURJPY"] = "0" * 64
    with pytest.raises(ValueError, match="source SHA mismatch"):
        g0c.census("EURJPY", root)


def test_reject_moved_vt08_cutoff(tmp_path) -> None:
    start = _utc("2023-03-27T07:00:00+00:00")
    root = _make_source(tmp_path,
                        [(start, start + timedelta(minutes=5))],
                        cutoff="2025-01-01T00:00:00+00:00")
    with pytest.raises(ValueError, match="unexpectedly moved"):
        g0c.census("EURJPY", root)
