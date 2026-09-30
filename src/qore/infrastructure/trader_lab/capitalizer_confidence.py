"""Evidence-bound confidence and metacognition contracts for Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.trader_lab.capitalizer_contract import EvidenceStrength


class CapitalizerEvidenceSource(StrEnum):
    DEVELOPMENT_REPLAY = "DEVELOPMENT_REPLAY"
    WALK_FORWARD = "WALK_FORWARD"
    HOLDOUT = "HOLDOUT"
    SHADOW_EXECUTION = "SHADOW_EXECUTION"


class CapitalizerKnowledgeState(StrEnum):
    KNOWN = "KNOWN"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True, slots=True)
class CapitalizerEvidenceCalibration:
    """Confidence is a provenance-bound evidence class, never a fabricated percentage."""

    state_family_id: str
    source: CapitalizerEvidenceSource
    source_fingerprint: str
    observations: int
    mean_r: Decimal
    strength: EvidenceStrength

    def __post_init__(self) -> None:
        if not self.state_family_id:
            raise ValueError("state_family_id must be non-empty")
        if fullmatch(r"[0-9a-f]{64}", self.source_fingerprint) is None:
            raise ValueError("source_fingerprint must be canonical sha256")
        if self.observations < 0:
            raise ValueError("observations must be non-negative")
        if not isinstance(self.mean_r, Decimal) or not self.mean_r.is_finite():
            raise ValueError("mean_r must be finite")
        if self.observations == 0 and self.strength is not EvidenceStrength.UNKNOWN:
            raise ValueError("zero-observation calibration must be UNKNOWN")
        if self.observations > 0 and self.strength is EvidenceStrength.UNKNOWN:
            raise ValueError("observed calibration cannot claim UNKNOWN strength")


def assess_knowledge_state(
    *,
    calibration: CapitalizerEvidenceCalibration | None,
    contradictions: tuple[str, ...],
) -> CapitalizerKnowledgeState:
    """Expose what the brain knows instead of manufacturing certainty."""

    if contradictions:
        return CapitalizerKnowledgeState.CONFLICTED
    if calibration is None or calibration.strength is EvidenceStrength.UNKNOWN:
        return CapitalizerKnowledgeState.UNKNOWN
    if calibration.strength is EvidenceStrength.LOW:
        return CapitalizerKnowledgeState.PARTIAL
    return CapitalizerKnowledgeState.KNOWN
