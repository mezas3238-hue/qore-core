"""Independent B causal source binding for *every* VT08 cognitive Situation field.

The raw-bar catalog is an input, not an authenticated oracle: callers must
derive it via the independent native raw verifier and pin its SHA lineage.
This only proves temporal/value-binding consistency. Semantic fidelity to
TTrades requires separately versioned source rules and independent reviewers.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    CAUSAL_FIELDS,
    Vt08FiveMarketResearchSituation,
)

SHA256: Final = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_CLASSES: Final = frozenset(
    ("A_WRITTEN", "B_INDEPENDENT", "C_QORE", "D_UNSPECIFIED")
)


def _sha(value: object) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("VT08 B per-field time must be ISO string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("VT08 B per-field time invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("VT08 B per-field time missing offset")
    return parsed.astimezone(UTC)


def _json_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class FieldSourceAuditResult:
    verified_field_clocks: int
    required_fields: int
    raw_bars_referenced: int
    qore_containment_fields: tuple[str, ...]
    unspecified_semantics_fields: tuple[str, ...]
    causal_values_and_clocks_bound: bool
    source_semantics_certified: bool = False
    economic_certified: bool = False
    order_authorized: bool = False


def verify_all_situation_field_receipts(
    situation: Vt08FiveMarketResearchSituation,
    proofs: Mapping[str, Mapping[str, object]],
    bar_catalog: Mapping[str, Mapping[str, object]],
    *,
    pinned_raw_shas: frozenset[str],
) -> FieldSourceAuditResult:
    """Do not confuse caller field hash with physical bar or semantic proof."""
    if set(proofs) != set(CAUSAL_FIELDS):
        raise ValueError("VT08 B missing/extra Situation source proof fields")
    if not pinned_raw_shas or any(not _sha(x) for x in pinned_raw_shas):
        raise ValueError("VT08 B missing immutable raw feed SHA custody")
    if not bar_catalog:
        raise ValueError("VT08 B no independently constructed bar catalog")
    values = situation.payload()
    cutoffs = dict(situation.feature_cutoffs)
    observed = 0
    referenced: set[str] = set()
    containment: list[str] = []
    unspecified: list[str] = []
    for field in CAUSAL_FIELDS:
        proof = proofs[field]
        actual = values.get(field)
        if proof.get("value_sha256") != _json_sha(actual):
            raise ValueError(f"VT08 B field value fingerprint drift: {field}")
        if proof.get("semantic_class") not in SOURCE_CLASSES:
            raise ValueError(f"VT08 B missing source semantic classification: {field}")
        label = proof.get("source_rule_ref")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"VT08 B missing source rule reference: {field}")
        if proof.get("semantic_class") == "C_QORE":
            containment.append(field)
        if proof.get("semantic_class") == "D_UNSPECIFIED":
            unspecified.append(field)
        bar_ids = proof.get("source_bar_ids")
        if not isinstance(bar_ids, (tuple, list)) or not bar_ids:
            raise ValueError(f"VT08 B field source bar IDs absent: {field}")
        if len(set(str(x) for x in bar_ids)) != len(bar_ids):
            raise ValueError(f"VT08 B duplicated field bars: {field}")
        max_available: datetime | None = None
        for bar_id in bar_ids:
            if not _sha(bar_id) or bar_id not in bar_catalog:
                raise ValueError(f"VT08 B missing authenticated source bar ID: {field}")
            record = bar_catalog[bar_id]
            if record.get("source_bar_id") != bar_id:
                raise ValueError(f"VT08 B altered source bar ID: {field}")
            if record.get("source_raw_sha256") not in pinned_raw_shas:
                raise ValueError(f"VT08 B source bar outside pinned raw feed: {field}")
            closed = _utc(record.get("closed_at_utc"))
            available = _utc(record.get("available_at_utc"))
            if closed != available:
                raise ValueError(f"VT08 B closed_at vs available_at drift: {field}")
            if available > situation.as_of.astimezone(UTC):
                raise ValueError(f"VT08 B field uses future bar: {field}")
            if available > cutoffs[field].astimezone(UTC):
                raise ValueError(f"VT08 B field reads after declared cutoff: {field}")
            if max_available is None or available > max_available:
                max_available = available
            referenced.add(str(bar_id))
        if max_available != cutoffs[field].astimezone(UTC):
            raise ValueError(f"VT08 B field cutoff differs from source bars: {field}")
        observed += 1
    return FieldSourceAuditResult(
        verified_field_clocks=observed,
        required_fields=len(CAUSAL_FIELDS),
        raw_bars_referenced=len(referenced),
        qore_containment_fields=tuple(containment),
        unspecified_semantics_fields=tuple(unspecified),
        causal_values_and_clocks_bound=True,
    )
