"""Build one five-Trader Story Forensics package for one market.

This market-level layer preserves each Trader's exact story pack and adds
session-aware comparison across Asia, London, and New York. It is research-only
and has no execution, Risk, DEMO/LIVE, or real-capital authority.
"""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_story_forensics import (
    FirstCohortStoryForensicsError,
    run_story_forensics,
)
from qore.infrastructure.trader_lab.story_forensics_session_intelligence import (
    enrich_story_payload_sessions,
)

_SCHEMA = "qore.trader_lab.first_cohort_market_story_forensics.v1"
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise FirstCohortStoryForensicsError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortStoryForensicsError(f"{field_name} must be non-empty text")
    return value


def _session_breakdown(story: dict[str, object]) -> dict[str, object]:
    intelligence = _object(
        story.get("session_intelligence"),
        field_name="session_intelligence",
    )
    return _object(intelligence.get("breakdown"), field_name="session breakdown")


def _outside_count(story: dict[str, object]) -> int:
    intelligence = _object(
        story.get("session_intelligence"),
        field_name="session_intelligence",
    )
    outside = _object(
        intelligence.get("outside_primary_sessions"),
        field_name="outside_primary_sessions",
    )
    count = outside.get("entry_count")
    if type(count) is not int or count < 0:
        raise FirstCohortStoryForensicsError(
            "outside entry count must be non-negative int"
        )
    return count


def _session_fingerprint(story: dict[str, object]) -> str:
    intelligence = _object(
        story.get("session_intelligence"),
        field_name="session_intelligence",
    )
    return _text(
        intelligence.get("session_intelligence_fingerprint"),
        field_name="session_intelligence_fingerprint",
    )


def _trader_summary(story: dict[str, object]) -> dict[str, object]:
    binding = _object(story.get("source_binding"), field_name="source_binding")
    statuses = _object(story.get("family_status"), field_name="family_status")
    episode_count = story.get("episode_count")
    if type(episode_count) is not int or episode_count < 0:
        raise FirstCohortStoryForensicsError("episode_count must be non-negative int")
    return {
        "trader_code": _text(binding.get("trader_code"), field_name="trader_code"),
        "episode_count": episode_count,
        "family_status": statuses,
        "session_breakdown": _session_breakdown(story),
        "outside_primary_session_entry_count": _outside_count(story),
        "forensics_fingerprint": _text(
            story.get("forensics_fingerprint"),
            field_name="forensics_fingerprint",
        ),
        "session_intelligence_fingerprint": _session_fingerprint(story),
    }


def run_market_story_forensics(
    market_path: Path,
    backtest_path: Path,
    characterization_path: Path,
) -> dict[str, object]:
    """Build the exact five-Trader market package in one deterministic pass."""
    stories: list[dict[str, object]] = []
    for trader_code in _CODES:
        story = run_story_forensics(
            market_path,
            backtest_path,
            characterization_path,
            trader_code,
        )
        stories.append(enrich_story_payload_sessions(story))

    bindings = [
        _object(story.get("source_binding"), field_name="source_binding")
        for story in stories
    ]
    symbols = {
        _text(binding.get("symbol"), field_name="symbol")
        for binding in bindings
    }
    software_shas = {
        _text(binding.get("software_sha"), field_name="software_sha")
        for binding in bindings
    }
    accounts = {
        _text(binding.get("account_fingerprint"), field_name="account_fingerprint")
        for binding in bindings
    }
    if len(symbols) != 1 or len(software_shas) != 1 or len(accounts) != 1:
        raise FirstCohortStoryForensicsError(
            "five-Trader market story bindings must be identical"
        )
    symbol = next(iter(symbols))
    software_sha = next(iter(software_shas))
    account_fingerprint = next(iter(accounts))
    summaries = [_trader_summary(story) for story in stories]
    fingerprint_material = json.dumps(
        {
            "schema": _SCHEMA,
            "symbol": symbol,
            "software_sha": software_sha,
            "traders": [
                {
                    "trader_code": summary["trader_code"],
                    "forensics_fingerprint": summary["forensics_fingerprint"],
                    "session_intelligence_fingerprint": summary[
                        "session_intelligence_fingerprint"
                    ],
                }
                for summary in summaries
            ],
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "symbol": symbol,
        "software_sha": software_sha,
        "account_fingerprint": account_fingerprint,
        "trader_codes": list(_CODES),
        "trader_count": len(stories),
        "session_groups": ["ASIA", "LONDON", "NEW_YORK"],
        "trader_summaries": summaries,
        "trader_story_packs": stories,
        "market_forensics_fingerprint": sha256(
            fingerprint_material.encode("utf-8")
        ).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.first_cohort_market_story_forensics "
            "MARKET_EVIDENCE BACKTEST CHARACTERIZATION",
            file=sys.stderr,
        )
        return 2
    try:
        payload = run_market_story_forensics(
            Path(arguments[0]),
            Path(arguments[1]),
            Path(arguments[2]),
        )
    except FirstCohortStoryForensicsError as error:
        print(f"market story forensics failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
