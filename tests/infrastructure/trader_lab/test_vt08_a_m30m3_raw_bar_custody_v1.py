"""VT08 native raw custody adversarial tests: snapshots are not fills."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_a_m30m3_raw_bar_custody_v1 import (
    attest_anchor_window,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar


def _bar(t: datetime, minutes: int, *, lo: str = "100", hi: str = "102"):
    return Vt08B01Bar(
        opened_at=t, closed_at=t+timedelta(minutes=minutes),
        open=Decimal("101"), high=Decimal(hi),
        low=Decimal(lo), close=Decimal("101"),
    )


def _sample(t: datetime):
    m3 = {
        t+timedelta(minutes=3*i):
        _bar(t+timedelta(minutes=3*i), 3) for i in range(10)
    }
    m15 = {
        t+timedelta(minutes=15*i):
        _bar(t+timedelta(minutes=15*i), 15) for i in range(2)
    }
    return m3, m15


def _audit(t: datetime, m3, m15):
    return attest_anchor_window(
        market="EURJPY", m3_bars=m3, m15_bars=m15,
        opened_at=t, raw_m3_sha="a"*64, raw_m15_sha="b"*64,
    )


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("hour", [1, 5, 9])
def test_native_m3_m15_same_source_m30_receipts_are_research_only(month, hour):
    t=datetime(2025, month, 15, hour, tzinfo=ZoneInfo("America/New_York"))
    m3,m15=_sample(t)
    record=_audit(t,m3,m15)
    assert len(record["m3_bar_receipts"]) == 10
    assert len(record["m15_bar_receipts"]) == 2
    assert record["m30_available_at_utc"] == (t+timedelta(minutes=30)).astimezone(UTC).isoformat()
    assert not record["source_author_fidelity_verified"]
    assert not record["cognitive_ready"]
    assert not record["broker_quotes_verified"]
    assert record["fills"] == 0
    assert len(set(r["source_bar_id"] for r in record["m3_bar_receipts"])) == 10
    assert all(
        r["available_at_utc"] == r["closed_at_utc"]
        for r in record["m3_bar_receipts"]
    )


def test_missing_m3_bar_is_not_cross_attested():
    t=datetime(2025, 1, 15, 1, tzinfo=ZoneInfo("America/New_York"))
    m3,m15=_sample(t)
    del m3[t+timedelta(minutes=6)]
    with pytest.raises(ValueError, match="incomplete"):
        _audit(t,m3,m15)


def test_m3_and_m15_disagree_on_high_is_rejected():
    t=datetime(2025, 1, 15, 1, tzinfo=ZoneInfo("America/New_York"))
    m3,m15=_sample(t)
    m15[t] = replace(m15[t], high=Decimal("103"))
    with pytest.raises(ValueError, match="disagree"):
        _audit(t,m3,m15)


def test_wrong_anchor_and_wrong_market_rejected():
    t=datetime(2025, 1, 15, 1, tzinfo=ZoneInfo("America/New_York"))
    m3,m15=_sample(t)
    with pytest.raises(ValueError, match="owner anchor"):
        _audit(t+timedelta(minutes=30),m3,m15)
    with pytest.raises(ValueError, match="five-market"):
        attest_anchor_window(
            market="NAS100", m3_bars=m3, m15_bars=m15,
            opened_at=t, raw_m3_sha="a"*64, raw_m15_sha="b"*64,
        )


def test_fake_sha_and_future_unclosed_bar_fail_closed():
    t=datetime(2025, 1, 15, 1, tzinfo=ZoneInfo("America/New_York"))
    m3,m15=_sample(t)
    with pytest.raises(ValueError, match="SHA256"):
        attest_anchor_window(
            market="EURJPY", m3_bars=m3, m15_bars=m15,
            opened_at=t, raw_m3_sha="fake", raw_m15_sha="b"*64,
        )
    m3[t] = replace(m3[t], closed_at=t+timedelta(minutes=9))
    with pytest.raises(ValueError, match="incomplete"):
        _audit(t,m3,m15)


def test_source_receipt_changes_if_ohlc_mutated():
    t=datetime(2025, 1, 15, 1, tzinfo=ZoneInfo("America/New_York"))
    m3,m15=_sample(t)
    original=_audit(t,m3,m15)["m3_bar_receipts"][0]["source_bar_id"]
    m3[t] = replace(m3[t], high=Decimal("101.99"))
    # M30 high still 102 (other bars): custody bar ID changes even though
    # aggregate OHLC stays the same.
    modified=_audit(t,m3,m15)["m3_bar_receipts"][0]["source_bar_id"]
    assert modified != original
