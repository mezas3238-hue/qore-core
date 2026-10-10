from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from qore.infrastructure.trader_lab import (
    first_cohort_market_story_forensics as market_module,
)
from qore.infrastructure.trader_lab.first_cohort_market_story_forensics import (
    run_market_story_forensics,
)
from qore.infrastructure.trader_lab.first_cohort_story_forensics import (
    FirstCohortStoryForensicsError,
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
                "chart": {
                    "frame_sequence": [
                        {
                            "stage": "signal",
                            "visible_through": "2026-01-05T00:05:00+00:00",
                            "visible_through_unix": 1767571500,
                        },
                        {
                            "stage": "entry",
                            "visible_through": "2026-01-05T00:30:00+00:00",
                            "visible_through_unix": 1767573000,
                        },
                    ]
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
    monkeypatch.setattr(market_module, "_file_digest", lambda _path: "d" * 64)
    payload = run_market_story_forensics(
        Path("market.json"),
        Path("backtest.json"),
        Path("characterization.json"),
    )

    assert payload["symbol"] == "US30"
    assert payload["trader_count"] == 5
    assert payload["session_groups"] == ["ASIA", "LONDON", "NEW_YORK"]
    summaries = cast(list[object], payload["trader_summaries"])
    assert [cast(dict[str, object], summary)["trader_code"] for summary in summaries] == [
        "vt-01",
        "vt-08",
        "vt-09",
        "vt-17",
        "vt-31",
    ]
    for summary in summaries:
        row = cast(dict[str, object], summary)
        breakdown = cast(dict[str, object], row["session_breakdown"])
        asia = cast(dict[str, object], breakdown["ASIA"])
        assert asia["entry_count"] == 1
        assert row["outside_primary_session_entry_count"] == 0
    fingerprint = cast(str, payload["market_forensics_fingerprint"])
    assert len(fingerprint) == 64
    assert len(cast(str, payload["market_forensics_payload_digest"])) == 64


def test_market_story_certifies_provider_alias_and_rejects_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        _market_path: Path,
        _backtest_path: Path,
        _characterization_path: Path,
        trader_code: str,
    ) -> dict[str, object]:
        story = _story(trader_code)
        binding = cast(dict[str, object], story["source_binding"])
        binding["symbol"] = "USTEC"
        return story

    monkeypatch.setattr(market_module, "run_story_forensics", fake_run)
    market = tmp_path / "market.json"
    backtest = tmp_path / "backtest.json"
    characterization = tmp_path / "characterization.json"
    for path in (market, backtest, characterization):
        path.write_text("{}", encoding="utf-8")
    identity = {
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "economic_identity_certified": True,
        "account_fingerprint": "b" * 64,
        "economic_target": "NAS100",
        "binding_basis": "certified-alias-v1",
        "provider_symbol": {"symbol_name": "USTEC"},
    }
    identity_path = tmp_path / "provider-identity.json"
    identity_path.write_text(json.dumps(identity), encoding="utf-8")
    status = {
        "stage": "MARKET_EVIDENCE",
        "terminal_state": "PASS",
        "collect_outcome": "success",
        "resolve_outcome": "success",
        "economic_target": "NAS100",
        "source_sha": "a" * 40,
        "market_evidence_sha256": sha256(market.read_bytes()).hexdigest(),
        "provider_identity_sha256": sha256(identity_path.read_bytes()).hexdigest(),
    }
    status_path = tmp_path / "stage1-status.json"
    status_path.write_text(json.dumps(status), encoding="utf-8")

    payload = run_market_story_forensics(
        market,
        backtest,
        characterization,
        identity_path,
        status_path,
    )
    assert payload["symbol"] == "NAS100"
    assert payload["provider_symbol"] == "USTEC"

    identity["economic_target"] = "SP500"
    identity_path.write_text(json.dumps(identity), encoding="utf-8")
    with pytest.raises(
        FirstCohortStoryForensicsError,
        match="economic target substitution|identity digest mismatch",
    ):
        run_market_story_forensics(
            market,
            backtest,
            characterization,
            identity_path,
            status_path,
        )
