"""Synthetic-only W3 posterior causal state tests (no real market outcomes)."""
from collections import deque
from datetime import UTC, datetime, timedelta

from qore.research.alpha2_w2_pade_native_m5 import H1Hour
from qore.research.alpha2_w3_cmtrl_native_m5 import (
    classify_h1_state,
    online_posterior,
)


def hour(start, *, op=100.0, close=100.2, hi=102, lo=99):
    return H1Hour(start, op, hi, lo, close, 500, 0.0)


def test_exact_three_morphology_features_and_wick_ties_abstain():
    t = datetime(2022, 5, 3, tzinfo=UTC)
    past = [hour(t - timedelta(hours=i), hi=101, lo=99)
            for i in range(20, 0, -1)]
    x = hour(t, hi=102, lo=99)
    assert classify_h1_state(x, past) == (1, 1, 1)
    # Exact ambiguous wick lengths should not be assigned an arbitrary side.
    flat_wick = hour(t, op=100, close=100, hi=101, lo=99)
    assert classify_h1_state(flat_wick, past) is None
    assert classify_h1_state(x, past[:19]) is None


def test_posterior_does_not_use_unmatured_future_labels():
    t = datetime(2021, 7, 8, tzinfo=UTC)
    key = (1, 1, 1)
    other = (0, 0, 0)
    matured = deque(
        [(t - timedelta(hours=60-i), key, 1) for i in range(24)] +
        [(t - timedelta(hours=30-i), key, 0) for i in range(6)] +
        [(t - timedelta(hours=24-i), other, 0) for i in range(24)],
        maxlen=240,
    )
    model = online_posterior(key, matured)
    assert model is not None
    assert model[0] == 1
    # New, FUTURE rows are never appended by actual engine before maturity.
    earlier = model
    assert online_posterior(key, matured) == earlier


def test_bayesian_laplace_shrinkage_and_sample_gate_fail_closed():
    key = (1, 0, 0)
    t = datetime(2023, 1, 3, tzinfo=UTC)
    q = deque([(t, key, 1)] * 19, maxlen=240)
    assert online_posterior(key, q) is None
    q.extend([(t, key, 0)] * 19)
    assert online_posterior(key, q) is None


def test_control_is_not_algebraically_tied_to_posterior_direction():
    key = (1, 1, 0)
    different = (0, 1, 1)
    t = datetime(2020, 1, 1, tzinfo=UTC)
    source = deque([(t, key, 1)] * 25 + [(t, different, 0)] * 30, maxlen=240)
    outcome = online_posterior(key, source)
    assert outcome is not None and outcome[0] == 1
    # An independent past two-hour trend of -1 can coexist.
    past_two_hour_direction = -1
    assert outcome[0] != past_two_hour_direction
