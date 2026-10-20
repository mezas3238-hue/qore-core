"""R7 DST-aware pattern evidence. Synthetic tests never certify broker hours."""
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_crt_original_fx_weekly_close_forensics import (
    GAP_TARGETS,
    _ny_friday_close,
    examine_original_fx_weekly_close_gaps,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

M5 = timedelta(minutes=5)
NY = ZoneInfo("America/New_York")


def bar(stamp: datetime) -> ReplayBar:
    return ReplayBar(
        opened_at=stamp, open_price=100, high_price=101,
        low_price=99, close_price=100,
    )


def rows(market: CrtPureMarket) -> tuple[dict, ...]:
    return tuple({
        "market": market.value, "source_event_id": f"e-{i}",
        "first_missing_original_m5_opened_at_utc": when,
        "gm4_terminal_remains_UNKNOWN": True,
        "forensics_is_expost_only": True,
        "observed_issue": "SOURCE_M5_GAP",
        "no_sizing": True, "G_M4_PASS": False,
    } for i, when in enumerate(GAP_TARGETS[market]))


def fixture(market: CrtPureMarket) -> tuple[ReplayBar, ...]:
    stamps = set()
    for when in GAP_TARGETS[market]:
        target = datetime.fromisoformat(when)
        if target.astimezone(NY).weekday() == 4:
            # All 17 comparison Fridays show the same preclose/no-after pattern.
            for i in range(-8, 9):
                center = target.astimezone(NY)
                friday = center.date() + timedelta(
                    days=(4 - center.weekday()) + i * 7
                )
                cut = datetime.combine(friday, time(17), NY).astimezone(UTC)
                stamps.add(cut - M5)
        else:
            # Wed 22:30 UTC has exactly one missing candle in active stream.
            stamps.add(target - M5)
            stamps.add(target + M5)
    return tuple(bar(x) for x in sorted(stamps))


def test_ny_1700_is_dst_sensitive_on_exact_years() -> None:
    edt_2025 = datetime.fromisoformat("2025-04-25T21:00:00+00:00")
    edt_2026 = datetime.fromisoformat("2026-06-19T21:00:00+00:00")
    est_2025 = datetime.fromisoformat("2025-02-07T22:00:00+00:00")
    assert _ny_friday_close(edt_2025) == edt_2025
    assert _ny_friday_close(edt_2026) == edt_2026
    assert _ny_friday_close(est_2025) == est_2025


@pytest.mark.parametrize("market,expected_weekly,expected_midweek", [
    (CrtPureMarket.AUDUSD, 1, 0),
    (CrtPureMarket.USDJPY, 1, 1),
])
def test_weekly_close_is_empirically_consistent_not_authorized(
    market: CrtPureMarket, expected_weekly: int, expected_midweek: int,
) -> None:
    summary, evidence = examine_original_fx_weekly_close_gaps(
        market, fixture(market), rows(market)
    )
    assert len(evidence) == expected_weekly + expected_midweek
    states = summary["diagnostics"]
    assert states.get("CONVENTION_CONSISTENT_PROVIDER_CALENDAR_UNVERIFIED", 0) == (
        expected_weekly
    )
    assert states.get("INTERNAL_ONE_BAR_GAP_PROVIDER_SOURCE_REQUIRED", 0) == (
        expected_midweek
    )
    assert summary["G_M4_PASS"] is False
    assert summary["terminal_adjudicated"] is False
    for row in evidence:
        assert row["gm4_original_terminal_remains_unknown"]
        assert not row["broker_specific_historical_calendar_authenticated"]
        assert row["G_M5_ISSUED"] is False
        assert row["not_a_trade"] and row["no_sizing"]
        assert row["no_rearm_authority"]
        if row["conventional_ny_friday_1700"]:
            assert row["neighbor_fridays_measured"] == 17
            assert row["neighbor_fridays_convention_pattern_matches"] == 17
        else:
            assert row["previous_m5_present"] and row["next_m5_present"]


def test_an_actual_bar_in_missing_slot_is_hard_failure() -> None:
    m = CrtPureMarket.AUDUSD
    target = datetime.fromisoformat(GAP_TARGETS[m][0])
    with pytest.raises(ValueError, match="actually exists"):
        examine_original_fx_weekly_close_gaps(
            m, (*fixture(m), bar(target)), rows(m)
        )


def test_false_gm4_approval_is_denied() -> None:
    m = CrtPureMarket.AUDUSD
    claim = list(rows(m))
    claim[0]["G_M4_PASS"] = True
    with pytest.raises(ValueError, match="forged"):
        examine_original_fx_weekly_close_gaps(m, fixture(m), tuple(claim))


def test_missing_neighbor_cannot_prove_convention_consistency() -> None:
    m = CrtPureMarket.AUDUSD
    out = examine_original_fx_weekly_close_gaps(m, (bar(
        datetime.fromisoformat("2025-04-24T21:00:00+00:00")
    ),), rows(m))[1][0]
    assert out["diagnostic_status"] == "NOT_CONSISTENT_NEEDS_PROVIDER_CALENDAR"
    assert not out["terminal_adjudicated"]


def test_cross_market_date_and_duplicate_timestamp_rejected() -> None:
    m = CrtPureMarket.AUDUSD
    source = fixture(m)
    with pytest.raises(ValueError, match="duplicate original M5"):
        examine_original_fx_weekly_close_gaps(m, (*source, source[0]), rows(m))
    with pytest.raises(ValueError, match="frozen R6 gap identity"):
        examine_original_fx_weekly_close_gaps(
            m, source, rows(CrtPureMarket.USDJPY)
        )
