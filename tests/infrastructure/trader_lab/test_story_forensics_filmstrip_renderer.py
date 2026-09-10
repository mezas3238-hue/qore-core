from __future__ import annotations

from typing import cast

import pytest

from qore.infrastructure.trader_lab.story_forensics_filmstrip_renderer import (
    StoryForensicsFilmstripError,
    render_filmstrip_html,
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
                "episode_id": "episode-filmstrip",
                "trader_code": "vt-17",
                "symbol": "NAS100",
                "execution_period": "M5",
                "classification": "LOSS_AFTER_1R_OR_MORE",
                "outcome": "loss",
                "decision_time": {
                    "signal_at": "2026-01-01T10:00:00+00:00",
                    "side": "long",
                    "entry_price": "25000",
                    "stop_loss": "24900",
                    "take_profit": "25200",
                    "setup_reason": "cycle-range-sweep",
                    "session": "new-york",
                    "trend_regime": "range",
                    "volatility_regime": "normal",
                    "timeframe": "M5",
                    "narrative": "Decision-time story.",
                },
                "post_outcome": {
                    "filled_at": "2026-01-01T10:05:00+00:00",
                    "exited_at": "2026-01-01T10:25:00+00:00",
                    "exit_reason": "stop",
                    "exit_price": "24900",
                    "return_rate": "-0.004",
                    "close_path_mfe_fraction": "0.006",
                    "close_path_mfe_r": "1.5",
                    "close_path_mfe_at": "2026-01-01T10:15:00+00:00",
                    "close_path_mae_fraction": "0.004",
                    "close_path_mae_r": "1",
                    "close_path_mae_at": "2026-01-01T10:25:00+00:00",
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
                            "open": 25000.0,
                            "high": 25020.0,
                            "low": 24990.0,
                            "close": 25010.0,
                        },
                        {
                            "time": 1767261900,
                            "opened_at": "2026-01-01T10:00:00+00:00",
                            "closed_at": "2026-01-01T10:05:00+00:00",
                            "open": 25010.0,
                            "high": 25050.0,
                            "low": 25000.0,
                            "close": 25030.0,
                        },
                    ],
                    "price_lines": [
                        {"kind": "entry", "price": "25000"},
                        {"kind": "stop_loss", "price": "24900"},
                        {"kind": "take_profit", "price": "25200"},
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
                            "visible_through": "2026-01-01T10:15:00+00:00",
                            "visible_through_unix": 1767262500,
                        },
                        {
                            "stage": "entry",
                            "visible_through": "2026-01-01T10:05:00+00:00",
                            "visible_through_unix": 1767261900,
                        },
                        {
                            "stage": "exit",
                            "visible_through": "2026-01-01T10:25:00+00:00",
                            "visible_through_unix": 1767263100,
                        },
                    ],
                    "screenshot_capable": True,
                },
                "trajectory": [],
            }
        ],
    }


def test_filmstrip_renders_all_frames_with_pinned_lightweight_charts() -> None:
    rendered = render_filmstrip_html(_payload(), episode_id="episode-filmstrip")

    assert "lightweight-charts@5.2.1/+esm" in rendered
    assert "const frames = [...chartData.frame_sequence].sort" in rendered
    assert "a.visible_through_unix - b.visible_through_unix" in rendered
    assert "for (const frame of frames)" in rendered
    assert "createSeriesMarkers" in rendered
    assert "createPriceLine" in rendered
    assert "fetch(" not in rendered


def test_filmstrip_can_export_one_composite_png_from_all_chart_frames() -> None:
    rendered = render_filmstrip_html(_payload(), episode_id="episode-filmstrip")

    assert "Save filmstrip PNG" in rendered
    assert "row.chart.takeScreenshot(true, false)" in rendered
    assert "context.drawImage(captures[index], 0, y)" in rendered
    assert "episode.episode_id}}-filmstrip.png" in rendered


def test_filmstrip_keeps_qore_as_authoritative_source() -> None:
    rendered = render_filmstrip_html(_payload(), episode_id="episode-filmstrip")

    assert "QORE retained evidence is authoritative" in rendered
    assert "TradingView is visualization only" in rendered
    assert "attributionLogo: true" in rendered
    assert "https://www.tradingview.com/" in rendered


def test_filmstrip_escapes_embedded_html_script_breakout() -> None:
    payload = _payload()
    episodes = cast(list[object], payload["episodes"])
    episode = cast(dict[str, object], episodes[0])
    decision = cast(dict[str, object], episode["decision_time"])
    decision["narrative"] = "</script><script>globalThis.compromised=true</script>"

    rendered = render_filmstrip_html(payload, episode_id="episode-filmstrip")

    assert "</script><script>globalThis.compromised" not in rendered
    assert "\\u003c/script\\u003e" in rendered


def test_filmstrip_fails_closed_on_tradingview_authority_claim() -> None:
    payload = _payload()
    contract = cast(dict[str, object], payload["renderer_contract"])
    contract["tradingview_has_execution_authority"] = True

    with pytest.raises(StoryForensicsFilmstripError, match="cannot have execution authority"):
        render_filmstrip_html(payload, episode_id="episode-filmstrip")
