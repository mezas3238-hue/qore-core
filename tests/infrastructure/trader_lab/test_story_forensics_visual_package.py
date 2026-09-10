from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from qore.infrastructure.trader_lab.story_forensics_visual_package import (
    StoryForensicsVisualPackageError,
    build_visual_package,
)

_EPISODE_ID = "episode-0123456789abcdef0123"


def _episode() -> dict[str, object]:
    return {
        "episode_id": _EPISODE_ID,
        "trader_code": "vt-08",
        "symbol": "NAS100",
        "execution_period": "M5",
        "classification": "WIN_CANONICAL",
        "outcome": "win",
        "decision_time": {
            "signal_at": "2026-01-01T10:00:00+00:00",
            "side": "short",
            "entry_price": "25000",
            "stop_loss": "25100",
            "take_profit": "24800",
            "setup_reason": "h4-context-test",
            "session": "new-york",
            "trend_regime": "range",
            "volatility_regime": "normal",
            "timeframe": "M5",
            "narrative": "Decision-time story.",
        },
        "post_outcome": {
            "filled_at": "2026-01-01T10:05:00+00:00",
            "exited_at": "2026-01-01T10:20:00+00:00",
            "exit_reason": "target",
            "exit_price": "24800",
            "return_rate": "0.008",
            "close_path_mfe_fraction": "0.008",
            "close_path_mfe_r": "2",
            "close_path_mfe_at": "2026-01-01T10:20:00+00:00",
            "close_path_mae_fraction": "0.001",
            "close_path_mae_r": "0.25",
            "close_path_mae_at": "2026-01-01T10:10:00+00:00",
            "measurement": "closed-bar-path; no intrabar ordering inferred",
            "narrative": "Post-outcome story.",
        },
        "chart": {
            "renderer": "tradingview-lightweight-charts",
            "renderer_version": "5.2.1",
            "source_of_truth": "qore-retained-evidence",
            "bars": [
                {
                    "time": 1767261600,
                    "opened_at": "2026-01-01T09:55:00+00:00",
                    "closed_at": "2026-01-01T10:00:00+00:00",
                    "open": 25010.0,
                    "high": 25020.0,
                    "low": 24990.0,
                    "close": 25000.0,
                }
            ],
            "price_lines": [
                {"kind": "entry", "price": "25000"},
                {"kind": "stop_loss", "price": "25100"},
                {"kind": "take_profit", "price": "24800"},
            ],
            "markers": [
                {
                    "kind": "signal",
                    "time": 1767261600,
                    "at": "2026-01-01T10:00:00+00:00",
                    "label": "SIG",
                }
            ],
            "frame_sequence": [
                {
                    "stage": "signal",
                    "visible_through": "2026-01-01T10:00:00+00:00",
                    "visible_through_unix": 1767261600,
                }
            ],
            "screenshot_capable": True,
        },
        "trajectory": [],
    }


def _payload() -> dict[str, object]:
    streak = {
        "streak_id": "streak-0123456789abcdef0123",
        "outcome": "win",
        "length": 1,
        "start_at": "2026-01-01T10:05:00+00:00",
        "end_at": "2026-01-01T10:20:00+00:00",
        "compounded_return": "0.008",
        "dominant_context_signature": "new-york|range|normal|M5",
        "episode_ids": [_EPISODE_ID],
        "selection_reason": "typical-length",
    }
    episode_ref = {
        "episode_id": _EPISODE_ID,
        "selection_reason": "metric-typical",
        "classification": "WIN_CANONICAL",
    }
    insufficient = {"required": 5, "selected": 1, "status": "INSUFFICIENT_EVIDENCE"}
    return {
        "schema": "qore.trader_lab.first_cohort_story_forensics.v1",
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "source_binding": {
            "symbol": "NAS100",
            "account_fingerprint": "a" * 64,
            "checked_at": "2026-01-02T00:00:00+00:00",
            "software_sha": "b" * 40,
            "trader_code": "vt-08",
            "config_fingerprint": "c" * 64,
            "methodology_fingerprint": "d" * 64,
            "execution_period": "M5",
        },
        "renderer_contract": {
            "default_renderer": "tradingview-lightweight-charts",
            "renderer_version": "5.2.1",
            "license_family": "Apache-2.0",
            "market_data_source": "qore-retained-evidence",
            "tradingview_is_evidence_source": False,
            "tradingview_has_execution_authority": False,
        },
        "family_status": {
            "winning_streaks": dict(insufficient),
            "losing_streaks": dict(insufficient),
            "direct_stop_episodes": dict(insufficient),
            "giveback_episodes": dict(insufficient),
            "canonical_winners": dict(insufficient),
        },
        "story_families": {
            "winning_streaks": [streak],
            "losing_streaks": [streak],
            "direct_stop_episodes": [episode_ref],
            "giveback_episodes": [episode_ref],
            "canonical_winners": [episode_ref],
        },
        "episode_count": 1,
        "episodes": [_episode()],
        "forensics_fingerprint": "e" * 64,
    }


