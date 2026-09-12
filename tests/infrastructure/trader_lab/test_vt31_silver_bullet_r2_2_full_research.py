from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_2_full_research import (
    build_payloads,
)


def _trade(index: int, r: str, outcome: str) -> dict[str, object]:
    day = (index % 28) + 1
    return {
        "signal_at": f"2025-01-{day:02d}T15:10:00+00:00",
        "filled_at": f"2025-01-{day:02d}T15:11:00+00:00",
        "resolved_at": f"2025-01-{day:02d}T16:00:00+00:00",
        "side": "short" if index % 2 else "long",
        "entry_price": "100",
        "stop_price": "101",
        "target_price": "97",
        "three_r_price": "97",
        "selected_family": "fair-value-gap" if index % 2 else "breaker",
        "candidate_families": ["fair-value-gap"],
        "breakeven_armed_at": None,
        "outcome": outcome,
        "exit_price": "97" if outcome == "target" else "101",
        "r_multiple": r,
    }


def test_research_package_never_grants_demo_eligible_and_retains_baseline(
    tmp_path: Path,
) -> None:
    trades = [
        _trade(
            index,
            "3" if index % 3 == 0 else "-1",
            "target" if index % 3 == 0 else "stop",
        )
        for index in range(30)
    ]
    payload = {
        "schema": "qore.trader_lab.vt31_r2_2_backtest.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "execution_policy": {"source_rule": False, "policy_id": "test"},
        "daily_cardinality_violations": 0,
        "eligible_market_days": 30,
        "selected_setup_count": 30,
        "filled_count": 30,
        "terminal_sample_size": 30,
        "target_count": 10,
        "stop_count": 20,
        "breakeven_count": 0,
        "win_rate": "0.3333333333333333333333333333",
        "expectancy_r": "0.3333333333333333333333333333",
        "max_drawdown_r": "3",
        "abstain_counts": {},
        "containment_counts": {},
        "ledgers": [],
        "trades": trades,
    }
    path = tmp_path / "backtest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    outputs = build_payloads(path)
    summary = cast(dict[str, object], outputs["research-summary.json"])
    assert summary["demo_eligible"] is False
    assert summary["execution_profile_is_source_rule"] is False
    comparison = cast(dict[str, object], summary["baseline_comparison"])
    baseline = cast(dict[str, object], comparison["baseline"])
    assert baseline["filled_count"] == 90
    governance = cast(dict[str, object], summary["holdout_governance"])
    assert governance[
        "fresh_previously_unseen_holdout_required_after_any_hypothesis_change"
    ] is True
