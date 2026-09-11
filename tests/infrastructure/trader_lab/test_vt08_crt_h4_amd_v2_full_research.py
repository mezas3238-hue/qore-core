import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt08_crt_h4_amd_v2_full_research import (
    generate_full_research,
)


def _source_audit(path: Path, count: int = 12) -> Path:
    start = datetime(2024, 1, 2, 5, tzinfo=UTC)
    rows: list[dict[str, object]] = []
    for index in range(count):
        signal = start + timedelta(days=index)
        rows.append(
            {
                "scenario_candidate": (
                    "reversal-expansion-candle2"
                    if index % 2 == 0
                    else "continuation-expansion-candle3"
                ),
                "anchor_opened_at": signal.isoformat(),
                "h4_closes_at": (signal + timedelta(hours=4)).isoformat(),
                "proposed_side": "long" if index % 2 == 0 else "short",
                "signal_at": (signal + timedelta(minutes=30)).isoformat(),
                "entry_observation": "100",
                "protected_swing_extreme": "99",
                "cisd_level": "99.5",
                "source_bias_status": "requires-source-context-confirmation",
                "source_wick_status": "qualitative-unresolved-by-video",
                "prior_candle2_wick_status": None,
                "automatic_setup": False,
                "post_signal_h4_close_r_descriptive_only": "0.5",
                "mfe_r_descriptive_only": "1.2",
                "mae_r_descriptive_only": "0.4",
                "post_signal_path_is_not_trade_result": True,
            }
        )
    payload: dict[str, object] = {
        "schema": "qore.trader_lab.vt08_crt_h4_amd_v2_source_audit.v3",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "source_fidelity_mode": True,
        "invalidates_prior_campaign": True,
        "prior_13468_campaign_valid_for_economics": False,
        "software_sha": "a" * 40,
        "symbol": "EURUSD",
        "eligible_anchor_windows": 100,
        "missing_anchor_windows": 3,
        "mechanical_candidate_count": len(rows),
        "source_judgment_required_count": len(rows),
        "automatic_setup_count": 0,
        "filled_count": 0,
        "win_count": None,
        "loss_count": None,
        "economic_backtest_authorized": False,
        "candidates": rows,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_full_research_emits_evidence_without_fake_economics(tmp_path: Path) -> None:
    output = tmp_path / "out"
    summary = generate_full_research(_source_audit(tmp_path / "audit.json"), output)
    assert {item.name for item in output.iterdir()} == {
        "walk-forward.json",
        "characterization.json",
        "stress.json",
        "monte-carlo.json",
        "failure-analysis.json",
        "story-forensics.json",
        "hypothesis-register.json",
        "research-summary.json",
    }
    assert summary["mechanical_candidate_count"] == 12
    assert summary["automatic_setup_count"] == 0
    assert summary["economic_result_available"] is False
    assert summary["win_count"] is None
    assert summary["loss_count"] is None
    assert summary["demo_eligible"] is False

    characterization = json.loads((output / "characterization.json").read_text())
    assert characterization["oracle_metrics_are_not_trade_results"] is True
    assert characterization["win_rate"] is None
    assert characterization["expectancy_r"] is None

    stress = json.loads((output / "stress.json").read_text())
    monte = json.loads((output / "monte-carlo.json").read_text())
    assert stress["status"] == "not-run"
    assert stress["pass"] is None
    assert monte["status"] == "not-run"
    assert monte["pass"] is None


def test_story_forensics_separates_candidate_decision_data_from_oracle(
    tmp_path: Path,
) -> None:
    output = tmp_path / "out"
    generate_full_research(_source_audit(tmp_path / "audit.json", count=3), output)
    story = json.loads((output / "story-forensics.json").read_text())
    assert story["decision_time_oracle_separation"] is True
    assert story["episode_count"] == 3
    first = cast(dict[str, object], story["episodes"][0])
    decision = cast(dict[str, object], first["decision_time"])
    assert decision["automatic_setup"] is False
    assert "h4_close_r" not in decision
    assert "post_outcome_oracle_descriptive_only" in first
