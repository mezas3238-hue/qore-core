"""Deterministic causal analog memory for Shared Core V2."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from qore.infrastructure.core_stack_v2.intelligence import (
    AnalogSummary,
    HistoricalAnalogEvidence,
)


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _decimal(value: str) -> Decimal | None:
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


@dataclass(frozen=True, slots=True)
class ClosedEpisode:
    episode_id: str
    market: str
    closed_at: datetime
    signature: tuple[tuple[str, str], ...]
    terminal_r: Decimal

    def __post_init__(self) -> None:
        if not self.episode_id or not self.market:
            raise ValueError("episode identity must be non-empty")
        _iso(self.closed_at)
        if self.signature != tuple(sorted(self.signature)):
            raise ValueError("episode signature must be canonical")
        if len({key for key, _ in self.signature}) != len(self.signature):
            raise ValueError("episode signature keys must be unique")
        if not self.terminal_r.is_finite():
            raise ValueError("terminal_r must be finite")


@dataclass(frozen=True, slots=True)
class AnalogQuery:
    market: str
    as_of: datetime
    signature: tuple[tuple[str, str], ...]
    maximum_analogs: int = 32
    minimum_similarity_bps: int = 2_500

    def __post_init__(self) -> None:
        _iso(self.as_of)
        if self.signature != tuple(sorted(self.signature)):
            raise ValueError("query signature must be canonical")
        if self.maximum_analogs <= 0:
            raise ValueError("maximum_analogs must be positive")
        if not 0 <= self.minimum_similarity_bps <= 10_000:
            raise ValueError("minimum similarity must be within 0..10000")


def _field_similarity(left: str, right: str) -> Decimal:
    if left == right:
        return Decimal(1)
    lnum = _decimal(left)
    rnum = _decimal(right)
    if lnum is None or rnum is None:
        return Decimal(0)
    scale = max(abs(lnum), abs(rnum), Decimal(1))
    relative = abs(lnum - rnum) / scale
    return max(Decimal(0), Decimal(1) - relative)


def _similarity(
    episode: ClosedEpisode,
    query: AnalogQuery,
    weights: dict[str, Decimal],
) -> int:
    current = dict(query.signature)
    historical = dict(episode.signature)
    common = sorted(set(current) & set(historical))
    if not common:
        return 0
    numerator = Decimal(0)
    denominator = Decimal(0)
    for field in common:
        weight = weights.get(field, Decimal(1))
        if weight <= 0:
            continue
        denominator += weight
        numerator += weight * _field_similarity(current[field], historical[field])
    if denominator <= 0:
        return 0
    return int(
        min(Decimal(10_000), (numerator / denominator) * Decimal(10_000))
    )


class CausalAnalogMemory:
    """Immutable-by-use memory of closed historical episodes."""

    def __init__(
        self,
        episodes: tuple[ClosedEpisode, ...],
        *,
        feature_weights: dict[str, Decimal] | None = None,
    ) -> None:
        ordered = tuple(
            sorted(episodes, key=lambda item: (item.closed_at, item.episode_id))
        )
        if len({item.episode_id for item in ordered}) != len(ordered):
            raise ValueError("duplicate historical episode id")
        self._episodes = ordered
        self._weights = dict(feature_weights or {})

    def query(self, request: AnalogQuery) -> AnalogSummary:
        eligible = [
            item
            for item in self._episodes
            if item.market == request.market and item.closed_at < request.as_of
        ]
        ranked = sorted(
            (
                (_similarity(item, request, self._weights), item)
                for item in eligible
            ),
            key=lambda pair: (-pair[0], pair[1].closed_at, pair[1].episode_id),
        )
        selected = [
            pair
            for pair in ranked
            if pair[0] >= request.minimum_similarity_bps
        ][: request.maximum_analogs]

        analogs = tuple(
            HistoricalAnalogEvidence(
                episode_id=item.episode_id,
                market=item.market,
                closed_at=item.closed_at,
                similarity_bps=similarity,
                predecision_signature=item.signature,
                terminal_r=format(item.terminal_r, "f"),
            )
            for similarity, item in selected
        )
        if not selected:
            return AnalogSummary(
                as_of=request.as_of,
                analogs=(),
                effective_sample_size="0",
                weighted_mean_r=None,
                weighted_loss_rate=None,
                confidence_bps=0,
            )

        weights = [Decimal(similarity) / Decimal(10_000) for similarity, _ in selected]
        weight_sum = sum(weights, Decimal(0))
        squared = sum((weight * weight for weight in weights), Decimal(0))
        effective_n = (
            Decimal(0)
            if squared == 0
            else (weight_sum * weight_sum) / squared
        )
        mean = sum(
            (
                weight * item.terminal_r
                for weight, (_, item) in zip(weights, selected, strict=True)
            ),
            Decimal(0),
        ) / weight_sum
        loss_rate = sum(
            (
                weight
                for weight, (_, item) in zip(weights, selected, strict=True)
                if item.terminal_r < 0
            ),
            Decimal(0),
        ) / weight_sum
        mean_similarity = sum(
            (Decimal(similarity) for similarity, _ in selected),
            Decimal(0),
        ) / Decimal(len(selected))
        sample_factor = min(
            Decimal(1),
            effective_n / Decimal(max(1, request.maximum_analogs // 2)),
        )
        confidence = int(min(Decimal(10_000), mean_similarity * sample_factor))

        return AnalogSummary(
            as_of=request.as_of,
            analogs=analogs,
            effective_sample_size=format(effective_n, "f"),
            weighted_mean_r=format(mean, "f"),
            weighted_loss_rate=format(loss_rate, "f"),
            confidence_bps=confidence,
        )
