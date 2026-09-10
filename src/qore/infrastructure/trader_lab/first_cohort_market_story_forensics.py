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
    validate_story_episode_contract,
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


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise FirstCohortStoryForensicsError(f"{field_name} must be bool")
    return value


def _read_json(path: Path, *, field_name: str) -> dict[str, object]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortStoryForensicsError(f"cannot read {field_name}: {path}") from error
    return _object(value, field_name=field_name)


def _file_digest(path: Path) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise FirstCohortStoryForensicsError(f"cannot digest retained evidence: {path}") from error


def _canonical_digest(value: object) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise FirstCohortStoryForensicsError(
            "market Story Forensics must be canonical JSON"
        ) from error
    return sha256(encoded).hexdigest()


def _market_identity(
    *,
    provider_symbol: str,
    software_sha: str,
    account_fingerprint: str,
    market_digest: str,
    provider_identity_path: Path | None,
    stage1_status_path: Path | None,
) -> tuple[str, dict[str, object]]:
    if provider_identity_path is None and stage1_status_path is None:
        return provider_symbol, {
            "binding_basis": "direct-market-symbol",
            "economic_target": provider_symbol,
            "provider_symbol": provider_symbol,
        }
    if provider_identity_path is None or stage1_status_path is None:
        raise FirstCohortStoryForensicsError(
            "provider identity and Stage 1 status must be supplied together"
        )
    identity = _read_json(provider_identity_path, field_name="provider identity")
    status = _read_json(stage1_status_path, field_name="Stage 1 status")
    if _text(identity.get("environment"), field_name="identity environment") != "demo":
        raise FirstCohortStoryForensicsError("provider identity must be DEMO")
    if not _strict_bool(identity.get("read_only"), field_name="identity read_only"):
        raise FirstCohortStoryForensicsError("provider identity must be read-only")
    if _strict_bool(identity.get("account_is_live"), field_name="account_is_live"):
        raise FirstCohortStoryForensicsError("provider identity cannot be LIVE")
    if not _strict_bool(
        identity.get("economic_identity_certified"),
        field_name="economic_identity_certified",
    ):
        raise FirstCohortStoryForensicsError("economic identity is not certified")
    if (
        _text(identity.get("account_fingerprint"), field_name="identity account")
        != account_fingerprint
    ):
        raise FirstCohortStoryForensicsError("provider identity account mismatch")
    provider = _object(identity.get("provider_symbol"), field_name="provider symbol")
    if _text(provider.get("symbol_name"), field_name="provider symbol name") != provider_symbol:
        raise FirstCohortStoryForensicsError("provider symbol substitution detected")
    economic_target = _text(identity.get("economic_target"), field_name="economic target")
    if _text(status.get("stage"), field_name="Stage 1 stage") != "MARKET_EVIDENCE":
        raise FirstCohortStoryForensicsError("unexpected Stage 1 status")
    if _text(status.get("terminal_state"), field_name="Stage 1 terminal state") != "PASS":
        raise FirstCohortStoryForensicsError("Stage 1 did not pass")
    if _text(status.get("collect_outcome"), field_name="collect outcome") != "success":
        raise FirstCohortStoryForensicsError("Stage 1 collection failed")
    if _text(status.get("resolve_outcome"), field_name="resolve outcome") != "success":
        raise FirstCohortStoryForensicsError("Stage 1 identity resolution failed")
    if (
        _text(status.get("economic_target"), field_name="Stage 1 economic target")
        != economic_target
    ):
        raise FirstCohortStoryForensicsError("economic target substitution detected")
    if _text(status.get("source_sha"), field_name="Stage 1 source SHA") != software_sha:
        raise FirstCohortStoryForensicsError("Stage 1 software SHA mismatch")
    if (
        _text(status.get("market_evidence_sha256"), field_name="market evidence digest")
        != market_digest
    ):
        raise FirstCohortStoryForensicsError("Stage 1 market evidence digest mismatch")
    identity_digest = _file_digest(provider_identity_path)
    if (
        _text(status.get("provider_identity_sha256"), field_name="identity digest")
        != identity_digest
    ):
        raise FirstCohortStoryForensicsError("provider identity digest mismatch")
    return economic_target, {
        "binding_basis": _text(identity.get("binding_basis"), field_name="binding basis"),
        "economic_target": economic_target,
        "provider_symbol": provider_symbol,
        "provider_identity_sha256": identity_digest,
        "stage1_status_sha256": _file_digest(stage1_status_path),
    }


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
        raise FirstCohortStoryForensicsError("outside entry count must be non-negative int")
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
    episodes = story.get("episodes")
    if type(episodes) is not list:
        raise FirstCohortStoryForensicsError("episodes must be a JSON array")
    for item in episodes:
        validate_story_episode_contract(_object(item, field_name="episode"))
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
    provider_identity_path: Path | None = None,
    stage1_status_path: Path | None = None,
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
        _object(story.get("source_binding"), field_name="source_binding") for story in stories
    ]
    symbols = {_text(binding.get("symbol"), field_name="symbol") for binding in bindings}
    software_shas = {
        _text(binding.get("software_sha"), field_name="software_sha") for binding in bindings
    }
    accounts = {
        _text(binding.get("account_fingerprint"), field_name="account_fingerprint")
        for binding in bindings
    }
    if len(symbols) != 1 or len(software_shas) != 1 or len(accounts) != 1:
        raise FirstCohortStoryForensicsError("five-Trader market story bindings must be identical")
    provider_symbol = next(iter(symbols))
    software_sha = next(iter(software_shas))
    account_fingerprint = next(iter(accounts))
    source_digests = {
        "market_evidence_sha256": _file_digest(market_path),
        "backtest_sha256": _file_digest(backtest_path),
        "characterization_sha256": _file_digest(characterization_path),
    }
    symbol, identity_binding = _market_identity(
        provider_symbol=provider_symbol,
        software_sha=software_sha,
        account_fingerprint=account_fingerprint,
        market_digest=source_digests["market_evidence_sha256"],
        provider_identity_path=provider_identity_path,
        stage1_status_path=stage1_status_path,
    )
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
                    "session_intelligence_fingerprint": summary["session_intelligence_fingerprint"],
                }
                for summary in summaries
            ],
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    payload: dict[str, object] = {
        "schema": _SCHEMA,
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "symbol": symbol,
        "provider_symbol": provider_symbol,
        "software_sha": software_sha,
        "account_fingerprint": account_fingerprint,
        "source_digests": source_digests,
        "identity_binding": identity_binding,
        "trader_codes": list(_CODES),
        "trader_count": len(stories),
        "session_groups": ["ASIA", "LONDON", "NEW_YORK"],
        "trader_summaries": summaries,
        "trader_story_packs": stories,
        "market_forensics_fingerprint": sha256(fingerprint_material.encode("utf-8")).hexdigest(),
    }
    payload["market_forensics_payload_digest"] = _canonical_digest(payload)
    return payload


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
