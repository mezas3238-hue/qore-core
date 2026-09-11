import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_crt_h4_amd_v2_full_research import (
    generate_full_research,
)


def _backtest(path: Path) -> Path:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    rows: list[dict[str, object]] = []
    for index in range(30):
        outcome = "target" if index % 3 == 0 else "stop"
        r_multiple = "2" if outcome == "target" else "-1"
        rows.append(
            {
                "signal_at": (start + timedelta(days=index)).isoformat(),
                "resolved_at": (start + timedelta(days=index, minutes=30)).isoformat(),
                "side": "long" if index % 2 == 0 else "short",
                "scenario": (
                    "candle2-expansion"
                    if index % 2 == 0
                    else "candle3-continuation"
                ),
                "entry_price": "100",
                "stop_loss": "95",
                "take_profit": "110",
                "outcome": outcome,
                "r_multiple": r_multiple,
                "mark_to_market_r_at_h4_close": r_multiple,
                "mfe_r": "2",
                "mae_r": "1",
                "cisd_level": "99",
                "manipulation_fraction_of_reference": "0.4",
            }
        )
    for index in range(5):
        rows.append(
            {
                "signal_at": (start + timedelta(days=40 + index)).isoformat(),
                "resolved_at": None,
                "side": "long",
                "scenario": "candle2-expansion",
                "entry_price": "100",
                "stop_loss": "95",
                "take_profit": "110",
                "outcome": "h4_close_censored",
                "r_multiple": None,
                "mark_to_market_r_at_h4_close": "1.2",
                "mfe_r": "1.5",
                "mae_r": "0.5",
                "cisd_level": "99",
                "manipulation_fraction_of_reference": "0.4",
            }
        )
    payload: dict[str, object] = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_backtest.v2",
        "read_only": True,
        "research_only": True,
        "invalidates_prior_campaign": True,
        "software_sha": "a" * 40,
        "symbol": "EURUSD",
        "decision_days": 100,
        "daily_bias_pass": 60,
        "candle2_setup_count": 20,
        "candle3_candidate_count": 40,
        "trades": rows,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_positive_censored_mark_never_becomes_research_win(tmp_path: Path) -> None:
    output = tmp_path / "out"
    summary = generate_full_research(_backtest(tmp_path / "backtest.json"), output)
    metrics = summary["all_history"]
    assert isinstance(metrics, dict)
    assert metrics["setup_count"] == 35
    assert metrics["terminal_sample_size"] == 30
    assert metrics["target_count"] == 10
    assert metrics["stop_count"] == 20
    assert metrics["censored_count"] == 5
    assert summary["demo_eligible"] is False
    characterization = json.loads((output / "characterization.json").read_text())
    assert characterization["positive_h4_close_mark_is_win"] is False


def test_reconstructed_research_is_deterministic_and_emits_full_family(
    tmp_path: Path,
) -> None:
    backtest = _backtest(tmp_path / "backtest.json")
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_full_research(backtest, first)
    generate_full_research(backtest, second)
    assert (first / "monte-carlo.json").read_bytes() == (
        second / "monte-carlo.json"
    ).read_bytes()
    assert {item.name for item in first.iterdir()} == {
        "walk-forward.json",
        "characterization.json",
        "stress.json",
        "monte-carlo.json",
        "failure-analysis.json",
        "story-forensics.json",
        "hypothesis-register.json",
        "research-summary.json",
    }
