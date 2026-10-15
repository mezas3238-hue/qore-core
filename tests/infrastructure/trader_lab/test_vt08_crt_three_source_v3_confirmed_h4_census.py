"""QORE V3 third-closed-M15 (not V2 two-candle) anti-future safety suite."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_confirmed_h4_census import (
    full_utc_h4_v3_census,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

START = datetime(2025, 3, 3, 0, tzinfo=UTC)


def _row(index: int, values: tuple[int, int, int, int]) -> ReplayBar:
    return ReplayBar(START + timedelta(minutes=5 * index), *values)


def _data(
    *,
    candidate_source_index: int = 1,
    third_close: int = 98,
    third_high: int = 99,
    third_low: int = 91,
    source_close: int = 94,
) -> tuple[ReplayBar, ...]:
    """Construct all source H4 bars and exactly 16 contiguous M15 in H4 C3."""
    out: list[ReplayBar] = []
    for index in range(48):
        out.append(_row(index, (100, 110, 90, 105)))
    for index in range(48, 96):
        out.append(_row(index, (105, 108, 88, 95)))
    for q in range(16):
        if q == candidate_source_index:
            bar = (97, 99, 90, source_close)
        elif q == candidate_source_index + 1:
            bar = (94, third_high, third_low, third_close)
        else:
            bar = (95, 99, 92, 95)
        for n in range(3):
            out.append(_row(96 + q * 3 + n, bar))
    return tuple(out)


def _first_result(bars: tuple[ReplayBar, ...]) -> dict[str, object]:
    _, rows = full_utc_h4_v3_census(CrtPureMarket.AUDUSD, bars)
    assert len(rows) == 2
    return rows[0]


def test_v3_waits_third_closed_candle_not_wick_and_releases_no_order() -> None:
    manifest, records = full_utc_h4_v3_census(
        CrtPureMarket.AUDUSD, _data()
    )
    assert manifest["complete_h4_c1_c2_contexts"] == 2
    assert manifest["state_counts"]["CONCEPTUAL_CANDIDATE_V3"] == 1
    assert records[0]["decision_clock_utc"] == "2025-03-03T08:45:00+00:00"
    assert records[0]["conceptual_state"] == "CONCEPTUAL_CANDIDATE_V3"
    assert records[0]["structural_invalidation_price_if_candidate"] == "90"
    assert records[0]["not_a_trade"] and records[0]["no_sizing_or_capital_authority"]
    assert manifest["GLOBAL_CERTIFIED"] is False


def test_confirming_wick_without_body_close_is_not_confirmation() -> None:
    record = _first_result(_data(third_close=96))
    assert record["conceptual_state"] != "CONCEPTUAL_CANDIDATE_V3"


def test_source_must_close_in_the_correct_direction() -> None:
    record = _first_result(_data(source_close=97))
    assert record["conceptual_state"] != "CONCEPTUAL_CANDIDATE_V3"


def test_confirming_candle_touching_old_target_invalidates_before_decision() -> None:
    record = _first_result(_data(third_high=100))
    assert record["conceptual_state"] == "ABSTAIN_TARGET_CONSUMED"


def test_confirmation_retouching_source_extreme_does_not_promote() -> None:
    record = _first_result(_data(third_low=90))
    assert record["conceptual_state"] == "ABSTAIN_THESIS_INVALIDATED"


def test_first_valid_clock_unchanged_by_arbitrary_postdecision_c3_prices() -> None:
    first = _first_result(_data())
    altered = list(_data())
    # All changes after index 2 M15 has CLOSED at 08:45.
    for n in range(105, len(altered)):
        original = altered[n]
        altered[n] = ReplayBar(original.opened_at, 95, 140, 80, 95)
    other = _first_result(tuple(altered))
    assert first["decision_clock_utc"] == other["decision_clock_utc"]
    assert first["source_event_id"] == other["source_event_id"]
    assert first["conceptual_state"] == other["conceptual_state"]


def test_confirmation_on_final_m15_expires_without_next_h4_peek() -> None:
    record = _first_result(_data(candidate_source_index=14))
    assert record["conceptual_state"] == "EXPIRED_AT_H4_C3_CLOSE"
    assert record["decision_clock_utc"] is None


def test_missing_m5_before_confirmation_fails_closed() -> None:
    broken = tuple(
        row for row in _data()
        if row.opened_at != START + timedelta(minutes=485)
    )
    record = _first_result(broken)
    assert record["conceptual_state"] == "WAIT_DATA_GAP"


def test_fake_duplicate_market_and_empty_source_rejected() -> None:
    data = _data()
    with pytest.raises(ValueError, match="duplicate original M5"):
        full_utc_h4_v3_census(CrtPureMarket.AUDUSD, data + (data[0],))
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        full_utc_h4_v3_census(CrtPureMarket.BTCUSD, data)
    with pytest.raises(ValueError, match="missing original M5"):
        full_utc_h4_v3_census(CrtPureMarket.USDJPY, ())
