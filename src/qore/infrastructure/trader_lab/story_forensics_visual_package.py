"""Build a browsable visual-research package from one Trader Story pack.

The package is intentionally static and research-only. It materializes a board,
replay page, chronological filmstrip page, and integrity manifest from already
bound QORE evidence. TradingView Lightweight Charts remains a replaceable visual
renderer and never becomes a market-data or trading-authority dependency.
"""

from __future__ import annotations

import html
import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_story_forensics import (
    FirstCohortStoryForensicsError,
)
from qore.infrastructure.trader_lab.story_forensics_filmstrip_renderer import (
    render_filmstrip_html,
)
from qore.infrastructure.trader_lab.story_forensics_lightweight_renderer import (
    render_story_html,
)

_STORY_SCHEMA = "qore.trader_lab.first_cohort_story_forensics.v1"
_PACKAGE_SCHEMA = "qore.trader_lab.story_forensics_visual_package.v1"
_RENDERER = "tradingview-lightweight-charts"
_RENDERER_VERSION = "5.2.1"
_EPISODE_ID = re.compile(r"^episode-[0-9a-f]{20}$")
_FAMILIES = (
    "winning_streaks",
    "losing_streaks",
    "direct_stop_episodes",
    "giveback_episodes",
    "canonical_winners",
)


class StoryForensicsVisualPackageError(FirstCohortStoryForensicsError):
    """Raised when a visual package cannot be built without losing provenance."""

    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise StoryForensicsVisualPackageError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise StoryForensicsVisualPackageError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise StoryForensicsVisualPackageError(f"{field_name} must be a non-empty string")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise StoryForensicsVisualPackageError(f"{field_name} must be bool")
    return value


def _episode_id(value: object, *, field_name: str) -> str:
    episode_id = _text(value, field_name=field_name)
    if _EPISODE_ID.fullmatch(episode_id) is None:
        raise StoryForensicsVisualPackageError(f"{field_name} is not a canonical episode id")
    return episode_id


def _validate(payload: dict[str, object]) -> None:
    if _text(payload.get("schema"), field_name="schema") != _STORY_SCHEMA:
        raise StoryForensicsVisualPackageError("visual package requires story-forensics v1")
    if not _strict_bool(payload.get("research_only"), field_name="research_only"):
        raise StoryForensicsVisualPackageError("visual package requires research-only evidence")
    if _strict_bool(payload.get("execution_authority"), field_name="execution_authority"):
        raise StoryForensicsVisualPackageError("visual package refuses execution authority")
    contract = _object(payload.get("renderer_contract"), field_name="renderer contract")
    if _text(contract.get("default_renderer"), field_name="renderer") != _RENDERER:
        raise StoryForensicsVisualPackageError("unexpected renderer")
    if _text(contract.get("renderer_version"), field_name="renderer version") != _RENDERER_VERSION:
        raise StoryForensicsVisualPackageError("renderer version must be pinned")
    if _text(contract.get("market_data_source"), field_name="market data source") != (
        "qore-retained-evidence"
    ):
        raise StoryForensicsVisualPackageError("visual package must use QORE evidence")
    if _strict_bool(
        contract.get("tradingview_is_evidence_source"),
        field_name="TradingView evidence flag",
    ):
        raise StoryForensicsVisualPackageError("TradingView cannot be an evidence source")
    if _strict_bool(
        contract.get("tradingview_has_execution_authority"),
        field_name="TradingView authority flag",
    ):
        raise StoryForensicsVisualPackageError("TradingView cannot have execution authority")


