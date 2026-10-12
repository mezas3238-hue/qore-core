"""Alpha2 G2 1-second fixed event-time BID ASK quality tests, no broker prices."""
import pytest

from qore.research.alpha2_g2_29_quote_quality_grid import (
    one_second_grid,
    percentile_linear,
)


def test_all_clock_points_missing_never_fake_spread():
    result=one_second_grid([],[],start_ms=100000)
    assert result["clock_points"]==600
    assert result["stale_or_missing"]==600
    assert result["positive_spread_median_bps"] is None
    assert result["positive_spread_p95_bps"] is None


def test_positive_bidask_and_future_quotes_never_seen_early():
    result=one_second_grid(
        [(103000,100000)],[(103000,100020)],start_ms=100000,seconds=10,
    )
    assert result["positive_spread"]==6  # t=103000..108000 inclusive
    assert result["stale_or_missing"]==4  # t=100000..102000 and 109000
    assert result["zero_spread"]==0
    assert result["positive_spread_median_bps"] == pytest.approx(
        20000*20/(100020+100000))


def test_asof_single_second_zero_crossed_positive_distinct():
    result=one_second_grid(
        [(100000,100000),(101000,100000),(102000,100000)],
        [(100000,100000),(101000,99999),(102000,100001)],
        start_ms=100000,seconds=3,
    )
    assert result["zero_spread"]==1
    assert result["crossed"]==1
    assert result["positive_spread"]==1
    assert result["stale_or_missing"]==0


def test_age_5000_inclusive_and_5001_rejected():
    # First tick visible at t=100000, 5 seconds later still valid, 6 stale.
    result=one_second_grid(
        [(100000,100000)],[(100000,100001)],
        start_ms=100000,seconds=8,
    )
    assert result["positive_spread"]==6
    assert result["stale_or_missing"]==2


def test_same_ms_latest_sequence_kept_by_native_order():
    result=one_second_grid(
        [(100000,100000),(100000,100001)],
        [(100000,100001)],
        start_ms=100000,seconds=1,
    )
    assert result["zero_spread"]==1
    assert result["positive_spread"]==0


def test_no_lookahead_for_quote_available_at_next_second():
    x=one_second_grid(
        [(101000,100000)],[(101000,100050)],
        start_ms=100000,seconds=1,
    )
    assert x["stale_or_missing"]==1


def test_malformed_or_unsorted_native_price_fails_closed():
    with pytest.raises(ValueError,match="SIDE_INTEGER_TICK_INVALID"):
        one_second_grid(
            [(101000,100000),(100000,100000)],[(100000,100010)],
            start_ms=100000,seconds=2,
        )
    with pytest.raises(ValueError,match="SIDE_INTEGER_TICK_INVALID"):
        one_second_grid([(100000,True)],[(100000,100001)],
                        start_ms=100000,seconds=1)


def test_frozen_sampling_length_and_age_reject_drift():
    with pytest.raises(ValueError,match="SECOND_GRID_SCOPE_DRIFT"):
        one_second_grid([],[],start_ms=100000,seconds=601)
    with pytest.raises(ValueError,match="SECOND_GRID_SCOPE_DRIFT"):
        one_second_grid([],[],start_ms=100000,max_age_ms=5001)


def test_p95_interpolation_for_known_descriptive_values():
    assert percentile_linear([1.,2.,3.,4.],0.95)==pytest.approx(3.85)
    assert percentile_linear([],0.95) is None
