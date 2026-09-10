from __future__ import annotations

from typing import cast

from qore.infrastructure.trader_lab.story_forensics_session_replay import (
    render_session_story_html,
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
                            "stage": "entry",
                            "visible_through": "2026-01-01T10:15:00+00:00",
                            "visible_through_unix": 1767262500,
                        },
                        {
                            "stage": "mfe",
                            "visible_through": "2026-01-01T10:30:00+00:00",
                            "visible_through_unix": 1767263400,
                        },
                    ],
                    "screenshot_capable": True,
                },
                "trajectory": [],
            }
        ],
    }


def test_session_replay_exposes_exact_entry_context() -> None:
    payload = _payload()
    episodes = cast(list[object], payload["episodes"])
    episode = cast(dict[str, object], episodes[0])
    decision = cast(dict[str, object], episode["decision_time"])
    decision["session_context"] = {
        "calendar_id": "qore-major-trading-sessions-v1",
        "signal": {
            "primary_session": "LONDON",
            "active_sessions": ["LONDON"],
            "overlap": False,
            "phase": "CORE",
            "local_at": "2026-01-01T10:00:00+00:00",
            "minutes_since_open": 120,
            "minutes_to_close": 300,
        },
        "entry": {
            "primary_session": "NEW_YORK",
            "active_sessions": ["LONDON", "NEW_YORK"],
            "overlap": True,
            "phase": "OPENING",
            "local_at": "2026-01-01T08:15:00-05:00",
            "minutes_since_open": 15,
            "minutes_to_close": 525,
        },
        "signal_to_entry_session_transition": True,
    }

    rendered = render_session_story_html(payload, episode_id="episode-123")

    assert "Session context" in rendered
    assert "Signal session" in rendered
    assert "Entry session" in rendered
    assert "LONDON, NEW_YORK" in rendered
    assert "OPENING" in rendered
    assert "Minutes since open" in rendered
    assert ">15<" in rendered
    assert "Session transition" in rendered
    assert ">true<" in rendered
    assert "TradingView is visualization only" in rendered
