"""Bind one market Story Forensics pack to its deep characterization evidence.

The resulting package is the per-market scientific input for eleven-market Trader
thesis review. It keeps Story Forensics and production-default characterization
under one fail-closed provenance contract without carrying execution authority.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import cast

_STORY_SCHEMA = "qore.trader_lab.first_cohort_market_story_forensics.v1"
_CHARACTERIZATION_SCHEMA = "qore.trader_lab.first_cohort_characterization.v1"
_SCHEMA = "qore.trader_lab.first_cohort_market_thesis_evidence.v1"
_TRADERS = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_REQUIRED_PROFILE_FIELDS = (
    "execution_period",
    "parameters",
    "setup_count",
    "filled_setup_count",
    "unfilled_setup_count",
    "fill_rate",
    "max_losing_streak",
    "exit_reason_counts",
    "outcomes",
    "by_side",
    "by_session",
    "by_trend_regime",
    "by_volatility_regime",
    "by_chronological_quartile",
    "close_path_excursions",
    "decision_funnel",
    "geometry",
    "execution_model_diagnostics",
    "walk_forward_assessment",
    "setup_reason_counts",
    "abstain_reason_counts",
)


class MarketThesisEvidenceError(ValueError):
    """Raised when Story Forensics and characterization cannot be bound."""

    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise MarketThesisEvidenceError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise MarketThesisEvidenceError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise MarketThesisEvidenceError(f"{field_name} must be non-empty text")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise MarketThesisEvidenceError(f"{field_name} must be bool")
    return value


def _strict_int(value: object, *, field_name: str) -> int:
    if type(value) is not int:
        raise MarketThesisEvidenceError(f"{field_name} must be int")
    return value


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise MarketThesisEvidenceError(
            "market thesis evidence must be canonical JSON"
        ) from error


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read_json(path: Path, *, field_name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MarketThesisEvidenceError(f"cannot read {field_name}: {path}") from error
    return _object(decoded, field_name=field_name)


def _story_rows(
    story: dict[str, object],
) -> tuple[
    str,
    str,
    str,
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
]:
    if _text(story.get("schema"), field_name="story schema") != _STORY_SCHEMA:
        raise MarketThesisEvidenceError("market Story Forensics schema mismatch")
    if _text(story.get("environment"), field_name="story environment") != "demo":
        raise MarketThesisEvidenceError("market Story Forensics must be DEMO")
    if not _strict_bool(story.get("research_only"), field_name="story research_only"):
        raise MarketThesisEvidenceError("market Story Forensics must be research-only")
    if not _strict_bool(story.get("read_only"), field_name="story read_only"):
        raise MarketThesisEvidenceError("market Story Forensics must be read-only")
    if _strict_bool(story.get("execution_authority"), field_name="story execution_authority"):
        raise MarketThesisEvidenceError(
            "market Story Forensics cannot carry execution authority"
        )
    symbol = _text(story.get("symbol"), field_name="story symbol")
    software_sha = _text(story.get("software_sha"), field_name="story software_sha")
    account = _text(story.get("account_fingerprint"), field_name="story account_fingerprint")
    if _strict_int(story.get("trader_count"), field_name="story trader_count") != len(_TRADERS):
        raise MarketThesisEvidenceError("market Story Forensics must contain five Traders")
    codes = [
        _text(item, field_name="story trader code")
        for item in _array(story.get("trader_codes"), field_name="story trader_codes")
    ]
    if codes != list(_TRADERS):
        raise MarketThesisEvidenceError("market Story Forensics Trader order mismatch")

    summaries: dict[str, dict[str, object]] = {}
    for item in _array(story.get("trader_summaries"), field_name="story trader_summaries"):
        row = _object(item, field_name="story trader summary")
        code = _text(row.get("trader_code"), field_name="summary trader_code")
        if code in summaries:
            raise MarketThesisEvidenceError("duplicate Story Forensics trader summary")
        summaries[code] = row
    packs: dict[str, dict[str, object]] = {}
    for item in _array(story.get("trader_story_packs"), field_name="story trader_story_packs"):
        pack = _object(item, field_name="story trader pack")
        binding = _object(pack.get("source_binding"), field_name="story source_binding")
        code = _text(binding.get("trader_code"), field_name="binding trader_code")
        if code in packs:
            raise MarketThesisEvidenceError("duplicate Story Forensics trader pack")
        if _text(binding.get("symbol"), field_name="binding symbol") != symbol:
            raise MarketThesisEvidenceError("Story Forensics trader symbol mismatch")
        if _text(binding.get("software_sha"), field_name="binding software_sha") != software_sha:
            raise MarketThesisEvidenceError("Story Forensics trader software SHA mismatch")
        if _text(binding.get("account_fingerprint"), field_name="binding account") != account:
            raise MarketThesisEvidenceError("Story Forensics trader account mismatch")
        packs[code] = pack
    if set(summaries) != set(_TRADERS) or set(packs) != set(_TRADERS):
        raise MarketThesisEvidenceError("Story Forensics must cover canonical five Traders")
    return symbol, software_sha, account, summaries, packs


def _characterization_profiles(
    characterization: dict[str, object],
    *,
    symbol: str,
    software_sha: str,
    account_fingerprint: str,
) -> dict[str, dict[str, object]]:
    if (
        _text(characterization.get("schema"), field_name="characterization schema")
        != _CHARACTERIZATION_SCHEMA
    ):
        raise MarketThesisEvidenceError("characterization schema mismatch")
    if (
        _text(
            characterization.get("environment"),
            field_name="characterization environment",
        )
        != "demo"
    ):
        raise MarketThesisEvidenceError("characterization must be DEMO")
    if not _strict_bool(
        characterization.get("read_only"),
        field_name="characterization read_only",
    ):
        raise MarketThesisEvidenceError("characterization must be read-only")
    if _text(characterization.get("symbol"), field_name="characterization symbol") != symbol:
        raise MarketThesisEvidenceError("Story/characterization symbol mismatch")
    if (
        _text(characterization.get("software_sha"), field_name="characterization software_sha")
        != software_sha
    ):
        raise MarketThesisEvidenceError("Story/characterization software SHA mismatch")
    if (
        _text(characterization.get("account_fingerprint"), field_name="characterization account")
        != account_fingerprint
    ):
        raise MarketThesisEvidenceError("Story/characterization account mismatch")
    holdout = _object(
        characterization.get("holdout_governance"),
        field_name="holdout governance",
    )
    if _text(holdout.get("state"), field_name="holdout state") != "consumed_for_research":
        raise MarketThesisEvidenceError("characterization must be consumed for research")

    profiles: dict[str, dict[str, object]] = {}
    for item in _array(characterization.get("results"), field_name="characterization results"):
        result = _object(item, field_name="characterization result")
        code = _text(result.get("trader_code"), field_name="characterization trader_code")
        if code not in _TRADERS:
            raise MarketThesisEvidenceError("unexpected Trader in characterization")
        defaults = [
            _object(profile, field_name="characterization profile")
            for profile in _array(result.get("profiles"), field_name="characterization profiles")
            if _text(
                _object(profile, field_name="characterization profile").get("profile"),
                field_name="profile label",
            )
            == "production-default"
        ]
        if len(defaults) != 1:
            raise MarketThesisEvidenceError(
                f"{code} must have exactly one production-default characterization profile"
            )
        profiles[code] = defaults[0]
    if set(profiles) != set(_TRADERS):
        raise MarketThesisEvidenceError("characterization must cover canonical five Traders")
    return profiles


def _research_profile(profile: dict[str, object]) -> dict[str, object]:
    for field_name in _REQUIRED_PROFILE_FIELDS:
        if field_name not in profile:
            raise MarketThesisEvidenceError(
                f"production-default profile missing required field: {field_name}"
            )
    result = {
        field_name: deepcopy(profile[field_name])
        for field_name in _REQUIRED_PROFILE_FIELDS
    }
    walk_forward = _object(
        result["walk_forward_assessment"],
        field_name="walk_forward_assessment",
    )
    config_fingerprint = _text(
        profile.get("config_fingerprint"),
        field_name="config_fingerprint",
    )
    if (
        _text(
            walk_forward.get("config_fingerprint"),
            field_name="walk-forward config_fingerprint",
        )
        != config_fingerprint
    ):
        raise MarketThesisEvidenceError(
            "production-default walk-forward assessment config mismatch"
        )
    return result


def build_market_thesis_evidence(
    story: dict[str, object],
    characterization: dict[str, object],
) -> dict[str, object]:
    """Build one compact, evidence-bound five-Trader research package."""
    symbol, software_sha, account, summaries, packs = _story_rows(story)
    profiles = _characterization_profiles(
        characterization,
        symbol=symbol,
        software_sha=software_sha,
        account_fingerprint=account,
    )
    characterization_digest = _digest(characterization)
    market_story_payload_digest = _digest(story)
    market_story_fingerprint = _text(
        story.get("market_forensics_fingerprint"),
        field_name="market_forensics_fingerprint",
    )
    trader_rows: list[dict[str, object]] = []
    for code in _TRADERS:
        pack = packs[code]
        summary = summaries[code]
        binding = _object(pack.get("source_binding"), field_name="story source_binding")
        profile = profiles[code]
        config_fingerprint = _text(
            profile.get("config_fingerprint"),
            field_name="config_fingerprint",
        )
        methodology = _object(
            profile.get("methodology_identity"),
            field_name="methodology_identity",
        )
        methodology_fingerprint = _text(
            methodology.get("methodology_fingerprint"),
            field_name="methodology_fingerprint",
        )
        execution_period = _text(
            profile.get("execution_period"),
            field_name="execution_period",
        )
        if (
            _text(binding.get("config_fingerprint"), field_name="binding config_fingerprint")
            != config_fingerprint
        ):
            raise MarketThesisEvidenceError(f"{code} config fingerprint mismatch")
        if (
            _text(
                binding.get("methodology_fingerprint"),
                field_name="binding methodology_fingerprint",
            )
            != methodology_fingerprint
        ):
            raise MarketThesisEvidenceError(f"{code} methodology fingerprint mismatch")
        if (
            _text(binding.get("execution_period"), field_name="binding execution_period")
            != execution_period
        ):
            raise MarketThesisEvidenceError(f"{code} execution period mismatch")

        research_profile = _research_profile(profile)
        profile_without_setups = {
            key: value for key, value in profile.items() if key != "setups"
        }
        row: dict[str, object] = {
            "trader_code": code,
            "identity": {
                "config_fingerprint": config_fingerprint,
                "methodology_fingerprint": methodology_fingerprint,
                "execution_period": execution_period,
            },
            "story_forensics": {
                "episode_count": summary.get("episode_count"),
                "family_status": deepcopy(summary.get("family_status")),
                "session_breakdown": deepcopy(summary.get("session_breakdown")),
                "outside_primary_session_entry_count": summary.get(
                    "outside_primary_session_entry_count"
                ),
                "forensics_fingerprint": _text(
                    summary.get("forensics_fingerprint"),
                    field_name="forensics_fingerprint",
                ),
                "session_intelligence_fingerprint": _text(
                    summary.get("session_intelligence_fingerprint"),
                    field_name="session_intelligence_fingerprint",
                ),
            },
            "characterization": research_profile,
            "provenance": {
                "market_story_fingerprint": market_story_fingerprint,
                "market_story_payload_digest": market_story_payload_digest,
                "characterization_digest": characterization_digest,
                "production_default_profile_digest": _digest(profile_without_setups),
            },
        }
        row["trader_market_evidence_digest"] = _digest(row)
        trader_rows.append(row)

    payload: dict[str, object] = {
        "schema": _SCHEMA,
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "symbol": symbol,
        "software_sha": software_sha,
        "account_fingerprint": account,
        "market_story_fingerprint": market_story_fingerprint,
        "market_story_payload_digest": market_story_payload_digest,
        "characterization_digest": characterization_digest,
        "trader_codes": list(_TRADERS),
        "trader_evidence": trader_rows,
    }
    payload["market_thesis_evidence_fingerprint"] = _digest(payload)
    return payload


def build_market_thesis_evidence_from_paths(
    story_path: Path,
    characterization_path: Path,
) -> dict[str, object]:
    """Read one market Story pack and characterization artifact and bind them."""
    return build_market_thesis_evidence(
        _read_json(story_path, field_name="market Story Forensics"),
        _read_json(characterization_path, field_name="characterization"),
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.first_cohort_market_thesis_evidence "
            "MARKET_STORY_FORENSICS CHARACTERIZATION",
            file=sys.stderr,
        )
        return 2
    try:
        payload = build_market_thesis_evidence_from_paths(
            Path(arguments[0]),
            Path(arguments[1]),
        )
    except MarketThesisEvidenceError as error:
        print(f"market thesis evidence build failed: {error}", file=sys.stderr)
        return 1
    print(_canonical(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
