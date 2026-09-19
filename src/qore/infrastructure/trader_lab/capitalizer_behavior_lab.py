"""Leakage-resistant Behavior Lab records for the QORE Capitalizer.

This module is diagnostic research infrastructure. It does not define an entry rule, grant
promotion authority, or create execution authority. Pre-decision features and post-outcome
labels are represented by separate immutable objects so an outcome cannot silently enter the
decision-time feature matrix.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from re import fullmatch

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    EvidenceStrength,
    MarketState,
    market_is_allowed,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerExecutionState,
)


def _validate_time(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _validate_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field_name} must be finite Decimal")


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    normalized = value.normalize()
    return format(normalized, "f") if normalized == normalized.to_integral() else str(normalized)


@dataclass(frozen=True, slots=True)
class CapitalizerFeatureValue:
    """One decision-time research feature with explicit observation time."""

    name: str
    value: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if fullmatch(r"[A-Z][A-Z0-9_]{1,63}", self.name) is None:
            raise ValueError("feature name must use canonical uppercase token syntax")
        if not self.value:
            raise ValueError("feature value must be non-empty")
        _validate_time(self.observed_at, field_name="feature observed_at")

    def logical_values(self) -> tuple[str, str, str]:
        return (
            self.name,
            self.value,
            self.observed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class CapitalizerBehaviorSnapshot:
    """Exact pre-entry state persisted for later causal/failure analysis."""

    episode_id: str
    symbol: str
    session: CapitalizerSession
    decision_at: datetime
    hypothesis_id: str
    source_event_id: str
    event_generation: int
    side: CapitalizerSide
    market_state: MarketState
    state_family_id: str
    evidence_strength: EvidenceStrength
    execution: CapitalizerExecutionState
    features: tuple[CapitalizerFeatureValue, ...] = ()

    def __post_init__(self) -> None:
        if not self.episode_id or not self.hypothesis_id or not self.source_event_id:
            raise ValueError("behavior snapshot identity fields must be non-empty")
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("behavior snapshot symbol is outside frozen session universe")
        _validate_time(self.decision_at, field_name="decision_at")
        if self.event_generation < 1:
            raise ValueError("event_generation must be >= 1")
        if not self.state_family_id:
            raise ValueError("state_family_id must be non-empty")
        names = tuple(feature.name for feature in self.features)
        if len(set(names)) != len(names):
            raise ValueError("behavior snapshot feature names must be unique")
        if names != tuple(sorted(names)):
            raise ValueError("behavior snapshot features must use canonical name order")
        if any(feature.observed_at > self.decision_at for feature in self.features):
            raise ValueError("future feature cannot enter pre-entry behavior snapshot")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.episode_id,
            self.symbol,
            self.session.value,
            self.decision_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.hypothesis_id,
            self.source_event_id,
            self.event_generation,
            self.side.value,
            self.market_state.value,
            self.state_family_id,
            self.evidence_strength.value,
            (
                _canonical_decimal(self.execution.spread_points),
                _canonical_decimal(self.execution.commission_cost_r),
                _canonical_decimal(self.execution.expected_slippage_r),
                self.execution.quote_age_ms,
                self.execution.observed_latency_ms,
                self.execution.quality.value,
            ),
            tuple(feature.logical_values() for feature in self.features),
        )


@dataclass(frozen=True, slots=True)
class CapitalizerBehaviorOutcome:
    """Post-close label. It is never admitted into the pre-entry feature snapshot."""

    episode_id: str
    closed_at: datetime
    gross_r: Decimal
    explicit_cost_r: Decimal
    net_r: Decimal
    exit_reason: str
    loss_cause_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("outcome episode_id must be non-empty")
        _validate_time(self.closed_at, field_name="closed_at")
        _validate_decimal(self.gross_r, field_name="gross_r")
        _validate_decimal(self.explicit_cost_r, field_name="explicit_cost_r")
        _validate_decimal(self.net_r, field_name="net_r")
        if self.explicit_cost_r < 0:
            raise ValueError("explicit_cost_r must be non-negative")
        if self.net_r != self.gross_r - self.explicit_cost_r:
            raise ValueError("net_r must equal gross_r minus explicit_cost_r")
        if not self.exit_reason:
            raise ValueError("exit_reason must be non-empty")
        if self.loss_cause_tags != tuple(sorted(set(self.loss_cause_tags))):
            raise ValueError("loss_cause_tags must be unique canonical order")
        if self.net_r >= 0 and self.loss_cause_tags:
            raise ValueError("non-losing outcome cannot carry loss_cause_tags")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.episode_id,
            self.closed_at.astimezone(UTC).isoformat(timespec="microseconds"),
            _canonical_decimal(self.gross_r),
            _canonical_decimal(self.explicit_cost_r),
            _canonical_decimal(self.net_r),
            self.exit_reason,
            self.loss_cause_tags,
        )


@dataclass(frozen=True, slots=True)
class CapitalizerBehaviorEpisode:
    """One fully observed research episode with causal snapshot and later label."""

    snapshot: CapitalizerBehaviorSnapshot
    outcome: CapitalizerBehaviorOutcome

    def __post_init__(self) -> None:
        if self.snapshot.episode_id != self.outcome.episode_id:
            raise ValueError("snapshot/outcome episode identities must match")
        if self.outcome.closed_at < self.snapshot.decision_at:
            raise ValueError("outcome cannot predate its decision-time snapshot")

    def logical_values(self) -> tuple[object, ...]:
        return (self.snapshot.logical_values(), self.outcome.logical_values())


def behavior_episode_fingerprint(episode: CapitalizerBehaviorEpisode) -> str:
    """Canonical SHA-256 for one complete research episode."""

    encoded = json.dumps(
        episode.logical_values(),
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def canonical_behavior_episodes(
    episodes: tuple[CapitalizerBehaviorEpisode, ...],
) -> tuple[CapitalizerBehaviorEpisode, ...]:
    """Chronological canonical order with duplicate episode rejection."""

    ids = tuple(item.snapshot.episode_id for item in episodes)
    if len(ids) != len(set(ids)):
        raise ValueError("behavior episode ids must be unique")
    return tuple(
        sorted(
            episodes,
            key=lambda item: (
                item.snapshot.decision_at.astimezone(UTC),
                item.snapshot.episode_id,
            ),
        )
    )
