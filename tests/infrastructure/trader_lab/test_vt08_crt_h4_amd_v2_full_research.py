import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_crt_h4_amd_v2_full_research import (
    generate_full_research,
)


def _backtest(path: Path, count: int = 40) -> Path:
    start = datetime(2024, 1, 2, tzinfo=UTC)
    trades = []
    for index in range(count):
        signal = start + timedelta(days=index, hours=10)
        side = "long" if index % 2 == 0 else "short"
        profile = "continuation-expansion" if index % 3 else "reversal-expansion"
        r_value = "0.60" if index % 4 else "-1"
        trades.append(
            {
                "signal_at": signal.isoformat(),
                "filled_at": signal.isoformat(),
                "resolved_at": (signal + timedelta(hours=2)).isoformat(),
                "side": side,
                "profile": profile,
                "htf_closure": (
                    "range-expansion-closure"
                    if profile == "continuation-expansion"
                    else "candle2-reversal-closure"
                ),
                "entry_price": "100",
                "stop_loss": "99" if side == "long" else "101",
                "exit_price": (
                    "100.6"
                    if r_value != "-1"
                    else ("99" if side == "long" else "101")
                ),
                "outcome": "h4_close" if r_value != "-1" else "stop",
                "r_multiple": r_value,
                "mfe_r": "0.8",
                "mae_r": "0.4" if r_value != "-1" else "1",
                "h4_opened_at": (signal - timedelta(hours=1)).isoformat(),
                "h4_closed_at": (signal + timedelta(hours=3)).isoformat(),
            }
        )
    payload = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_backtest.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": "a" * 40,
        "symbol": "EURUSD",
        "complete_h4_windows": 100,
        "eligible_h4_windows": 80,
        "terminal_sample_size": len(trades),
        "trades": trades,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_full_research_emits_complete_evidence_family_and_governance(tmp_path: Path) -> None:
    output = tmp_path / "research"
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
    assert (
        walk["holdout_governance"]
        ["fresh_previously_unseen_holdout_required_after_any_change"]
        is True
    )
    story = json.loads((output / "story-forensics.json").read_text())
    assert story["episode_count"] == 40
    assert story["decision_time_oracle_separation"] is True
    monte = json.loads((output / "monte-carlo.json").read_text())
    assert monte["governed_stage_authority"] is False
    assert summary["demo_eligible"] is False
    assert summary["governed_lifecycle_authority"] is False


def test_monte_carlo_is_deterministic(tmp_path: Path) -> None:
    backtest = _backtest(tmp_path / "backtest.json", count=50)
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_full_research(backtest, first)
    generate_full_research(backtest, second)
    assert (first / "monte-carlo.json").read_bytes() == (
        second / "monte-carlo.json"
    ).read_bytes()
