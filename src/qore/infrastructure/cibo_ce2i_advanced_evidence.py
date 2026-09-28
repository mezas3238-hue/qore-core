"""Causal provenance envelope for advanced CE2I evidence.

The snapshot is assembled before one capital decision and binds the exact source
references plus the typed advanced evidence payload. It contains no broker
mutation authority and rejects synthetic/outcome-aware provenance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedPortfolioEvidence,
)


@dataclass(frozen=True, slots=True)
class AdvancedCe2iEvidenceSnapshot:
    evidence_id: str
    assembled_at: datetime
    source_refs: tuple[str, ...]
    evidence: AdvancedPortfolioEvidence
    synthetic: bool = False
    outcome_aware: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise CiboCapitalManagementError(
                "advanced CE2I evidence snapshot id is required"
            )
        _aware(self.assembled_at, "assembled_at")
        if not self.source_refs:
            raise CiboCapitalManagementError(
                "advanced CE2I evidence source refs are required"
            )
        if (
            len(self.source_refs) != len(set(self.source_refs))
            or any(not item for item in self.source_refs)
        ):
            raise CiboCapitalManagementError(
                "advanced CE2I source refs must be unique/non-empty"
            )
        if not isinstance(self.evidence, AdvancedPortfolioEvidence):
            raise CiboCapitalManagementError(
                "advanced CE2I evidence payload must be canonical"
            )
        if type(self.synthetic) is not bool or type(self.outcome_aware) is not bool:
            raise CiboCapitalManagementError(
                "advanced CE2I provenance flags must be bool"
            )
        if self.synthetic or self.outcome_aware:
            raise CiboCapitalManagementError(
                "advanced CE2I qualification evidence must be causal/non-synthetic"
            )


def assert_advanced_evidence_snapshot_causal(
    snapshot: AdvancedCe2iEvidenceSnapshot,
    *,
    decision_at: datetime,
    max_age_seconds: Decimal,
) -> None:
    if not isinstance(snapshot, AdvancedCe2iEvidenceSnapshot):
        raise CiboCapitalManagementError(
            "advanced CE2I snapshot must be canonical"
        )
    _aware(decision_at, "decision_at")
    if (
        not isinstance(max_age_seconds, Decimal)
        or not max_age_seconds.is_finite()
        or max_age_seconds <= 0
    ):
        raise CiboCapitalManagementError(
            "advanced CE2I max age must be finite positive Decimal"
        )
    if snapshot.assembled_at > decision_at:
        raise CiboCapitalManagementError(
            "advanced CE2I snapshot cannot postdate decision"
        )
    delta = decision_at - snapshot.assembled_at
    age = (
        Decimal(delta.days * 86400 + delta.seconds)
        + Decimal(delta.microseconds) / Decimal(1_000_000)
    )
    if age > max_age_seconds:
        raise CiboCapitalManagementError(
            "advanced CE2I snapshot exceeds decision freshness bound"
        )


def advanced_evidence_snapshot_sha256(
    snapshot: AdvancedCe2iEvidenceSnapshot,
) -> str:
    if not isinstance(snapshot, AdvancedCe2iEvidenceSnapshot):
        raise CiboCapitalManagementError(
            "advanced CE2I snapshot must be canonical"
        )
    raw = json.dumps(
        _canonicalize(snapshot),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonicalize(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"advanced CE2I {name} must be timezone-aware"
        )