def test_visual_package_materializes_board_replay_filmstrip_and_manifest(
    tmp_path: Path,
) -> None:
    manifest = build_visual_package(_payload(), tmp_path)

    assert (tmp_path / "index.html").is_file()
    assert (tmp_path / "manifest.json").is_file()
    assert (tmp_path / "episodes" / f"{_EPISODE_ID}-replay.html").is_file()
    assert (tmp_path / "episodes" / f"{_EPISODE_ID}-filmstrip.html").is_file()
    assert manifest["schema"] == "qore.trader_lab.story_forensics_visual_package.v1"
    assert manifest["research_only"] is True
    assert manifest["execution_authority"] is False
    assert manifest["selected_episode_ids"] == [_EPISODE_ID]
    files = cast(dict[str, object], manifest["files_sha256"])
    assert len(files) == 3
    assert all(len(cast(str, digest)) == 64 for digest in files.values())


def test_visual_board_exposes_all_required_research_families(tmp_path: Path) -> None:
    build_visual_package(_payload(), tmp_path)
    board = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert "5 winning streaks" in board
    assert "5 losing streaks" in board
    assert "Direct-to-stop episodes" in board
    assert "Profit-then-stop / giveback episodes" in board
    assert "Canonical winners" in board
    assert f"episodes/{_EPISODE_ID}-replay.html" in board
    assert f"episodes/{_EPISODE_ID}-filmstrip.html" in board
    assert "TradingView Lightweight Charts is a visualization surface only" in board


def test_visual_package_deduplicates_episode_files_across_families(tmp_path: Path) -> None:
    build_visual_package(_payload(), tmp_path)

    html_files = sorted((tmp_path / "episodes").glob("*.html"))
    assert [path.name for path in html_files] == [
        f"{_EPISODE_ID}-filmstrip.html",
        f"{_EPISODE_ID}-replay.html",
    ]


def test_visual_package_manifest_on_disk_matches_returned_manifest(tmp_path: Path) -> None:
    manifest = build_visual_package(_payload(), tmp_path)
    decoded = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert decoded == manifest
    assert decoded["renderer"] == "tradingview-lightweight-charts"
    assert decoded["renderer_version"] == "5.2.1"


def test_visual_package_rejects_noncanonical_episode_path_material(tmp_path: Path) -> None:
    payload = _payload()
    episodes = cast(list[object], payload["episodes"])
    episode = cast(dict[str, object], episodes[0])
    episode["episode_id"] = "../../escape"

    with pytest.raises(StoryForensicsVisualPackageError, match="canonical episode id"):
        build_visual_package(payload, tmp_path)


def test_visual_manifest_binds_exact_story_payload_content(tmp_path: Path) -> None:
    first_payload = _payload()
    first_manifest = build_visual_package(first_payload, tmp_path / "first")

    second_payload = _payload()
    second_episodes = cast(list[object], second_payload["episodes"])
    second_episode = cast(dict[str, object], second_episodes[0])
    second_decision = cast(dict[str, object], second_episode["decision_time"])
    second_decision["setup_reason"] = "different-evidence-bound-reason"
    second_manifest = build_visual_package(second_payload, tmp_path / "second")

    first_digest = cast(str, first_manifest["story_payload_sha256"])
    second_digest = cast(str, second_manifest["story_payload_sha256"])
    assert len(first_digest) == 64
    assert len(second_digest) == 64
    assert first_digest != second_digest
