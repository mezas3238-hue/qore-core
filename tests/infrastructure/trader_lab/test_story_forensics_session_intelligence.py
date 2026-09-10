from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from qore.infrastructure.trader_lab.story_forensics_session_intelligence import (
    classify_market_session,
    enrich_story_payload_sessions,
)


def _episode(
    *,
    episode_id: str,
    signal_at: datetime,
    filled_at: datetime,
    outcome: str,
    return_rate: str,
    classification: str,
    exit_reason: str,
    mfe_r: str,
    mae_r: str,
) -> dict[str, object]:
    return {
        "episode_id": episode_id,
        "classification": classification,
        "outcome": outcome,
        "decision_time": {
            "signal_at": signal_at.isoformat(),
            "side": "long",
        },
        "post_outcome": {
            "filled_at": filled_at.isoformat(),
            "return_rate": return_rate,
            "exit_reason": exit_reason,
            "close_path_mfe_r": mfe_r,
            "close_path_mae_r": mae_r,
        },
        "chart": {
            "frame_sequence": [
                {
                    "stage": "signal",
                    "visible_through": signal_at.isoformat(),
                    "visible_through_unix": int(signal_at.timestamp()),
                },
                {
                    "stage": "entry",
                    "visible_through": filled_at.isoformat(),
                    "visible_through_unix": int(filled_at.timestamp()),
                },
            ]
        },
    }


def test_session_classifier_is_dst_aware_and_retains_overlaps() -> None:
    asia = classify_market_session(datetime(2026, 1, 5, 0, 30, tzinfo=UTC))
    assert asia["primary_session"] == "ASIA"
    assert asia["phase"] == "OPENING"
    assert asia["timezone"] == "Asia/Tokyo"

    london_summer = classify_market_session(
        datetime(2026, 7, 6, 7, 30, tzinfo=UTC)
    )
    assert london_summer["primary_session"] == "LONDON"
    assert london_summer["overlap"] is True
    assert london_summer["utc_offset_seconds"] == 3600
    assert london_summer["active_sessions"] == ["ASIA", "LONDON"]

    new_york_summer = classify_market_session(
        datetime(2026, 7, 6, 12, 30, tzinfo=UTC)
    )
    assert new_york_summer["primary_session"] == "NEW_YORK"
    assert new_york_summer["overlap"] is True
    assert new_york_summer["utc_offset_seconds"] == -14400
    assert new_york_summer["active_sessions"] == ["LONDON", "NEW_YORK"]


def test_session_classifier_retains_outside_primary_sessions() -> None:
    outside = classify_market_session(datetime(2026, 1, 5, 23, 30, tzinfo=UTC))
    assert outside["primary_session"] == "OUTSIDE_PRIMARY_SESSIONS"
    assert outside["active_sessions"] == []
    assert outside["phase"] == "OUTSIDE"


def test_story_payload_gets_three_group_breakdown_and_entry_context() -> None:
    episodes = [
        _episode(
            episode_id="episode-00000000000000000001",
            signal_at=datetime(2026, 1, 5, 0, 5, tzinfo=UTC),
            filled_at=datetime(2026, 1, 5, 0, 30, tzinfo=UTC),
            outcome="win",
            return_rate="0.02",
            classification="WIN_CANONICAL",
            exit_reason="target",
            mfe_r="2",
            mae_r="0.2",
        ),
        _episode(
            episode_id="episode-00000000000000000002",
            signal_at=datetime(2026, 1, 5, 7, 55, tzinfo=UTC),
            filled_at=datetime(2026, 1, 5, 8, 30, tzinfo=UTC),
            outcome="loss",
            return_rate="-0.01",
            classification="LOSS_DIRECT_NO_EDGE",
            exit_reason="stop",
            mfe_r="0.1",
            mae_r="1",
        ),
        _episode(
            episode_id="episode-00000000000000000003",
            signal_at=datetime(2026, 1, 5, 12, 55, tzinfo=UTC),
            filled_at=datetime(2026, 1, 5, 13, 30, tzinfo=UTC),
            outcome="loss",
            return_rate="-0.01",
            classification="LOSS_AFTER_1R_OR_MORE",
            exit_reason="stop",
            mfe_r="1.4",
            mae_r="1",
        ),
        _episode(
            episode_id="episode-00000000000000000004",
            signal_at=datetime(2026, 1, 5, 23, 0, tzinfo=UTC),
            filled_at=datetime(2026, 1, 5, 23, 30, tzinfo=UTC),
            outcome="win",
            return_rate="0.01",
            classification="WIN_CANONICAL",
            exit_reason="target",
            mfe_r="1.2",
            mae_r="0.3",
        ),
    ]
    payload: dict[str, object] = {"episodes": episodes}

    enriched = enrich_story_payload_sessions(payload)
    intelligence = cast(dict[str, object], enriched["session_intelligence"])
    breakdown = cast(dict[str, object], intelligence["breakdown"])
    assert cast(dict[str, object], breakdown["ASIA"])["entry_count"] == 1
    assert cast(dict[str, object], breakdown["LONDON"])["entry_count"] == 1
    assert cast(dict[str, object], breakdown["NEW_YORK"])["entry_count"] == 1
    assert cast(dict[str, object], breakdown["LONDON"])["direct_stop_count"] == 1
    assert cast(dict[str, object], breakdown["NEW_YORK"])["giveback_count"] == 1
    outside = cast(dict[str, object], intelligence["outside_primary_sessions"])
    assert outside["entry_count"] == 1

    enriched_episodes = cast(list[object], enriched["episodes"])
    london_episode = cast(dict[str, object], enriched_episodes[1])
    decision = cast(dict[str, object], london_episode["decision_time"])
    session_context = cast(dict[str, object], decision["session_context"])
    entry = cast(dict[str, object], session_context["entry"])
    assert entry["primary_session"] == "LONDON"
    assert entry["minutes_since_open"] == 30
