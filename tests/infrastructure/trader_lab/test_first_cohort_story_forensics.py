from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from qore.infrastructure.trader_lab.first_cohort_story_forensics import (
    FirstCohortStoryForensicsError,
    run_story_forensics,
)

_ACCOUNT = "a" * 64
_SOFTWARE_SHA = "b" * 40
_SYMBOL = "EURUSD"


def _bar(opened_at: datetime, *, minutes: int, close: float) -> dict[str, object]:
    return {
        "opened_at": opened_at.isoformat(),
        "closed_at": (opened_at + timedelta(minutes=minutes)).isoformat(),
        "open": f"{close:.6f}",
        "high": f"{close + 0.001:.6f}",
        "low": f"{close - 0.001:.6f}",
        "close": f"{close:.6f}",
    }


def _coverage(rows: list[dict[str, object]]) -> dict[str, object]:
    first = datetime.fromisoformat(cast(str, rows[0]["opened_at"]))
    last = datetime.fromisoformat(cast(str, rows[-1]["closed_at"]))
    return {
        "bar_count": len(rows),
        "first_opened_at": first.isoformat(),
        "last_closed_at": last.isoformat(),
        "span_seconds": int((last - first).total_seconds()),
    }


def _write_market(tmp_path: Path) -> tuple[Path, list[dict[str, object]]]:
    anchor = datetime(2024, 1, 1, tzinfo=UTC)
    recent = datetime(2026, 1, 3, tzinfo=UTC)
    closes = [1.0] * 90
    for trade_index in range(20):
        signal_index = 1 + trade_index * 4
        fill_index = signal_index + 1
        exit_index = signal_index + 2
        closes[signal_index] = 1.0
        if trade_index % 2 == 0:
            closes[fill_index] = 1.005
            closes[exit_index] = 1.02
        elif (trade_index // 2) % 2 == 0:
            closes[fill_index] = 0.995
            closes[exit_index] = 0.99
        else:
            closes[fill_index] = 1.012
            closes[exit_index] = 0.99
    recent_m5 = [
        _bar(recent + timedelta(minutes=5 * index), minutes=5, close=close)
        for index, close in enumerate(closes)
    ]
    m5 = [_bar(anchor, minutes=5, close=1.0), *recent_m5]
    m15 = [
        _bar(anchor, minutes=15, close=1.0),
        _bar(recent + timedelta(hours=10), minutes=15, close=1.0),
    ]
    h4 = [
        _bar(anchor, minutes=240, close=1.0),
        _bar(recent + timedelta(hours=12), minutes=240, close=1.0),
    ]
    payload = {
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "trading_permission_verified": True,
        "account_fingerprint": _ACCOUNT,
        "symbol": {"symbol_name": _SYMBOL},
        "checked_at": (recent + timedelta(days=1)).isoformat(),
        "software_sha": _SOFTWARE_SHA,
        "required_coverage_days": 730,
        "requested_lookback_days": 760,
        "periods": {"M1": [], "M5": m5, "M15": m15, "H4": h4},
        "coverage": {
            "M5": _coverage(m5),
            "M15": _coverage(m15),
            "H4": _coverage(h4),
        },
    }
    path = tmp_path / "market.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, recent_m5


def _trade(
    *,
    signal_at: str,
    filled_at: str,
    exited_at: str,
    winner: bool,
    giveback: bool,
) -> dict[str, object]:
    if winner:
        exit_price = "1.02"
        return_rate = "0.02"
        reason = "target"
    else:
        exit_price = "0.99"
        return_rate = "-0.01"
        reason = "stop"
    return {
        "trader_code": "vt-01",
        "signal_at": signal_at,
        "filled_at": filled_at,
        "exited_at": exited_at,
        "side": "long",
        "entry_price": "1",
        "stop_loss": "0.99",
        "take_profit": "1.02",
        "exit_price": exit_price,
        "return_rate": return_rate,
        "exit_reason": reason,
        "test_giveback": giveback,
    }


def _write_backtest(
    tmp_path: Path,
    recent_m5: list[dict[str, object]],
) -> tuple[Path, list[dict[str, object]]]:
    trades: list[dict[str, object]] = []
    for trade_index in range(20):
        signal_index = 1 + trade_index * 4
        fill_index = signal_index + 1
        exit_index = signal_index + 2
        winner = trade_index % 2 == 0
        giveback = not winner and (trade_index // 2) % 2 == 1
        trades.append(
            _trade(
                signal_at=cast(str, recent_m5[signal_index]["closed_at"]),
                filled_at=cast(str, recent_m5[fill_index]["closed_at"]),
                exited_at=cast(str, recent_m5[exit_index]["closed_at"]),
                winner=winner,
                giveback=giveback,
            )
        )
    payload = {
        "schema": "qore.trader_lab.first_cohort_backtest.v1",
        "environment": "demo",
        "read_only": True,
        "account_fingerprint": _ACCOUNT,
        "symbol": _SYMBOL,
        "checked_at": datetime(2026, 1, 4, tzinfo=UTC).isoformat(),
        "software_sha": _SOFTWARE_SHA,
        "execution_model": "limit-3bar-fill-24bar-hold-stop-first-v1",
        "results": [
            {
                "trader_code": "vt-01",
                "execution_period": "M5",
                "setup_count": 20,
                "unfilled_setup_count": 0,
                "sample_size": 20,
                "mean_return": "0.005",
                "win_rate": "0.5",
                "population_variance": "0",
                "trades": trades,
            }
        ],
    }
    path = tmp_path / "backtest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, trades


def _write_characterization(
    tmp_path: Path,
    trades: list[dict[str, object]],
) -> Path:
    setups = [
        {
            "signal_at": trade["signal_at"],
            "side": "long",
            "entry_price": "1",
            "signal_close": "1",
            "entry_offset_from_signal_close_fraction": "0",
            "stop_distance": "0.01",
            "target_distance": "0.02",
            "risk_fraction": "0.01",
            "reward_fraction": "0.02",
            "reward_risk_multiple": "2",
            "setup_reason": "canonical-test-setup",
            "timeframe": "M5",
            "session": "new-york",
            "trend_regime": "range" if index % 3 else "mixed",
            "volatility_regime": "normal",
            "filled": True,
            "fill_at": trade["filled_at"],
            "exit_at": trade["exited_at"],
            "exit_reason": trade["exit_reason"],
            "return_rate": trade["return_rate"],
            "close_path_mfe_fraction": "0",
            "close_path_mae_fraction": "0",
        }
        for index, trade in enumerate(trades)
    ]
    payload = {
        "schema": "qore.trader_lab.first_cohort_characterization.v1",
        "environment": "demo",
        "read_only": True,
        "symbol": _SYMBOL,
        "account_fingerprint": _ACCOUNT,
        "checked_at": datetime(2026, 1, 4, tzinfo=UTC).isoformat(),
        "software_sha": _SOFTWARE_SHA,
        "holdout_governance": {
            "state": "consumed_for_research",
            "analysis_reads_oos": True,
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "fresh_unseen_holdout_required_after_methodology_change": True,
            "source_symbol": _SYMBOL,
            "source_account_fingerprint": _ACCOUNT,
            "source_checked_at": datetime(2026, 1, 4, tzinfo=UTC).isoformat(),
            "source_software_sha": _SOFTWARE_SHA,
        },
        "results": [
            {
                "trader_code": "vt-01",
                "profiles": [
                    {
                        "profile": "production-default",
                        "config_fingerprint": "c" * 64,
                        "methodology_identity": {
                            "trader_version": "v1",
                            "methodology_id": "vt-01",
                            "methodology_version": "v1",
                            "methodology_fingerprint": "d" * 64,
                            "timeframe": "M5",
                            "session": "new-york",
                        },
                        "execution_period": "M5",
                        "setups": setups,
                    }
                ],
            }
        ],
    }
    path = tmp_path / "characterization.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _evidence(tmp_path: Path) -> tuple[Path, Path, Path]:
    market, recent_m5 = _write_market(tmp_path)
    backtest, trades = _write_backtest(tmp_path, recent_m5)
    characterization = _write_characterization(tmp_path, trades)
    return market, backtest, characterization


def test_story_forensics_builds_all_required_visual_families(tmp_path: Path) -> None:
    market, backtest, characterization = _evidence(tmp_path)

    payload = run_story_forensics(market, backtest, characterization, "vt-01")

    assert payload["schema"] == "qore.trader_lab.first_cohort_story_forensics.v1"
    assert payload["research_only"] is True
    assert payload["execution_authority"] is False
    assert payload["episode_count"] == 20
    renderer = cast(dict[str, object], payload["renderer_contract"])
    assert renderer["default_renderer"] == "tradingview-lightweight-charts"
    assert renderer["renderer_version"] == "5.2.1"
    assert renderer["market_data_source"] == "qore-retained-evidence"
    assert renderer["tradingview_is_evidence_source"] is False
    assert renderer["tradingview_has_execution_authority"] is False

    statuses = cast(dict[str, object], payload["family_status"])
    for family in (
        "winning_streaks",
        "losing_streaks",
        "direct_stop_episodes",
        "giveback_episodes",
        "canonical_winners",
    ):
        status = cast(dict[str, object], statuses[family])
        assert status == {"required": 5, "selected": 5, "status": "READY"}


def test_story_forensics_separates_direct_stops_from_givebacks(tmp_path: Path) -> None:
    market, backtest, characterization = _evidence(tmp_path)

    payload = run_story_forensics(market, backtest, characterization, "vt-01")
    families = cast(dict[str, object], payload["story_families"])
    episodes = cast(list[object], payload["episodes"])
    by_id = {
        cast(str, cast(dict[str, object], item)["episode_id"]): cast(dict[str, object], item)
        for item in episodes
    }
    direct = cast(list[object], families["direct_stop_episodes"])
    giveback = cast(list[object], families["giveback_episodes"])
    assert len(direct) == 5
    assert len(giveback) == 5

    for row in direct:
        episode = by_id[cast(str, cast(dict[str, object], row)["episode_id"])]
        assert episode["classification"] == "LOSS_DIRECT_NO_EDGE"
        post = cast(dict[str, object], episode["post_outcome"])
        assert float(cast(str, post["close_path_mfe_r"])) <= 0.25

    for row in giveback:
        episode = by_id[cast(str, cast(dict[str, object], row)["episode_id"])]
        assert episode["classification"] == "LOSS_AFTER_1R_OR_MORE"
        post = cast(dict[str, object], episode["post_outcome"])
        assert float(cast(str, post["close_path_mfe_r"])) >= 1.0
        assert cast(str, post["close_path_mfe_at"]) < cast(str, post["exited_at"])


def test_story_forensics_keeps_decision_and_oracle_state_separate(tmp_path: Path) -> None:
    market, backtest, characterization = _evidence(tmp_path)

    payload = run_story_forensics(market, backtest, characterization, "vt-01")
    epistemic = cast(dict[str, object], payload["epistemic_contract"])
    assert epistemic["decision_time_and_post_outcome_separated"] is True
    assert epistemic["intrabar_ordering_inferred"] is False

    episode = cast(dict[str, object], cast(list[object], payload["episodes"])[0])
    decision = cast(dict[str, object], episode["decision_time"])
    post = cast(dict[str, object], episode["post_outcome"])
    assert "close_path_mfe_r" not in decision
    assert "exit_reason" not in decision
    assert "close_path_mfe_r" in post
    chart = cast(dict[str, object], episode["chart"])
    assert chart["source_of_truth"] == "qore-retained-evidence"
    assert chart["screenshot_capable"] is True


def test_story_forensics_is_deterministic_for_identical_evidence(tmp_path: Path) -> None:
    market, backtest, characterization = _evidence(tmp_path)

    first = run_story_forensics(market, backtest, characterization, "vt-01")
    second = run_story_forensics(market, backtest, characterization, "vt-01")

    assert first["forensics_fingerprint"] == second["forensics_fingerprint"]
    assert first["story_families"] == second["story_families"]
    assert first["episodes"] == second["episodes"]


def test_story_forensics_fails_closed_on_evidence_binding_mismatch(tmp_path: Path) -> None:
    market, backtest, characterization = _evidence(tmp_path)
    decoded = cast(
        dict[str, object], json.loads(characterization.read_text(encoding="utf-8"))
    )
    decoded["software_sha"] = "e" * 40
    characterization.write_text(json.dumps(decoded), encoding="utf-8")

    with pytest.raises(
        FirstCohortStoryForensicsError,
        match="market/characterization software SHA mismatch",
    ):
        run_story_forensics(market, backtest, characterization, "vt-01")


def test_story_forensics_fingerprint_binds_exact_source_artifact_bytes(
    tmp_path: Path,
) -> None:
    market, backtest, characterization = _evidence(tmp_path)

    first = run_story_forensics(market, backtest, characterization, "vt-01")
    first_binding = cast(dict[str, object], first["source_binding"])
    first_digests = cast(dict[str, object], first_binding["source_artifact_sha256"])
    assert set(first_digests) == {"market", "backtest", "characterization"}
    assert all(len(cast(str, value)) == 64 for value in first_digests.values())

    original = characterization.read_text(encoding="utf-8")
    assert "canonical-test-setup" in original
    characterization.write_text(
        original.replace("canonical-test-setup", "changed-test-setup", 1),
        encoding="utf-8",
    )
    second = run_story_forensics(market, backtest, characterization, "vt-01")
    second_binding = cast(dict[str, object], second["source_binding"])
    second_digests = cast(dict[str, object], second_binding["source_artifact_sha256"])

    assert first_digests["market"] == second_digests["market"]
    assert first_digests["backtest"] == second_digests["backtest"]
    assert first_digests["characterization"] != second_digests["characterization"]
    assert first["forensics_fingerprint"] != second["forensics_fingerprint"]
    second_episode = cast(dict[str, object], cast(list[object], second["episodes"])[0])
    second_decision = cast(dict[str, object], second_episode["decision_time"])
    assert second_decision["setup_reason"] == "changed-test-setup"
