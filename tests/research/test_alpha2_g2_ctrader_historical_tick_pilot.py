"""Only synthetic official backward-delta historical BID ASK source tests."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.research.alpha2_g2_ctrader_historical_tick_pilot import (
    END_MS,
    START_MS,
    classify_pilot,
    decode_newest_first,
)


def test_newest_first_first_absolute_then_backward_deltas():
    rows = [(START_MS + 900, 109975), (-500, -2), (-250, -1)]
    data = decode_newest_first(rows)
    assert [x["provider_tick_at_ms"] for x in data] == [
        START_MS + 150, START_MS + 400, START_MS + 900,
    ]
    assert [x["raw_tick_price_1e5"] for x in data] == [
        109972, 109973, 109975,
    ]


def test_ask_and_bid_are_separate_immutable_legs_not_synthetic_spread():
    result = classify_pilot(
        bid_rows=[(START_MS + 750, 109970)],
        ask_rows=[(START_MS + 500, 109974)],
        bid_has_more=False, ask_has_more=False,broker_verified=True,
    )
    assert result["bid_count"] == result["ask_count"] == 1
    assert result["bid_last_ms"] != result["ask_last_ms"]
    assert "spread" not in result


def test_has_more_cannot_masquerade_as_full_tick_history():
    with pytest.raises(ValueError, match="TRUNCATED"):
        classify_pilot(
            bid_rows=[(START_MS + 400, 109970)],
            ask_rows=[(START_MS + 400, 109974)],
            bid_has_more=True,ask_has_more=False,broker_verified=True,
        )


def test_no_quote_side_is_not_zero_spread():
    with pytest.raises(ValueError, match="NO_HISTORIC_TICKS"):
        classify_pilot(
            bid_rows=[],ask_rows=[(START_MS + 100, 109973)],
            bid_has_more=False,ask_has_more=False,broker_verified=True,
        )


def test_end_exclusive_and_reverse_overflow_invalid():
    with pytest.raises(ValueError, match="OUTSIDE"):
        decode_newest_first([(END_MS,109970)])
    with pytest.raises(ValueError, match="OUTSIDE"):
        decode_newest_first([(START_MS + 100,109970),(-200,-1)])
    with pytest.raises(ValueError,match="BAD_CTRADER_TICK_TYPE"):
        decode_newest_first([(START_MS+100, True)])


def test_window_max_one_week_and_no_broker_proof():
    with pytest.raises(ValueError,match="BAD_WINDOW"):
        decode_newest_first([(START_MS + 1, 109970)],
                            end_ms=START_MS + 604800001)
    with pytest.raises(ValueError,match="BROKER_OR_PAGINATION"):
        classify_pilot(bid_rows=[],ask_rows=[],bid_has_more=False,
                       ask_has_more=False,broker_verified=False)


def test_fixed_pilot_is_in_consumed_not_holdout_period():
    start=datetime.fromtimestamp(START_MS/1000,tz=UTC)
    end=datetime.fromtimestamp(END_MS/1000,tz=UTC)
    assert end-start==timedelta(minutes=1)
    assert end < datetime(2024, 9, 17, tzinfo=UTC)

def test_signed_time_and_signed_price_delta_must_reconstruct_real_quote():
    raw = [(START_MS + 900, 121234), (-350, -7), (0, 3)]
    observed = decode_newest_first(raw)
    assert [v["provider_tick_at_ms"] for v in observed] == [
        START_MS + 550, START_MS + 550, START_MS + 900,
    ]
    assert [v["raw_tick_price_1e5"] for v in observed] == [
        121230, 121227, 121234,
    ]


def test_positive_time_delta_is_invalid_even_if_newer_quote_is_in_window():
    with pytest.raises(ValueError, match="BAD_CTRADER_SIGNED_DELTA"):
        decode_newest_first([(START_MS+300, 120000), (100, 1)])
