from __future__ import annotations

from qore.infrastructure.trader_lab.story_forensics_market_board import (
    render_market_board_html,
)


def _stats(entries: int) -> dict[str, object]:
    return {
        "entry_count": entries,
        "win_count": 1 if entries else 0,
        "loss_count": max(entries - 1, 0),
        "win_rate": "0.5" if entries else "0",
        "mean_return_rate": "0.001",
        "compounded_return_rate": "0.002",
        "mean_closed_bar_mfe_r": "0.8",
        "mean_closed_bar_mae_r": "0.6",
        "direct_stop_count": 1 if entries else 0,
        "giveback_count": 1 if entries > 1 else 0,
        "overlap_entry_count": 1 if entries else 0,
        "signal_to_entry_session_transition_count": 0,
        "exit_reasons": {"stop": entries},
        "directions": {"long": entries},
        "entry_phases": {"OPENING": entries},
    }


def _payload() -> dict[str, object]:
    summaries: list[dict[str, object]] = []
    for index, trader in enumerate(("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")):
        summaries.append(
            {
                "trader_code": trader,
                "episode_count": 100 + index,
                "family_status": {},
                "session_breakdown": {
                    "ASIA": _stats(10 + index),
                    "LONDON": _stats(20 + index),
                    "NEW_YORK": _stats(30 + index),
                },
                "outside_primary_session_entry_count": index,
                "forensics_fingerprint": "a" * 64,
            }
        )
    return {
        "schema": "qore.trader_lab.first_cohort_market_story_forensics.v1",
        "research_only": True,
        "execution_authority": False,
        "symbol": "AUDJPY",
        "market_forensics_fingerprint": "b" * 64,
        "trader_summaries": summaries,
    }


def test_market_board_shows_five_traders_and_three_sessions() -> None:
    rendered = render_market_board_html(_payload())

    assert "AUDJPY · 5 Traders · Session Forensics" in rendered
    for trader in ("VT-01", "VT-08", "VT-09", "VT-17", "VT-31"):
        assert trader in rendered
    assert "ASIA" in rendered
    assert "LONDON" in rendered
    assert "NEW YORK" in rendered
    assert "Direct stops" in rendered
    assert "Givebacks" in rendered
    assert "Mean MFE R" in rendered
    assert "Mean MAE R" in rendered
    assert "Outside primary sessions" in rendered
    assert "no execution or real-capital authority" in rendered
