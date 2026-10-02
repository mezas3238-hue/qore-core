"""Deterministic lineage and replay contract for the Market Digital Twin.

WP-01 requires more than isolated snapshots. The twin must preserve a causal
history that can be replayed, audited and reproduced.

This module chains immutable MarketDigitalTwinSnapshot instances. It fails
closed on:
- non-monotonic timestamps;
- evidence-cutoff regression;
- prediction errors disappearing after they were observed;
- duplicate snapshots;
- future-tainted snapshots;
- lineage tampering.

The history itself carries no trading authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.market_digital_twin import (
    MarketDigitalTwinSnapshot,
)


@dataclass(frozen=True, slots=True)
class DigitalTwinLineageEntry:
    sequence: int
    as_of: datetime
    snapshot_fingerprint: str
    parent_snapshot_fingerprint: str | None
    cumulative_prediction_error_ids: tuple[str, ...]
    unresolved_prediction_ids: tuple[str, ...]
    lineage_hash: str

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("lineage sequence must be positive")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("lineage as_of must be timezone-aware")
        if not self.snapshot_fingerprint:
            raise ValueError("snapshot fingerprint must be non-empty")
        if self.sequence == 1 and self.parent_snapshot_fingerprint is not None:
            raise ValueError("genesis lineage entry cannot have a parent")
        if self.sequence > 1 and not self.parent_snapshot_fingerprint:
            raise ValueError("non-genesis lineage entry requires a parent")
        if not self.lineage_hash:
            raise ValueError("lineage hash must be non-empty")


@dataclass(frozen=True, slots=True)
class MarketDigitalTwinHistory:
    entries: tuple[DigitalTwinLineageEntry, ...]
    snapshots: tuple[MarketDigitalTwinSnapshot, ...]
    head_snapshot_fingerprint: str | None
    head_lineage_hash: str | None
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if len(self.entries) != len(self.snapshots):
            raise ValueError("history entries and snapshots must have equal length")
        if bool(self.entries) != bool(self.head_snapshot_fingerprint):
            raise ValueError("history head snapshot fingerprint mismatch")
        if bool(self.entries) != bool(self.head_lineage_hash):
            raise ValueError("history head lineage hash mismatch")
        if self.entries:
            if self.entries[-1].snapshot_fingerprint != self.head_snapshot_fingerprint:
                raise ValueError("history head snapshot fingerprint is inconsistent")
            if self.entries[-1].lineage_hash != self.head_lineage_hash:
                raise ValueError("history head lineage hash is inconsistent")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("digital twin history cannot carry trading authority")


def empty_market_digital_twin_history() -> MarketDigitalTwinHistory:
    return MarketDigitalTwinHistory(
        entries=(),
        snapshots=(),
        head_snapshot_fingerprint=None,
        head_lineage_hash=None,
    )


def _lineage_hash(
    *,
    sequence: int,
    as_of: datetime,
    snapshot_fingerprint: str,
    parent_snapshot_fingerprint: str | None,
    parent_lineage_hash: str | None,
    cumulative_prediction_error_ids: tuple[str, ...],
    unresolved_prediction_ids: tuple[str, ...],
) -> str:
    payload = {
        "sequence": sequence,
        "as_of": as_of.astimezone(UTC).isoformat(),
        "snapshot_fingerprint": snapshot_fingerprint,
        "parent_snapshot_fingerprint": parent_snapshot_fingerprint,
        "parent_lineage_hash": parent_lineage_hash,
        "cumulative_prediction_error_ids": cumulative_prediction_error_ids,
        "unresolved_prediction_ids": unresolved_prediction_ids,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def append_market_digital_twin_snapshot(
    history: MarketDigitalTwinHistory,
    snapshot: MarketDigitalTwinSnapshot,
) -> MarketDigitalTwinHistory:
    """Append one causal snapshot and return a new immutable history."""

    if snapshot.future_market_used:
        raise ValueError("future-tainted digital twin snapshot is forbidden")

    if history.snapshots:
        previous = history.snapshots[-1]
        if snapshot.as_of <= previous.as_of:
            raise ValueError("digital twin snapshots must advance strictly in time")
        if snapshot.evidence_cutoff_at < previous.evidence_cutoff_at:
            raise ValueError("digital twin evidence cutoff cannot regress")
        if snapshot.fingerprint == previous.fingerprint:
            raise ValueError("duplicate digital twin snapshot is forbidden")

        previous_error_ids = {
            item.prediction_id
            for item in previous.prediction_error_ledger
        }
        current_error_ids = {
            item.prediction_id
            for item in snapshot.prediction_error_ledger
        }
        disappeared = previous_error_ids - current_error_ids
        if disappeared:
            raise ValueError(
                "matured prediction errors cannot disappear from lineage: "
                f"{sorted(disappeared)}"
            )

    cumulative_error_ids = tuple(
        sorted(
            {
                item.prediction_id
                for existing in (*history.snapshots, snapshot)
                for item in existing.prediction_error_ledger
            }
        )
    )
    sequence = len(history.entries) + 1
    parent_snapshot = history.head_snapshot_fingerprint
    parent_lineage = history.head_lineage_hash
    lineage_hash = _lineage_hash(
        sequence=sequence,
        as_of=snapshot.as_of,
        snapshot_fingerprint=snapshot.fingerprint,
        parent_snapshot_fingerprint=parent_snapshot,
        parent_lineage_hash=parent_lineage,
        cumulative_prediction_error_ids=cumulative_error_ids,
        unresolved_prediction_ids=snapshot.unresolved_prediction_ids,
    )
    entry = DigitalTwinLineageEntry(
        sequence=sequence,
        as_of=snapshot.as_of,
        snapshot_fingerprint=snapshot.fingerprint,
        parent_snapshot_fingerprint=parent_snapshot,
        cumulative_prediction_error_ids=cumulative_error_ids,
        unresolved_prediction_ids=snapshot.unresolved_prediction_ids,
        lineage_hash=lineage_hash,
    )
    return MarketDigitalTwinHistory(
        entries=(*history.entries, entry),
        snapshots=(*history.snapshots, snapshot),
        head_snapshot_fingerprint=snapshot.fingerprint,
        head_lineage_hash=lineage_hash,
    )


def verify_market_digital_twin_history(
    history: MarketDigitalTwinHistory,
) -> None:
    """Recompute the full lineage and fail closed on any inconsistency."""

    if len(history.entries) != len(history.snapshots):
        raise ValueError("history shape mismatch")

    parent_snapshot: str | None = None
    parent_lineage: str | None = None
    cumulative_error_ids: set[str] = set()
    previous_as_of: datetime | None = None
    previous_cutoff: datetime | None = None

    for index, (entry, snapshot) in enumerate(
        zip(history.entries, history.snapshots, strict=True),
        start=1,
    ):
        if entry.sequence != index:
            raise ValueError("lineage sequence mismatch")
        if snapshot.fingerprint != entry.snapshot_fingerprint:
            raise ValueError("snapshot fingerprint mismatch")
        if entry.parent_snapshot_fingerprint != parent_snapshot:
            raise ValueError("parent snapshot fingerprint mismatch")
        if previous_as_of is not None and snapshot.as_of <= previous_as_of:
            raise ValueError("history time is not strictly increasing")
        if (
            previous_cutoff is not None
            and snapshot.evidence_cutoff_at < previous_cutoff
        ):
            raise ValueError("history evidence cutoff regressed")

        current_ids = {
            item.prediction_id
            for item in snapshot.prediction_error_ledger
        }
        cumulative_error_ids.update(current_ids)
        expected_cumulative = tuple(sorted(cumulative_error_ids))
        if entry.cumulative_prediction_error_ids != expected_cumulative:
            raise ValueError("prediction-error lineage mismatch")

        expected_hash = _lineage_hash(
            sequence=index,
            as_of=snapshot.as_of,
            snapshot_fingerprint=snapshot.fingerprint,
            parent_snapshot_fingerprint=parent_snapshot,
            parent_lineage_hash=parent_lineage,
            cumulative_prediction_error_ids=expected_cumulative,
            unresolved_prediction_ids=snapshot.unresolved_prediction_ids,
        )
        if entry.lineage_hash != expected_hash:
            raise ValueError("lineage hash mismatch")

        parent_snapshot = snapshot.fingerprint
        parent_lineage = entry.lineage_hash
        previous_as_of = snapshot.as_of
        previous_cutoff = snapshot.evidence_cutoff_at

    if history.head_snapshot_fingerprint != parent_snapshot:
        raise ValueError("history head snapshot mismatch")
    if history.head_lineage_hash != parent_lineage:
        raise ValueError("history head lineage mismatch")
