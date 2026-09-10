"""Session-aware evidence enrichment for Trader Story Forensics.

The calendar is a versioned QORE research convention, not an exchange-hours
authority. It groups entries into Asia, London, and New York while retaining
session overlaps, daylight-saving offsets, and out-of-session observations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from typing import cast
from zoneinfo import ZoneInfo

_SESSION_SCHEMA = "qore.trader_lab.story_session_intelligence.v1"
_SESSION_CALENDAR_ID = "qore-major-trading-sessions-v1"


class SessionGroup(StrEnum):
    """Primary research groups used by Trader Lab."""

    ASIA = "ASIA"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OUTSIDE_PRIMARY_SESSIONS = "OUTSIDE_PRIMARY_SESSIONS"


class SessionPhase(StrEnum):
    """Coarse position of an entry within an active session."""

    OPENING = "OPENING"
    CORE = "CORE"
    CLOSING = "CLOSING"
    OUTSIDE = "OUTSIDE"


@dataclass(frozen=True, slots=True)
class _SessionDefinition:
    group: SessionGroup
    timezone_name: str
    open_local: time
    close_local: time


_DEFINITIONS = (
    _SessionDefinition(
        SessionGroup.ASIA,
        "Asia/Tokyo",
        time(9, 0),
        time(18, 0),
    ),
    _SessionDefinition(
        SessionGroup.LONDON,
        "Europe/London",
        time(8, 0),
        time(17, 0),
    ),
    _SessionDefinition(
        SessionGroup.NEW_YORK,
        "America/New_York",
        time(8, 0),
        time(17, 0),
    ),
)
_PRIMARY_GROUPS = (
    SessionGroup.ASIA,
    SessionGroup.LONDON,
    SessionGroup.NEW_YORK,
)


@dataclass(frozen=True, slots=True)
class _ActiveSession:
    definition: _SessionDefinition
    local_at: datetime
    opened_at: datetime
    closes_at: datetime

    @property
    def minutes_since_open(self) -> int:
        return int((self.local_at - self.opened_at).total_seconds() // 60)

    @property
    def minutes_to_close(self) -> int:
        return int((self.closes_at - self.local_at).total_seconds() // 60)

    @property
    def phase(self) -> SessionPhase:
        if self.minutes_since_open < 120:
            return SessionPhase.OPENING
        if self.minutes_to_close <= 120:
            return SessionPhase.CLOSING
        return SessionPhase.CORE


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("session timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _active_session(
    at: datetime,
    definition: _SessionDefinition,
) -> _ActiveSession | None:
    zone = ZoneInfo(definition.timezone_name)
    local_at = at.astimezone(zone)
    opened_at = datetime.combine(
        local_at.date(),
        definition.open_local,
        tzinfo=zone,
    )
    closes_at = datetime.combine(
        local_at.date(),
        definition.close_local,
        tzinfo=zone,
    )
    if not opened_at <= local_at < closes_at:
        return None
    return _ActiveSession(definition, local_at, opened_at, closes_at)


def classify_market_session(at: datetime) -> dict[str, object]:
    """Classify one instant without hiding overlaps or DST semantics."""
    checked = _aware(at)
    active = tuple(
        session
        for definition in _DEFINITIONS
        if (session := _active_session(checked, definition)) is not None
    )
    if not active:
        return {
            "calendar_id": _SESSION_CALENDAR_ID,
            "at_utc": checked.isoformat(),
            "primary_session": SessionGroup.OUTSIDE_PRIMARY_SESSIONS.value,
            "active_sessions": [],
            "overlap": False,
            "phase": SessionPhase.OUTSIDE.value,
            "timezone": None,
            "local_at": None,
            "utc_offset_seconds": None,
            "minutes_since_open": None,
            "minutes_to_close": None,
        }

    # During an overlap, the session that opened most recently is primary.
    primary = max(active, key=lambda item: item.opened_at.astimezone(UTC))
    offset = primary.local_at.utcoffset()
    if offset is None:
        raise ValueError("session timezone produced a naive UTC offset")
    return {
        "calendar_id": _SESSION_CALENDAR_ID,
        "at_utc": checked.isoformat(),
        "primary_session": primary.definition.group.value,
        "active_sessions": [item.definition.group.value for item in active],
        "overlap": len(active) > 1,
        "phase": primary.phase.value,
        "timezone": primary.definition.timezone_name,
        "local_at": primary.local_at.isoformat(),
        "utc_offset_seconds": int(offset.total_seconds()),
        "minutes_since_open": primary.minutes_since_open,
        "minutes_to_close": primary.minutes_to_close,
    }


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ValueError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise ValueError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{field_name} must be non-empty text")
    return value


def _timestamp(value: object, *, field_name: str) -> datetime:
    raw = _text(value, field_name=field_name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{field_name} must be RFC3339") from error
    return _aware(parsed)


def _decimal(value: object, *, field_name: str) -> Decimal:
    raw = _text(value, field_name=field_name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise ValueError(f"{field_name} must be decimal") from error
    if not parsed.is_finite():
        raise ValueError(f"{field_name} must be finite decimal")
    return parsed


def _format_decimal(value: Decimal) -> str:
    return format(value, "f")


def _ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0"
    return _format_decimal(Decimal(numerator) / Decimal(denominator))


def _empty_accumulator() -> dict[str, object]:
    return {
        "entries": 0,
        "wins": 0,
        "losses": 0,
        "return_sum": Decimal(0),
        "equity": Decimal(1),
        "mfe_sum": Decimal(0),
        "mae_sum": Decimal(0),
        "direct_stops": 0,
        "givebacks": 0,
        "overlaps": 0,
        "transitions": 0,
        "exit_reasons": {},
        "directions": {},
        "phases": {},
    }


def _increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _accumulate(
    accumulator: dict[str, object],
    episode: dict[str, object],
    entry: dict[str, object],
    transitioned: bool,
) -> None:
    decision = _object(episode.get("decision_time"), field_name="decision_time")
    post = _object(episode.get("post_outcome"), field_name="post_outcome")
    entries = cast(int, accumulator["entries"]) + 1
    accumulator["entries"] = entries
    outcome = _text(episode.get("outcome"), field_name="outcome")
    if outcome == "win":
        accumulator["wins"] = cast(int, accumulator["wins"]) + 1
    elif outcome == "loss":
        accumulator["losses"] = cast(int, accumulator["losses"]) + 1
    else:
        raise ValueError("episode outcome must be win or loss")

    return_rate = _decimal(post.get("return_rate"), field_name="return_rate")
    accumulator["return_sum"] = cast(Decimal, accumulator["return_sum"]) + return_rate
    accumulator["equity"] = cast(Decimal, accumulator["equity"]) * (
        Decimal(1) + return_rate
    )
    accumulator["mfe_sum"] = cast(Decimal, accumulator["mfe_sum"]) + _decimal(
        post.get("close_path_mfe_r"),
        field_name="close_path_mfe_r",
    )
    accumulator["mae_sum"] = cast(Decimal, accumulator["mae_sum"]) + _decimal(
        post.get("close_path_mae_r"),
        field_name="close_path_mae_r",
    )

    classification = _text(
        episode.get("classification"),
        field_name="classification",
    )
    if classification == "LOSS_DIRECT_NO_EDGE":
        accumulator["direct_stops"] = cast(int, accumulator["direct_stops"]) + 1
    if classification in {
        "LOSS_AFTER_SIGNIFICANT_MFE",
        "LOSS_AFTER_1R_OR_MORE",
    }:
        accumulator["givebacks"] = cast(int, accumulator["givebacks"]) + 1
    if entry["overlap"] is True:
        accumulator["overlaps"] = cast(int, accumulator["overlaps"]) + 1
    if transitioned:
        accumulator["transitions"] = cast(int, accumulator["transitions"]) + 1

    exit_reasons = cast(dict[str, int], accumulator["exit_reasons"])
    directions = cast(dict[str, int], accumulator["directions"])
    phases = cast(dict[str, int], accumulator["phases"])
    _increment(
        exit_reasons,
        _text(post.get("exit_reason"), field_name="exit_reason"),
    )
    _increment(
        directions,
        _text(decision.get("side"), field_name="side"),
    )
    _increment(
        phases,
        _text(entry.get("phase"), field_name="entry phase"),
    )


def _freeze_accumulator(accumulator: dict[str, object]) -> dict[str, object]:
    entries = cast(int, accumulator["entries"])
    wins = cast(int, accumulator["wins"])
    losses = cast(int, accumulator["losses"])
    return_sum = cast(Decimal, accumulator["return_sum"])
    equity = cast(Decimal, accumulator["equity"])
    mfe_sum = cast(Decimal, accumulator["mfe_sum"])
    mae_sum = cast(Decimal, accumulator["mae_sum"])
    denominator = Decimal(entries) if entries else Decimal(1)
    return {
        "entry_count": entries,
        "win_count": wins,
        "loss_count": losses,
        "win_rate": _ratio(wins, entries),
        "mean_return_rate": _format_decimal(return_sum / denominator),
        "compounded_return_rate": _format_decimal(equity - Decimal(1)),
        "mean_closed_bar_mfe_r": _format_decimal(mfe_sum / denominator),
        "mean_closed_bar_mae_r": _format_decimal(mae_sum / denominator),
        "direct_stop_count": cast(int, accumulator["direct_stops"]),
        "giveback_count": cast(int, accumulator["givebacks"]),
        "overlap_entry_count": cast(int, accumulator["overlaps"]),
        "signal_to_entry_session_transition_count": cast(
            int,
            accumulator["transitions"],
        ),
        "exit_reasons": dict(
            sorted(cast(dict[str, int], accumulator["exit_reasons"]).items())
        ),
        "directions": dict(
            sorted(cast(dict[str, int], accumulator["directions"]).items())
        ),
        "entry_phases": dict(
            sorted(cast(dict[str, int], accumulator["phases"]).items())
        ),
    }


def enrich_story_payload_sessions(payload: dict[str, object]) -> dict[str, object]:
    """Attach entry-session evidence and aggregate three-group behavior."""
    enriched = dict(payload)
    raw_episodes = _array(payload.get("episodes"), field_name="episodes")
    accumulators = {
        group.value: _empty_accumulator()
        for group in (*_PRIMARY_GROUPS, SessionGroup.OUTSIDE_PRIMARY_SESSIONS)
    }
    enriched_episodes: list[dict[str, object]] = []
    for item in raw_episodes:
        episode = dict(_object(item, field_name="episode"))
        decision = dict(
            _object(episode.get("decision_time"), field_name="decision_time")
        )
        post = _object(episode.get("post_outcome"), field_name="post_outcome")
        signal = classify_market_session(
            _timestamp(decision.get("signal_at"), field_name="signal_at")
        )
        entry = classify_market_session(
            _timestamp(post.get("filled_at"), field_name="filled_at")
        )
        transitioned = signal["primary_session"] != entry["primary_session"]
        decision["session_context"] = {
            "calendar_id": _SESSION_CALENDAR_ID,
            "signal": signal,
            "entry": entry,
            "signal_to_entry_session_transition": transitioned,
        }
        episode["decision_time"] = decision
        primary = _text(entry.get("primary_session"), field_name="primary_session")
        _accumulate(accumulators[primary], episode, entry, transitioned)
        enriched_episodes.append(episode)

    breakdown = {
        group.value: _freeze_accumulator(accumulators[group.value])
        for group in _PRIMARY_GROUPS
    }
    outside = _freeze_accumulator(
        accumulators[SessionGroup.OUTSIDE_PRIMARY_SESSIONS.value]
    )
    fingerprint_material = json.dumps(
        {
            "calendar_id": _SESSION_CALENDAR_ID,
            "episodes": [
                {
                    "episode_id": episode.get("episode_id"),
                    "session_context": _object(
                        _object(
                            episode.get("decision_time"),
                            field_name="decision_time",
                        ).get("session_context"),
                        field_name="session_context",
                    ),
                }
                for episode in enriched_episodes
            ],
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    session_fingerprint = sha256(fingerprint_material.encode("utf-8")).hexdigest()
    enriched["episodes"] = enriched_episodes
    enriched["session_intelligence"] = {
        "schema": _SESSION_SCHEMA,
        "calendar_id": _SESSION_CALENDAR_ID,
        "session_intelligence_fingerprint": session_fingerprint,
        "research_convention": True,
        "exchange_hours_authority": False,
        "primary_assignment_rule": "most-recently-opened-active-session-v1",
        "primary_groups": [group.value for group in _PRIMARY_GROUPS],
        "session_windows_local": {
            "ASIA": {
                "timezone": "Asia/Tokyo",
                "open": "09:00",
                "close": "18:00",
            },
            "LONDON": {
                "timezone": "Europe/London",
                "open": "08:00",
                "close": "17:00",
            },
            "NEW_YORK": {
                "timezone": "America/New_York",
                "open": "08:00",
                "close": "17:00",
            },
        },
        "dst_aware": True,
        "overlaps_retained": True,
        "outside_primary_sessions_retained": True,
        "breakdown": breakdown,
        "outside_primary_sessions": outside,
    }
    return enriched
