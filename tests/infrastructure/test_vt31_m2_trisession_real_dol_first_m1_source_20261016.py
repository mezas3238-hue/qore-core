"""Three session M2: closed M1 QORE DOL source only, never ICT certificate."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    NEW_YORK,
    M1Bar,
    SessionId,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader
from scripts.vt31_m2_trisession_real_dol_first_m1_source_20261016 import (
    POOL_FAMILIES,
    first_m1_case,
    stream_m2_first_bar_witnesses,
)


def m1(month: int, hour: int, minute: int) -> M1Bar:
    at = datetime(2025, month, 15, hour, minute, tzinfo=NEW_YORK).astimezone(UTC)
    return M1Bar(
        at, at + timedelta(minutes=1),
        Decimal("100"), Decimal("104"),
        Decimal("97"), Decimal("100"),
    )


def native() -> VT31Trader:
    return VT31Trader(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
        strict_source_admission=True,
    )


def sample(month: int, *hours: int):
    return [m1(month, hour, minute) for hour in hours for minute in range(60)]


def market(bars: list[M1Bar]) -> list[dict[str, str]]:
    return [
        {
            "opened_at": x.opened_at.isoformat(),
            "closed_at": x.closed_at.isoformat(),
            "open": str(x.open),
            "high": str(x.high),
            "low": str(x.low),
            "close": str(x.close),
        }
        for x in bars
    ]


@pytest.mark.parametrize("month", [1, 7])
def test_native_first_m1_three_sessions_and_nyam_only_09h(month):
    bars = sample(month, 0, 1, 2, 3, 9, 10, 14)
    cases, n = stream_m2_first_bar_witnesses(
        market(bars), expected_m1=len(bars),
    )
    day = f"2025-{month:02d}-15"
    assert n == len(bars)
    assert set(cases) == {
        (day, SessionId.LONDON), (day, SessionId.NY_AM),
        (day, SessionId.NY_PM),
    }
    for sess in SessionId:
        value = cases[(day, sess)]
        assert value["original_native_G3_invoked_at_first_m1"]
        assert value["first_closed_M1_utc"] is not None
        assert value["M2_QORE_independent_attestation_state"] in {
            "CONFIRMED", "UNKNOWN", "REJECTED",
        }
        assert len(value["source_pool_six_independent_M1_witnesses"]) == 6
        assert {
            p["family"] for p in value["source_pool_six_independent_M1_witnesses"]
        } == POOL_FAMILIES
        assert value["nyam_h1_09_completed_at_10_if_applicable"] is (
            True if sess is SessionId.NY_AM else None
        )
        assert not value["ict_author_dol_certified"]
        assert value["broker_trades_or_fills"] == value["sizing"] == 0
    london = cases[(day, SessionId.LONDON)]
    assert all(
        p["state"] == "UNKNOWN" and p["level"] is None
        for p in london["source_pool_six_independent_M1_witnesses"]
        if p["family"].startswith("LONDON_NY_CLOCK_")
    )
    assert cases[(day, SessionId.NY_PM)]["native_M0_source_wait"] is None


@pytest.mark.parametrize("month", [1, 7])
def test_incomplete_nyam_09h_causes_wait_not_positive_m2(month):
    bars = (
        sample(month, 0, 1, 2, 3)
        + [m1(month, 9, k) for k in range(59)]
        + sample(month, 10, 14)
    )
    cases, _ = stream_m2_first_bar_witnesses(
        market(bars), expected_m1=len(bars),
    )
    day = f"2025-{month:02d}-15"
    nyam = cases[(day, SessionId.NY_AM)]
    assert nyam["native_M0_source_wait"] == "SOURCE_09H_INCOMPLETE_WAIT"
    assert not nyam["original_native_G3_invoked_at_first_m1"]
    assert not nyam["original_G3_QORE_DTO_present_not_trade"]
    assert nyam["M2_QORE_independent_attestation_state"] == "UNKNOWN"
    assert cases[(day, SessionId.LONDON)]["native_M0_source_wait"] is None
    assert cases[(day, SessionId.NY_PM)]["native_M0_source_wait"] is None


@pytest.mark.parametrize("month", [1, 7])
def test_missing_first_session_m1_does_not_fabricate_m2_witness(month):
    bars = [
        m1(month, 3, k) for k in range(1, 60)
    ]
    cases, _ = stream_m2_first_bar_witnesses(
        market(bars), expected_m1=len(bars),
    )
    assert cases == {}


def test_future_bar_fails_source_causal_attestor_even_without_cog():
    trader = native()
    current = m1(7, 3, 0)
    later = m1(7, 3, 1)
    original = trader.on_closed_m1(current)
    with pytest.raises(AssertionError, match="FUTURE_M1"):
        first_m1_case(
            trader=trader, bar=current, history=(current, later),
            session=SessionId.LONDON, observation=original,
        )


def test_wrong_first_bar_utc_session_rejected():
    trader = native()
    current = m1(7, 3, 0)
    original = trader.on_closed_m1(current)
    with pytest.raises(AssertionError, match="WRONG_SESSION"):
        first_m1_case(
            trader=trader, bar=current, history=(current,),
            session=SessionId.NY_PM, observation=original,
        )


def test_cannot_read_original_market_source_future_ledger_during_online_scan():
    import inspect

    assert tuple(inspect.signature(stream_m2_first_bar_witnesses).parameters) == (
        "rows", "expected_m1",
    )


def test_broken_duplicate_m1_times_aborts_without_repair():
    bar = m1(7, 3, 0)
    with pytest.raises(ValueError, match="NON_MONOTONIC"):
        stream_m2_first_bar_witnesses(
            market([bar, bar]), expected_m1=2,
        )


def test_m1_trades_count_never_substitutes_source_attestation():
    source, _ = stream_m2_first_bar_witnesses(
        market([m1(7, 3, 0)]), expected_m1=1,
    )
    item = source[("2025-07-15", SessionId.LONDON)]
    assert item["broker_trades_or_fills"] == 0
    assert item["sizing"] == 0
    assert item["M2_QORE_independent_attestation_state"] == "UNKNOWN"
    assert item["M2_QORE_independent_attestation_reasons"]
