"""Truth audit for VT08 Cognitive Expansion 5M density and Profit Factor.

This audit deliberately separates:
1. raw/equal-risk VT08 methodology economics;
2. managed-r Core Stack economics;
3. capital weighting (not applied here).

All five markets are evaluated on the same immutable 1095-day evidence artifacts
from run 35934924907. No market selection or retuning is allowed.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Final, cast

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    stack_rows,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
    metrics,
    run_market_backtest,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    EXPANSION_MARKETS,
)

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_5m_density_pf_truth_audit.v1"
SOURCE_RUN_ID: Final = 35934924907
SOURCE_HEAD: Final = "b2d33e1b4829d8b4afc76983decca8a99131403c"


def _d(payload: dict[str, object], key: str) -> Decimal | None:
    raw = payload[key]
    if raw is None:
        return None
    return Decimal(str(raw))


def evaluate(path: Path) -> dict[str, object]:
    _fingerprint, symbol, checked_at, software_sha, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside frozen VT08 5M universe")

    baseline_report = run_market_backtest(path)
    baseline = cast(dict[str, object], baseline_report["economics"]).copy()
    stack = stack_rows(path)
    managed = metrics(tuple(row.as_trade() for row in stack))

    baseline_count_raw = baseline["sample_size"]
    managed_count_raw = managed["sample_size"]
    if not isinstance(baseline_count_raw, int) or not isinstance(managed_count_raw, int):
        raise ValueError("trade sample sizes must be ints")
    baseline_count = baseline_count_raw
    managed_count = managed_count_raw
    if baseline_count != managed_count:
        raise AssertionError("Core Stack changed VT08 trade density")

    first_open = min(bar.opened_at for bar in bars)
    last_close = max(bar.closed_at for bar in bars)
    coverage_days = Decimal(str((last_close - first_open).total_seconds())) / Decimal("86400")
    annualized = (
        Decimal(baseline_count) * Decimal("365") / coverage_days
        if coverage_days > 0
        else Decimal(0)
    )
    two_year_equivalent = annualized * Decimal("2")

    baseline_pf = _d(baseline, "profit_factor")
    managed_pf = _d(managed, "profit_factor")

    return {
        "schema": SCHEMA,
        "source_run_id": SOURCE_RUN_ID,
        "source_head": SOURCE_HEAD,
        "market": symbol,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "coverage": {
            "first_m15": first_open.isoformat(),
            "last_m15_close": last_close.isoformat(),
            "coverage_days": format(coverage_days, "f"),
        },
        "density": {
            "terminal_trades": baseline_count,
            "annualized_trades": format(annualized, "f"),
            "two_year_equivalent_trades": format(two_year_equivalent, "f"),
            "candidate_count_before_daily_uniqueness": baseline_report["candidate_count"],
            "multiple_candidate_day_count": baseline_report["multiple_candidate_day_count"],
            "incomplete_exit_window_count": baseline_report["incomplete_exit_window_count"],
            "by_anchor_ny": baseline_report["by_anchor_ny"],
            "by_side": baseline_report["by_side"],
        },
        "profit_factor_truth": {
            "vt08_equal_risk_pf": (
                None if baseline_pf is None else format(baseline_pf, "f")
            ),
            "vt08_equal_risk_total_r": baseline["total_r"],
            "vt08_equal_risk_dd_r": baseline["max_drawdown_r"],
            "core_stack_managed_r_pf": (
                None if managed_pf is None else format(managed_pf, "f")
            ),
            "core_stack_managed_r_total_r": managed["total_r"],
            "core_stack_managed_r_dd_r": managed["max_drawdown_r"],
            "capital_weighting_applied": False,
            "capital_weighted_pf": None,
        },
        "governance": {
            "all_five_markets_reported": True,
            "market_selection": False,
            "anchor_selection": False,
            "side_selection": False,
            "trade_filtering": False,
            "capital_weighting": False,
            "density_optimization": False,
            "research_only": True,
            "live_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
