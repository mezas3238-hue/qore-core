from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from qore.infrastructure.trader_lab import (
    first_cohort_market_story_forensics as market_module,
)
from qore.infrastructure.trader_lab.first_cohort_market_story_forensics import (
    run_market_story_forensics,
)


def _story(trader_code: str) -> dict[str, object]:
    return {
        "source_binding": {
            "symbol": "US30",
            "software_sha": "a" * 40,
            "account_fingerprint": "b" * 64,
            "trader_code": trader_code,
        },
        "family_status": {},
        "episode_count": 1,
        "forensics_fingerprint": (trader_code.replace("-", "") + "c" * 64)[:64],
        "episodes": [
            {
                "episode_id": f"episode-{trader_code}",
                "classification": "WIN_CANONICAL",
                "outcome": "win",
                "decision_time": {
                    "signal_at": "2026-01-05T00:05:00+00:00",
                    "side": "long",
                },
                "post_outcome": {
                    "filled_at": "2026-01-05T00:30:00+00:00",
                    "return_rate": "0.02",
                    "exit_reason": "target",
                    "close_path_mfe_r": "2",
                    "close_path_mae_r": "0.2",
                },
            }
        ],
    }


def test_market_story_forensics_runs_all_five_traders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        _market_path: Path,
        _backtest_path: Path,
        _characterization_path: Path,
        trader_code: str,
    ) -> dict[str, object]:
        return _story(trader_code)

    monkeypatch.setattr(market_module, "run_story_forensics", fake_run)
    payload = run_market_story_forensics(
        Path("market.json"),
        Path("backtest.json"),
        Path("characterization.json"),
    )

    assert payload["symbol"] == "US30"
    assert payload["trader_count"] == 5
    assert payload["session_groups"] == ["ASIA", "LONDON", "NEW_YORK"]
    summaries = cast(list[object], payload["trader_summaries"])
    assert [
        cast(dict[str, object], summary)["trader_code"] for summary in summaries
    ] == ["vt-01", "vt-08", "vt-09", "vt-17", "vt-31"]
    for summary in summaries:
        row = cast(dict[str, object], summary)
        breakdown = cast(dict[str, object], row["session_breakdown"])
        asia = cast(dict[str, object], breakdown["ASIA"])
        assert asia["entry_count"] == 1
        assert row["outside_primary_session_entry_count"] == 0
    fingerprint = cast(str, payload["market_forensics_fingerprint"])
    assert len(fingerprint) == 64
