from __future__ import annotations

from typing import cast

import pytest

from qore.infrastructure.trader_lab.story_forensics_lightweight_renderer import (
    StoryForensicsRendererError,
    render_story_html,
)


def _payload() -> dict[str, object]:
    return {
        "schema": "qore.trader_lab.first_cohort_story_forensics.v1",
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "renderer_contract": {
            "default_renderer": "tradingview-lightweight-charts",
            "renderer_version": "5.2.1",
            "license_family": "Apache-2.0",
            "market_data_source": "qore-retained-evidence",
            "tradingview_is_evidence_source": False,
            "tradingview_has_execution_authority": False,
        },
        "episodes": [
            {
                "episode_id": "episode-123",
                "trader_code": "vt-09",
                "symbol": "NAS100",
                "execution_period": "M15",
                "classification": "LOSS_AFTER_1R_OR_MORE",
                "outcome": "loss",
                "decision_time": {
                    "signal_at": "2026-01-01T10:00:00+00:00",
                    "side": "short",
                    "entry_price": "25000",
                    "stop_loss": "25100",
                    "take_profit": "24800",
                    "setup_reason": "turtle-soup-test",
                    "session": "new-york",
                    "trend_regime": "range",
                    "volatility_regime": "normal",
                    "timeframe": "M15",
                    "narrative": "Decision-time evidence only.",
                },
                "post_outcome": {
                    "filled_at": "2026-01-01T10:15:00+00:00",
                    "exited_at": "2026-01-01T11:00:00+00:00",
                    "exit_reason": "stop",
                    "exit_price": "25100",
                    "return_rate": "-0.004",
                    "close_path_mfe_fraction": "0.005",
                    "close_path_mfe_r": "1.25",
                    "close_path_mfe_at": "2026-01-01T10:30:00+00:00",
                    "close_path_mae_fraction": "0.004",
                    "close_path_mae_r": "1",
                    "close_path_mae_at": "2026-01-01T11:00:00+00:00",
                    "measurement": "closed-bar-path; no intrabar ordering inferred",
                    "narrative": "Post-outcome evidence only.",
                },
                "chart": {
                    "renderer": "tradingview-lightweight-charts",
                    "renderer_version": "5.2.1",
                    "source_of_truth": "qore-retained-evidence",
                    "bars": [
                        {
                            "time": 1767261600,
                            "opened_at": "2026-01-01T09:45:00+00:00",
                            "closed_at": "2026-01-01T10:00:00+00:00",
                            "open": 25010.0,
                            "high": 25020.0,
                            "low": 24980.0,
                            "close": 25000.0,
                        },
                        {
                            "time": 1767262500,
                            "opened_at": "2026-01-01T10:00:00+00:00",
                            "closed_at": "2026-01-01T10:15:00+00:00",
                            "open": 25000.0,
                            "high": 25010.0,
                            "low": 24920.0,
                            "close": 24950.0,
                        },
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
                            "stage": "mfe",
                            "visible_through": "2026-01-01T10:30:00+00:00",
                            "visible_through_unix": 1767263400,
                        },
                        {
                            "stage": "entry",
                            "visible_through": "2026-01-01T10:15:00+00:00",
                            "visible_through_unix": 1767262500,
                        },
                    ],
                    "screenshot_capable": True,
                },
                "trajectory": [],
            }
        ],
    }


def test_renderer_pins_lightweight_charts_and_never_fetches_market_data() -> None:
    rendered = render_story_html(_payload(), episode_id="episode-123")

    assert "lightweight-charts@5.2.1/+esm" in rendered
    assert "createChart" in rendered
    assert "CandlestickSeries" in rendered
    assert "createSeriesMarkers" in rendered
    assert "createPriceLine" in rendered
    assert "takeScreenshot(true, false)" in rendered
    assert "fetch(" not in rendered
    assert "qore-retained-evidence" in rendered
    assert "TradingView is visualization only" in rendered
    assert "https://www.tradingview.com/" in rendered
    assert "attributionLogo: true" in rendered


def test_renderer_sorts_replay_frames_by_evidence_timestamp() -> None:
    rendered = render_story_html(_payload(), episode_id="episode-123")

    assert "a.visible_through_unix - b.visible_through_unix" in rendered
    assert "const frames = [...chartData.frame_sequence].sort" in rendered


def test_renderer_separates_chronological_replay_from_full_forensic_view() -> None:
    rendered = render_story_html(_payload(), episode_id="episode-123")

    assert "Chronological replay" in rendered
    assert "Oracle / post-outcome permitted" in rendered
    assert "chartData.bars.filter(row => row.time <= through)" in rendered
    assert "decision.narrative" in rendered
    assert "post.narrative" in rendered


def test_renderer_escapes_embedded_story_text() -> None:
    payload = _payload()
    episodes = cast(list[object], payload["episodes"])
    episode = cast(dict[str, object], episodes[0])
    decision = cast(dict[str, object], episode["decision_time"])
    decision["narrative"] = "</script><script>globalThis.compromised=true</script>"

    rendered = render_story_html(payload, episode_id="episode-123")

    assert "</script><script>globalThis.compromised" not in rendered
    assert "\\u003c/script\\u003e" in rendered


def test_renderer_fails_closed_if_tradingview_is_declared_evidence_source() -> None:
    payload = _payload()
    contract = cast(dict[str, object], payload["renderer_contract"])
    contract["tradingview_is_evidence_source"] = True

    with pytest.raises(StoryForensicsRendererError, match="cannot be an evidence source"):
        render_story_html(payload, episode_id="episode-123")
