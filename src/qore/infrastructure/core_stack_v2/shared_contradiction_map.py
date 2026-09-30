"""First-class causal contradiction map for Shared scientific cognition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ContradictionEvidence:
    evidence_id: str
    hypothesis_id: str
    as_of: datetime
    evidence_cutoff_at: datetime
    support_bps: int
    contradiction_bps: int
    data_quality_bps: int
    independent_group: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.hypothesis_id.strip():
            raise ValueError("contradiction evidence identity must be explicit")
        for name in ("as_of", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"contradiction evidence {name} must be aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("contradiction evidence cannot use future evidence")
        for name in ("support_bps", "contradiction_bps", "data_quality_bps"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if not self.independent_group.strip():
            raise ValueError("independent_group must be explicit")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("evidence_refs must be canonical")


@dataclass(frozen=True, slots=True)
class HypothesisContradictionState:
    hypothesis_id: str
    as_of: datetime | None
    evidence_cutoff_at: datetime | None
    support_bps: int
    contradiction_bps: int
    net_support_bps: int
    independent_group_count: int
    evidence_count: int
    data_quality_bps: int
    assertiveness_ceiling_bps: int
    missing_evidence: tuple[str, ...]
    reason_codes: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("as_of", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{name} must be timezone-aware when present")
        if (
            self.as_of is not None
            and self.evidence_cutoff_at is not None
            and self.evidence_cutoff_at > self.as_of
        ):
            raise ValueError("contradiction state cannot contain future evidence")
        for name in (
            "support_bps",
            "contradiction_bps",
            "data_quality_bps",
            "assertiveness_ceiling_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        for name in ("independent_group_count", "evidence_count"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative int")
        if (
            type(self.net_support_bps) is not int
            or not -10_000 <= self.net_support_bps <= 10_000
        ):
            raise ValueError("net_support_bps must be within -10000..10000")
        if self.missing_evidence != tuple(sorted(set(self.missing_evidence))):
            raise ValueError("missing_evidence must be unique and canonical")
        if not self.reason_codes:
            raise ValueError("contradiction state requires reason codes")
        if self.productive_authority:
            raise ValueError("contradiction map grants no productive authority")


def build_contradiction_state(
    evidence: tuple[ContradictionEvidence, ...],
    *,
    hypothesis_id: str,
    required_groups: tuple[str, ...],
) -> HypothesisContradictionState:
    """Aggregate support, contradiction and missing evidence at one causal instant."""

    if not hypothesis_id.strip():
        raise ValueError("hypothesis_id must be explicit")
    if required_groups != tuple(sorted(set(required_groups))):
        raise ValueError("required_groups must be unique and canonical")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != tuple(sorted(set(evidence_ids))):
        raise ValueError("contradiction evidence ids must be unique and canonical")

    rows = tuple(item for item in evidence if item.hypothesis_id == hypothesis_id)
    if not rows:
        return HypothesisContradictionState(
            hypothesis_id=hypothesis_id,
            as_of=None,
            evidence_cutoff_at=None,
            support_bps=0,
            contradiction_bps=0,
            net_support_bps=0,
            independent_group_count=0,
            evidence_count=0,
            data_quality_bps=0,
            assertiveness_ceiling_bps=0,
            missing_evidence=required_groups,
            reason_codes=("NO_EVIDENCE_UNKNOWN",),
        )

    as_of = rows[0].as_of
    if any(item.as_of != as_of for item in rows):
        raise ValueError("contradiction map evidence must share one causal as_of")
    cutoff = max(item.evidence_cutoff_at for item in rows)
    if cutoff > as_of:
        raise ValueError("contradiction map cannot aggregate future evidence")

    support = sum(item.support_bps for item in rows) // len(rows)
    contradiction = sum(item.contradiction_bps for item in rows) // len(rows)
    quality = sum(item.data_quality_bps for item in rows) // len(rows)
    groups = {item.independent_group for item in rows}
    missing = tuple(sorted(set(required_groups) - groups))

    missing_penalty = min(10_000, len(missing) * 1_500)
    conflict_penalty = min(10_000, contradiction)
    assertiveness = max(
        0,
        min(
            quality,
            10_000 - conflict_penalty,
            10_000 - missing_penalty,
        ),
    )

    reasons: list[str] = []
    if contradiction >= 6_000:
        reasons.append("CONTRADICTION_HIGH")
    if support >= 6_000:
        reasons.append("SUPPORT_HIGH")
    if missing:
        reasons.append("REQUIRED_EVIDENCE_MISSING")
    if abs(support - contradiction) <= 1_000:
        reasons.append("SUPPORT_CONTRADICTION_CONTESTED")
    if assertiveness <= 2_500:
        reasons.append("ASSERTIVENESS_REDUCED")
    if not reasons:
        reasons.append("EVIDENCE_BALANCE_RESOLVED")

    return HypothesisContradictionState(
        hypothesis_id=hypothesis_id,
        as_of=as_of,
        evidence_cutoff_at=cutoff,
        support_bps=support,
        contradiction_bps=contradiction,
        net_support_bps=support - contradiction,
        independent_group_count=len(groups),
        evidence_count=len(rows),
        data_quality_bps=quality,
        assertiveness_ceiling_bps=assertiveness,
        missing_evidence=missing,
        reason_codes=tuple(sorted(set(reasons))),
    )
