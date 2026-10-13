"""Synthetic weekly cross-market TSMOM bootstrap with frozen 33-symbol counts."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from qore.research.alpha2_intermarket import MARKETS
from qore.research.alpha2_tsmom_daily_weekly_panel import (
    _bootstrap,
    era_weeks,
    panel,
)


def synthetic_workers(*, gross=10.0, ctrl_opposed=True, truncate=False):
    events = {}
    blocks = (
        (date(2019, 1, 7), 60, "DEVELOPMENT"),
        (date(2023, 1, 9), 30, "DIAGNOSTIC"),
    )
    for symbol in MARKETS:
        rows = []
        for start, n, era in blocks:
            for i in range(n if not truncate else 1):
                d = start + timedelta(weeks=i)
                week = d.isocalendar()
                rows.append({
                    "symbol": symbol,
                    "era": era,
                    "iso_week": f"{week.year}-W{week.week:02d}",
                    "entry_first_native_M5_open_on_utc_day": d.isoformat(),
                    "strategy_gross_reference_bps": gross,
                    "paired_delta_gross_reference_bps": 2 * gross if ctrl_opposed else 0,
                    "opposed_control": ctrl_opposed,
                    "NET_economic_execution_not_measured": True,
                    "source_provider_BID_ASK_asof": False,
                })
        events[symbol] = {"events": rows}
    return events


def test_exact33_calendar_bootstrap_positive_gross_is_only_exploratory():
    r = panel(synthetic_workers())
    assert r["status"] == "TSMOM_EXPLORATORY_GROSS_SIGNAL_REQUIRES_TRUE_OOS"
    assert r["universe_markets"] == 33
    assert r["original12"] == 12 and r["new21"] == 21
    assert r["historical_2016_2024_panel_was_previously_exposed"]
    assert r["no_independent_OOS_claim"]
    assert not r["broker_NET_PF_Sharpe_DD_computed"]
    assert not r["UTC001_certified"] and r["orders"] == 0
    assert all(a["synchronized_market_calendar_4week_bootstrap"][
        "CI95_mean_portfolio_gross_reference_bps_per_week"][0] > 0
        for a in r["eras"].values())
    assert sum(a["events"] for a in r["per_market"].values()) == 33 * 90


def test_flat_negative_synthetic_outcomes_do_not_pass_positive_screen():
    r = panel(synthetic_workers(gross=-1))
    assert r["status"] == "TSMOM_EXPLORATORY_GROSS_SCREEN_FAIL"
    assert all(a["mean_equal_33_weight_weekly_strategy_gross_reference_bps"] < 0
               for a in r["eras"].values())


def test_underpowered_week_count_never_claims_falsification():
    r = panel(synthetic_workers(truncate=True))
    assert r["status"] == "INCONCLUSIVE_UNDERPOWERED"
    assert all(not a["meets_min_week_gate"] for a in r["eras"].values())


def test_control_undiscriminating_prevents_discovery_label():
    r = panel(synthetic_workers(ctrl_opposed=False))
    assert r["status"] == (
        "TSMOM_EXPLORATORY_GROSS_SCREEN_FAIL_NONDISCRIMINATIVE_CONTROL"
    )


def test_fixed_all33_and_asof_non_net_guards():
    workers = synthetic_workers(truncate=True)
    del workers["AUDJPY"]
    with pytest.raises(ValueError, match="ALL33_MISSING_WORKER"):
        panel(workers)
    workers = synthetic_workers(truncate=True)
    workers["AUDJPY"]["events"][0]["source_provider_BID_ASK_asof"] = True
    with pytest.raises(ValueError, match="GROSS_ONLY_CONTRACT"):
        panel(workers)


def test_four_week_bootstrap_stable_and_calendar_weeks_include_zero():
    a = [(10.0, 2.0)] * 44 + [(0.0, 0.0)] * 12
    b = _bootstrap(a, 20261012)
    assert b == _bootstrap(a, 20261012)
    assert b["bootstrap_draws"] == 2000 and b["block_calendar_weeks"] == 4
    assert len(era_weeks("DEVELOPMENT")) > 300
    assert len(era_weeks("DIAGNOSTIC")) > 100
    with pytest.raises(ValueError, match="UNKNOWN_ERA"):
        era_weeks("ALL")
