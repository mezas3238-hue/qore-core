from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_full_research import (
    Vt31SilverBulletV2FullResearchError,
    build_vt31_silver_bullet_v2_full_research_payloads,
)

_SHA = "1" * 40


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _market() -> dict[str, object]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    rows: list[dict[str, object]] = []
    for index in range(1000):
        opened = start + timedelta(minutes=index)
        rows.append(
            {
                "opened_at": _iso(opened),
                "closed_at": _iso(opened + timedelta(minutes=1)),
                "open": "100",
                "high": "104",
                "low": "96",
                "close": "100",
            }
        )
    return {
        "schema": "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1",
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "required_coverage_days": 730,
        "source_authorized_market": "NAS100",
        "symbol": {"symbol_name": "NAS100"},
        "software_sha": _SHA,
        "periods": {"M1": rows},
    }


def _trade(index: int, *, after_split: bool) -> dict[str, object]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    base_index = 720 + index * 3 if after_split else 50 + index * 3
    signal = start + timedelta(minutes=base_index + 1)
    filled = signal + timedelta(minutes=1)
    resolved = filled + timedelta(minutes=1)
    target = index % 2 == 0
    side = "long" if index % 2 == 0 else "short"
    return {
        "signal_at": _iso(signal),
        "filled_at": _iso(filled),
        "resolved_at": _iso(resolved),
        "side": side,
        "entry_price": "100",
        "stop_loss": "99" if side == "long" else "101",
        "take_profit": "102" if side == "long" else "98",
        "exit_price": "102" if target and side == "long" else (
            "98" if target else ("99" if side == "long" else "101")
        ),
        "outcome": "target" if target else "stop",
        "r_multiple": "2" if target else "-1",
    }


def _backtest() -> dict[str, object]:
    trades = [
        *(_trade(index, after_split=False) for index in range(30)),
        *(_trade(index, after_split=True) for index in range(20)),
    ]
    return {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_backtest.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "trader_code": "vt-31",
        "trader_version": "v2",
        "methodology": "silver-bullet-am-nq-v2",
        "symbol": "NAS100",
        "software_sha": _SHA,
        "decision_days": 80,
        "setup_count": 60,
        "filled_count": len(trades),
        "unfilled_setup_count": 10,
        "pending_gap_count": 0,
        "trades": trades,
    }


def test_full_research_emits_all_trader_lab_evidence_families() -> None:
    result = build_vt31_silver_bullet_v2_full_research_payloads(
        _market(),
        _backtest(),
    )

    assert set(result) == {
        "walk-forward.json",
        "characterization.json",
        "stress.json",
        "monte-carlo.json",
        "failure-analysis.json",
        "story-forensics.json",
        "hypothesis-register.json",
        "research-summary.json",
    }

    walk_forward = result["walk-forward.json"]
    assert walk_forward["configuration_selection"] == "source_frozen_no_parameter_search"
    assert walk_forward["in_sample_pass"] is True
    assert walk_forward["oos_pass"] is True
    governance = cast(dict[str, object], walk_forward["holdout_governance"])
    assert governance["state"] == "consumed_for_research"
    assert governance["new_previously_unseen_holdout_required_after_any_hypothesis_change"] is True

    characterization = result["characterization.json"]
    funnel = cast(dict[str, object], characterization["decision_funnel"])
    assert funnel["setup_count"] == 60
    assert funnel["filled_count"] == 50
    assert funnel["unfilled_setup_count"] == 10
    assert cast(dict[str, object], characterization["parameter_sensitivity"])["status"] == "not_applicable"

    stress = result["stress.json"]
    assert stress["stress_pass"] is True
    assert stress["governed_stage_authority"] is False

    monte_carlo = result["monte-carlo.json"]
    assert monte_carlo["status"] == "qualified"
    assert monte_carlo["governed_stage_authority"] is False
    policy = cast(dict[str, object], monte_carlo["policy"])
    assert policy["algorithm"] == "qore-circular-block-bootstrap-v1"
    assert policy["simulation_count"] == 5000

    stories = result["story-forensics.json"]
    assert stories["trade_story_count"] == 50
    assert len(cast(list[object], stories["stories"])) == 50

    summary = result["research-summary.json"]
    assert summary["walk_forward_oos_pass"] is True
    assert summary["stress_pass"] is True
    assert summary["monte_carlo_status"] == "qualified"
    assert summary["demo_eligible"] is False


def test_full_research_monte_carlo_is_deterministic() -> None:
    first = build_vt31_silver_bullet_v2_full_research_payloads(_market(), _backtest())
    second = build_vt31_silver_bullet_v2_full_research_payloads(_market(), _backtest())

    assert first["monte-carlo.json"] == second["monte-carlo.json"]


def test_full_research_fails_closed_on_software_sha_mismatch() -> None:
    market = _market()
    backtest = _backtest()
    backtest["software_sha"] = "2" * 40

    with pytest.raises(
        Vt31SilverBulletV2FullResearchError,
        match="software SHA must match",
    ):
        build_vt31_silver_bullet_v2_full_research_payloads(market, backtest)
