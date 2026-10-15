"""V2 later M15 micro CRT admission test; no retrospective winner selection."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_three_source_v2_full_h4_census import (
    full_utc_h4_v2_census,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

BASE = datetime(2025, 3, 3, 0, tzinfo=UTC)


def _bars() -> tuple[ReplayBar, ...]:
    bars: list[ReplayBar] = []
    for i in range(48):
        bars.append(ReplayBar(
            BASE + timedelta(minutes=5 * i), 100, 110, 90, 105
        ))
    for i in range(48):
        bars.append(ReplayBar(
            BASE + timedelta(minutes=240 + 5 * i), 105, 108, 88, 95
        ))
    for i in range(48):
        index = i // 3
        if index == 3:
            values = (95, 98, 92, 96)
        elif index == 4:
            values = (96, 98, 90, 96)
        else:
            values = (95, 98, 92, 95)
        bars.append(ReplayBar(
            BASE + timedelta(minutes=480 + 5 * i), *values
        ))
    return tuple(bars)


def test_later_micro_can_emit_one_conceptual_candidate_per_parent() -> None:
    m, rows = full_utc_h4_v2_census(CrtPureMarket.AUDUSD, _bars())
    assert m["complete_h4_c1_c2_contexts"] == 2
    assert m["states"]["CONCEPTUAL_CANDIDATE"] == 1
    assert rows[0]["first_conceptual_decision_clock_utc"] == (
        "2025-03-03T09:15:00+00:00"
    )
    assert rows[0]["m15_admissible_pairs_examined_until_terminal"] == 4
    assert rows[0]["grants_volume_or_broker_authority"] is False
    assert m["no_PnL"] is True and m["no_sizing"] is True
    assert m["global_certified"] is False


def test_later_unknown_C3_cannot_rewrite_earliest_causal_admission() -> None:
    data = _bars()
    before, all_rows = full_utc_h4_v2_census(CrtPureMarket.AUDUSD, data)
    no_later = tuple(
        bar for bar in data if bar.opened_at < BASE + timedelta(minutes=555)
    )
    after, truncated_rows = full_utc_h4_v2_census(
        CrtPureMarket.AUDUSD, no_later
    )
    assert before["states"]["CONCEPTUAL_CANDIDATE"] == 1
    assert after["states"]["CONCEPTUAL_CANDIDATE"] == 1
    assert all_rows[0]["first_conceptual_decision_clock_utc"] == (
        truncated_rows[0]["first_conceptual_decision_clock_utc"]
    )


def test_if_prior_early_wick_consumes_parent_target_late_candidate_is_blocked() -> None:
    bars = list(_bars())
    at = BASE + timedelta(minutes=480)
    ix = next(i for i, bar in enumerate(bars) if bar.opened_at == at)
    old = bars[ix]
    bars[ix] = ReplayBar(
        old.opened_at, old.open_price, 101, old.low_price, old.close_price
    )
    _, rows = full_utc_h4_v2_census(CrtPureMarket.USDJPY, tuple(bars))
    assert rows[0]["state"] == "ABSTAIN"
    assert rows[0]["why"] == "H4_MIDPOINT_PREVIOUSLY_TOUCHED_OR_CONSUMED"


def test_missing_predecision_m5_must_fail_closed_without_looking_ahead() -> None:
    bars = tuple(
        b for b in _bars()
        if b.opened_at != BASE + timedelta(minutes=485)
    )
    _, rows = full_utc_h4_v2_census(CrtPureMarket.AUDUSD, bars)
    assert rows[0]["state"] == "WAIT"
    assert rows[0]["why"] == "UNCERTAIN_C3_PRICE_PATH_GAP"


def test_bad_source_or_market_rejected() -> None:
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        full_utc_h4_v2_census(CrtPureMarket.BTCUSD, _bars())
    first = _bars()
    with pytest.raises(ValueError, match="duplicate M5"):
        full_utc_h4_v2_census(CrtPureMarket.USDJPY, first + (first[0],))
