"""MC-26 top-level Cognitive Arbitration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class CognitiveFacet(StrEnum):
    WORLD_MODELS = "WORLD_MODELS"
    SPECIALIST_DISAGREEMENT = "SPECIALIST_DISAGREEMENT"
    NEGATIVE_EVIDENCE = "NEGATIVE_EVIDENCE"
    UNCERTAINTY = "UNCERTAINTY"
    OOD_NOVELTY = "OOD_NOVELTY"
    TRAJECTORY_STATE = "TRAJECTORY_STATE"
    STABILITY = "STABILITY"
    CAUSAL_CONSISTENCY = "CAUSAL_CONSISTENCY"
    INFORMATION_GAPS = "INFORMATION_GAPS"


class SharedSituationState(StrEnum):
    COHERENT = "COHERENT"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True, slots=True)
class CognitiveFacetEvidence:
    facet: CognitiveFacet
    support_bps: int
    contradiction_bps: int
    uncertainty_bps: int
    critical_negative: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("support_bps", "contradiction_bps", "uncertainty_bps"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if not self.evidence_refs or self.evidence_refs != tuple(sorted(set(self.evidence_refs))):
            raise ValueError("cognitive facet evidence must be canonical")


@dataclass(frozen=True, slots=True)
class SharedSituation:
    situation_id: str
    state: SharedSituationState
    assertiveness_bps: int
    facets: tuple[CognitiveFacetEvidence, ...]
    critical_negative_preserved: bool
    information_gap_preserved: bool
    reason_codes: tuple[str, ...]
    trading_command: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False
    broker_authority: bool = False

    def __post_init__(self) -> None:
        if not self.situation_id:
            raise ValueError("Shared Situation requires identity")
        if type(self.assertiveness_bps) is not int or not 0 <= self.assertiveness_bps <= 10_000:
            raise ValueError("assertiveness_bps must be int within 0..10000")
        if {item.facet for item in self.facets} != set(CognitiveFacet):
            raise ValueError("cognitive arbitration requires all nine facets")
        if self.facets != tuple(sorted(self.facets, key=lambda item: item.facet.value)):
            raise ValueError("cognitive facets must be canonical")
        if not self.critical_negative_preserved or not self.information_gap_preserved:
            raise ValueError("negative evidence and information gaps must survive")
        if (
            self.trading_command
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
            or self.broker_authority
        ):
            raise ValueError("Shared Situation cannot carry downstream authority")

    def fingerprint(self) -> str:
        payload = {
            "situation_id": self.situation_id,
            "state": self.state.value,
            "assertiveness_bps": self.assertiveness_bps,
            "facets": tuple(
                {**asdict(item), "facet": item.facet.value}
                for item in self.facets
            ),
            "critical_negative_preserved": self.critical_negative_preserved,
            "information_gap_preserved": self.information_gap_preserved,
            "reason_codes": self.reason_codes,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def arbitrate_shared_situation(
    situation_id: str,
    facets: tuple[CognitiveFacetEvidence, ...],
) -> SharedSituation:
    ordered = tuple(sorted(facets, key=lambda item: item.facet.value))
    if {item.facet for item in ordered} != set(CognitiveFacet):
        raise ValueError("all cognitive facets are required")
    critical = any(item.critical_negative for item in ordered)
    gaps = next(item for item in ordered if item.facet is CognitiveFacet.INFORMATION_GAPS)
    stability = next(item for item in ordered if item.facet is CognitiveFacet.STABILITY)
    mean_support = sum(item.support_bps for item in ordered) // len(ordered)
    max_contradiction = max(item.contradiction_bps for item in ordered)
    max_uncertainty = max(item.uncertainty_bps for item in ordered)
    ceiling = max(0, 10_000 - max(max_contradiction, max_uncertainty))
    assertiveness = min(mean_support, ceiling)

    reasons = []
    if critical:
        state = SharedSituationState.CONTESTED
        assertiveness = min(assertiveness, 2_500)
        reasons.append("CRITICAL_NEGATIVE_EVIDENCE")
    elif gaps.uncertainty_bps >= 6_500 or gaps.contradiction_bps >= 6_500:
        state = SharedSituationState.INSUFFICIENT
        assertiveness = min(assertiveness, 2_000)
        reasons.append("MATERIAL_INFORMATION_GAPS")
    elif stability.contradiction_bps >= 8_000:
        state = SharedSituationState.DEGRADED
        assertiveness = min(assertiveness, 1_500)
        reasons.append("SYSTEM_STABILITY_DEGRADED")
    elif max_contradiction >= 5_000 or max_uncertainty >= 6_000:
        state = SharedSituationState.CONTESTED
        reasons.append("COGNITIVE_CONTEST")
    else:
        state = SharedSituationState.COHERENT
        reasons.append("MULTI_FACET_COHERENCE")

    return SharedSituation(
        situation_id=situation_id,
        state=state,
        assertiveness_bps=assertiveness,
        facets=ordered,
        critical_negative_preserved=True,
        information_gap_preserved=True,
        reason_codes=tuple(sorted(reasons)),
    )
