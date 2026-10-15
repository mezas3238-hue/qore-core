"""Frozen UTC-H4 census uses all complete H4 parents, not cherry-picked cases."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_three_source_v1_full_h4_census import (
    full_utc_h4_census,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

BASE = datetime(2025, 3, 3, 0, 0, tzinfo=UTC)


def _bar(minute: int, o: int, h: int, lo: int, close: int) -> ReplayBar:
    return ReplayBar(
        BASE + timedelta(minutes=minute), o, h, lo, close
    )


def _m5() -> tuple[ReplayBar, ...]:
    rows = []
    for i in range(48):
        rows.append(_bar(i * 5, 100, 110, 90, 105))
    for i in range(48):
        rows.append(_bar(240 + i * 5, 105, 108, 88, 95))
    for i in range(48):
        minute = 480 + i * 5
        if i < 3:
            rows.append(_bar(minute, 95, 99, 92, 97))
        elif i < 6:
            rows.append(_bar(minute, 97, 99, 90, 96))
        else:
            rows.append(_bar(minute, 96, 98, 94, 96))
    return tuple(rows)


def test_all_parent_pairs_included_and_conceptual_not_order() -> None:
    summary, records = full_utc_h4_census(CrtPureMarket.AUDUSD, _m5())
    assert summary["complete_utc_h4"] == 3
    assert summary["complete_h4_c1_c2_contexts"] == 2
    assert len(records) == 2
    assert summary["conceptual_states"]["CONCEPTUAL_CANDIDATE"] == 1
    assert records[0]["first30_clock_utc"] == "2025-03-03T08:30:00+00:00"
    assert summary["sizing_used"] is False and summary["PnL_computed"] is False
    assert summary["not_fresh_holdout"] and not summary["global_certified"]


def test_saving_or_changing_later_c3_bars_must_not_change_earliest_event() -> None:
    original = _m5()
    summary_a, results_a = full_utc_h4_census(CrtPureMarket.AUDUSD, original)
    first_six_only = tuple(
        bar for bar in original if bar.opened_at < BASE + timedelta(minutes=510)
    )
    summary_b, results_b = full_utc_h4_census(
        CrtPureMarket.AUDUSD, first_six_only
    )
    assert summary_a["conceptual_states"]["CONCEPTUAL_CANDIDATE"] == 1
    assert summary_b["conceptual_states"]["CONCEPTUAL_CANDIDATE"] == 1
    assert results_a[0]["why"] == results_b[0]["why"]
    assert results_a[0]["first30_clock_utc"] == results_b[0]["first30_clock_utc"]


def test_missing_m5_in_first_30_minutes_yields_wait_not_fake_bar() -> None:
    broken = tuple(
        bar for bar in _m5()
        if bar.opened_at != BASE + timedelta(minutes=485)
    )
    _, result = full_utc_h4_census(CrtPureMarket.USDJPY, broken)
    assert result[0]["conceptual_state"] == "WAIT"
    assert result[0]["why"] == "M15_PREFIX_MISSING_FIRST30"


def test_duplicate_clock_and_missing_feed_rejected() -> None:
    original = _m5()
    with pytest.raises(ValueError, match="duplicate source"):
        full_utc_h4_census(CrtPureMarket.AUDUSD, original + (original[0],))
    with pytest.raises(ValueError, match="missing original"):
        full_utc_h4_census(CrtPureMarket.AUDUSD, ())


def test_btc_is_still_frozen_without_cibo_trade_authority() -> None:
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        full_utc_h4_census(CrtPureMarket.BTCUSD, _m5())