def _episode_map(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    episodes: dict[str, dict[str, object]] = {}
    for item in _array(payload.get("episodes"), field_name="episodes"):
        row = _object(item, field_name="episode")
        episode_id = _episode_id(row.get("episode_id"), field_name="episode id")
        if episode_id in episodes:
            raise StoryForensicsVisualPackageError("duplicate episode id")
        episodes[episode_id] = row
    if not episodes:
        raise StoryForensicsVisualPackageError("visual package requires at least one episode")
    return episodes


def _selected_ids(payload: dict[str, object]) -> tuple[str, ...]:
    families = _object(payload.get("story_families"), field_name="story families")
    selected: list[str] = []
    for family in _FAMILIES:
        rows = _array(families.get(family), field_name=family)
        for item in rows:
            row = _object(item, field_name=f"{family} row")
            if family in {"winning_streaks", "losing_streaks"}:
                for episode in _array(row.get("episode_ids"), field_name="streak episode ids"):
                    selected.append(_episode_id(episode, field_name="streak episode id"))
            else:
                selected.append(_episode_id(row.get("episode_id"), field_name="episode id"))
    return tuple(dict.fromkeys(selected))


def _family_title(family: str) -> str:
    labels = {
        "winning_streaks": "5 winning streaks",
        "losing_streaks": "5 losing streaks",
        "direct_stop_episodes": "Direct-to-stop episodes",
        "giveback_episodes": "Profit-then-stop / giveback episodes",
        "canonical_winners": "Canonical winners",
    }
    return labels[family]


def _episode_links(episode_id: str) -> str:
    safe = html.escape(episode_id)
    return (
        f'<a href="episodes/{safe}-replay.html">Replay</a>'
        f' <a href="episodes/{safe}-filmstrip.html">Filmstrip</a>'
    )


def _board_html(payload: dict[str, object]) -> str:
    binding = _object(payload.get("source_binding"), field_name="source binding")
    trader = html.escape(_text(binding.get("trader_code"), field_name="trader code").upper())
    symbol = html.escape(_text(binding.get("symbol"), field_name="symbol"))
    families = _object(payload.get("story_families"), field_name="story families")
    statuses = _object(payload.get("family_status"), field_name="family status")
    sections: list[str] = []
    for family in _FAMILIES:
        status = _object(statuses.get(family), field_name=f"{family} status")
        state = html.escape(_text(status.get("status"), field_name="family state"))
        cards: list[str] = []
        for item in _array(families.get(family), field_name=family):
            row = _object(item, field_name=f"{family} row")
            reason = html.escape(_text(row.get("selection_reason"), field_name="selection reason"))
            if family in {"winning_streaks", "losing_streaks"}:
                streak_id = html.escape(_text(row.get("streak_id"), field_name="streak id"))
                episode_ids = [
                    _episode_id(value, field_name="streak episode id")
                    for value in _array(row.get("episode_ids"), field_name="streak episode ids")
                ]
                links = "<br>".join(_episode_links(episode_id) for episode_id in episode_ids)
                body = (
                    f"<strong>{streak_id}</strong>"
                    f"<span>{reason}</span>"
                    f"<span>{len(episode_ids)} episode(s)</span>"
                    f"<div class=\"links\">{links}</div>"
                )
            else:
                episode_id = _episode_id(row.get("episode_id"), field_name="episode id")
                classification = html.escape(
                    _text(row.get("classification"), field_name="classification")
                )
                body = (
                    f"<strong>{html.escape(episode_id)}</strong>"
                    f"<span>{classification}</span>"
                    f"<span>{reason}</span>"
                    f"<div class=\"links\">{_episode_links(episode_id)}</div>"
                )
            cards.append(f'<article class="card">{body}</article>')
        sections.append(
            f"<section><div class=\"section-head\"><h2>{html.escape(_family_title(family))}</h2>"
            f"<span>{state}</span></div><div class=\"cards\">{''.join(cards)}</div></section>"
        )
    fingerprint = html.escape(
        _text(payload.get("forensics_fingerprint"), field_name="forensics fingerprint")
    )
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{trader} · {symbol} · Story Forensics Board</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
body {{ margin: 0; background: #0f1117; color: #e7e9ee; }}
main {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
h1 {{ margin: 0; font-size: 22px; }}
.sub {{ color: #aeb4c0; margin: 5px 0 20px; font-size: 13px; overflow-wrap: anywhere; }}
section {{ margin: 22px 0; }}
.section-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }}
h2 {{ font-size: 16px; margin: 0 0 9px; }}
.section-head span {{ font-size: 12px; color: #aeb4c0; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }}
.card {{ border: 1px solid #2b303b; border-radius: 9px; padding: 11px; background: #151922; }}
.card strong, .card span {{ display: block; overflow-wrap: anywhere; }}
.card strong {{ font-size: 12px; }}
.card span {{ color: #aeb4c0; font-size: 11px; margin-top: 4px; }}
.links {{ margin-top: 9px; font-size: 12px; line-height: 1.7; }}
a {{ color: #a9c8ff; margin-right: 7px; }}
footer {{ margin-top: 26px; color: #949ba9; font-size: 12px; }}
</style>
</head>
<body>
<main>
<h1>{trader} · {symbol} · Trader Story Forensics</h1>
<p class=\"sub\">Forensics fingerprint: {fingerprint}</p>
{''.join(sections)}
<footer>
Research-only package. QORE retained evidence is authoritative.
TradingView Lightweight Charts is a visualization surface only.
</footer>
</main>
</body>
</html>
"""


def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def build_visual_package(payload: dict[str, object], output_dir: Path) -> dict[str, object]:
    """Materialize the exact selected visual stories plus an integrity manifest."""
    _validate(payload)
    episodes = _episode_map(payload)
    selected_ids = _selected_ids(payload)
    if not selected_ids:
        raise StoryForensicsVisualPackageError("no selected episodes in story families")
    missing = [episode_id for episode_id in selected_ids if episode_id not in episodes]
    if missing:
        raise StoryForensicsVisualPackageError("story family references missing episode")
    output_dir.mkdir(parents=True, exist_ok=True)
    episode_dir = output_dir / "episodes"
    episode_dir.mkdir(parents=True, exist_ok=True)
    file_hashes: dict[str, str] = {}
    board = _board_html(payload)
    (output_dir / "index.html").write_text(board, encoding="utf-8")
    file_hashes["index.html"] = _sha256_text(board)
    for episode_id in selected_ids:
        replay = render_story_html(payload, episode_id=episode_id)
        replay_name = f"{episode_id}-replay.html"
        (episode_dir / replay_name).write_text(replay, encoding="utf-8")
        file_hashes[f"episodes/{replay_name}"] = _sha256_text(replay)
        filmstrip = render_filmstrip_html(payload, episode_id=episode_id)
        filmstrip_name = f"{episode_id}-filmstrip.html"
        (episode_dir / filmstrip_name).write_text(filmstrip, encoding="utf-8")
        file_hashes[f"episodes/{filmstrip_name}"] = _sha256_text(filmstrip)
    manifest: dict[str, object] = {
        "schema": _PACKAGE_SCHEMA,
        "research_only": True,
        "execution_authority": False,
        "source_binding": payload.get("source_binding"),
        "forensics_fingerprint": payload.get("forensics_fingerprint"),
        "renderer": _RENDERER,
        "renderer_version": _RENDERER_VERSION,
        "selected_episode_ids": list(selected_ids),
        "files_sha256": dict(sorted(file_hashes.items())),
    }
    manifest_text = json.dumps(
        manifest,
        ensure_ascii=True,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    )
    (output_dir / "manifest.json").write_text(manifest_text + "\n", encoding="utf-8")
    return manifest


def build_visual_package_from_file(story_path: Path, output_dir: Path) -> dict[str, object]:
    """Read one story JSON artifact and materialize its complete visual package."""
    try:
        decoded: object = json.loads(story_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StoryForensicsVisualPackageError("cannot read story pack") from error
    return build_visual_package(_object(decoded, field_name="story pack"), output_dir)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print(
            "usage: python -m qore.infrastructure.trader_lab.story_forensics_visual_package "
            "STORY_JSON OUTPUT_DIR",
            file=sys.stderr,
        )
        return 2
    try:
        build_visual_package_from_file(Path(arguments[0]), Path(arguments[1]))
    except FirstCohortStoryForensicsError as error:
        print(f"visual package failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
