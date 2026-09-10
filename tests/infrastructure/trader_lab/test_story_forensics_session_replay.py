from __future__ import annotations

from typing import cast

from qore.infrastructure.trader_lab.story_forensics_session_replay import (
    render_session_story_html,
)
from tests.infrastructure.trader_lab.test_story_forensics_lightweight_renderer import (
    _payload,
)


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
