"""Session-aware wrapper for one Trader Story Forensics replay page.

The base Lightweight Charts renderer remains unchanged. This wrapper requires an
enriched story pack and adds the exact QORE session observation beside the
individual replay so pair-level and episode-level views expose the same context.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.story_forensics_lightweight_renderer import (
    StoryForensicsRendererError,
    render_story_html,
)


class StoryForensicsSessionReplayError(StoryForensicsRendererError):
    """Raised when an enriched session replay cannot be rendered exactly."""

    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise StoryForensicsSessionReplayError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise StoryForensicsSessionReplayError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise StoryForensicsSessionReplayError(f"{field_name} must be non-empty text")
    return value


def _episode(payload: dict[str, object], episode_id: str) -> dict[str, object]:
    matches: list[dict[str, object]] = []
    for item in _array(payload.get("episodes"), field_name="episodes"):
        row = _object(item, field_name="episode")
        if _text(row.get("episode_id"), field_name="episode_id") == episode_id:
            matches.append(row)
    if len(matches) != 1:
        raise StoryForensicsSessionReplayError(
            "episode_id must identify exactly one enriched episode"
        )
    return matches[0]


def _optional_text(value: object) -> str:
    return "n/a" if value is None else str(value)


def render_session_story_html(
    payload: dict[str, object],
    *,
    episode_id: str,
) -> str:
    """Render the base replay plus exact signal/entry session context."""
    episode = _episode(payload, episode_id)
    decision = _object(episode.get("decision_time"), field_name="decision_time")
    context = _object(
        decision.get("session_context"),
        field_name="session_context",
    )
    signal = _object(context.get("signal"), field_name="signal session")
    entry = _object(context.get("entry"), field_name="entry session")
    base = render_story_html(payload, episode_id=episode_id)
    marker = '<div id="chart" role="img" aria-label="QORE forensic candlestick replay"></div>'
    if marker not in base:
        raise StoryForensicsSessionReplayError("base renderer insertion point changed")

    active = entry.get("active_sessions")
    if type(active) is not list or any(type(item) is not str for item in active):
        raise StoryForensicsSessionReplayError(
            "entry active_sessions must be a string list"
        )
    transition = context.get("signal_to_entry_session_transition")
    if type(transition) is not bool:
        raise StoryForensicsSessionReplayError(
            "signal_to_entry_session_transition must be bool"
        )

    signal_primary = html.escape(
        _text(signal.get("primary_session"), field_name="signal primary_session")
    )
    entry_primary = html.escape(
        _text(entry.get("primary_session"), field_name="entry primary_session")
    )
    active_text = html.escape(", ".join(cast(list[str], active)) or "none")
    entry_phase = html.escape(_text(entry.get("phase"), field_name="entry phase"))
    overlap = str(entry.get("overlap") is True).lower()
    since_open = html.escape(_optional_text(entry.get("minutes_since_open")))
    to_close = html.escape(_optional_text(entry.get("minutes_to_close")))
    local_at = html.escape(_optional_text(entry.get("local_at")))
    transition_text = str(transition).lower()
    panel = (
        '<section class="panel" aria-label="QORE session context">'
        '<h2>Session context</h2>'
        '<dl class="kv">'
        f"<dt>Signal session</dt><dd>{signal_primary}</dd>"
        f"<dt>Entry session</dt><dd>{entry_primary}</dd>"
        f"<dt>Active at entry</dt><dd>{active_text}</dd>"
        f"<dt>Entry phase</dt><dd>{entry_phase}</dd>"
        f"<dt>Overlap</dt><dd>{overlap}</dd>"
        f"<dt>Minutes since open</dt><dd>{since_open}</dd>"
        f"<dt>Minutes to close</dt><dd>{to_close}</dd>"
        f"<dt>Local entry time</dt><dd>{local_at}</dd>"
        f"<dt>Session transition</dt><dd>{transition_text}</dd>"
        "</dl>"
        "</section>"
    )
    return base.replace(marker, panel + marker, 1)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.story_forensics_session_replay "
            "ENRICHED_STORY_JSON EPISODE_ID OUTPUT_HTML",
            file=sys.stderr,
        )
        return 2
    story_path, episode_id, output_path = arguments
    try:
        decoded: object = json.loads(Path(story_path).read_text(encoding="utf-8"))
        payload = _object(decoded, field_name="enriched story pack")
        rendered = render_session_story_html(payload, episode_id=episode_id)
        Path(output_path).write_text(rendered, encoding="utf-8")
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        StoryForensicsRendererError,
    ) as error:
        print(f"session replay failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
