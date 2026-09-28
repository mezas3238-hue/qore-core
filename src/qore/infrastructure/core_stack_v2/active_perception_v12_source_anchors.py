"""Frozen source-only evaluation anchors for Shared WP-05 V12.

These anchors are reconstructed from the exact same causal R8 source population
used to build the historical BID/ASK acquisition manifest.  They contain no
matured target/outcome information and exist only to define deterministic
evaluation timestamps for later microstructure representation building.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

SOURCE_ANCHOR_IDENTITY: Final = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_SOURCE_ANCHORS_001"
)
EXPECTED_SOURCE_COUNT: Final = 6804
EXPECTED_ACQUISITION_MANIFEST_SHA256: Final = (
    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("source anchor timestamp must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class V12SourceAnchorManifest:
    partition: str
    acquisition_manifest_sha256: str
    source_times: tuple[datetime, ...]
    target_or_outcome_used: bool = False
    r6_r5_read: bool = False
    fresh_holdout_opened: bool = False
    methodology_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.partition != "r8":
            raise ValueError("V12 source anchors are restricted to R8")
        if self.acquisition_manifest_sha256 != EXPECTED_ACQUISITION_MANIFEST_SHA256:
            raise ValueError("source anchors must bind frozen acquisition manifest")
        if len(self.source_times) != EXPECTED_SOURCE_COUNT:
            raise ValueError("source anchor population drift")
        normalized = tuple(_utc(value) for value in self.source_times)
        if normalized != tuple(sorted(normalized)):
            raise ValueError("source anchors must be chronological")
        if len(normalized) != len(set(normalized)):
            raise ValueError("source anchors must be unique")
        if (
            self.target_or_outcome_used
            or self.r6_r5_read
            or self.fresh_holdout_opened
            or self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("source anchors contain forbidden evidence or authority")

    def logical_payload(self) -> dict[str, object]:
        ordered = tuple(_utc(value) for value in self.source_times)
        return {
            "identity": SOURCE_ANCHOR_IDENTITY,
            "partition": self.partition,
            "acquisition_manifest_sha256": self.acquisition_manifest_sha256,
            "source_count": len(ordered),
            "source_min": ordered[0].isoformat(timespec="microseconds"),
            "source_max": ordered[-1].isoformat(timespec="microseconds"),
            "source_times": [
                value.isoformat(timespec="microseconds") for value in ordered
            ],
            "target_or_outcome_used": False,
            "r6_r5_read": False,
            "fresh_holdout_opened": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
        }

    @property
    def digest_sha256(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.logical_payload(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()


def build_v12_source_anchor_manifest(
    source_times: Sequence[datetime],
    *,
    acquisition_manifest_sha256: str,
) -> V12SourceAnchorManifest:
    ordered = tuple(sorted({_utc(value) for value in source_times}))
    return V12SourceAnchorManifest(
        partition="r8",
        acquisition_manifest_sha256=acquisition_manifest_sha256,
        source_times=ordered,
    )
