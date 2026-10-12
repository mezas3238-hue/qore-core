"""Only synthetic PADE feature proofs. No broker historical prices in tests."""
from datetime import UTC, datetime, timedelta

from qore.research.alpha2_intermarket import M5, Bar
from qore.research.alpha2_w2_pade_native_m5 import (
    H1,
    H1Hour,
    NativeM5,
    complete_hours,
    propose,
)


def make_hour(at, *, volume=100, imbalance=0.5, start=100, end=100.05):
    return H1Hour(at, start, 101.0, 99.0, end, volume, imbalance)


def synthetic_fixture():
    at = datetime(2023, 6, 15, 10, tzinfo=UTC)
    earlier = {at - k * H1: make_hour(at - k * H1)
               for k in range(1, 21)}
    # Independent PRE-event two-hour trend is down, current imbalance points up.
    earlier[at - 3*H1] = make_hour(at-3*H1, end=100.0)
    earlier[at - H1] = make_hour(at-H1, end=99.0)
    for days in range(1, 11):
        earlier[at - timedelta(days=days)] = make_hour(
            at - timedelta(days=days), volume=100
        )
    return at, earlier


def test_pade_strategy_is_not_algebraically_identical_to_baseline():
    at, history = synthetic_fixture()
    proposal, code = propose(make_hour(at, volume=200, imbalance=0.70), history)
    assert code == "EVENT"
    assert proposal["direction"] == 1
    assert proposal["control_direction"] == -1
    assert proposal["activity_ratio"] == 2.0
    assert proposal["entry_utc"] == (at + H1 + M5).isoformat()
    assert proposal["stop_distance_price"] == 2.0


def test_no_future_h1_can_alter_causal_decision():
    at, history = synthetic_fixture()
    current = make_hour(at, volume=200, imbalance=-0.65)
    previous = propose(current, history)
    history[at + H1] = make_hour(at + H1, volume=500000, imbalance=1.0)
    assert previous == propose(current, history)
    assert previous[0]["direction"] == -1


def test_low_activity_and_high_displacement_fail_closed():
    at, history = synthetic_fixture()
    assert propose(make_hour(at, volume=120), history)[1] == (
        "ACTIVITY_SHOCK_NOT_ABNORMAL"
    )
    assert propose(make_hour(at, volume=200, end=100.8), history)[1] == (
        "H1_DISPLACEMENT_NOT_ABSORBED"
    )


def test_donor_history_at_same_utc_hour_is_mandatory():
    at, history = synthetic_fixture()
    history.pop(at - timedelta(days=1))
    assert propose(make_hour(at, volume=250), history)[1] == (
        "MISSING_TEN_SAME_UTC_HOUR_HISTORY_DAYS"
    )


def test_twenty_h1_missing_censors_signal_instead_of_filling():
    at, history = synthetic_fixture()
    history.pop(at - H1)
    assert propose(make_hour(at, volume=200), history)[1] == (
        "MISSING_TWENTY_PRIOR_CONTIGUOUS_HOURS"
    )


def test_complete_h1_exact_twelve_native_M5_without_interpolation():
    at = datetime(2022, 7, 8, 11, tzinfo=UTC)
    rows = {}
    for i in range(12):
        t = at + i * M5
        bar = Bar(t, 100, 101, 99, 100.1 if i % 2 == 0 else 99.9)
        rows[t] = NativeM5(bar, 25)
    hours = complete_hours(rows)
    assert hours[at].volume_sum == 300
    assert hours[at].weighted_signed_imbalance == 0.0
    rows.pop(at + 3 * M5)
    assert complete_hours(rows) == {}
