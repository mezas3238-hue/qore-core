import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_crt_159_v3_full_research import (
    generate_full_research,
)


def _backtest(path: Path, count: int = 40) -> Path:
    start = datetime(2024, 1, 2, 16, 30, tzinfo=UTC)
    trades = []
    for index in range(count):
        signal = start + timedelta(days=index)
        terminal = index % 5 != 0
        outcome = "target" if index % 3 else "stop"
        trades.append(
            {
                "signal_at": signal.isoformat(),
                "filled_at": signal.isoformat(),
                "resolved_at": (
                    (signal + timedelta(minutes=45)).isoformat() if terminal else None
                ),
                "side": "long" if index % 2 == 0 else "short",
                "entry_price": "100",
                "stop_loss": "99",
                "take_profit": "102",
                "daily_target": "105",
                "outcome": outcome if terminal else "h4_close_censored",
                "r_multiple": ("2" if outcome == "target" else "-1") if terminal else None,
                "mfe_r": "2.1" if terminal else "0.7",
                "mae_r": "1" if outcome == "stop" else "0.4",
                "daily_target_touched": False,
            }
        )
    payload = {
        "schema": "qore.trader_lab.vt08_crt_159_v3_backtest.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": "a" * 40,
        "symbol": "EURUSD",
        "decision_days": 100,
        "daily_context_pass": 70,
        "h4_159_pass": 55,
        "h1_nested_pass": 48,
        "m15_nested_pass": 44,
        "direction_agreement_pass": 40,
        "daily_target_touch_count": 3,
        "trades": trades,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_v3_full_research_emits_all_evidence_and_stays_research_only(
    tmp_path: Path,
) -> None:
    output = tmp_path / "out"
    summary = generate_full_research(_backtest(tmp_path / "backtest.json"), output)
    assert set(item.name for item in output.iterdir()) == {
        "walk-forward.json",
        "characterization.json",
        "stress.json",
        "monte-carlo.json",
        "failure-analysis.json",
        "story-forensics.json",
        "hypothesis-register.json",
        "research-summary.json",
    }
    walk = json.loads((output / "walk-forward.json").read_text())
    assert walk["in_sample_fraction"] == "0.70"
    assert walk["oos_fraction"] == "0.30"
    assert walk["source_frozen_configuration"] is True
    assert walk["parameter_search_performed"] is False
    assert walk["holdout_governance"]["state"] == "consumed_for_research"
    story = json.loads((output / "story-forensics.json").read_text())
    assert story["episode_count"] == 40
    assert story["decision_time_oracle_separation"] is True
    monte = json.loads((output / "monte-carlo.json").read_text())
    assert monte["governed_stage_authority"] is False
    assert summary["demo_eligible"] is False
    assert summary["governed_lifecycle_authority"] is False


def test_v3_monte_carlo_is_deterministic(tmp_path: Path) -> None:
    backtest = _backtest(tmp_path / "backtest.json", count=50)
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_full_research(backtest, first)
    generate_full_research(backtest, second)
    assert (first / "monte-carlo.json").read_bytes() == (
        second / "monte-carlo.json"
    ).read_bytes()
