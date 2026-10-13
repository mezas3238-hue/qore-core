"""QORE Alpha2 G1A panel inference tests, fully synthetic."""
from datetime import date

import pytest

from qore.research.alpha2_g1a_panel_stats import (
    _full_weeks,
    _gross_pf,
    block_bootstrap,
)


def event(week, delta, observed=True):
    return {"iso_week":week, "paired_observed":observed,
            "paired_delta_gross_bps":delta if observed else None}


def test_no_events_cannot_create_significance():
    r = block_bootstrap([], era="DIAGNOSTIC", length=4, draws=20)
    assert r["p_centered_two_sided"] == 1
    assert r["ci95_bps"] is None
    assert r["weeks_with_events"] == 0


def test_week_clusters_include_all_empty_calendar_weeks():
    ws = _full_weeks(date(2022, 9, 17), date(2024, 9, 17))
    assert len(ws) > 100
    assert "2023-W01" in ws
    assert len(ws) == len(set(ws))


def test_sign_is_event_weighted_not_equal_week_weight():
    events = [event("2023-W01", 10.0)] * 3 + [event("2023-W02", -10.0)]
    r = block_bootstrap(events, era="DIAGNOSTIC", length=1, draws=20)
    assert r["mean_delta_bps"] == pytest.approx(5.0)
    assert r["week_clusters"] > 100


def test_frozen_three_block_sizes_only():
    with pytest.raises(ValueError):
        block_bootstrap([], era="DIAGNOSTIC", length=3)
    with pytest.raises(ValueError):
        block_bootstrap([], era="FAKE", length=1)


def test_no_fake_infinite_profit_factor():
    assert _gross_pf([]) is None
    assert _gross_pf([1, 2, 3]) is None
    assert _gross_pf([2, -1, -1]) == 1.0
