"""Render the five-Trader market/session Story Forensics dashboard."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_story_forensics import (
    FirstCohortStoryForensicsError,
)

_SCHEMA = "qore.trader_lab.first_cohort_market_story_forensics.v1"
_SESSIONS = ("ASIA", "LONDON", "NEW_YORK")


class StoryForensicsMarketBoardError(FirstCohortStoryForensicsError):
    """Raised when the market dashboard payload is invalid."""

    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise StoryForensicsMarketBoardError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise StoryForensicsMarketBoardError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise StoryForensicsMarketBoardError(f"{field_name} must be non-empty text")
    return value


def _integer(value: object, *, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise StoryForensicsMarketBoardError(
            f"{field_name} must be a non-negative int"
        )
    return value


def _metric(stats: dict[str, object], key: str) -> str:
    value = stats.get(key)
    if type(value) is int:
        return str(value)
    return html.escape(_text(value, field_name=key))


def _counter(stats: dict[str, object], key: str) -> str:
    values = _object(stats.get(key), field_name=key)
    if not values:
        return "none"
    parts: list[str] = []
    for name, value in sorted(values.items()):
        parts.append(
            f"{html.escape(name)}={_integer(value, field_name=f'{key} count')}"
        )
    return ", ".join(parts)


def _session_card(
    trader_code: str,
    session: str,
    stats: dict[str, object],
) -> str:
    metrics = (
        ("Entries", "entry_count"),
        ("Win rate", "win_rate"),
        ("Mean return", "mean_return_rate"),
        ("Compounded", "compounded_return_rate"),
        ("Mean MFE R", "mean_closed_bar_mfe_r"),
        ("Mean MAE R", "mean_closed_bar_mae_r"),
        ("Direct stops", "direct_stop_count"),
        ("Givebacks", "giveback_count"),
        ("Overlap entries", "overlap_entry_count"),
    )
    metric_rows = "".join(
        f'<div class="metric"><b>{label}</b><span>{_metric(stats, key)}</span></div>'
        for label, key in metrics
    )
    return (
        '<article class="session-card">'
        f"<h3>{html.escape(trader_code.upper())}</h3>"
        f"{metric_rows}"
        f"<p><b>Exits:</b> {_counter(stats, 'exit_reasons')}</p>"
        f"<p><b>Directions:</b> {_counter(stats, 'directions')}</p>"
        f"<p><b>Entry phases:</b> {_counter(stats, 'entry_phases')}</p>"
        f"<footer>{html.escape(session)}</footer>"
        "</article>"
    )


def render_market_board_html(payload: dict[str, object]) -> str:
    """Render one pair-level dashboard with five Traders and three sessions."""
    if _text(payload.get("schema"), field_name="schema") != _SCHEMA:
        raise StoryForensicsMarketBoardError(
            "market board requires market forensics v1"
        )
    if payload.get("research_only") is not True:
        raise StoryForensicsMarketBoardError(
            "market board requires research-only evidence"
        )
    if payload.get("execution_authority") is not False:
        raise StoryForensicsMarketBoardError("market board refuses execution authority")
    symbol = html.escape(_text(payload.get("symbol"), field_name="symbol"))
    fingerprint = html.escape(
        _text(
            payload.get("market_forensics_fingerprint"),
            field_name="market_forensics_fingerprint",
        )
    )
    summaries = [
        _object(item, field_name="trader summary")
        for item in _array(payload.get("trader_summaries"), field_name="summaries")
    ]
    if len(summaries) != 5:
        raise StoryForensicsMarketBoardError(
            "market board requires exactly five Traders"
        )

    overview_cards: list[str] = []
    session_columns: dict[str, list[str]] = {session: [] for session in _SESSIONS}
    for summary in summaries:
        trader = _text(summary.get("trader_code"), field_name="trader_code")
        episode_count = _integer(
            summary.get("episode_count"),
            field_name="episode_count",
        )
        outside_count = _integer(
            summary.get("outside_primary_session_entry_count"),
            field_name="outside_primary_session_entry_count",
        )
        overview_cards.append(
            "<article class=\"trader-card\">"
            f"<h2>{html.escape(trader.upper())}</h2>"
            f"<p><b>Total entries:</b> {episode_count}</p>"
            f"<p><b>Outside primary sessions:</b> {outside_count}</p>"
            "</article>"
        )
        breakdown = _object(
            summary.get("session_breakdown"),
            field_name="session_breakdown",
        )
        for session in _SESSIONS:
            stats = _object(breakdown.get(session), field_name=f"{session} stats")
            session_columns[session].append(_session_card(trader, session, stats))

    session_sections = "".join(
        f"<section><h2>{session.replace('_', ' ')}</h2>"
        f"<div class=\"session-grid\">{''.join(session_columns[session])}</div>"
        "</section>"
        for session in _SESSIONS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{symbol} · Five-Trader Session Forensics</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
body {{ margin: 0; background: #0f1117; color: #e7e9ee; }}
main {{ max-width: 1500px; margin: 0 auto; padding: 20px; }}
h1 {{ margin-bottom: 4px; }}
.sub {{ color: #aeb4c0; overflow-wrap: anywhere; }}
.overview, .session-grid {{ display: grid; gap: 10px; }}
.overview {{ grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }}
.session-grid {{ grid-template-columns: repeat(auto-fit, minmax(245px, 1fr)); }}
.trader-card, .session-card {{
  border: 1px solid #2b303b; border-radius: 10px; padding: 12px; background: #151922;
}}
.session-card h3, .trader-card h2 {{ margin: 0 0 8px; }}
.metric {{ display: flex; justify-content: space-between; gap: 12px; font-size: 12px; }}
.metric span {{ overflow-wrap: anywhere; text-align: right; }}
.session-card p {{ color: #b7bdc8; font-size: 11px; overflow-wrap: anywhere; }}
.session-card footer {{ color: #8f98a8; font-size: 10px; margin-top: 8px; }}
section {{ margin-top: 26px; }}
.note {{ margin-top: 28px; color: #949ba9; font-size: 12px; }}
</style>
</head>
<body>
<main>
<h1>{symbol} · 5 Traders · Session Forensics</h1>
<p class="sub">Market forensics fingerprint: {fingerprint}</p>
<div class="overview">{''.join(overview_cards)}</div>
{session_sections}
<p class="note">
Asia/London/New York are QORE versioned research groups. DST and overlaps are retained.
Outside-session entries are never silently forced into a primary group. Research-only;
no execution or real-capital authority.
</p>
</main>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.story_forensics_market_board "
            "MARKET_FORENSICS_JSON OUTPUT_HTML",
            file=sys.stderr,
        )
        return 2
    input_path, output_path = map(Path, arguments)
    try:
        decoded: object = json.loads(input_path.read_text(encoding="utf-8"))
        payload = _object(decoded, field_name="market forensics payload")
        rendered = render_market_board_html(payload)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        StoryForensicsMarketBoardError,
    ) as error:
        print(f"market story board failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
