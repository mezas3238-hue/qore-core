"""Causal acquisition manifest for Shared WP-05 Active Perception V12.

This boundary accepts source timestamps only. It has no target/outcome input and
therefore cannot select provider evidence using matured structural-failure
labels. Historical tick acquisition is bounded to the causal context required
by the pre-existing V11 source state and its final +15 minute checkpoint.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

V12_TICK_PRE_SOURCE_MINUTES: Final = 60
V12_TICK_POST_SOURCE_MINUTES: Final = 15
V12_TICK_PARTITION: Final = "r8"


def _utc(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("V12 acquisition timestamps must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class V12TickAcquisitionWindow:
    from_at: datetime
    to_at: datetime
    source_count: int

    def __post_init__(self) -> None:
        start = _utc(self.from_at)
        end = _utc(self.to_at)
        if end <= start:
            raise ValueError("V12 acquisition window must be positive")
        if type(self.source_count) is not int or self.source_count <= 0:
            raise ValueError("V12 acquisition window source_count must be positive")

    def logical_values(self) -> tuple[object, ...]:
        return (
            _utc(self.from_at).isoformat(timespec="microseconds"),
            _utc(self.to_at).isoformat(timespec="microseconds"),
            self.source_count,
        )


@dataclass(frozen=True, slots=True)
class V12TickAcquisitionManifest:
    partition: str
    provider_symbol: str
    source_count: int
    source_min: datetime
    source_max: datetime
    windows: tuple[V12TickAcquisitionWindow, ...]
    evidence_sha256: tuple[tuple[str, str], ...]
    pre_source_minutes: int = V12_TICK_PRE_SOURCE_MINUTES
    post_source_minutes: int = V12_TICK_POST_SOURCE_MINUTES

    def __post_init__(self) -> None:
        if self.partition != V12_TICK_PARTITION:
            raise ValueError("V12 sensor discovery manifest must be R8 only")
        if (
            not isinstance(self.provider_symbol, str)
            or not self.provider_symbol
            or self.provider_symbol != self.provider_symbol.strip()
        ):
            raise ValueError("V12 provider_symbol must be non-empty and trimmed")
        if type(self.source_count) is not int or self.source_count <= 0:
            raise ValueError("V12 source_count must be positive")
        if _utc(self.source_max) < _utc(self.source_min):
            raise ValueError("V12 source range is inverted")
        if not self.windows:
            raise ValueError("V12 acquisition manifest requires windows")
        if self.pre_source_minutes != V12_TICK_PRE_SOURCE_MINUTES:
            raise ValueError("V12 pre-source acquisition horizon drift")
        if self.post_source_minutes != V12_TICK_POST_SOURCE_MINUTES:
            raise ValueError("V12 post-source acquisition horizon drift")
        names = [name for name, _digest in self.evidence_sha256]
        if names != sorted(names) or len(names) != len(set(names)):
            raise ValueError("V12 evidence identities must be unique and sorted")
        for name, digest in self.evidence_sha256:
            if not name or len(digest) != 64:
                raise ValueError("V12 evidence identity must contain SHA-256")
            int(digest, 16)

    def logical_payload(self) -> Mapping[str, object]:
        return {
            "partition": self.partition,
            "provider_symbol": self.provider_symbol,
            "source_count": self.source_count,
            "source_min": _utc(self.source_min).isoformat(timespec="microseconds"),
            "source_max": _utc(self.source_max).isoformat(timespec="microseconds"),
            "pre_source_minutes": self.pre_source_minutes,
            "post_source_minutes": self.post_source_minutes,
            "evidence_sha256": list(self.evidence_sha256),
            "windows": [window.logical_values() for window in self.windows],
            "target_or_outcome_used_for_selection": False,
            "r6_r5_read_for_selection": False,
            "fresh_holdout_opened": False,
        }

    @property
    def digest_sha256(self) -> str:
        encoded = json.dumps(
            self.logical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def build_v12_tick_acquisition_manifest(
    *,
    source_times: Sequence[datetime],
    provider_symbol: str,
    evidence_sha256: Mapping[str, str],
) -> V12TickAcquisitionManifest:
    """Build an R8-only manifest from already causal source timestamps."""

    ordered = tuple(sorted({_utc(item) for item in source_times}))
    if not ordered:
        raise ValueError("V12 acquisition requires at least one causal source")

    raw = [
        V12TickAcquisitionWindow(
            from_at=source - timedelta(minutes=V12_TICK_PRE_SOURCE_MINUTES),
            to_at=source + timedelta(minutes=V12_TICK_POST_SOURCE_MINUTES),
            source_count=1,
        )
        for source in ordered
    ]

    merged: list[V12TickAcquisitionWindow] = []
    for window in raw:
        if not merged or _utc(window.from_at) > _utc(merged[-1].to_at):
            merged.append(window)
            continue
        previous = merged.pop()
        merged.append(
            V12TickAcquisitionWindow(
                from_at=previous.from_at,
                to_at=max(_utc(previous.to_at), _utc(window.to_at)),
                source_count=previous.source_count + window.source_count,
            )
        )

    identities = tuple(sorted(evidence_sha256.items()))
    return V12TickAcquisitionManifest(
        partition=V12_TICK_PARTITION,
        provider_symbol=provider_symbol,
        source_count=len(ordered),
        source_min=ordered[0],
        source_max=ordered[-1],
        windows=tuple(merged),
        evidence_sha256=identities,
    )
